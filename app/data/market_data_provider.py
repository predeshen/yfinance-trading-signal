"""Market data provider protocol"""
from typing import Protocol
from datetime import datetime, timedelta
import pandas as pd


class MarketDataProvider(Protocol):
    """Protocol for market data providers"""
    
    async def get_candles(
        self,
        symbol: str,
        interval: str,  # "1m", "5m", "15m", "30m", "60m", "240m"
        lookback: timedelta
    ) -> pd.DataFrame:
        """
        Fetch OHLC candles for a symbol and interval.
        
        Args:
            symbol: yfinance symbol (e.g., "^DJI", "XAUUSD=X")
            interval: Timeframe interval
            lookback: How far back to fetch data
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        ...
    
    async def validate_symbol(self, symbol: str) -> bool:
        """
        Validate that a symbol is available from the data provider.
        
        Args:
            symbol: yfinance symbol
        
        Returns:
            True if symbol is valid, False otherwise
        """
        ...
