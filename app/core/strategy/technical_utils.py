"""Technical analysis utilities"""
import pandas as pd
import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    
    Args:
        df: DataFrame with OHLC data
        period: ATR period
    
    Returns:
        Series with ATR values
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR is EMA of TR
    atr = tr.ewm(span=period, adjust=False).mean()
    
    return atr


def identify_swing_points(df: pd.DataFrame, window: int = 5) -> Tuple[List[float], List[float]]:
    """
    Identify swing highs and lows.
    
    Args:
        df: DataFrame with OHLC data
        window: Window size for swing detection
    
    Returns:
        Tuple of (swing_highs, swing_lows)
    """
    swing_highs = []
    swing_lows = []
    
    if len(df) < window * 2 + 1:
        return swing_highs, swing_lows
    
    highs = df['high'].values
    lows = df['low'].values
    
    for i in range(window, len(df) - window):
        # Swing high: highest in window
        if highs[i] == max(highs[i-window:i+window+1]):
            swing_highs.append(highs[i])
        
        # Swing low: lowest in window
        if lows[i] == min(lows[i-window:i+window+1]):
            swing_lows.append(lows[i])
    
    return swing_highs, swing_lows


def detect_bos(df: pd.DataFrame, lookback: int = 20) -> List[dict]:
    """
    Detect Break of Structure (BOS).
    
    A BOS occurs when price breaks a significant high or low.
    
    Args:
        df: DataFrame with OHLC data
        lookback: Lookback period for structure
    
    Returns:
        List of BOS events
    """
    bos_events = []
    
    if len(df) < lookback + 5:
        return bos_events
    
    recent_df = df.tail(lookback)
    
    # Find recent high and low
    recent_high = recent_df['high'].max()
    recent_low = recent_df['low'].min()
    
    # Check if latest candle breaks structure
    latest = df.iloc[-1]
    
    if latest['high'] > recent_high:
        bos_events.append({
            'type': 'bullish_bos',
            'price': latest['high'],
            'timestamp': df.index[-1]
        })
    
    if latest['low'] < recent_low:
        bos_events.append({
            'type': 'bearish_bos',
            'price': latest['low'],
            'timestamp': df.index[-1]
        })
    
    return bos_events


def detect_choch(df: pd.DataFrame, lookback: int = 20) -> List[dict]:
    """
    Detect Change of Character (CHOCH).
    
    A CHOCH indicates a potential trend reversal.
    
    Args:
        df: DataFrame with OHLC data
        lookback: Lookback period
    
    Returns:
        List of CHOCH events
    """
    choch_events = []
    
    if len(df) < lookback + 10:
        return choch_events
    
    # Simplified CHOCH detection:
    # Look for trend change in recent candles
    recent_df = df.tail(lookback)
    
    # Calculate simple trend (more ups vs downs)
    ups = (recent_df['close'] > recent_df['open']).sum()
    downs = (recent_df['close'] < recent_df['open']).sum()
    
    # Check last few candles for reversal
    last_5 = df.tail(5)
    recent_ups = (last_5['close'] > last_5['open']).sum()
    recent_downs = (last_5['close'] < last_5['open']).sum()
    
    # CHOCH: trend was up, now turning down
    if ups > downs * 1.5 and recent_downs > recent_ups:
        choch_events.append({
            'type': 'bearish_choch',
            'timestamp': df.index[-1]
        })
    
    # CHOCH: trend was down, now turning up
    if downs > ups * 1.5 and recent_ups > recent_downs:
        choch_events.append({
            'type': 'bullish_choch',
            'timestamp': df.index[-1]
        })
    
    return choch_events


def detect_liquidity_sweep(df: pd.DataFrame, lookback: int = 20) -> List[dict]:
    """
    Detect liquidity sweeps.
    
    A liquidity sweep occurs when price briefly breaks a level then reverses.
    
    Args:
        df: DataFrame with OHLC data
        lookback: Lookback period
    
    Returns:
        List of liquidity sweep events
    """
    sweeps = []
    
    if len(df) < lookback + 3:
        return sweeps
    
    recent_df = df.tail(lookback)
    
    # Find recent high and low
    recent_high = recent_df['high'].max()
    recent_low = recent_df['low'].min()
    
    # Check last 3 candles for sweep pattern
    last_3 = df.tail(3)
    
    # Bullish sweep: wick below recent low, then close above
    if (last_3.iloc[0]['low'] < recent_low and
        last_3.iloc[-1]['close'] > last_3.iloc[0]['open']):
        sweeps.append({
            'type': 'bullish_sweep',
            'price': last_3.iloc[0]['low'],
            'timestamp': df.index[-1]
        })
    
    # Bearish sweep: wick above recent high, then close below
    if (last_3.iloc[0]['high'] > recent_high and
        last_3.iloc[-1]['close'] < last_3.iloc[0]['open']):
        sweeps.append({
            'type': 'bearish_sweep',
            'price': last_3.iloc[0]['high'],
            'timestamp': df.index[-1]
        })
    
    return sweeps
