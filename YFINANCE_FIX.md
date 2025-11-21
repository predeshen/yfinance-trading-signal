# yfinance API Fix - Troubleshooting Steps

## Problem
yfinance API returning empty responses: "Expecting value: line 1 column 1 (char 0)"
This typically means Yahoo Finance is blocking requests from your IP.

## Fixes Applied

### 1. User-Agent Header
Added browser user-agent to bypass bot detection:
- Updated `app/data/yfinance_provider.py` to use custom session with Mozilla user-agent
- This makes requests look like they're coming from a real browser

### 2. Rate Limiting
Added 0.5 second delay between requests to avoid triggering rate limits

### 3. Test Script
Created `test_yfinance_direct.py` to test API connectivity directly

## Testing on Server

### Step 1: Pull latest changes
```bash
cd ~/yfinance-trading-signal
git pull
```

### Step 2: Test yfinance directly
```bash
python3 test_yfinance_direct.py
```

This will test each symbol and show which ones work.

### Step 3: If test passes, restart the service
```bash
# Stop the running service (Ctrl+C if running in foreground)

# Or if running as systemd service:
sudo systemctl restart trading-scanner

# Or run directly:
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Expected Results

If the fix works, you should see:
- ✓ Ticker info retrieved
- ✓ Got X candles for each test
- No "Expecting value" errors

## If Still Failing

The issue might be:

1. **IP Blacklist**: Your VM's IP is blocked by Yahoo Finance
   - Solution: Use a proxy or VPN
   - Solution: Try a different cloud provider/region

2. **Network Restrictions**: Firewall blocking outbound HTTPS
   - Check: `curl -I https://query1.finance.yahoo.com`
   - Solution: Configure firewall rules

3. **Yahoo Finance API Changes**: API endpoints changed
   - Check yfinance GitHub issues: https://github.com/ranaroussi/yfinance/issues
   - Solution: Update yfinance version: `pip install --upgrade yfinance`

## Alternative: Mock Data Mode

If yfinance continues to fail, we can:
1. Update the spec to add a "mock data mode" for testing
2. Create a new spec for multi-provider fallback (Alpha Vantage, Twelve Data, etc.)

## Next Steps

After testing, let me know:
- Did the test script work?
- Are you seeing data now?
- Do you want to proceed with alternative data providers?
