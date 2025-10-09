"""
Trading API endpoints for placing orders, managing positions, and real-time trading operations
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database.database import get_db
from app.services.mt5_interface import mt5_interface, TradeRequest
from app.models.models import Trade, TradingSession, TradeType, TradeStatus
from app.core.config import settings

router = APIRouter()

# Pydantic models for request/response
class TradeRequestModel(BaseModel):
    symbol: str
    volume: float
    trade_type: str  # 'buy' or 'sell'
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: Optional[str] = "FastAPI AlgoBot"
    trading_session_id: Optional[int] = None

class TradeResponseModel(BaseModel):
    id: int
    mt5_ticket: Optional[str]
    symbol: str
    trade_type: str
    volume: float
    open_price: Optional[float]
    status: str
    open_time: datetime
    comment: Optional[str]
    
    class Config:
        from_attributes = True

class PriceResponseModel(BaseModel):
    symbol: str
    bid: float
    ask: float
    spread: float
    timestamp: datetime

class PositionModel(BaseModel):
    ticket: str
    symbol: str
    type: str
    volume: float
    open_price: float
    current_price: float
    profit: float
    open_time: datetime

class MT5ConnectionRequest(BaseModel):
    account_id: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    mt5_path: Optional[str] = None

@router.post("/connect", summary="Connect to MetaTrader 5")
async def connect_mt5(request: Optional[MT5ConnectionRequest] = None):
    """Connect to MetaTrader 5 platform"""
    if request:
        success = await mt5_interface.connect(
            account_id=request.account_id,
            password=request.password,
            server=request.server,
            mt5_path=request.mt5_path
        )
    else:
        success = await mt5_interface.connect()
    
    if success:
        return {
            "status": "connected",
            "platform": mt5_interface.current_platform,
            "mock_mode": mt5_interface.mock_mode,
            "message": "Connected to MT5" if not mt5_interface.mock_mode else "Connected in mock mode"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to MT5")

@router.post("/disconnect", summary="Disconnect from MetaTrader 5")
async def disconnect_mt5():
    """Disconnect from MetaTrader 5 platform"""
    await mt5_interface.disconnect()
    return {"status": "disconnected", "message": "Disconnected from MT5"}

@router.get("/connection-status", summary="Check MT5 connection status")
async def get_connection_status():
    """Get current MT5 connection status"""
    return {
        "connected": mt5_interface.is_connected,
        "mock_mode": mt5_interface.mock_mode,
        "platform": mt5_interface.current_platform,
        "mt5_available": mt5_interface.is_mt5_available
    }

@router.get("/price/{symbol}", response_model=PriceResponseModel, summary="Get current price")
async def get_price(symbol: str):
    """Get current bid/ask price for a symbol"""
    price_info = await mt5_interface.get_price(symbol.upper())
    
    if not price_info:
        raise HTTPException(status_code=404, detail=f"Could not get price for {symbol}")
    
    return PriceResponseModel(
        symbol=price_info.symbol,
        bid=price_info.bid,
        ask=price_info.ask,
        spread=price_info.spread,
        timestamp=price_info.timestamp
    )

@router.post("/orders", response_model=TradeResponseModel, summary="Place a market order")
async def place_order(
    trade_request: TradeRequestModel,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Place a new market order"""
    
    # Validate trade type
    if trade_request.trade_type.lower() not in ['buy', 'sell']:
        raise HTTPException(status_code=400, detail="Trade type must be 'buy' or 'sell'")
    
    # Create trade record in database
    db_trade = Trade(
        trading_session_id=trade_request.trading_session_id,
        symbol=trade_request.symbol.upper(),
        trade_type=TradeType.BUY if trade_request.trade_type.lower() == 'buy' else TradeType.SELL,
        volume=trade_request.volume,
        open_price=0.0,  # Will be updated after order execution
        status=TradeStatus.PENDING,
        stop_loss=trade_request.stop_loss,
        take_profit=trade_request.take_profit,
        comment=trade_request.comment
    )
    
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    
    # Send order to MT5
    mt5_request = TradeRequest(
        symbol=trade_request.symbol.upper(),
        volume=trade_request.volume,
        trade_type=trade_request.trade_type.lower(),
        stop_loss=trade_request.stop_loss,
        take_profit=trade_request.take_profit,
        comment=trade_request.comment or "FastAPI AlgoBot"
    )
    
    result = await mt5_interface.send_market_order(mt5_request)
    
    # Update trade record with result
    if result.success:
        db_trade.mt5_ticket = result.ticket
        db_trade.open_price = result.price or 0.0
        db_trade.status = TradeStatus.OPEN
    else:
        db_trade.status = TradeStatus.CANCELLED
        db_trade.comment = f"Failed: {result.error_message}"
    
    db.commit()
    db.refresh(db_trade)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=f"Order failed: {result.error_message}")
    
    return TradeResponseModel(
        id=db_trade.id,
        mt5_ticket=db_trade.mt5_ticket,
        symbol=db_trade.symbol,
        trade_type=db_trade.trade_type.value,
        volume=db_trade.volume,
        open_price=db_trade.open_price,
        status=db_trade.status.value,
        open_time=db_trade.open_time,
        comment=db_trade.comment
    )

@router.get("/positions", response_model=List[PositionModel], summary="Get open positions")
async def get_positions(symbol: Optional[str] = None):
    """Get all open positions or positions for a specific symbol"""
    positions = await mt5_interface.get_positions(symbol.upper() if symbol else None)
    
    return [
        PositionModel(
            ticket=pos["ticket"],
            symbol=pos["symbol"],
            type=pos["type"],
            volume=pos["volume"],
            open_price=pos["open_price"],
            current_price=pos["current_price"],
            profit=pos["profit"],
            open_time=pos["open_time"]
        )
        for pos in positions
    ]

@router.delete("/positions/{ticket}", summary="Close a specific position")
async def close_position(ticket: str, db: Session = Depends(get_db)):
    """Close a specific position by ticket number"""
    
    # Find the trade in database
    db_trade = db.query(Trade).filter(Trade.mt5_ticket == ticket).first()
    if not db_trade:
        raise HTTPException(status_code=404, detail=f"Trade with ticket {ticket} not found")
    
    # Close position in MT5
    result = await mt5_interface.close_position(ticket, db_trade.symbol)
    
    if result.success:
        # Update trade record
        db_trade.status = TradeStatus.CLOSED
        db_trade.close_price = result.price
        db_trade.close_time = datetime.now()
        
        # Calculate P&L (simplified)
        if db_trade.trade_type == TradeType.BUY:
            db_trade.profit_loss = (result.price - db_trade.open_price) * db_trade.volume
        else:
            db_trade.profit_loss = (db_trade.open_price - result.price) * db_trade.volume
        
        db.commit()
        
        return {"status": "success", "message": f"Position {ticket} closed successfully"}
    else:
        raise HTTPException(status_code=400, detail=f"Failed to close position: {result.error_message}")

@router.delete("/positions", summary="Close all positions")
async def close_all_positions(symbol: Optional[str] = None, db: Session = Depends(get_db)):
    """Close all open positions or all positions for a specific symbol"""
    
    results = await mt5_interface.close_all_positions(symbol.upper() if symbol else None)
    
    success_count = sum(1 for r in results if r.success)
    total_count = len(results)
    
    # Update database records for closed positions
    if symbol:
        open_trades = db.query(Trade).filter(
            Trade.symbol == symbol.upper(),
            Trade.status == TradeStatus.OPEN
        ).all()
    else:
        open_trades = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).all()
    
    for trade in open_trades:
        trade.status = TradeStatus.CLOSED
        trade.close_time = datetime.now()
    
    db.commit()
    
    return {
        "status": "completed",
        "message": f"Closed {success_count}/{total_count} positions",
        "symbol": symbol,
        "results": [
            {
                "ticket": r.ticket,
                "success": r.success,
                "error": r.error_message if not r.success else None
            }
            for r in results
        ]
    }

@router.get("/trades", response_model=List[TradeResponseModel], summary="Get trade history")
async def get_trades(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get trade history with optional filters"""
    
    query = db.query(Trade)
    
    if symbol:
        query = query.filter(Trade.symbol == symbol.upper())
    
    if status:
        try:
            status_enum = TradeStatus(status.lower())
            query = query.filter(Trade.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    trades = query.order_by(Trade.open_time.desc()).limit(limit).all()
    
    return [
        TradeResponseModel(
            id=trade.id,
            mt5_ticket=trade.mt5_ticket,
            symbol=trade.symbol,
            trade_type=trade.trade_type.value,
            volume=trade.volume,
            open_price=trade.open_price,
            status=trade.status.value,
            open_time=trade.open_time,
            comment=trade.comment
        )
        for trade in trades
    ]