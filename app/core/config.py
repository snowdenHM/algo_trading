from pydantic_settings import BaseSettings
from pydantic import Field
import os
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    api_title: str = "AlgoTrading API"
    api_version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./algotrading.db", env="DATABASE_URL")
    
    # MT5 Configuration (Optional - for cross-platform compatibility)
    mt5_path: Optional[str] = Field(default=None, env="MT5_PATH")
    mt5_account_id: Optional[int] = Field(default=None, env="MT5_ACCOUNT_ID")
    mt5_password: Optional[str] = Field(default=None, env="MT5_PASSWORD")
    mt5_server: Optional[str] = Field(default=None, env="MT5_SERVER")
    
    # Trading Configuration
    default_symbol: str = Field(default="BTCUSD", env="DEFAULT_SYMBOL")
    default_lot_size: float = Field(default=0.01, env="DEFAULT_LOT_SIZE")
    max_concurrent_trades: int = Field(default=10, env="MAX_CONCURRENT_TRADES")
    
    # Risk Management
    max_drawdown_percent: float = Field(default=10.0, env="MAX_DRAWDOWN_PERCENT")
    max_risk_per_trade: float = Field(default=2.0, env="MAX_RISK_PER_TRADE")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()