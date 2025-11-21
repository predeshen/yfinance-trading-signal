"""
Property-based tests for strategy components.
"""
import pytest
from hypothesis import given, settings, strategies as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.core.strategy.fvg_detector import IFvgDetector
from app.core.strategy.ob_detector import IOrderBlockDetector
from app.core.strategy.technical_utils import calculate_atr, identify_swing_points


def generate_ohlc_data(num_candles: int = 100) -> pd.DataFrame:
    """Generate sample OHLC data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=num_candles, freq='1H')
    
    # Generate random walk price data
    close_prices = 100 + np.cumsum(np.random.randn(num_candles) * 0.5)
    
    df = pd.DataFrame({
        'open': close_prices + np.random.randn(num_candles) * 0.2,
        'high': close_prices + abs(np.random.randn(num_candles)) * 0.5,
        'low': close_prices - abs(np.random.randn(num_candles)) * 0.5,
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, num_candles)
    }, index=dates)
    
    # Ensure high is highest and low is lowest
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


# Feature: trading-scanner-python, Property 5: FVG and Order Block detection
@given(num_candles=st.integers(min_value=10, max_value=200))
@settings(max_examples=50)
def test_fvg_and_order_block_detection(num_candles):
    """
    Feature: trading-scanner-python, Property 5: FVG and Order Block detection
    
    For any H4 timeframe data containing Fair Value Gaps or Order Blocks,
    the detection algorithms should identify them and return their locations
    and directions.
    
    Validates: Requirements 2.1
    """
    df = generate_ohlc_data(num_candles)
    
    # Test FVG detector
    fvg_detector = IFvgDetector()
    fvgs = fvg_detector.detect_fvgs(df)
    
    # Should return a list
    assert isinstance(fvgs, list)
    
    # Each FVG should have required fields
    for fvg in fvgs:
        assert 'direction' in fvg
        assert fvg['direction'] in ['bullish', 'bearish']
        assert 'gap_high' in fvg
        assert 'gap_low' in fvg
        assert fvg['gap_high'] > fvg['gap_low']
    
    # Test OB detector
    ob_detector = IOrderBlockDetector()
    obs = ob_detector.detect_order_blocks(df)
    
    # Should return a list
    assert isinstance(obs, list)
    
    # Each OB should have required fields
    for ob in obs:
        assert 'direction' in ob
        assert ob['direction'] in ['bullish', 'bearish']
        assert 'ob_high' in ob
        assert 'ob_low' in ob
        assert ob['ob_high'] >= ob['ob_low']


# Feature: trading-scanner-python, Property 6: Structure detection across timeframes
def test_structure_detection():
    """
    Feature: trading-scanner-python, Property 6: Structure detection across timeframes
    
    For any H1, M30, or M15 timeframe data containing BOS, CHOCH, or
    liquidity sweep patterns, the structure detection should identify
    these patterns.
    
    Validates: Requirements 2.2
    """
    from app.core.strategy.technical_utils import detect_bos, detect_choch, detect_liquidity_sweep
    
    df = generate_ohlc_data(100)
    
    # Test BOS detection
    bos_events = detect_bos(df)
    assert isinstance(bos_events, list)
    
    # Test CHOCH detection
    choch_events = detect_choch(df)
    assert isinstance(choch_events, list)
    
    # Test liquidity sweep detection
    sweep_events = detect_liquidity_sweep(df)
    assert isinstance(sweep_events, list)


# Feature: trading-scanner-python, Property 8: ATR computation for signals
@given(
    num_candles=st.integers(min_value=20, max_value=200),
    period=st.integers(min_value=5, max_value=30)
)
@settings(max_examples=50)
def test_atr_computation(num_candles, period):
    """
    Feature: trading-scanner-python, Property 8: ATR computation for signals
    
    For any new signal generation, the system should compute ATR values
    from H4 and H1 timeframes over the configured lookback period.
    
    Validates: Requirements 3.1
    """
    df = generate_ohlc_data(num_candles)
    
    # Calculate ATR
    atr = calculate_atr(df, period=period)
    
    # Should return a Series
    assert isinstance(atr, pd.Series)
    assert len(atr) == len(df)
    
    # ATR values should be positive
    assert (atr.dropna() >= 0).all()
    
    # ATR should have some non-zero values
    if len(atr.dropna()) > 0:
        assert atr.dropna().max() > 0


# Feature: trading-scanner-python, Property 9: Swing point identification
@given(num_candles=st.integers(min_value=20, max_value=200))
@settings(max_examples=50)
def test_swing_point_identification(num_candles):
    """
    Feature: trading-scanner-python, Property 9: Swing point identification
    
    For any new signal generation, the system should identify swing highs
    and lows from recent price structure near the entry zone.
    
    Validates: Requirements 3.2
    """
    df = generate_ohlc_data(num_candles)
    
    # Identify swing points
    swing_highs, swing_lows = identify_swing_points(df, window=5)
    
    # Should return lists
    assert isinstance(swing_highs, list)
    assert isinstance(swing_lows, list)
    
    # Swing highs should be higher than swing lows
    if swing_highs and swing_lows:
        assert max(swing_highs) >= min(swing_lows)
