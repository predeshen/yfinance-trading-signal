"""Order Block (OB) detector"""
import pandas as pd
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class IOrderBlockDetector:
    """
    Detects Order Blocks in OHLC data.
    
    An Order Block is a consolidation area before a strong move,
    indicating institutional activity.
    
    Simplified detection:
    - Bullish OB: Last down candle before strong up move
    - Bearish OB: Last up candle before strong down move
    """
    
    def detect_order_blocks(self, df: pd.DataFrame, lookback: int = 50, threshold: float = 0.02) -> List[Dict]:
        """
        Detect Order Blocks in OHLC data.
        
        Args:
            df: DataFrame with OHLC data
            lookback: Number of recent candles to analyze
            threshold: Minimum move size (as fraction) to consider "strong"
        
        Returns:
            List of OB dictionaries with:
            - start_idx: Start index
            - end_idx: End index
            - ob_high: Upper bound of OB
            - ob_low: Lower bound of OB
            - direction: "bullish" or "bearish"
        """
        if len(df) < 5:
            return []
        
        obs = []
        
        # Analyze recent candles
        recent_df = df.tail(lookback) if len(df) > lookback else df
        
        for i in range(2, len(recent_df) - 2):
            prev_candle = recent_df.iloc[i - 1]
            curr_candle = recent_df.iloc[i]
            next_candle = recent_df.iloc[i + 1]
            next2_candle = recent_df.iloc[i + 2]
            
            # Calculate move size
            curr_close = curr_candle['close']
            next2_close = next2_candle['close']
            move_size = abs(next2_close - curr_close) / curr_close
            
            # Bullish OB: down candle followed by strong up move
            if (curr_candle['close'] < curr_candle['open'] and
                next2_close > curr_close and
                move_size > threshold):
                
                obs.append({
                    'start_idx': i,
                    'end_idx': i,
                    'ob_high': curr_candle['high'],
                    'ob_low': curr_candle['low'],
                    'direction': 'bullish',
                    'timestamp': recent_df.index[i]
                })
            
            # Bearish OB: up candle followed by strong down move
            elif (curr_candle['close'] > curr_candle['open'] and
                  next2_close < curr_close and
                  move_size > threshold):
                
                obs.append({
                    'start_idx': i,
                    'end_idx': i,
                    'ob_high': curr_candle['high'],
                    'ob_low': curr_candle['low'],
                    'direction': 'bearish',
                    'timestamp': recent_df.index[i]
                })
        
        logger.debug(f"Detected {len(obs)} Order Blocks in {len(recent_df)} candles")
        return obs
