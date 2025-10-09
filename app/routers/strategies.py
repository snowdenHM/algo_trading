"""
Strategy management endpoints for creating, managing, and controlling trading strategies
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.database.database import get_db
from app.models.models import Strategy, TradingSession, StrategyStatus
from app.services.martingale_service import MartingaleService
from app.core.config import settings

router = APIRouter()

# Pydantic models
class StrategyCreateModel(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_type: str = "martingale"
    symbol: str
    initial_lot_size: float
    max_lot_size: float = 1.0
    recovery_step: float = 50.0
    take_profit: float = 100.0
    stop_loss: float = 500.0
    max_trades: int = 5
    max_drawdown: float = 1000.0
    risk_per_trade: float = 2.0

class StrategyResponseModel(BaseModel):
    id: int
    name: str
    description: Optional[str]
    strategy_type: str
    status: str
    symbol: str
    initial_lot_size: float
    max_lot_size: float
    recovery_step: float
    take_profit: float
    stop_loss: float
    max_trades: int
    max_drawdown: float
    risk_per_trade: float
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class StrategyUpdateModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    symbol: Optional[str] = None
    initial_lot_size: Optional[float] = None
    max_lot_size: Optional[float] = None
    recovery_step: Optional[float] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    max_trades: Optional[int] = None
    max_drawdown: Optional[float] = None
    risk_per_trade: Optional[float] = None

class TradingSessionModel(BaseModel):
    id: int
    strategy_id: int
    session_name: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_profit_loss: float
    max_drawdown_reached: float
    
    class Config:
        from_attributes = True

@router.post("/", response_model=StrategyResponseModel, summary="Create a new strategy")
async def create_strategy(strategy: StrategyCreateModel, db: Session = Depends(get_db)):
    """Create a new trading strategy"""
    
    # Check if strategy name already exists
    existing_strategy = db.query(Strategy).filter(Strategy.name == strategy.name).first()
    if existing_strategy:
        raise HTTPException(status_code=400, detail="Strategy name already exists")
    
    # Create new strategy
    db_strategy = Strategy(
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type,
        symbol=strategy.symbol.upper(),
        initial_lot_size=strategy.initial_lot_size,
        max_lot_size=strategy.max_lot_size,
        recovery_step=strategy.recovery_step,
        take_profit=strategy.take_profit,
        stop_loss=strategy.stop_loss,
        max_trades=strategy.max_trades,
        max_drawdown=strategy.max_drawdown,
        risk_per_trade=strategy.risk_per_trade,
        status=StrategyStatus.INACTIVE
    )
    
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    
    return StrategyResponseModel(
        id=db_strategy.id,
        name=db_strategy.name,
        description=db_strategy.description,
        strategy_type=db_strategy.strategy_type,
        status=db_strategy.status.value,
        symbol=db_strategy.symbol,
        initial_lot_size=db_strategy.initial_lot_size,
        max_lot_size=db_strategy.max_lot_size,
        recovery_step=db_strategy.recovery_step,
        take_profit=db_strategy.take_profit,
        stop_loss=db_strategy.stop_loss,
        max_trades=db_strategy.max_trades,
        max_drawdown=db_strategy.max_drawdown,
        risk_per_trade=db_strategy.risk_per_trade,
        created_at=db_strategy.created_at,
        updated_at=db_strategy.updated_at
    )

@router.get("/", response_model=List[StrategyResponseModel], summary="Get all strategies")
async def get_strategies(
    status: Optional[str] = None,
    strategy_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all strategies with optional filtering"""
    
    query = db.query(Strategy)
    
    if status:
        try:
            status_enum = StrategyStatus(status.lower())
            query = query.filter(Strategy.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if strategy_type:
        query = query.filter(Strategy.strategy_type == strategy_type.lower())
    
    strategies = query.all()
    
    return [
        StrategyResponseModel(
            id=s.id,
            name=s.name,
            description=s.description,
            strategy_type=s.strategy_type,
            status=s.status.value,
            symbol=s.symbol,
            initial_lot_size=s.initial_lot_size,
            max_lot_size=s.max_lot_size,
            recovery_step=s.recovery_step,
            take_profit=s.take_profit,
            stop_loss=s.stop_loss,
            max_trades=s.max_trades,
            max_drawdown=s.max_drawdown,
            risk_per_trade=s.risk_per_trade,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in strategies
    ]

@router.get("/{strategy_id}", response_model=StrategyResponseModel, summary="Get strategy by ID")
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Get a specific strategy by ID"""
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return StrategyResponseModel(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type,
        status=strategy.status.value,
        symbol=strategy.symbol,
        initial_lot_size=strategy.initial_lot_size,
        max_lot_size=strategy.max_lot_size,
        recovery_step=strategy.recovery_step,
        take_profit=strategy.take_profit,
        stop_loss=strategy.stop_loss,
        max_trades=strategy.max_trades,
        max_drawdown=strategy.max_drawdown,
        risk_per_trade=strategy.risk_per_trade,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at
    )

@router.put("/{strategy_id}", response_model=StrategyResponseModel, summary="Update strategy")
async def update_strategy(
    strategy_id: int, 
    strategy_update: StrategyUpdateModel, 
    db: Session = Depends(get_db)
):
    """Update an existing strategy"""
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Check if strategy is active
    if strategy.status == StrategyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot update active strategy. Stop it first.")
    
    # Update fields
    update_data = strategy_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(strategy, field):
            if field == 'symbol' and value:
                setattr(strategy, field, value.upper())
            else:
                setattr(strategy, field, value)
    
    strategy.updated_at = datetime.now()
    
    db.commit()
    db.refresh(strategy)
    
    return StrategyResponseModel(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type,
        status=strategy.status.value,
        symbol=strategy.symbol,
        initial_lot_size=strategy.initial_lot_size,
        max_lot_size=strategy.max_lot_size,
        recovery_step=strategy.recovery_step,
        take_profit=strategy.take_profit,
        stop_loss=strategy.stop_loss,
        max_trades=strategy.max_trades,
        max_drawdown=strategy.max_drawdown,
        risk_per_trade=strategy.risk_per_trade,
        created_at=strategy.created_at,
        updated_at=strategy.updated_at
    )

@router.delete("/{strategy_id}", summary="Delete strategy")
async def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Delete a strategy"""
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy.status == StrategyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot delete active strategy. Stop it first.")
    
    db.delete(strategy)
    db.commit()
    
    return {"message": f"Strategy '{strategy.name}' deleted successfully"}

@router.post("/{strategy_id}/start", summary="Start strategy")
async def start_strategy(
    strategy_id: int, 
    session_name: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Start a trading strategy"""
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy.status == StrategyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Strategy is already active")
    
    # Create new trading session
    session = TradingSession(
        strategy_id=strategy_id,
        session_name=session_name or f"{strategy.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        status="active"
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Update strategy status
    strategy.status = StrategyStatus.ACTIVE
    db.commit()
    
    # Start strategy in background
    if strategy.strategy_type == "martingale":
        martingale_service = MartingaleService()
        background_tasks.add_task(
            martingale_service.run_strategy,
            strategy_id=strategy_id,
            session_id=session.id
        )
    
    return {
        "message": f"Strategy '{strategy.name}' started successfully",
        "session_id": session.id,
        "session_name": session.session_name
    }

@router.post("/{strategy_id}/stop", summary="Stop strategy")
async def stop_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Stop a running strategy"""
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy.status != StrategyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Strategy is not active")
    
    # Update strategy status
    strategy.status = StrategyStatus.STOPPED
    
    # Close active session
    active_session = db.query(TradingSession).filter(
        TradingSession.strategy_id == strategy_id,
        TradingSession.status == "active"
    ).first()
    
    if active_session:
        active_session.status = "stopped"
        active_session.end_time = datetime.now()
    
    db.commit()
    
    return {"message": f"Strategy '{strategy.name}' stopped successfully"}

@router.get("/{strategy_id}/sessions", response_model=List[TradingSessionModel], summary="Get strategy sessions")
async def get_strategy_sessions(strategy_id: int, db: Session = Depends(get_db)):
    """Get all trading sessions for a strategy"""
    
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    sessions = db.query(TradingSession).filter(
        TradingSession.strategy_id == strategy_id
    ).order_by(TradingSession.start_time.desc()).all()
    
    return [
        TradingSessionModel(
            id=session.id,
            strategy_id=session.strategy_id,
            session_name=session.session_name,
            start_time=session.start_time,
            end_time=session.end_time,
            status=session.status,
            total_trades=session.total_trades,
            winning_trades=session.winning_trades,
            losing_trades=session.losing_trades,
            total_profit_loss=session.total_profit_loss,
            max_drawdown_reached=session.max_drawdown_reached
        )
        for session in sessions
    ]