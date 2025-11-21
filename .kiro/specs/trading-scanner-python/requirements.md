# Requirements Document

## Introduction

This document specifies the requirements for a Python-based, production-ready trading scanner service that monitors multiple financial instruments using a smart-money strategy (H4 FVG/Order Block with multi-timeframe analysis). The system operates in pure signal mode (no broker execution), sends real-time alerts via Telegram and email, tracks trade lifecycle with a state machine, and runs 24/7 as a Dockerized service on Google Cloud VM.

## Glossary

- **Scanner Service**: The main Python application that monitors instruments and generates trading signals
- **FVG**: Fair Value Gap - a price imbalance area used in smart money concepts
- **Order Block (OB)**: A consolidation area before a strong move, indicating institutional activity
- **BOS**: Break of Structure - price breaking a significant high/low
- **CHOCH**: Change of Character - shift in market structure indicating potential reversal
- **MAE**: Maximum Adverse Excursion - the worst drawdown a trade experiences
- **MFE**: Maximum Favorable Excursion - the best profit a trade achieves
- **ATR**: Average True Range - volatility indicator
- **RR**: Risk-Reward ratio
- **Pure Signal Mode**: Trading mode where entry price equals the price at signal generation time (no broker execution)
- **Trade State Machine**: System managing trade lifecycle states (Open, ClosedByTp, ClosedBySl, ClosedManual, Expired)
- **yfinance**: Yahoo Finance Python library for market data
- **Multi-Timeframe Context**: Analysis combining data from 1m, 5m, 15m, 30m, 1h, and 4h timeframes
- **CAT**: Central Africa Time (Africa/Johannesburg timezone)

## Requirements

### Requirement 1

**User Story:** As a trader, I want the system to monitor multiple financial instruments continuously, so that I can receive trading signals across different markets.

#### Acceptance Criteria

1. WHEN the Scanner Service starts THEN the system SHALL validate all configured symbol mappings (US30→^DJI, US30_FT→^DJI, US100→^NDX, NAS100→^NDX, DAX→^GDAXI, XAUUSD→XAUUSD=X) by fetching sample data from yfinance
2. WHEN any symbol validation fails during startup THEN the system SHALL log the error, send a Telegram [ERROR] message, and abort startup with clear error messages
3. WHILE the Scanner Service is running THEN the system SHALL fetch and update market data for all configured symbols at the configured scan interval
4. WHEN fetching market data THEN the system SHALL retrieve OHLC candles for all required timeframes (1m, 5m, 15m, 30m, 1h, 4h) from yfinance
5. WHEN the system has fetched initial historical data THEN the system SHALL only fetch new candles since the last timestamp on subsequent scans to minimize API load

### Requirement 2

**User Story:** As a trader, I want the system to analyze market data using a H4 FVG/Order Block strategy with multi-timeframe confirmation, so that I receive high-quality trading signals.

#### Acceptance Criteria

1. WHEN analyzing H4 timeframe data THEN the system SHALL detect Fair Value Gaps and Order Blocks to determine overall market bias
2. WHEN analyzing H1, M30, and M15 timeframe data THEN the system SHALL identify structure changes including BOS, CHOCH, and liquidity sweeps
3. WHEN analyzing M5 and M1 timeframe data THEN the system SHALL evaluate entry context and confirmation signals including wick rejections and micro structure
4. WHEN a H4 candle closes THEN the system SHALL evaluate whether conditions exist for generating a new trading signal
5. WHEN all multi-timeframe conditions align THEN the system SHALL generate a Signal record with direction (buy/sell), entry price, and strategy notes

### Requirement 3

**User Story:** As a trader, I want the system to compute dynamic stop-loss and take-profit levels based on historical performance and market volatility, so that my risk management adapts to market conditions.

#### Acceptance Criteria

1. WHEN generating a new signal THEN the system SHALL compute ATR values from H4 and H1 timeframes over recent candles
2. WHEN generating a new signal THEN the system SHALL identify swing highs and lows near the entry zone from recent price structure
3. WHEN generating a new signal THEN the system SHALL query historical trade data to compute typical MAE and MFE values for the symbol and direction
4. WHEN setting stop-loss THEN the system SHALL place it beyond recent structure plus an ATR-based buffer
5. WHEN setting take-profit THEN the system SHALL place it based on typical MFE values (near median MFE from historical data)
6. WHEN evaluating an open trade THEN the system SHALL analyze current risk-reward ratio, trend continuation signals, and time in trade to determine if SL/TP adjustments are needed

### Requirement 4

**User Story:** As a trader, I want the system to track trade lifecycle through a state machine, so that I have clear visibility into trade status and outcomes.

#### Acceptance Criteria

1. WHEN a new signal is generated THEN the system SHALL create a Trade record with state "Open" and store planned entry price, stop-loss, and take-profit
2. WHEN scanning an open trade and price hits the stop-loss THEN the system SHALL transition trade state to "ClosedBySl" and record close time and reason
3. WHEN scanning an open trade and price hits the take-profit THEN the system SHALL transition trade state to "ClosedByTp" and record close time and reason
4. WHEN the system recommends early closure and it is applied THEN the system SHALL transition trade state to "ClosedManual" and record the closure reason
5. WHEN a trade is in a closed state (ClosedManual, ClosedBySl, Expired) and price later touches the original take-profit THEN the system SHALL NOT send a take-profit notification
6. WHEN a trade transitions from "Open" to "ClosedByTp" THEN the system SHALL send a congratulatory take-profit notification

### Requirement 5

**User Story:** As a trader, I want to receive real-time Telegram alerts for signals, trade updates, and closures, so that I can act on opportunities immediately.

#### Acceptance Criteria

1. WHEN a new signal is generated THEN the system SHALL send a Telegram [SIGNAL] message containing symbol, direction, entry price, SL, TP, estimated RR, timeframe analysis, strategy name, session, and signal ID
2. WHEN an open trade has SL or TP adjusted THEN the system SHALL send a Telegram [UPDATE] message showing old and new SL/TP values, current price, and adjustment reason
3. WHEN an open trade is closed by stop-loss THEN the system SHALL send a Telegram [CLOSE] message with "SL HIT ❌" including entry/exit prices, SL/TP, R multiple, and holding time
4. WHEN an open trade is closed by take-profit THEN the system SHALL send a Telegram [CLOSE] message with "TP HIT 🎯" including entry/exit prices, SL/TP, R multiple, and holding time
5. WHEN formatting any Telegram message with timestamps THEN the system SHALL convert all times to Africa/Johannesburg timezone (CAT)

### Requirement 6

**User Story:** As a trader, I want to receive email summaries every 2 hours and error alerts, so that I have a comprehensive record of system activity and can respond to issues.

#### Acceptance Criteria

1. WHEN the configured email summary interval elapses THEN the system SHALL compile a summary of signals, opened/closed trades, SL/TP updates, errors, and heartbeats from the period
2. WHEN the email summary is compiled THEN the system SHALL send it via SMTP to the configured recipient email address
3. WHEN a critical error occurs in any system component THEN the system SHALL send an email alert containing error severity, message, exception type, and affected symbol
4. WHEN sending emails via SMTP THEN the system SHALL use the configured SMTP server, port, credentials, and SSL settings from environment variables
5. WHEN formatting any email content with timestamps THEN the system SHALL convert all times to Africa/Johannesburg timezone (CAT)

### Requirement 7

**User Story:** As a system administrator, I want the system to send periodic heartbeat messages, so that I can verify the scanner is running and healthy.

#### Acceptance Criteria

1. WHEN the configured heartbeat interval elapses THEN the system SHALL write a heartbeat record to the database with current timestamp
2. WHEN writing a heartbeat record THEN the system SHALL send a Telegram [HEARTBEAT] message for each monitored symbol showing last scan time, open trade count, and last error (if any)
3. WHEN formatting heartbeat timestamps THEN the system SHALL convert all times to Africa/Johannesburg timezone (CAT)

### Requirement 8

**User Story:** As a trader, I want the system to suggest position sizes based on configured risk parameters, so that I can maintain consistent risk management.

#### Acceptance Criteria

1. WHEN generating a new signal THEN the system SHALL compute risk amount using configured equity and risk percentage
2. WHEN computing position size THEN the system SHALL calculate lot size based on risk amount divided by stop-loss distance in points multiplied by point value per lot
3. WHEN sending a [SIGNAL] Telegram message THEN the system SHALL include suggested lot size and risk percentage in the message

### Requirement 9

**User Story:** As a developer, I want all configuration managed through environment variables, so that I can deploy the system without code changes.

#### Acceptance Criteria

1. WHEN the Scanner Service starts THEN the system SHALL load all configuration from environment variables using Pydantic settings classes
2. WHEN loading configuration THEN the system SHALL validate required fields including Telegram bot token, chat ID, SMTP settings, symbol mappings, and database credentials
3. WHEN configuration validation fails THEN the system SHALL log clear error messages and abort startup
4. WHEN symbol mappings are loaded THEN the system SHALL parse them from environment variables in the format "SCANNER__SYMBOLS__ALIAS=yfinance_symbol"
5. WHEN timezone configuration is loaded THEN the system SHALL use the configured APP_TIMEZONE for all timestamp conversions

### Requirement 10

**User Story:** As a developer, I want the system to persist all signals, trades, and events in PostgreSQL, so that I have a reliable audit trail and can analyze historical performance.

#### Acceptance Criteria

1. WHEN the Scanner Service starts THEN the system SHALL connect to PostgreSQL using credentials from environment variables
2. WHEN the database connection is established THEN the system SHALL automatically run Alembic migrations to ensure schema is up to date
3. WHEN a signal is generated THEN the system SHALL persist a Signal record with symbol, direction, entry price, SL, TP, timestamp, and strategy notes
4. WHEN a trade is created or updated THEN the system SHALL persist the Trade record with current state, prices, timestamps, and relationships to Signal
5. WHEN querying historical trade data for MAE/MFE calculations THEN the system SHALL retrieve closed trades filtered by symbol and direction

### Requirement 11

**User Story:** As a system administrator, I want the system packaged as Docker containers with docker-compose, so that I can deploy it easily on any Linux VM.

#### Acceptance Criteria

1. WHEN building the Docker image THEN the system SHALL use Python 3.11+ base image and install all required dependencies
2. WHEN the Docker container starts THEN the system SHALL set the timezone to Africa/Johannesburg and configure logging to stdout
3. WHEN running docker-compose up THEN the system SHALL start both scanner-service and scanner-postgres containers with proper networking
4. WHEN the scanner-service container starts THEN the system SHALL wait for PostgreSQL to be ready before running migrations and starting the application
5. WHEN docker-compose is configured THEN the system SHALL mount a persistent volume for PostgreSQL data to prevent data loss on container restart

### Requirement 12

**User Story:** As a developer, I want the system to expose a health check HTTP endpoint, so that I can monitor service status and integrate with orchestration tools.

#### Acceptance Criteria

1. WHEN the Scanner Service starts THEN the system SHALL start a FastAPI HTTP server on port 8000
2. WHEN a GET request is made to /health THEN the system SHALL return a JSON response indicating database reachability, scheduler status, and last heartbeat timestamps
3. WHEN the health check detects issues THEN the system SHALL return appropriate HTTP status codes (200 for healthy, 503 for unhealthy)

### Requirement 13

**User Story:** As a developer, I want comprehensive logging throughout the system, so that I can troubleshoot issues and monitor system behavior.

#### Acceptance Criteria

1. WHEN any system component performs an operation THEN the system SHALL log the operation with appropriate log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
2. WHEN logging to stdout THEN the system SHALL use structured logging format including timestamp, level, component, and message
3. WHEN an exception occurs THEN the system SHALL log the full stack trace and exception details
4. WHEN the system is running in Docker THEN the system SHALL ensure all logs are written to stdout for Docker log collection

### Requirement 14

**User Story:** As a trader, I want the system to handle yfinance data limitations gracefully, so that the scanner continues operating even with partial data availability.

#### Acceptance Criteria

1. WHEN fetching 1-minute data THEN the system SHALL only request data for the recent period (e.g., last 7 days) due to yfinance limitations
2. WHEN a data fetch fails for a symbol THEN the system SHALL log the error, send an error alert, but continue processing other symbols
3. WHEN yfinance rate limits are encountered THEN the system SHALL implement exponential backoff and retry logic
4. WHEN historical data is insufficient for analysis THEN the system SHALL skip signal generation for that symbol and log a warning

### Requirement 15

**User Story:** As a developer, I want clear separation between data providers, strategy logic, and notification services, so that the system is maintainable and extensible.

#### Acceptance Criteria

1. WHEN implementing market data access THEN the system SHALL define a MarketDataProvider protocol with get_candles method
2. WHEN implementing strategy logic THEN the system SHALL define a Strategy protocol with evaluate_new_signal and evaluate_open_trade methods
3. WHEN implementing SL/TP calculation THEN the system SHALL define a SlTpEstimator protocol with estimate_for_new_signal and evaluate_adjustment methods
4. WHEN implementing FVG detection THEN the system SHALL create an IFvgDetector class that operates on pandas DataFrames
5. WHEN implementing Order Block detection THEN the system SHALL create an IOrderBlockDetector class that operates on pandas DataFrames
