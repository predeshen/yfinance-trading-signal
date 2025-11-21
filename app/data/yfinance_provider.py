"""yfinance market data provider implementation"""
import logging
from typing import Dict, Tuple
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class YFinanceMarketDataProvider:
    """
    Market data provider using yfinance library.
    
    Features:
    - Intelligent caching: fetch full history on first call, then only new candles
    - Handles yfinance limitations (1m data only for recent 7 days)
    - Retry logic with exponential backoff for rate limits
    """
    
    # Interval mapping: our format -> yfinance format
    INTERVAL_MAP = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "60m": "1h",
        "240m": "4h",
    }
    
    # Maximum lookback periods for each interval (yfinance limitations)
    MAX_LOOKBACK = {
        "1m": timedelta(days=7),
        "5m": timedelta(days=60),
        "15m": timedelta(days=60),
        "30m": timedelta(days=60),
        "60m": timedelta(days=730),
        "240m": timedelta(days=730),
    }
    
    def __init__(self):
        """Initialize provider with empty cache"""
        # Cache: (symbol, interval) -> DataFrame
        self._cache: Dict[Tuple[str, str], pd.DataFrame] = {}
        # Last fetch timestamp: (symbol, interval) -> datetime
        self._last_fetch: Dict[Tuple[str, str], datetime] = {}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    async def get_candles(
        self,
        symbol: str,
        interval: str,
        lookback: timedelta
    ) -> pd.DataFrame:
        """
        Fetch OHLC candles with intelligent caching.
        
        On first call: fetch full lookback period
        On subsequent calls: fetch only new candles since last timestamp
        
        Args:
            symbol: yfinance symbol
            interval: Timeframe interval
            lookback: How far back to fetch data
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        cache_key = (symbol, interval)
        
        # Map interval to yfinance format
        yf_interval = self.INTERVAL_MAP.get(interval)
        if not yf_interval:
            raise ValueError(f"Unsupported interval: {interval}")
        
        # Respect yfinance limitations
        max_lookback = self.MAX_LOOKBACK.get(interval, timedelta(days=730))
        if lookback > max_lookback:
            logger.warning(
                f"Lookback {lookback} exceeds max {max_lookback} for {interval}. "
                f"Using max lookback."
            )
            lookback = max_lookback
        
        # Check if we have cached data
        if cache_key in self._cache:
            # Fetch only new candles since last fetch
            last_timestamp = self._cache[cache_key].index[-1]
            new_data = await self._fetch_yfinance(
                symbol,
                yf_interval,
                start=last_timestamp,
                end=None
            )
            
            if not new_data.empty:
                # Append new data to cache (avoid duplicates)
                combined = pd.concat([self._cache[cache_key], new_data])
                combined = combined[~combined.index.duplicated(keep='last')]
                combined = combined.sort_index()
                self._cache[cache_key] = combined
            
            self._last_fetch[cache_key] = datetime.utcnow()
            return self._cache[cache_key].copy()
        
        else:
            # First fetch: get full lookback period
            start_date = datetime.utcnow() - lookback
            data = await self._fetch_yfinance(
                symbol,
                yf_interval,
                start=start_date,
                end=None
            )
            
            if data.empty:
                raise ValueError(f"No data returned for {symbol} {interval}")
            
            # Cache the data
            self._cache[cache_key] = data
            self._last_fetch[cache_key] = datetime.utcnow()
            
            return data.copy()
    
    async def _fetch_yfinance(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime | None
    ) -> pd.DataFrame:
        """
        Fetch data from yfinance.
        
        Args:
            symbol: yfinance symbol
            interval: yfinance interval format
            start: Start datetime
            end: End datetime (None for now)
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Fetch history
            df = ticker.history(
                start=start,
                end=end,
                interval=interval,
                auto_adjust=True,
                actions=False
            )
            
            if df.empty:
                logger.warning(f"No data returned for {symbol} {interval}")
                return pd.DataFrame()
            
            # Standardize column names
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Keep only OHLCV columns
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # Ensure index is datetime
            df.index = pd.to_datetime(df.index)
            df.index.name = 'timestamp'
            
            logger.info(
                f"Fetched {len(df)} candles for {symbol} {interval} "
                f"from {df.index[0]} to {df.index[-1]}"
            )
            
            return df
        
        except Exception as e:
            logger.error(f"Error fetching data for {symbol} {interval}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5)
    )
    async def validate_symbol(self, symbol: str) -> bool:
        """
        Validate symbol by attempting to fetch 1 day of data.
        
        Args:
            symbol: yfinance symbol
        
        Returns:
            True if symbol is valid, False otherwise
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Try to fetch 1 day of data
            df = ticker.history(period="1d", interval="1d")
            
            if df.empty:
                logger.warning(f"Symbol validation failed: {symbol} returned no data")
                return False
            
            logger.info(f"Symbol validation successful: {symbol}")
            return True
        
        except Exception as e:
            logger.error(f"Symbol validation error for {symbol}: {e}")
            return False
    
    def clear_cache(self, symbol: str | None = None, interval: str | None = None) -> None:
        """
        Clear cache for specific symbol/interval or all.
        
        Args:
            symbol: Symbol to clear (None for all)
            interval: Interval to clear (None for all)
        """
        if symbol is None and interval is None:
            self._cache.clear()
            self._last_fetch.clear()
            logger.info("Cleared all cache")
        else:
            keys_to_remove = [
                key for key in self._cache.keys()
                if (symbol is None or key[0] == symbol) and
                   (interval is None or key[1] == interval)
            ]
            for key in keys_to_remove:
                del self._cache[key]
                del self._last_fetch[key]
            logger.info(f"Cleared cache for {len(keys_to_remove)} entries")
