from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.database import Base
import enum

class TradeType(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class TradeStatus(enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class StrategyStatus(enum.Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"

class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    strategy_type = Column(String, nullable=False)  # e.g., "martingale", "grid", etc.
    status = Column(Enum(StrategyStatus), default=StrategyStatus.INACTIVE)
    
    # Strategy Parameters (JSON-like storage)
    symbol = Column(String, nullable=False)
    initial_lot_size = Column(Float, nullable=False)
    max_lot_size = Column(Float, nullable=False, default=1.0)
    recovery_step = Column(Float, nullable=False, default=50.0)  # in pips
    take_profit = Column(Float, nullable=False, default=100.0)  # in pips
    stop_loss = Column(Float, nullable=False, default=500.0)  # in pips
    max_trades = Column(Integer, default=5)
    
    # Risk Management
    max_drawdown = Column(Float, nullable=False, default=1000.0)  # in currency
    risk_per_trade = Column(Float, default=2.0)  # percentage
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    trading_sessions = relationship("TradingSession", back_populates="strategy")

class TradingSession(Base):
    __tablename__ = "trading_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    
    # Session Info
    session_name = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="active")  # active, stopped, completed
    
    # Session Statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_profit_loss = Column(Float, default=0.0)
    max_drawdown_reached = Column(Float, default=0.0)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="trading_sessions")
    trades = relationship("Trade", back_populates="trading_session")

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trading_session_id = Column(Integer, ForeignKey("trading_sessions.id"), nullable=False)
    
    # MT5 Trade Info
    mt5_ticket = Column(String, unique=True, nullable=True)  # MT5 position ticket
    symbol = Column(String, nullable=False)
    trade_type = Column(Enum(TradeType), nullable=False)
    
    # Trade Details
    volume = Column(Float, nullable=False)  # lot size
    open_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=True)
    
    # Timing
    open_time = Column(DateTime(timezone=True), server_default=func.now())
    close_time = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING)
    
    # P&L
    profit_loss = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    
    # Risk Management
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    
    # Additional Info
    comment = Column(String, nullable=True)
    magic_number = Column(Integer, default=123456)
    
    # Recovery Trade Info
    is_recovery_trade = Column(Boolean, default=False)
    recovery_level = Column(Integer, default=0)  # 0 = initial trade, 1+ = recovery levels
    
    # Relationships
    trading_session = relationship("TradingSession", back_populates="trades")

class MarketData(Base):
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    
    # Price Data
    bid = Column(Float, nullable=False)
    ask = Column(Float, nullable=False)
    spread = Column(Float, nullable=False)
    
    # Volume and Time
    volume = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Additional Market Info
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    
class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String, nullable=False)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    component = Column(String, nullable=False)  # MT5_INTERFACE, STRATEGY, API, etc.
    
    # Optional References
    trading_session_id = Column(Integer, ForeignKey("trading_sessions.id"), nullable=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Additional Context (JSON-like)
    extra_data = Column(Text, nullable=True)  # JSON string for additional context