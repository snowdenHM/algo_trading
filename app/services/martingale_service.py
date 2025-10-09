"""
Martingale Trading Strategy Service
Refactored version of the original MartingaleBot to work with FastAPI and database
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.models import Strategy, TradingSession, Trade, TradeType, TradeStatus, SystemLog
from app.services.mt5_interface import mt5_interface, TradeRequest
from app.core.config import settings

logger = logging.getLogger(__name__)

class MartingaleService:
    """
    Martingale trading strategy implementation for FastAPI
    """
    
    def __init__(self):
        self.is_running = False
        self.current_session_id = None
        self.strategy_id = None
        
    async def run_strategy(self, strategy_id: int, session_id: int):
        """
        Main method to run the Martingale strategy
        """
        self.strategy_id = strategy_id
        self.current_session_id = session_id
        self.is_running = True
        
        logger.info(f"Starting Martingale strategy {strategy_id}, session {session_id}")
        
        db = SessionLocal()
        try:
            # Get strategy configuration
            strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return
            
            # Ensure MT5 connection
            if not mt5_interface.is_connected:
                await mt5_interface.connect()
            
            # Log strategy start
            await self._log_system_event(
                "INFO", "STRATEGY", f"Martingale strategy started for {strategy.symbol}", 
                session_id, db
            )
            
            # Initialize strategy state
            trades_in_sequence = []
            initial_trade_placed = False
            
            while self.is_running:
                try:
                    # Check if strategy is still active
                    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
                    if not strategy or strategy.status.value != "active":
                        logger.info("Strategy stopped or deactivated")
                        break
                    
                    # Get current price
                    price_info = await mt5_interface.get_price(strategy.symbol)
                    if not price_info:
                        logger.error(f"Could not get price for {strategy.symbol}")
                        await asyncio.sleep(5)
                        continue
                    
                    current_price = price_info.ask  # Use ask price for reference
                    
                    # Place initial trade if not done yet
                    if not initial_trade_placed:
                        await self._place_initial_trade(strategy, session_id, db)
                        initial_trade_placed = True
                        continue
                    
                    # Get current open trades for this session
                    open_trades = db.query(Trade).filter(
                        Trade.trading_session_id == session_id,
                        Trade.status == TradeStatus.OPEN
                    ).order_by(Trade.open_time.asc()).all()
                    
                    if not open_trades:
                        # No open trades, check if we should start a new sequence
                        await asyncio.sleep(10)
                        continue
                    
                    # Check if we need to place recovery trades
                    await self._check_and_place_recovery_trades(
                        strategy, session_id, open_trades, current_price, db
                    )
                    
                    # Check exit conditions
                    await self._check_exit_conditions(
                        strategy, session_id, open_trades, current_price, db
                    )
                    
                    # Update session statistics
                    await self._update_session_stats(session_id, db)
                    
                    # Wait before next iteration
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error in strategy loop: {e}")
                    await self._log_system_event(
                        "ERROR", "STRATEGY", f"Strategy error: {str(e)}", 
                        session_id, db
                    )
                    await asyncio.sleep(10)
            
        finally:
            # Mark strategy as stopped
            strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
            if strategy:
                strategy.status = "stopped"
            
            session = db.query(TradingSession).filter(TradingSession.id == session_id).first()
            if session and session.status == "active":
                session.status = "completed"
                session.end_time = datetime.now()
            
            db.commit()
            db.close()
            
            logger.info(f"Martingale strategy {strategy_id} stopped")
            self.is_running = False
    
    async def _place_initial_trade(self, strategy: Strategy, session_id: int, db: Session):
        """Place the initial trade"""
        
        # Default to BUY for initial trade (can be parameterized)
        trade_type = "buy"
        
        trade_request = TradeRequest(
            symbol=strategy.symbol,
            volume=strategy.initial_lot_size,
            trade_type=trade_type,
            comment=f"Martingale Initial - Session {session_id}"
        )
        
        # Create trade record
        db_trade = Trade(
            trading_session_id=session_id,
            symbol=strategy.symbol,
            trade_type=TradeType.BUY if trade_type == "buy" else TradeType.SELL,
            volume=strategy.initial_lot_size,
            open_price=0.0,
            status=TradeStatus.PENDING,
            comment=trade_request.comment,
            is_recovery_trade=False,
            recovery_level=0
        )
        
        db.add(db_trade)
        db.commit()
        db.refresh(db_trade)
        
        # Send to MT5
        result = await mt5_interface.send_market_order(trade_request)
        
        if result.success:
            db_trade.mt5_ticket = result.ticket
            db_trade.open_price = result.price or 0.0
            db_trade.status = TradeStatus.OPEN
            
            logger.info(f"Initial trade placed: {trade_type.upper()} {strategy.initial_lot_size} {strategy.symbol} @ {result.price}")
            
            await self._log_system_event(
                "INFO", "STRATEGY", 
                f"Initial trade: {trade_type.upper()} {strategy.initial_lot_size} {strategy.symbol} @ {result.price}",
                session_id, db
            )
        else:
            db_trade.status = TradeStatus.CANCELLED
            db_trade.comment = f"Failed: {result.error_message}"
            
            logger.error(f"Initial trade failed: {result.error_message}")
            
            await self._log_system_event(
                "ERROR", "STRATEGY", 
                f"Initial trade failed: {result.error_message}",
                session_id, db
            )
        
        db.commit()
    
    async def _check_and_place_recovery_trades(
        self, strategy: Strategy, session_id: int, open_trades: List[Trade], 
        current_price: float, db: Session
    ):
        """Check if we need to place recovery trades based on current loss"""
        
        if len(open_trades) >= strategy.max_trades:
            return  # Already at maximum trades
        
        # Calculate total unrealized P&L
        total_unrealized_pnl = self._calculate_unrealized_pnl(open_trades, current_price)
        
        # Check if we need a recovery trade (if we're in loss beyond recovery step)
        loss_in_pips = abs(total_unrealized_pnl) / strategy.initial_lot_size  # Simplified pip calculation
        
        if loss_in_pips >= strategy.recovery_step:
            recovery_level = len(open_trades)
            
            # Calculate recovery lot size (simple martingale: double the size)
            recovery_lot = strategy.initial_lot_size * (2 ** recovery_level)
            
            # Cap at max lot size
            if recovery_lot > strategy.max_lot_size:
                recovery_lot = strategy.max_lot_size
            
            # Determine recovery trade direction (opposite of majority losing trades)
            if total_unrealized_pnl < 0:
                # If in loss, determine counter direction
                buy_trades = [t for t in open_trades if t.trade_type == TradeType.BUY]
                sell_trades = [t for t in open_trades if t.trade_type == TradeType.SELL]
                
                # Place counter trade (simplified logic)
                if len(buy_trades) > len(sell_trades):
                    recovery_direction = "sell"
                else:
                    recovery_direction = "buy"
                
                await self._place_recovery_trade(
                    strategy, session_id, recovery_direction, recovery_lot, 
                    recovery_level, db
                )
    
    async def _place_recovery_trade(
        self, strategy: Strategy, session_id: int, trade_direction: str, 
        lot_size: float, recovery_level: int, db: Session
    ):
        """Place a recovery trade"""
        
        trade_request = TradeRequest(
            symbol=strategy.symbol,
            volume=lot_size,
            trade_type=trade_direction,
            comment=f"Recovery L{recovery_level} - Session {session_id}"
        )
        
        # Create trade record
        db_trade = Trade(
            trading_session_id=session_id,
            symbol=strategy.symbol,
            trade_type=TradeType.BUY if trade_direction == "buy" else TradeType.SELL,
            volume=lot_size,
            open_price=0.0,
            status=TradeStatus.PENDING,
            comment=trade_request.comment,
            is_recovery_trade=True,
            recovery_level=recovery_level
        )
        
        db.add(db_trade)
        db.commit()
        db.refresh(db_trade)
        
        # Send to MT5
        result = await mt5_interface.send_market_order(trade_request)
        
        if result.success:
            db_trade.mt5_ticket = result.ticket
            db_trade.open_price = result.price or 0.0
            db_trade.status = TradeStatus.OPEN
            
            logger.info(f"Recovery trade placed: {trade_direction.upper()} {lot_size} {strategy.symbol} @ {result.price}")
            
            await self._log_system_event(
                "INFO", "STRATEGY", 
                f"Recovery L{recovery_level}: {trade_direction.upper()} {lot_size} {strategy.symbol} @ {result.price}",
                session_id, db
            )
        else:
            db_trade.status = TradeStatus.CANCELLED
            db_trade.comment = f"Failed: {result.error_message}"
            
            logger.error(f"Recovery trade failed: {result.error_message}")
        
        db.commit()
    
    async def _check_exit_conditions(
        self, strategy: Strategy, session_id: int, open_trades: List[Trade], 
        current_price: float, db: Session
    ):
        """Check if we should close all positions based on exit conditions"""
        
        total_unrealized_pnl = self._calculate_unrealized_pnl(open_trades, current_price)
        
        # Check take profit condition
        if total_unrealized_pnl >= strategy.take_profit:
            await self._close_all_session_trades(session_id, "Take Profit Hit", db)
            return
        
        # Check stop loss condition
        if abs(total_unrealized_pnl) >= strategy.stop_loss:
            await self._close_all_session_trades(session_id, "Stop Loss Hit", db)
            return
        
        # Check max drawdown condition
        if abs(total_unrealized_pnl) >= strategy.max_drawdown:
            await self._close_all_session_trades(session_id, "Max Drawdown Reached", db)
            return
    
    def _calculate_unrealized_pnl(self, trades: List[Trade], current_price: float) -> float:
        """Calculate total unrealized P&L for open trades"""
        total_pnl = 0.0
        
        for trade in trades:
            if trade.trade_type == TradeType.BUY:
                pnl = (current_price - trade.open_price) * trade.volume
            else:
                pnl = (trade.open_price - current_price) * trade.volume
            
            # Multiply by point value (simplified - should be configurable per symbol)
            total_pnl += pnl * 10  # Assuming 10 currency units per point
        
        return total_pnl
    
    async def _close_all_session_trades(self, session_id: int, reason: str, db: Session):
        """Close all open trades for the session"""
        
        open_trades = db.query(Trade).filter(
            Trade.trading_session_id == session_id,
            Trade.status == TradeStatus.OPEN
        ).all()
        
        logger.info(f"Closing {len(open_trades)} trades for session {session_id}. Reason: {reason}")
        
        for trade in open_trades:
            if trade.mt5_ticket:
                result = await mt5_interface.close_position(trade.mt5_ticket, trade.symbol)
                
                if result.success:
                    trade.status = TradeStatus.CLOSED
                    trade.close_price = result.price
                    trade.close_time = datetime.now()
                    
                    # Calculate realized P&L
                    if trade.trade_type == TradeType.BUY:
                        trade.profit_loss = (result.price - trade.open_price) * trade.volume * 10
                    else:
                        trade.profit_loss = (trade.open_price - result.price) * trade.volume * 10
                else:
                    logger.error(f"Failed to close trade {trade.mt5_ticket}: {result.error_message}")
        
        db.commit()
        
        await self._log_system_event(
            "INFO", "STRATEGY", 
            f"Closed all trades for session {session_id}. Reason: {reason}",
            session_id, db
        )
    
    async def _update_session_stats(self, session_id: int, db: Session):
        """Update trading session statistics"""
        
        session = db.query(TradingSession).filter(TradingSession.id == session_id).first()
        if not session:
            return
        
        # Get all trades for this session
        all_trades = db.query(Trade).filter(Trade.trading_session_id == session_id).all()
        closed_trades = [t for t in all_trades if t.status == TradeStatus.CLOSED]
        
        session.total_trades = len(closed_trades)
        session.winning_trades = len([t for t in closed_trades if t.profit_loss > 0])
        session.losing_trades = len([t for t in closed_trades if t.profit_loss < 0])
        session.total_profit_loss = sum(t.profit_loss for t in closed_trades)
        
        db.commit()
    
    async def _log_system_event(
        self, level: str, component: str, message: str, 
        session_id: Optional[int], db: Session
    ):
        """Log system events to database"""
        
        log_entry = SystemLog(
            level=level,
            message=message,
            component=component,
            trading_session_id=session_id
        )
        
        db.add(log_entry)
        db.commit()
    
    def stop_strategy(self):
        """Stop the running strategy"""
        self.is_running = False
        logger.info("Strategy stop requested")