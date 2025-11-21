"""H4 FVG/Order Block strategy implementation"""
import logging
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.domain.multi_timeframe_context import MultiTimeframeContext
from app.core.domain.signal import Signal
from app.core.strategy.strategy_protocol import TradeContext, TradeUpdateAction
from app.core.strategy.fvg_detector import IFvgDetector
from app.core.strategy.ob_detector import IOrderBlockDetector
from app.core.strategy.technical_utils import (
    detect_bos, detect_choch, detect_liquidity_sweep, identify_swing_points
)
from app.core.sl_tp.sl_tp_estimator import SignalContext, DynamicSlTpEstimator

logger = logging.getLogger(__name__)


class H4FvgStrategy:
    """
    H4 FVG/Order Block strategy with multi-timeframe confirmation.
    
    Analysis approach:
    - H4: Detect FVGs and OBs for overall bias
    - H1/M30/M15: Identify structure (BOS, CHOCH, liquidity sweeps)
    - M5/M1: Entry confirmation (wick rejection, micro structure)
    """
    
    def __init__(
        self,
        db: Session,
        config,
        fvg_detector: Optional[IFvgDetector] = None,
        ob_detector: Optional[IOrderBlockDetector] = None,
        sl_tp_estimator: Optional[DynamicSlTpEstimator] = None
    ):
        """
        Initialize strategy.
        
        Args:
            db: Database session
            config: Application configuration
            fvg_detector: FVG detector instance
            ob_detector: Order Block detector instance
            sl_tp_estimator: SL/TP estimator instance
        """
        self.db = db
        self.config = config
        self.fvg_detector = fvg_detector or IFvgDetector()
        self.ob_detector = ob_detector or IOrderBlockDetector()
        self.sl_tp_estimator = sl_tp_estimator or DynamicSlTpEstimator(db, config)
        
        # Track last H4 candle timestamp per symbol to detect closes
        self.last_h4_timestamp = {}
    
    async def evaluate_new_signal(
        self,
        ctx: MultiTimeframeContext
    ) -> Optional[Signal]:
        """
        Evaluate multi-timeframe conditions for signal generation.
        
        Steps:
        1. Check if H4 candle just closed
        2. Detect H4 FVGs and OBs for bias
        3. Check H1/M30/M15 for structure confirmation
        4. Check M5/M1 for entry confirmation
        5. If all align, generate signal
        
        Args:
            ctx: Multi-timeframe context
        
        Returns:
            Signal if conditions met, None otherwise
        """
        try:
            # Step 1: Check if H4 candle just closed
            if not self._has_h4_candle_closed(ctx):
                logger.debug(f"{ctx.alias}: No new H4 candle close")
                return None
            
            logger.info(f"{ctx.alias}: New H4 candle closed, evaluating for signal...")
            
            # Step 2: Detect H4 FVGs and OBs for bias
            h4_fvgs = self.fvg_detector.detect_fvgs(ctx.h4, lookback=20)
            h4_obs = self.ob_detector.detect_order_blocks(ctx.h4, lookback=20)
            
            if not h4_fvgs and not h4_obs:
                logger.debug(f"{ctx.alias}: No H4 FVGs or OBs detected")
                return None
            
            # Determine bias from most recent FVG/OB
            bias = self._determine_bias(h4_fvgs, h4_obs)
            if not bias:
                logger.debug(f"{ctx.alias}: Could not determine clear bias")
                return None
            
            logger.info(f"{ctx.alias}: H4 bias is {bias}")
            
            # Step 3: Check H1/M30/M15 for structure confirmation
            structure_confirmed = self._check_structure_confirmation(ctx, bias)
            if not structure_confirmed:
                logger.debug(f"{ctx.alias}: Structure not confirmed on lower timeframes")
                return None
            
            logger.info(f"{ctx.alias}: Structure confirmed")
            
            # Step 4: Check M5/M1 for entry confirmation
            entry_confirmed = self._check_entry_confirmation(ctx, bias)
            if not entry_confirmed:
                logger.debug(f"{ctx.alias}: Entry not confirmed on M5/M1")
                return None
            
            logger.info(f"{ctx.alias}: Entry confirmed - generating signal!")
            
            # Step 5: Generate signal with SL/TP
            signal = await self._generate_signal(ctx, bias)
            return signal
        
        except Exception as e:
            logger.error(f"Error evaluating signal for {ctx.alias}: {e}", exc_info=True)
            return None
    
    def _has_h4_candle_closed(self, ctx: MultiTimeframeContext) -> bool:
        """
        Check if a new H4 candle has closed since last check.
        
        Args:
            ctx: Multi-timeframe context
        
        Returns:
            True if new H4 candle closed, False otherwise
        """
        if ctx.h4.empty:
            return False
        
        current_h4_timestamp = ctx.h4.index[-1]
        last_timestamp = self.last_h4_timestamp.get(ctx.alias)
        
        # Update last timestamp
        self.last_h4_timestamp[ctx.alias] = current_h4_timestamp
        
        # If this is first check or timestamp changed, candle closed
        if last_timestamp is None or current_h4_timestamp > last_timestamp:
            return True
        
        return False
    
    def _determine_bias(self, fvgs: list, obs: list) -> Optional[str]:
        """
        Determine market bias from FVGs and OBs.
        
        Args:
            fvgs: List of detected FVGs
            obs: List of detected Order Blocks
        
        Returns:
            "buy" or "sell" if clear bias, None otherwise
        """
        # Count bullish vs bearish signals
        bullish_count = 0
        bearish_count = 0
        
        for fvg in fvgs[-3:]:  # Look at last 3 FVGs
            if fvg['direction'] == 'bullish':
                bullish_count += 1
            else:
                bearish_count += 1
        
        for ob in obs[-3:]:  # Look at last 3 OBs
            if ob['direction'] == 'bullish':
                bullish_count += 1
            else:
                bearish_count += 1
        
        # Need clear bias (at least 2:1 ratio)
        if bullish_count > bearish_count * 2:
            return "buy"
        elif bearish_count > bullish_count * 2:
            return "sell"
        
        return None
    
    def _check_structure_confirmation(
        self,
        ctx: MultiTimeframeContext,
        bias: str
    ) -> bool:
        """
        Check for structure confirmation on H1/M30/M15.
        
        Args:
            ctx: Multi-timeframe context
            bias: Market bias ("buy" or "sell")
        
        Returns:
            True if structure confirms bias, False otherwise
        """
        # Check H1 for BOS/CHOCH
        h1_bos = detect_bos(ctx.h1, lookback=20)
        h1_choch = detect_choch(ctx.h1, lookback=20)
        
        # Check M15 for liquidity sweeps
        m15_sweeps = detect_liquidity_sweep(ctx.m15, lookback=20)
        
        # For bullish bias, look for bullish structure
        if bias == "buy":
            has_bullish_bos = any(b['type'] == 'bullish_bos' for b in h1_bos)
            has_bullish_choch = any(c['type'] == 'bullish_choch' for c in h1_choch)
            has_bullish_sweep = any(s['type'] == 'bullish_sweep' for s in m15_sweeps)
            
            # Need at least one confirmation
            return has_bullish_bos or has_bullish_choch or has_bullish_sweep
        
        # For bearish bias, look for bearish structure
        else:
            has_bearish_bos = any(b['type'] == 'bearish_bos' for b in h1_bos)
            has_bearish_choch = any(c['type'] == 'bearish_choch' for c in h1_choch)
            has_bearish_sweep = any(s['type'] == 'bearish_sweep' for s in m15_sweeps)
            
            return has_bearish_bos or has_bearish_choch or has_bearish_sweep
    
    def _check_entry_confirmation(
        self,
        ctx: MultiTimeframeContext,
        bias: str
    ) -> bool:
        """
        Check for entry confirmation on M5/M1.
        
        Args:
            ctx: Multi-timeframe context
            bias: Market bias ("buy" or "sell")
        
        Returns:
            True if entry confirmed, False otherwise
        """
        # Check last few M5 candles for wick rejection
        if len(ctx.m5) < 3:
            return False
        
        last_candles = ctx.m5.tail(3)
        
        for _, candle in last_candles.iterrows():
            # For buy: look for bullish wick rejection (long lower wick, close near high)
            if bias == "buy":
                body_size = abs(candle['close'] - candle['open'])
                lower_wick = min(candle['open'], candle['close']) - candle['low']
                
                # Wick should be at least 2x body size
                if lower_wick > body_size * 2 and candle['close'] > candle['open']:
                    return True
            
            # For sell: look for bearish wick rejection (long upper wick, close near low)
            else:
                body_size = abs(candle['close'] - candle['open'])
                upper_wick = candle['high'] - max(candle['open'], candle['close'])
                
                if upper_wick > body_size * 2 and candle['close'] < candle['open']:
                    return True
        
        # If no clear wick rejection, accept if recent trend aligns
        recent_trend_up = ctx.m5['close'].iloc[-1] > ctx.m5['close'].iloc[-5]
        
        if bias == "buy" and recent_trend_up:
            return True
        elif bias == "sell" and not recent_trend_up:
            return True
        
        return False
    
    async def _generate_signal(
        self,
        ctx: MultiTimeframeContext,
        bias: str
    ) -> Signal:
        """
        Generate signal with SL/TP.
        
        Args:
            ctx: Multi-timeframe context
            bias: Market bias ("buy" or "sell")
        
        Returns:
            Generated signal
        """
        # Identify swing points
        swing_highs, swing_lows = identify_swing_points(ctx.h4, window=5)
        
        # Create signal context for SL/TP estimation
        signal_ctx = SignalContext(
            symbol_alias=ctx.alias,
            yf_symbol=ctx.yf_symbol,
            direction=bias,
            entry_price=ctx.current_price,
            h4_df=ctx.h4,
            h1_df=ctx.h1,
            recent_swing_highs=swing_highs,
            recent_swing_lows=swing_lows
        )
        
        # Estimate SL/TP
        sl_price, tp_price = await self.sl_tp_estimator.estimate_for_new_signal(signal_ctx)
        
        # Calculate estimated RR
        sl_distance = abs(ctx.current_price - sl_price)
        tp_distance = abs(tp_price - ctx.current_price)
        estimated_rr = tp_distance / sl_distance if sl_distance > 0 else 0
        
        # Create signal
        signal = Signal(
            symbol_alias=ctx.alias,
            yf_symbol=ctx.yf_symbol,
            direction=bias,
            time_generated_utc=ctx.now_utc,
            entry_price_at_signal=ctx.current_price,
            initial_sl=sl_price,
            initial_tp=tp_price,
            strategy_name="H4 FVG / OB + structure",
            notes=f"H4 bias: {bias}, multi-timeframe confirmation",
            estimated_rr=estimated_rr
        )
        
        return signal
    
    async def evaluate_open_trade(
        self,
        ctx: TradeContext
    ) -> Optional[TradeUpdateAction]:
        """
        Evaluate if open trade needs adjustments.
        
        Checks:
        - Has SL been hit?
        - Has TP been hit?
        - Should SL be moved (BE or trail)?
        - Should TP be extended?
        - Should trade be closed early?
        
        Args:
            ctx: Trade context
        
        Returns:
            TradeUpdateAction if action needed, None otherwise
        """
        try:
            # Check if SL hit
            if ctx.direction == "buy" and ctx.candle_low <= ctx.current_sl:
                return TradeUpdateAction(
                    action_type="close_by_sl",
                    new_state="ClosedBySl",
                    close_price=ctx.current_sl,
                    close_reason="Stop loss hit"
                )
            elif ctx.direction == "sell" and ctx.candle_high >= ctx.current_sl:
                return TradeUpdateAction(
                    action_type="close_by_sl",
                    new_state="ClosedBySl",
                    close_price=ctx.current_sl,
                    close_reason="Stop loss hit"
                )
            
            # Check if TP hit
            if ctx.direction == "buy" and ctx.candle_high >= ctx.current_tp:
                return TradeUpdateAction(
                    action_type="close_by_tp",
                    new_state="ClosedByTp",
                    close_price=ctx.current_tp,
                    close_reason="Take profit hit"
                )
            elif ctx.direction == "sell" and ctx.candle_low <= ctx.current_tp:
                return TradeUpdateAction(
                    action_type="close_by_tp",
                    new_state="ClosedByTp",
                    close_price=ctx.current_tp,
                    close_reason="Take profit hit"
                )
            
            # Check for SL/TP adjustments using estimator
            from app.core.sl_tp.sl_tp_estimator import OpenTradeAnalytics
            from datetime import datetime
            
            analytics = OpenTradeAnalytics(
                trade_id=ctx.trade_id,
                symbol_alias=ctx.symbol_alias,
                direction=ctx.direction,
                entry_price=ctx.entry_price,
                current_price=ctx.current_price,
                current_sl=ctx.current_sl,
                current_tp=ctx.current_tp,
                open_duration=timedelta(hours=1),  # Simplified
                current_rr=0,  # Simplified
                h4_df=ctx.mtf_context.h4,
                h1_df=ctx.mtf_context.h1
            )
            
            adjustment = await self.sl_tp_estimator.evaluate_adjustment(analytics)
            
            if adjustment:
                return TradeUpdateAction(
                    action_type="update_sl_tp" if adjustment.action != "close_early" else "close_manual",
                    new_sl=adjustment.new_sl,
                    new_tp=adjustment.new_tp,
                    new_state="ClosedManual" if adjustment.action == "close_early" else None,
                    close_reason=adjustment.reason if adjustment.action == "close_early" else None
                )
            
            return None
        
        except Exception as e:
            logger.error(f"Error evaluating trade {ctx.trade_id}: {e}", exc_info=True)
            return None
