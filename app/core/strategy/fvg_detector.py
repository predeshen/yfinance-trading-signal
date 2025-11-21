"""Fair Value Gap (FVG) detector"""
import pandas as pd
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class IFvgDetector:
    """
    Detects Fair Value Gaps in OHLC data.
    
    A Fair Value Gap (FVG) is a price imbalance where:
    - Bullish FVG: candle[i-1].high < candle[i+1].low (gap up)
    - Bearish FVG: candle[i-1].low > candle[i+1].high (gap down)
    """
    
    def detect_fvgs(self, df: pd.DataFrame, lookback: int = 50) -> List[Dict]:
        """
        Detect FVGs in OHLC data.
        
        Args:
            df: DataFrame with OHLC data
            lookback: Number of recent candles to analyze
        
        Returns:
            List of FVG dictionaries with:
            - start_idx: Start index
            - end_idx: End index
            - gap_high: Upper bound of gap
            - gap_low: Lower bound of gap
            - direction: "bullish" or "bearish"
        """
        if len(df) < 3:
            return []
        
        fvgs = []
        
        # Analyze recent candles
        recent_df = df.tail(lookback) if len(df) > lookback else df
        
        for i in range(1, len(recent_df) - 1):
            prev_candle = recent_df.iloc[i - 1]
            curr_candle = recent_df.iloc[i]
            next_candle = recent_df.iloc[i + 1]
            
            # Bullish FVG: gap between prev high and next low
            if prev_candle['high'] < next_candle['low']:
                fvgs.append({
                    'start_idx': i - 1,
                    'end_idx': i + 1,
                    'gap_high': next_candle['low'],
                    'gap_low': prev_candle['high'],
                    'direction': 'bullish',
                    'timestamp': recent_df.index[i]
                })
            
            # Bearish FVG: gap between prev low and next high
            elif prev_candle['low'] > next_candle['high']:
                fvgs.append({
                    'start_idx': i - 1,
                    'end_idx': i + 1,
                    'gap_high': prev_candle['low'],
                    'gap_low': next_candle['high'],
                    'direction': 'bearish',
                    'timestamp': recent_df.index[i]
                })
        
        logger.debug(f"Detected {len(fvgs)} FVGs in {len(recent_df)} candles")
        return fvgs
