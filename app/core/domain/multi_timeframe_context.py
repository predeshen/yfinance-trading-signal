"""Multi-timeframe context dataclass"""
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass
class MultiTimeframeContext:
    """
    Context containing all timeframe data for analysis.
    
    Attributes:
        alias: Symbol alias (e.g., "US30")
        yf_symbol: yfinance symbol (e.g., "^DJI")
        now_utc: Current timestamp in UTC
        h4: 4-hour timeframe DataFrame
        h1: 1-hour timeframe DataFrame
        m30: 30-minute timeframe DataFrame
        m15: 15-minute timeframe DataFrame
        m5: 5-minute timeframe DataFrame
        m1: 1-minute timeframe DataFrame
        current_price: Current price (close of most recent candle)
    """
    alias: str
    yf_symbol: str
    now_utc: datetime
    h4: pd.DataFrame
    h1: pd.DataFrame
    m30: pd.DataFrame
    m15: pd.DataFrame
    m5: pd.DataFrame
    m1: pd.DataFrame
    current_price: float
