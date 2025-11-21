#!/usr/bin/env python3
"""Direct yfinance test to diagnose API connectivity issues"""
import yfinance as yf
import requests
import time
from datetime import datetime, timedelta

# Test symbols
symbols = {
    "US30": "^DJI",
    "US100": "^NDX", 
    "NAS100": "^NDX",
    "DAX": "^GDAXI",
    "XAUUSD": "XAUUSD=X"
}

print("=" * 60)
print("yfinance Direct API Test (with User-Agent fix)")
print("=" * 60)
print()

# Create session with user-agent
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

for alias, symbol in symbols.items():
    print(f"\nTesting {alias} ({symbol})...")
    print("-" * 40)
    
    try:
        ticker = yf.Ticker(symbol, session=session)
        
        # Add small delay between requests
        time.sleep(0.5)
        
        # Test 1: Get basic info
        print(f"  1. Getting ticker info...")
        try:
            info = ticker.info
            print(f"     ✓ Info retrieved: {info.get('longName', 'N/A')}")
        except Exception as e:
            print(f"     ✗ Info failed: {e}")
        
        # Test 2: Get 1 day history
        print(f"  2. Getting 1 day history...")
        try:
            df_1d = ticker.history(period="1d", interval="1d")
            if not df_1d.empty:
                print(f"     ✓ Got {len(df_1d)} candles")
                print(f"       Last close: {df_1d['Close'].iloc[-1]:.2f}")
            else:
                print(f"     ✗ No data returned")
        except Exception as e:
            print(f"     ✗ Failed: {e}")
        
        # Test 3: Get 5 days of 1h data
        print(f"  3. Getting 5 days of 1h data...")
        try:
            df_1h = ticker.history(period="5d", interval="1h")
            if not df_1h.empty:
                print(f"     ✓ Got {len(df_1h)} candles")
                print(f"       Date range: {df_1h.index[0]} to {df_1h.index[-1]}")
            else:
                print(f"     ✗ No data returned")
        except Exception as e:
            print(f"     ✗ Failed: {e}")
        
        # Test 4: Get 4h data
        print(f"  4. Getting 4h data...")
        try:
            df_4h = ticker.history(period="60d", interval="4h")
            if not df_4h.empty:
                print(f"     ✓ Got {len(df_4h)} candles")
                print(f"       Date range: {df_4h.index[0]} to {df_4h.index[-1]}")
            else:
                print(f"     ✗ No data returned")
        except Exception as e:
            print(f"     ✗ Failed: {e}")
            
    except Exception as e:
        print(f"  ✗ Ticker creation failed: {e}")

print()
print("=" * 60)
print("Test Complete")
print("=" * 60)
