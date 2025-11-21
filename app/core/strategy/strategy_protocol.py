"""Strategy protocol definition"""
from typing import Protocol, Optional
from app.core.domain.multi_timeframe_context import MultiTimeframeContext
from app.core.domain.signal import Signal
from dataclasses import dataclass


@dataclass
class TradeContext:
    """Context for evaluating an open trade"""
    trade_id: int
    symbol_alias: str
    yf_symbol: str
    direction: str
    entry_price: float
    current_price: float
    current_sl: float
    current_tp: float
    candle_high: float
    candle_low: float
    mtf_context: MultiTimeframeContext


@dataclass
class TradeUpdateAction:
    """Action to apply to a trade"""
    action_type: str  # "close_by_tp", "close_by_sl", "close_manual", "update_sl_tp", "none"
    new_state: Optional[str] = None
    new_sl: Optional[float] = None
    new_tp: Optional[float] = None
    close_reason: Optional[str] = None
    close_price: Optional[float] = None


class Strategy(Protocol):
    """Protocol for trading strategies"""
    
    async def evaluate_new_signal(
        self,
        ctx: MultiTimeframeContext
    ) -> Optional[Signal]:
        """
        Evaluate if conditions exist for a new signal.
        
        Args:
            ctx: Multi-timeframe context
        
        Returns:
            Signal if conditions met, None otherwise
        """
        ...
    
    async def evaluate_open_trade(
        self,
        ctx: TradeContext
    ) -> Optional[TradeUpdateAction]:
        """
        Evaluate if an open trade needs updates.
        
        Args:
            ctx: Trade context
        
        Returns:
            TradeUpdateAction if action needed, None otherwise
        """
        ...
