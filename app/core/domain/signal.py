"""Signal dataclass"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Signal:
    """
    Generated trading signal.
    
    Attributes:
        symbol_alias: Symbol alias (e.g., "US30")
        yf_symbol: yfinance symbol (e.g., "^DJI")
        direction: Trade direction ("buy" or "sell")
        time_generated_utc: Signal generation timestamp
        entry_price_at_signal: Entry price at signal time
        initial_sl: Initial stop-loss price
        initial_tp: Initial take-profit price
        strategy_name: Strategy that generated the signal
        notes: Additional notes about the signal
        estimated_rr: Estimated risk-reward ratio
    """
    symbol_alias: str
    yf_symbol: str
    direction: str  # "buy" or "sell"
    time_generated_utc: datetime
    entry_price_at_signal: float
    initial_sl: float
    initial_tp: float
    strategy_name: str
    notes: str
    estimated_rr: float
