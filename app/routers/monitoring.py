"""
Monitoring and analytics endpoints for tracking trades, performance, and system status
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database.database import get_db
from app.models.models import Trade, TradingSession, Strategy, TradeStatus, MarketData, SystemLog
from app.services.mt5_interface import mt5_interface

router = APIRouter()

# Pydantic models
class PerformanceStatsModel(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit_loss: float
    average_profit: float
    average_loss: float
    max_drawdown: float
    profit_factor: float

class SymbolStatsModel(BaseModel):
    symbol: str
    total_trades: int
    total_profit_loss: float
    win_rate: float
    active_positions: int

class SessionStatsModel(BaseModel):
    session_id: int
    session_name: str
    strategy_name: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    performance: PerformanceStatsModel

class SystemStatusModel(BaseModel):
    mt5_connected: bool
    mt5_mock_mode: bool
    active_strategies: int
    active_sessions: int
    total_open_positions: int
    system_uptime: str

class LogEntryModel(BaseModel):
    id: int
    level: str
    message: str
    component: str
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/system-status", response_model=SystemStatusModel, summary="Get system status")
async def get_system_status(db: Session = Depends(get_db)):
    """Get overall system status and health"""
    
    # Count active strategies
    active_strategies = db.query(Strategy).filter(
        Strategy.status == "active"
    ).count()
    
    # Count active sessions
    active_sessions = db.query(TradingSession).filter(
        TradingSession.status == "active"
    ).count()
    
    # Get open positions count
    positions = await mt5_interface.get_positions()
    open_positions_count = len(positions)
    
    return SystemStatusModel(
        mt5_connected=mt5_interface.is_connected,
        mt5_mock_mode=mt5_interface.mock_mode,
        active_strategies=active_strategies,
        active_sessions=active_sessions,
        total_open_positions=open_positions_count,
        system_uptime="Not implemented"  # Could implement actual uptime tracking
    )

@router.get("/performance/overall", response_model=PerformanceStatsModel, summary="Get overall performance")
async def get_overall_performance(
    days: Optional[int] = 30,
    db: Session = Depends(get_db)
):
    """Get overall trading performance statistics"""
    
    # Calculate date filter
    if days:
        start_date = datetime.now() - timedelta(days=days)
        trades_query = db.query(Trade).filter(Trade.open_time >= start_date)
    else:
        trades_query = db.query(Trade)
    
    # Get closed trades only
    closed_trades = trades_query.filter(Trade.status == TradeStatus.CLOSED).all()
    
    if not closed_trades:
        return PerformanceStatsModel(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_profit_loss=0.0,
            average_profit=0.0,
            average_loss=0.0,
            max_drawdown=0.0,
            profit_factor=0.0
        )
    
    # Calculate statistics
    total_trades = len(closed_trades)
    winning_trades = len([t for t in closed_trades if t.profit_loss > 0])
    losing_trades = len([t for t in closed_trades if t.profit_loss < 0])
    
    total_profit_loss = sum(t.profit_loss for t in closed_trades)
    
    profits = [t.profit_loss for t in closed_trades if t.profit_loss > 0]
    losses = [t.profit_loss for t in closed_trades if t.profit_loss < 0]
    
    average_profit = sum(profits) / len(profits) if profits else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    # Calculate profit factor
    total_profits = sum(profits)
    total_losses = abs(sum(losses))
    profit_factor = total_profits / total_losses if total_losses > 0 else 0.0
    
    # Calculate max drawdown (simplified)
    running_total = 0
    peak = 0
    max_drawdown = 0
    
    for trade in closed_trades:
        running_total += trade.profit_loss
        if running_total > peak:
            peak = running_total
        drawdown = peak - running_total
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return PerformanceStatsModel(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=round(win_rate, 2),
        total_profit_loss=round(total_profit_loss, 2),
        average_profit=round(average_profit, 2),
        average_loss=round(average_loss, 2),
        max_drawdown=round(max_drawdown, 2),
        profit_factor=round(profit_factor, 2)
    )

@router.get("/performance/by-symbol", response_model=List[SymbolStatsModel], summary="Get performance by symbol")
async def get_performance_by_symbol(
    days: Optional[int] = 30,
    db: Session = Depends(get_db)
):
    """Get trading performance grouped by symbol"""
    
    # Calculate date filter
    if days:
        start_date = datetime.now() - timedelta(days=days)
        query = db.query(Trade).filter(Trade.open_time >= start_date)
    else:
        query = db.query(Trade)
    
    # Get stats by symbol
    symbol_stats = query.filter(Trade.status == TradeStatus.CLOSED).group_by(Trade.symbol).all()
    
    results = []
    for symbol in set(trade.symbol for trade in symbol_stats):
        symbol_trades = [t for t in symbol_stats if t.symbol == symbol]
        
        total_trades = len(symbol_trades)
        winning_trades = len([t for t in symbol_trades if t.profit_loss > 0])
        total_profit_loss = sum(t.profit_loss for t in symbol_trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # Count active positions for this symbol
        active_positions = db.query(Trade).filter(
            Trade.symbol == symbol,
            Trade.status == TradeStatus.OPEN
        ).count()
        
        results.append(SymbolStatsModel(
            symbol=symbol,
            total_trades=total_trades,
            total_profit_loss=round(total_profit_loss, 2),
            win_rate=round(win_rate, 2),
            active_positions=active_positions
        ))
    
    return sorted(results, key=lambda x: x.total_profit_loss, reverse=True)

@router.get("/sessions/{session_id}/performance", response_model=SessionStatsModel, summary="Get session performance")
async def get_session_performance(session_id: int, db: Session = Depends(get_db)):
    """Get performance statistics for a specific trading session"""
    
    session = db.query(TradingSession).filter(TradingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Trading session not found")
    
    # Get trades for this session
    trades = db.query(Trade).filter(Trade.trading_session_id == session_id).all()
    closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED]
    
    # Calculate performance stats
    total_trades = len(closed_trades)
    winning_trades = len([t for t in closed_trades if t.profit_loss > 0])
    losing_trades = len([t for t in closed_trades if t.profit_loss < 0])
    
    total_profit_loss = sum(t.profit_loss for t in closed_trades)
    
    profits = [t.profit_loss for t in closed_trades if t.profit_loss > 0]
    losses = [t.profit_loss for t in closed_trades if t.profit_loss < 0]
    
    average_profit = sum(profits) / len(profits) if profits else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    total_profits = sum(profits)
    total_losses = abs(sum(losses))
    profit_factor = total_profits / total_losses if total_losses > 0 else 0.0
    
    performance = PerformanceStatsModel(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=round(win_rate, 2),
        total_profit_loss=round(total_profit_loss, 2),
        average_profit=round(average_profit, 2),
        average_loss=round(average_loss, 2),
        max_drawdown=0.0,  # Could implement session-specific drawdown
        profit_factor=round(profit_factor, 2)
    )
    
    return SessionStatsModel(
        session_id=session.id,
        session_name=session.session_name,
        strategy_name=session.strategy.name,
        start_time=session.start_time,
        end_time=session.end_time,
        status=session.status,
        performance=performance
    )

@router.get("/logs", response_model=List[LogEntryModel], summary="Get system logs")
async def get_system_logs(
    level: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get system logs with optional filtering"""
    
    query = db.query(SystemLog)
    
    if level:
        query = query.filter(SystemLog.level == level.upper())
    
    if component:
        query = query.filter(SystemLog.component == component.upper())
    
    logs = query.order_by(SystemLog.created_at.desc()).limit(limit).all()
    
    return [
        LogEntryModel(
            id=log.id,
            level=log.level,
            message=log.message,
            component=log.component,
            created_at=log.created_at
        )
        for log in logs
    ]

@router.get("/market-data/{symbol}", summary="Get recent market data")
async def get_market_data(
    symbol: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get recent market data for a symbol"""
    
    start_time = datetime.now() - timedelta(hours=hours)
    
    market_data = db.query(MarketData).filter(
        MarketData.symbol == symbol.upper(),
        MarketData.timestamp >= start_time
    ).order_by(MarketData.timestamp.desc()).all()
    
    return [
        {
            "symbol": data.symbol,
            "bid": data.bid,
            "ask": data.ask,
            "spread": data.spread,
            "timestamp": data.timestamp
        }
        for data in market_data
    ]

@router.get("/active-trades", summary="Get all active trades")
async def get_active_trades(db: Session = Depends(get_db)):
    """Get all currently active trades"""
    
    active_trades = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).all()
    
    return [
        {
            "id": trade.id,
            "mt5_ticket": trade.mt5_ticket,
            "symbol": trade.symbol,
            "trade_type": trade.trade_type.value,
            "volume": trade.volume,
            "open_price": trade.open_price,
            "open_time": trade.open_time,
            "unrealized_pnl": 0.0,  # Could calculate real-time P&L
            "session_id": trade.trading_session_id
        }
        for trade in active_trades
    ]