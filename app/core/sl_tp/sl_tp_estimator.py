"""SL/TP estimator protocol and implementation"""
from typing import Protocol, Optional, Tuple
from dataclasses import dataclass
from datetime import timedelta
import pandas as pd
from sqlalchemy.orm import Session
from app.db.queries import get_mae_mfe_stats
from app.core.strategy.technical_utils import calculate_atr, identify_swing_points
import logging

logger = logging.getLogger(__name__)


@dataclass
class SignalContext:
    """Context for estimating SL/TP for a new signal"""
    symbol_alias: str
    yf_symbol: str
    direction: str
    entry_price: float
    h4_df: pd.DataFrame
    h1_df: pd.DataFrame
    recent_swing_highs: list[float]
    recent_swing_lows: list[float]


@dataclass
class OpenTradeAnalytics:
    """Analytics for an open trade"""
    trade_id: int
    symbol_alias: str
    direction: str
    entry_price: float
    current_price: float
    current_sl: float
    current_tp: float
    open_duration: timedelta
    current_rr: float
    h4_df: pd.DataFrame
    h1_df: pd.DataFrame


@dataclass
class SlTpAdjustment:
    """Recommended SL/TP adjustment"""
    action: str  # "move_sl", "extend_tp", "close_early"
    new_sl: Optional[float]
    new_tp: Optional[float]
    reason: str


class SlTpEstimator(Protocol):
    """Protocol for SL/TP estimation"""
    
    async def estimate_for_new_signal(
        self,
        ctx: SignalContext
    ) -> Tuple[float, float]:
        """Estimate SL and TP prices for a new signal"""
        ...
    
    async def evaluate_adjustment(
        self,
        ctx: OpenTradeAnalytics
    ) -> Optional[SlTpAdjustment]:
        """Evaluate if SL/TP should be adjusted"""
        ...


class DynamicSlTpEstimator:
    """
    Dynamic SL/TP estimator using:
    - ATR for volatility
    - Recent structure (swing highs/lows)
    - Historical MAE/MFE from database
    """
    
    def __init__(self, db: Session, config):
        """
        Initialize estimator.
        
        Args:
            db: Database session
            config: Scanner configuration
        """
        self.db = db
        self.config = config
        self.atr_multiplier_sl = 1.5  # SL buffer
        self.atr_multiplier_tp = 2.5  # TP target
    
    async def estimate_for_new_signal(
        self,
        ctx: SignalContext
    ) -> Tuple[float, float]:
        """
        Estimate SL/TP for new signal.
        
        Steps:
        1. Compute ATR(14) on H4 and H1
        2. Identify nearest swing high/low
        3. Query DB for historical MAE/MFE
        4. Set SL: beyond structure + ATR buffer
        5. Set TP: based on median MFE or ATR multiple
        
        Args:
            ctx: Signal context
        
        Returns:
            Tuple of (sl_price, tp_price)
        """
        # Calculate ATR
        h4_atr = calculate_atr(ctx.h4_df, period=14).iloc[-1]
        h1_atr = calculate_atr(ctx.h1_df, period=14).iloc[-1]
        avg_atr = (h4_atr + h1_atr) / 2
        
        logger.info(f"ATR: H4={h4_atr:.2f}, H1={h1_atr:.2f}, Avg={avg_atr:.2f}")
        
        # Get historical MAE/MFE stats
        mae_mfe_stats = get_mae_mfe_stats(
            self.db,
            ctx.symbol_alias,
            ctx.direction,
            limit=100
        )
        
        # Determine SL based on direction and structure
        if ctx.direction == "buy":
            # SL below recent swing low
            if ctx.recent_swing_lows:
                nearest_swing = min([s for s in ctx.recent_swing_lows if s < ctx.entry_price], default=ctx.entry_price * 0.98)
            else:
                nearest_swing = ctx.entry_price * 0.98
            
            sl_price = nearest_swing - (avg_atr * self.atr_multiplier_sl)
            
            # TP above entry
            if mae_mfe_stats['median_mfe']:
                tp_price = ctx.entry_price + mae_mfe_stats['median_mfe']
            else:
                tp_price = ctx.entry_price + (avg_atr * self.atr_multiplier_tp)
        
        else:  # sell
            # SL above recent swing high
            if ctx.recent_swing_highs:
                nearest_swing = max([s for s in ctx.recent_swing_highs if s > ctx.entry_price], default=ctx.entry_price * 1.02)
            else:
                nearest_swing = ctx.entry_price * 1.02
            
            sl_price = nearest_swing + (avg_atr * self.atr_multiplier_sl)
            
            # TP below entry
            if mae_mfe_stats['median_mfe']:
                tp_price = ctx.entry_price - mae_mfe_stats['median_mfe']
            else:
                tp_price = ctx.entry_price - (avg_atr * self.atr_multiplier_tp)
        
        logger.info(
            f"Estimated SL/TP for {ctx.symbol_alias} {ctx.direction}: "
            f"Entry={ctx.entry_price:.2f}, SL={sl_price:.2f}, TP={tp_price:.2f}"
        )
        
        return sl_price, tp_price
    
    async def evaluate_adjustment(
        self,
        ctx: OpenTradeAnalytics
    ) -> Optional[SlTpAdjustment]:
        """
        Evaluate if adjustments needed.
        
        Checks:
        - If profit > 1R: consider moving SL to BE
        - If profit > 2R: consider trailing SL
        - If trend exhaustion signals: consider early close
        - If time in trade > typical duration: consider early close
        
        Args:
            ctx: Open trade analytics
        
        Returns:
            SlTpAdjustment if adjustment recommended, None otherwise
        """
        # Calculate current profit in R
        sl_distance = abs(ctx.entry_price - ctx.current_sl)
        current_profit = abs(ctx.current_price - ctx.entry_price)
        
        if sl_distance > 0:
            profit_in_r = current_profit / sl_distance
        else:
            profit_in_r = 0
        
        logger.debug(
            f"Trade {ctx.trade_id}: Profit={profit_in_r:.2f}R, "
            f"Duration={ctx.open_duration}"
        )
        
        # Move SL to breakeven if profit > 1R
        if profit_in_r > 1.0:
            if ctx.direction == "buy" and ctx.current_sl < ctx.entry_price:
                return SlTpAdjustment(
                    action="move_sl",
                    new_sl=ctx.entry_price,
                    new_tp=None,
                    reason="Move SL to breakeven (1R profit)"
                )
            elif ctx.direction == "sell" and ctx.current_sl > ctx.entry_price:
                return SlTpAdjustment(
                    action="move_sl",
                    new_sl=ctx.entry_price,
                    new_tp=None,
                    reason="Move SL to breakeven (1R profit)"
                )
        
        # Trail SL if profit > 2R
        if profit_in_r > 2.0:
            h4_atr = calculate_atr(ctx.h4_df, period=14).iloc[-1]
            
            if ctx.direction == "buy":
                trailing_sl = ctx.current_price - (h4_atr * 1.0)
                if trailing_sl > ctx.current_sl:
                    return SlTpAdjustment(
                        action="move_sl",
                        new_sl=trailing_sl,
                        new_tp=None,
                        reason="Trail SL (2R profit)"
                    )
            else:
                trailing_sl = ctx.current_price + (h4_atr * 1.0)
                if trailing_sl < ctx.current_sl:
                    return SlTpAdjustment(
                        action="move_sl",
                        new_sl=trailing_sl,
                        new_tp=None,
                        reason="Trail SL (2R profit)"
                    )
        
        # Consider early close if trade is open too long
        if ctx.open_duration > timedelta(days=7):
            return SlTpAdjustment(
                action="close_early",
                new_sl=None,
                new_tp=None,
                reason="Trade open > 7 days"
            )
        
        return None
    
    def calculate_risk_and_lot_size(
        self,
        entry_price: float,
        sl_price: float,
        direction: str
    ) -> Tuple[float, float]:
        """
        Calculate risk amount and suggested lot size.
        
        Args:
            entry_price: Entry price
            sl_price: Stop loss price
            direction: Trade direction
        
        Returns:
            Tuple of (risk_amount, lot_size)
        """
        equity = self.config.scanner.default_equity
        risk_percentage = self.config.scanner.risk_percentage
        
        # Calculate risk amount
        risk_amount = equity * risk_percentage
        
        # Calculate SL distance in points
        sl_distance = abs(entry_price - sl_price)
        
        # Simplified lot size calculation
        # In reality, this depends on instrument specifications
        # For indices: 1 point = $1 per lot typically
        point_value_per_lot = 1.0
        
        if sl_distance > 0:
            lot_size = risk_amount / (sl_distance * point_value_per_lot)
        else:
            lot_size = 0.01  # Minimum lot size
        
        # Round to 2 decimal places
        lot_size = round(lot_size, 2)
        
        logger.info(
            f"Risk calculation: Equity=${equity:.2f}, Risk%={risk_percentage*100:.1f}%, "
            f"Risk$={risk_amount:.2f}, SL distance={sl_distance:.2f}, Lot size={lot_size}"
        )
        
        return risk_amount, lot_size
