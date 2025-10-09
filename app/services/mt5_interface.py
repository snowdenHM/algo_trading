"""
Cross-platform MetaTrader 5 Interface
Handles MT5 connections and trading operations with proper error handling for different operating systems
"""

import platform
import logging
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
import asyncio
from dataclasses import dataclass

# Try to import MT5, but handle gracefully if not available
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class TradeRequest:
    symbol: str
    volume: float
    trade_type: str  # 'buy' or 'sell'
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: str = "AlgoTrading Bot"
    magic: int = 123456

@dataclass
class TradeResult:
    success: bool
    ticket: Optional[str] = None
    price: Optional[float] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    retcode: Optional[int] = None

@dataclass
class PriceInfo:
    symbol: str
    bid: float
    ask: float
    spread: float
    timestamp: datetime

class CrossPlatformMT5Interface:
    """
    Cross-platform MT5 interface that works on Windows, macOS, and Linux
    """
    
    def __init__(self):
        self.is_connected = False
        self.is_mt5_available = MT5_AVAILABLE
        self.current_platform = platform.system()
        self.mock_mode = False
        
        # Mock prices for testing on non-Windows systems
        self._mock_prices = {
            "BTCUSD": {"bid": 43000.0, "ask": 43010.0},
            "EURUSD": {"bid": 1.0850, "ask": 1.0852},
            "GBPUSD": {"bid": 1.2650, "ask": 1.2652},
            "USDJPY": {"bid": 149.50, "ask": 149.52},
            "AUDUSD": {"bid": 0.6720, "ask": 0.6722},
            "USDCAD": {"bid": 1.3580, "ask": 1.3582},
            "NZDUSD": {"bid": 0.6120, "ask": 0.6122},
            "USDCHF": {"bid": 0.8950, "ask": 0.8952},
        }
        
        logger.info(f"MT5 Interface initialized on {self.current_platform}")
        logger.info(f"MT5 Python package available: {self.is_mt5_available}")
        
        # Try to auto-connect to MT5 if available
        if self.is_mt5_available:
            # Attempt automatic connection on startup
            asyncio.create_task(self._auto_connect())
        else:
            logger.warning("MT5 package not available - will use mock mode when connected")
    
    async def _auto_connect(self):
        """Automatically attempt to connect to MT5 on startup"""
        try:
            logger.info("Attempting automatic MT5 connection...")
            success = await self.connect()
            if success:
                logger.info("Successfully auto-connected to MT5")
            else:
                logger.warning("Auto-connection failed, will require manual connection")
        except Exception as e:
            logger.error(f"Auto-connection error: {e}")
    
    async def connect(
        self, 
        account_id: Optional[int] = None, 
        password: Optional[str] = None, 
        server: Optional[str] = None,
        mt5_path: Optional[str] = None
    ) -> bool:
        """
        Connect to MetaTrader 5
        Falls back to mock mode on non-Windows systems or when MT5 is not available
        """
        
        # Use settings values as defaults
        account_id = account_id or settings.mt5_account_id
        password = password or settings.mt5_password
        server = server or settings.mt5_server
        mt5_path = mt5_path or settings.mt5_path
        
        if not self.is_mt5_available:
            logger.warning("MT5 Python package not available. Using mock mode.")
            self.mock_mode = True
            self.is_connected = True
            return True
        
        logger.info(f"Attempting MT5 connection on {self.current_platform}...")
        
        try:
            # Initialize MT5
            if mt5_path:
                if not mt5.initialize(path=mt5_path):
                    error = mt5.last_error()
                    logger.error(f"MT5 initialize failed: {error}")
                    logger.warning("MT5 initialization failed, falling back to mock mode")
                    self.mock_mode = True
                    self.is_connected = True
                    return True
            else:
                if not mt5.initialize():
                    error = mt5.last_error()
                    logger.error(f"MT5 initialize failed: {error}")
                    logger.warning("MT5 initialization failed, falling back to mock mode")
                    self.mock_mode = True
                    self.is_connected = True
                    return True
            
            # Login if credentials provided
            if account_id and password and server:
                authorized = mt5.login(login=account_id, password=password, server=server)
                if not authorized:
                    error = mt5.last_error()
                    logger.error(f"MT5 login failed: {error}")
                    mt5.shutdown()
                    logger.warning("MT5 login failed, falling back to mock mode")
                    self.mock_mode = True
                    self.is_connected = True
                    return True
                    
                logger.info(f"Successfully connected to MT5 account: {account_id}")
            else:
                logger.info("Connected to MT5 without login (using current account)")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Exception during MT5 connection: {e}")
            logger.warning("Falling back to mock mode")
            self.mock_mode = True
            self.is_connected = True
            return True
    
    async def disconnect(self) -> None:
        """Disconnect from MT5"""
        if self.mock_mode:
            logger.info("Disconnecting from mock MT5")
            self.is_connected = False
            return
        
        if self.is_mt5_available and mt5:
            mt5.shutdown()
            logger.info("Disconnected from MT5")
        
        self.is_connected = False
    
    async def get_price(self, symbol: str) -> Optional[PriceInfo]:
        """Get current price for a symbol"""
        if not self.is_connected:
            logger.error("Not connected to MT5")
            return None
        
        if self.mock_mode:
            return self._get_mock_price(symbol)
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Failed to get tick for {symbol}")
                return None
            
            return PriceInfo(
                symbol=symbol,
                bid=tick.bid,
                ask=tick.ask,
                spread=tick.ask - tick.bid,
                timestamp=datetime.fromtimestamp(tick.time)
            )
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def _get_mock_price(self, symbol: str) -> PriceInfo:
        """Get mock price for testing"""
        if symbol in self._mock_prices:
            mock_data = self._mock_prices[symbol]
            return PriceInfo(
                symbol=symbol,
                bid=mock_data["bid"],
                ask=mock_data["ask"],
                spread=mock_data["ask"] - mock_data["bid"],
                timestamp=datetime.now()
            )
        else:
            # Generate mock price for unknown symbols
            return PriceInfo(
                symbol=symbol,
                bid=1.0000,
                ask=1.0002,
                spread=0.0002,
                timestamp=datetime.now()
            )
    
    async def send_market_order(self, trade_request: TradeRequest) -> TradeResult:
        """Send a market order"""
        if not self.is_connected:
            return TradeResult(
                success=False,
                error_message="Not connected to MT5"
            )
        
        if self.mock_mode:
            return self._mock_market_order(trade_request)
        
        try:
            # Get current price
            price_info = await self.get_price(trade_request.symbol)
            if not price_info:
                return TradeResult(
                    success=False,
                    error_message="Could not get current price"
                )
            
            # Determine order type and price
            if trade_request.trade_type.lower() == 'buy':
                order_type = mt5.ORDER_TYPE_BUY
                price = price_info.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = price_info.bid
            
            # Prepare request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": trade_request.symbol,
                "volume": trade_request.volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": trade_request.magic,
                "comment": trade_request.comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Add SL/TP if provided
            if trade_request.stop_loss:
                request["sl"] = trade_request.stop_loss
            if trade_request.take_profit:
                request["tp"] = trade_request.take_profit
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return TradeResult(
                    success=False,
                    retcode=result.retcode,
                    error_message=f"Order failed: {result.comment}"
                )
            
            return TradeResult(
                success=True,
                ticket=str(result.order),
                price=result.price,
                retcode=result.retcode
            )
            
        except Exception as e:
            logger.error(f"Error sending market order: {e}")
            return TradeResult(
                success=False,
                error_message=str(e)
            )
    
    def _mock_market_order(self, trade_request: TradeRequest) -> TradeResult:
        """Mock market order for testing"""
        import random
        import time
        
        # Simulate order processing delay
        time.sleep(0.1)
        
        # Generate mock ticket
        mock_ticket = f"MOCK_{int(time.time() * 1000)}"
        
        # Get mock price
        price_info = self._get_mock_price(trade_request.symbol)
        execution_price = price_info.ask if trade_request.trade_type.lower() == 'buy' else price_info.bid
        
        logger.info(f"Mock order: {trade_request.trade_type.upper()} {trade_request.volume} {trade_request.symbol} @ {execution_price}")
        
        return TradeResult(
            success=True,
            ticket=mock_ticket,
            price=execution_price,
            retcode=10009  # TRADE_RETCODE_DONE
        )
    
    async def close_position(self, ticket: str, symbol: str) -> TradeResult:
        """Close a specific position"""
        if not self.is_connected:
            return TradeResult(success=False, error_message="Not connected to MT5")
        
        if self.mock_mode:
            logger.info(f"Mock: Closing position {ticket} for {symbol}")
            return TradeResult(success=True, ticket=ticket)
        
        try:
            # Get position info
            positions = mt5.positions_get(ticket=int(ticket))
            if not positions:
                return TradeResult(
                    success=False,
                    error_message=f"Position {ticket} not found"
                )
            
            position = positions[0]
            
            # Determine close order type
            close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            
            # Get current price
            price_info = await self.get_price(symbol)
            if not price_info:
                return TradeResult(success=False, error_message="Could not get current price")
            
            close_price = price_info.bid if close_type == mt5.ORDER_TYPE_SELL else price_info.ask
            
            # Close request
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position.volume,
                "type": close_type,
                "position": int(ticket),
                "price": close_price,
                "deviation": 20,
                "magic": position.magic,
                "comment": "Close by AlgoBot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(close_request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return TradeResult(
                    success=False,
                    retcode=result.retcode,
                    error_message=f"Close failed: {result.comment}"
                )
            
            return TradeResult(
                success=True,
                ticket=str(result.order),
                price=result.price
            )
            
        except Exception as e:
            logger.error(f"Error closing position {ticket}: {e}")
            return TradeResult(success=False, error_message=str(e))
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open positions"""
        if not self.is_connected:
            return []
        
        if self.mock_mode:
            # Return mock positions for testing
            return []
        
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    "ticket": str(pos.ticket),
                    "symbol": pos.symbol,
                    "type": "buy" if pos.type == 0 else "sell",
                    "volume": pos.volume,
                    "open_price": pos.price_open,
                    "current_price": pos.price_current,
                    "profit": pos.profit,
                    "open_time": datetime.fromtimestamp(pos.time),
                    "magic": pos.magic,
                    "comment": pos.comment
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def close_all_positions(self, symbol: Optional[str] = None) -> List[TradeResult]:
        """Close all open positions for a symbol or all symbols"""
        positions = await self.get_positions(symbol)
        results = []
        
        for position in positions:
            result = await self.close_position(
                ticket=position["ticket"],
                symbol=position["symbol"]
            )
            results.append(result)
        
        return results

# Global instance
mt5_interface = CrossPlatformMT5Interface()