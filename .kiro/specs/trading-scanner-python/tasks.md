# Implementation Plan

- [x] 1. Set up project structure and configuration management


  - Create directory structure: app/core, app/data, app/services, app/notifications, app/db, app/api, app/config, app/utils, tests/
  - Implement Pydantic settings classes for configuration (TelegramConfig, SmtpConfig, ScannerConfig, DatabaseConfig, AppConfig)
  - Create .env.example with all required environment variables
  - Implement configuration validation and loading from environment variables
  - Set up timezone utilities for Africa/Johannesburg conversions
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 1.1 Write property test for configuration validation


  - **Property 34: Configuration validation**
  - **Validates: Requirements 9.2, 9.3**

- [x] 1.2 Write property test for symbol mapping parsing


  - **Property 35: Symbol mapping parsing**
  - **Validates: Requirements 9.4**

- [x] 1.3 Write property test for timezone configuration usage


  - **Property 36: Timezone configuration usage**
  - **Validates: Requirements 9.5**

- [x] 2. Set up database layer with SQLAlchemy and Alembic



  - Create SQLAlchemy models: Signal, Trade, Heartbeat, ErrorLog
  - Configure database connection and session management
  - Initialize Alembic and create initial migration
  - Implement automatic migration execution on startup
  - Create database utility functions for common queries
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 2.1 Write property test for automatic database migrations


  - **Property 37: Automatic database migrations**
  - **Validates: Requirements 10.2**


- [x] 2.2 Write property test for signal persistence

  - **Property 38: Signal persistence**
  - **Validates: Requirements 10.3**


- [x] 2.3 Write property test for trade persistence

  - **Property 39: Trade persistence**
  - **Validates: Requirements 10.4**


- [x] 2.4 Write property test for historical trade query filtering

  - **Property 40: Historical trade query filtering**
  - **Validates: Requirements 10.5**

- [x] 3. Implement market data provider with yfinance


  - Define MarketDataProvider protocol interface
  - Implement YFinanceMarketDataProvider class with caching
  - Implement symbol validation method
  - Implement get_candles method with intelligent caching (fetch only new candles after initial load)
  - Handle yfinance limitations (1m data only for recent 7 days)
  - Implement retry logic with exponential backoff for rate limits
  - _Requirements: 1.1, 1.2, 1.4, 1.5, 14.1, 14.2, 14.3, 14.4_

- [x] 3.1 Write property test for symbol validation

  - **Property 1: Symbol validation on startup**
  - **Validates: Requirements 1.1**

- [x] 3.2 Write property test for error handling on invalid symbols

  - **Property 2: Error handling on invalid symbols**
  - **Validates: Requirements 1.2**

- [x] 3.3 Write property test for multi-timeframe data completeness

  - **Property 3: Multi-timeframe data completeness**
  - **Validates: Requirements 1.4**

- [x] 3.4 Write property test for incremental data fetching

  - **Property 4: Incremental data fetching**
  - **Validates: Requirements 1.5**

- [x] 3.5 Write property test for 1-minute data period limitation

  - **Property 49: 1-minute data period limitation**
  - **Validates: Requirements 14.1**

- [x] 3.6 Write property test for symbol fetch error isolation

  - **Property 50: Symbol fetch error isolation**
  - **Validates: Requirements 14.2**

- [x] 3.7 Write property test for rate limit retry with backoff

  - **Property 51: Rate limit retry with backoff**
  - **Validates: Requirements 14.3**

- [x] 3.8 Write property test for insufficient data handling

  - **Property 52: Insufficient data handling**
  - **Validates: Requirements 14.4**

- [x] 4. Implement strategy components (FVG and Order Block detection)



  - Create MultiTimeframeContext dataclass
  - Implement IFvgDetector class for Fair Value Gap detection on pandas DataFrames
  - Implement IOrderBlockDetector class for Order Block detection on pandas DataFrames
  - Implement structure detection utilities (BOS, CHOCH, liquidity sweeps)
  - Implement swing high/low identification
  - Implement ATR calculation utility
  - _Requirements: 2.1, 2.2, 3.1, 3.2_

- [x] 4.1 Write property test for FVG and Order Block detection

  - **Property 5: FVG and Order Block detection**
  - **Validates: Requirements 2.1**

- [x] 4.2 Write property test for structure detection

  - **Property 6: Structure detection across timeframes**
  - **Validates: Requirements 2.2**

- [x] 4.3 Write property test for ATR computation

  - **Property 8: ATR computation for signals**
  - **Validates: Requirements 3.1**

- [x] 4.4 Write property test for swing point identification

  - **Property 9: Swing point identification**
  - **Validates: Requirements 3.2**

- [x] 5. Implement SL/TP estimation logic



  - Define SlTpEstimator protocol interface
  - Create SignalContext and OpenTradeAnalytics dataclasses
  - Implement DynamicSlTpEstimator class
  - Implement estimate_for_new_signal method (ATR + structure + historical MAE/MFE)
  - Implement evaluate_adjustment method (check for BE, trailing, early close)
  - Implement risk calculation (risk amount and lot size)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 8.1, 8.2_

- [x] 5.1 Write property test for historical MAE/MFE query

  - **Property 10: Historical MAE/MFE query**
  - **Validates: Requirements 3.3**

- [x] 5.2 Write property test for stop-loss placement

  - **Property 11: Stop-loss placement beyond structure**
  - **Validates: Requirements 3.4**

- [x] 5.3 Write property test for take-profit based on MFE

  - **Property 12: Take-profit based on MFE**
  - **Validates: Requirements 3.5**

- [x] 5.4 Write property test for trade evaluation metrics

  - **Property 13: Trade evaluation metrics**
  - **Validates: Requirements 3.6**

- [x] 5.5 Write property test for risk amount calculation

  - **Property 31: Risk amount calculation**
  - **Validates: Requirements 8.1**

- [x] 5.6 Write property test for lot size calculation

  - **Property 32: Lot size calculation**
  - **Validates: Requirements 8.2**

- [x] 6. Implement H4 FVG strategy



  - Define Strategy protocol interface
  - Create Signal dataclass
  - Implement H4FvgStrategy class
  - Implement evaluate_new_signal method (check H4 candle close, detect FVG/OB, check multi-timeframe alignment)
  - Implement evaluate_open_trade method (check for SL/TP hits, evaluate adjustments)
  - Integrate FVG detector, OB detector, and SL/TP estimator
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6.1 Write property test for signal generation on H4 candle close

  - **Property 7: Signal generation on H4 candle close**
  - **Validates: Requirements 2.4, 2.5**

- [x] 7. Implement trade state machine


  - Create TradeState enum and TradeUpdateAction dataclass
  - Implement TradeStateMachine class
  - Implement check_and_update_trade method (check SL/TP hits based on candle high/low)
  - Implement apply_action method (update trade state in database)
  - Ensure no TP notifications for already-closed trades
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 7.1 Write property test for trade creation from signal

  - **Property 14: Trade creation from signal**
  - **Validates: Requirements 4.1**

- [x] 7.2 Write property test for state transition on SL hit

  - **Property 15: State transition on SL hit**
  - **Validates: Requirements 4.2**


- [x] 7.3 Write property test for state transition on TP hit

  - **Property 16: State transition on TP hit**
  - **Validates: Requirements 4.3**

- [x] 7.4 Write property test for manual closure state transition

  - **Property 17: Manual closure state transition**
  - **Validates: Requirements 4.4**

- [x] 7.5 Write property test for no TP notification for closed trardes

  - **Property 18: No TP notification for closed trades**
  - **Validates: Requirements 4.5**

- [x] 7.6 Write property test for TP notification on state transition

  - **Property 19: TP notification on state transition**
  - **Validates: Requirements 4.6**

- [x] 8. Implement notification services


  - Define NotificationService protocol interface
  - Implement TelegramNotificationService class
  - Implement all Telegram message methods: send_signal_alert, send_update_alert, send_close_alert, send_heartbeat, send_error_alert
  - Format messages according to specification with proper emoji and structure
  - Implement timezone conversion to CAT for all timestamps
  - Implement EmailNotificationService class
  - Implement send_summary_email and send_error_email methods
  - Configure SMTP with SSL support
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5, 7.2, 7.3, 8.3_

- [x] 8.1 Write property test for signal message completeness


  - **Property 20: Signal message completeness**
  - **Validates: Requirements 5.1**

- [x] 8.2 Write property test for update message format

  - **Property 21: Update message format**
  - **Validates: Requirements 5.2**

- [x] 8.3 Write property test for SL close message format

  - **Property 22: SL close message format**
  - **Validates: Requirements 5.3**

- [x] 8.4 Write property test for TP close message format

  - **Property 23: TP close message format**
  - **Validates: Requirements 5.4**

- [x] 8.5 Write property test for Telegram timestamp conversion

  - **Property 24: Telegram timestamp conversion**
  - **Validates: Requirements 5.5**

- [x] 8.6 Write property test for email summary delivery

  - **Property 25: Email summary delivery**
  - **Validates: Requirements 6.2**

- [x] 8.7 Write property test for error email alerts

  - **Property 26: Error email alerts**
  - **Validates: Requirements 6.3**

- [x] 8.8 Write property test for SMTP configuration usage

  - **Property 27: SMTP configuration usage**
  - **Validates: Requirements 6.4**

- [x] 8.9 Write property test for email timestamp conversion

  - **Property 28: Email timestamp conversion**
  - **Validates: Requirements 6.5**

- [x] 8.10 Write property test for heartbeat Telegram messages

  - **Property 29: Heartbeat Telegram messages**
  - **Validates: Requirements 7.2**

- [x] 8.11 Write property test for heartbeat timestamp conversion

  - **Property 30: Heartbeat timestamp conversion**
  - **Validates: Requirements 7.3**

- [x] 8.12 Write property test for lot size in signal message

  - **Property 33: Lot size in signal message**
  - **Validates: Requirements 8.3**

- [x] 9. Implement error handling and logging


  - Set up structured logging with Python logging module
  - Implement ErrorHandler class for centralized error handling
  - Implement handle_startup_error, handle_runtime_error, handle_data_error methods
  - Configure logging to stdout for Docker
  - Implement error log persistence to database
  - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [x] 9.1 Write property test for operation logging

  - **Property 45: Operation logging**
  - **Validates: Requirements 13.1**

- [x] 9.2 Write property test for structured log format

  - **Property 46: Structured log format**
  - **Validates: Requirements 13.2**

- [x] 9.3 Write property test for exception logging completeness

  - **Property 47: Exception logging completeness**
  - **Validates: Requirements 13.3**

- [x] 9.4 Write property test for Docker stdout logging

  - **Property 48: Docker stdout logging**
  - **Validates: Requirements 13.4**

- [x] 10. Implement background services


  - Implement SymbolScannerService class
  - Implement scan_symbol method (fetch data, build context, evaluate signals, check open trades)
  - Implement run_scan_cycle method (iterate all symbols with error isolation)
  - Implement HeartbeatService class
  - Implement send_heartbeats method
  - Implement SummaryEmailService class
  - Implement send_summary method (compile activity from database)
  - Set up APScheduler for periodic task execution
  - _Requirements: 1.3, 6.1, 7.1_

- [x] 11. Implement FastAPI health check endpoint

  - Create FastAPI application instance
  - Implement /health endpoint
  - Check database reachability
  - Check scheduler status
  - Return last heartbeat timestamps
  - Return appropriate HTTP status codes (200 for healthy, 503 for unhealthy)
  - _Requirements: 12.1, 12.2, 12.3_

- [x] 11.1 Write property test for health endpoint response

  - **Property 43: Health endpoint response**
  - **Validates: Requirements 12.2**

- [x] 11.2 Write property test for health status codes

  - **Property 44: Health status codes**
  - **Validates: Requirements 12.3**

- [x] 12. Implement application startup and main entry point


  - Create main.py with FastAPI app initialization
  - Implement startup event handler: load config, connect to DB, run migrations, validate symbols, start background services
  - Implement shutdown event handler: cleanup resources
  - Wire all components together with dependency injection
  - Start FastAPI server with uvicorn
  - _Requirements: 1.1, 1.2, 9.1, 10.1, 10.2_

- [x] 13. Create Docker configuration


  - Write Dockerfile with Python 3.11-slim base
  - Install tzdata and set timezone to Africa/Johannesburg
  - Copy application code and install dependencies
  - Set up entrypoint to run migrations then start uvicorn
  - Write docker-compose.yml with scanner-service, scanner-postgres, and scanner-pgadmin services
  - Configure health checks for PostgreSQL
  - Configure persistent volume for PostgreSQL data
  - Configure logging with json-file driver
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 13.1 Write property test for PostgreSQL readiness wait

  - **Property 41: PostgreSQL readiness wait**
  - **Validates: Requirements 11.4**

- [x] 13.2 Write property test for data persistence across restarts

  - **Property 42: Data persistence across restarts**
  - **Validates: Requirements 11.5**

- [x] 14. Create requirements.txt and dependencies


  - List all Python dependencies with versions: fastapi, uvicorn, sqlalchemy, alembic, yfinance, pandas, numpy, apscheduler, hypothesis, pytest, python-telegram-bot, aiosmtplib, pydantic, pydantic-settings, tenacity, psycopg2-binary
  - Pin versions for reproducibility
  - _Requirements: All_

- [x] 15. Create comprehensive README.md


  - Document system overview and features
  - Explain requirements (Docker, docker-compose)
  - Provide setup instructions: clone, configure .env, docker compose up
  - Document how to view logs and access PgAdmin
  - Explain folder structure
  - Document monitoring and maintenance procedures
  - Include troubleshooting section
  - _Requirements: All_

- [x] 16. Checkpoint - Ensure all tests pass


  - Ensure all tests pass, ask the user if questions arise.
