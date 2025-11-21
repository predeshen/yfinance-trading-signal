# Design Document

## Overview

The Trading Scanner Service is a Python-based application that continuously monitors financial instruments using smart money concepts (FVG/Order Block strategy) with multi-timeframe analysis. The system operates in pure signal mode, generating trading signals without broker execution. It provides real-time notifications via Telegram, periodic email summaries, and maintains a complete audit trail in PostgreSQL.

The architecture follows clean architecture principles with clear separation between:
- Data providers (yfinance integration)
- Domain logic (strategy, signal generation, trade management)
- Infrastructure (database, notifications, scheduling)
- API layer (FastAPI health endpoints)

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI HTTP Server                      │
│                    (Health Check Endpoint)                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Background Services Layer                  │
├─────────────────────────────────────────────────────────────┤
│  SymbolScannerService  │  HeartbeatService  │  EmailService │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Domain Services Layer                   │
├─────────────────────────────────────────────────────────────┤
│  H4FvgStrategy  │  SlTpEstimator  │  TradeStateMachine      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                      │
├─────────────────────────────────────────────────────────────┤
│  YFinanceProvider  │  PostgreSQL  │  Telegram  │  SMTP      │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Startup Sequence**:
   - Load and validate configuration from environment variables
   - Connect to PostgreSQL and run Alembic migrations
   - Validate all symbol mappings with yfinance
   - Initialize background services (scanner, heartbeat, email)
   - Start FastAPI server

2. **Scanning Loop** (every 60 seconds):
   - For each symbol:
     - Fetch/update candles for all timeframes (1m, 5m, 15m, 30m, 1h, 4h)
     - Build MultiTimeframeContext
     - If H4 candle closed: evaluate for new signal
     - For each open trade: evaluate for SL/TP hit or adjustment
     - Send notifications as needed

3. **Heartbeat Loop** (every 15 minutes):
   - Write heartbeat record to database
   - Send Telegram heartbeat message per symbol

4. **Email Summary Loop** (every 2 hours):
   - Compile activity summary from database
   - Send email via SMTP

## Components and Interfaces

### 1. Configuration Management

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class TelegramConfig(BaseSettings):
    bot_token: str = Field(..., alias="TELEGRAM__BOT_TOKEN")
    chat_id: str = Field(..., alias="TELEGRAM__CHAT_ID")
    
    class Config:
        env_file = ".env"

class SmtpConfig(BaseSettings):
    server: str = Field(..., alias="SMTP__SERVER")
    port: int = Field(..., alias="SMTP__PORT")
    user: str = Field(..., alias="SMTP__USER")
    password: str = Field(..., alias="SMTP__PASSWORD")
    from_email: str = Field(..., alias="SMTP__FROM_EMAIL")
    to_email: str = Field(..., alias="SMTP__TO_EMAIL")
    use_ssl: bool = Field(..., alias="SMTP__USE_SSL")
    
    class Config:
        env_file = ".env"

class ScannerConfig(BaseSettings):
    symbols: dict[str, str] = Field(default_factory=dict)  # alias -> yf_symbol
    scan_interval_seconds: int = Field(60, alias="SCANNER__SCAN_INTERVAL_SECONDS")
    heartbeat_interval_minutes: int = Field(15, alias="SCANNER__HEARTBEAT_INTERVAL_MINUTES")
    email_summary_interval_hours: int = Field(2, alias="SCANNER__EMAIL_SUMMARY_INTERVAL_HOURS")
    risk_percentage: float = Field(0.01, alias="SCANNER__RISK_PERCENTAGE")
    default_equity: float = Field(10000, alias="SCANNER__DEFAULT_EQUITY")
    
    class Config:
        env_file = ".env"

class DatabaseConfig(BaseSettings):
    user: str = Field(..., alias="POSTGRES_USER")
    password: str = Field(..., alias="POSTGRES_PASSWORD")
    db: str = Field(..., alias="POSTGRES_DB")
    host: str = Field(..., alias="POSTGRES_HOST")
    port: int = Field(..., alias="POSTGRES_PORT")
    
    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
    
    class Config:
        env_file = ".env"

class AppConfig(BaseSettings):
    timezone: str = Field("Africa/Johannesburg", alias="APP_TIMEZONE")
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    smtp: SmtpConfig = Field(default_factory=SmtpConfig)
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
```

### 2. Market Data Provider

```python
from typing import Protocol
from datetime import datetime, timedelta
import pandas as pd

class MarketDataProvider(Protocol):
    """Protocol for market data providers"""
    
    async def get_candles(
        self,
        symbol: str,
        interval: str,  # "1m", "5m", "15m", "30m", "60m", "240m"
        lookback: timedelta
    ) -> pd.DataFrame:
        """
        Fetch OHLC candles for a symbol and interval.
        
        Returns DataFrame with columns: timestamp, open, high, low, close, volume
        """
        ...
    
    async def validate_symbol(self, symbol: str) -> bool:
        """Validate that a symbol is available"""
        ...

class YFinanceMarketDataProvider:
    """Implementation using yfinance library"""
    
    def __init__(self):
        self._cache: dict[tuple[str, str], pd.DataFrame] = {}
        self._last_fetch: dict[tuple[str, str], datetime] = {}
    
    async def get_candles(
        self,
        symbol: str,
        interval: str,
        lookback: timedelta
    ) -> pd.DataFrame:
        """
        Fetch candles from yfinance with intelligent caching.
        
        On first call: fetch full lookback period
        On subsequent calls: fetch only new candles since last timestamp
        """
        ...
    
    async def validate_symbol(self, symbol: str) -> bool:
        """Attempt to fetch 1 day of data to validate symbol"""
        ...
```

### 3. Strategy Components

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import pandas as pd

@dataclass
class MultiTimeframeContext:
    """Context containing all timeframe data for analysis"""
    alias: str
    yf_symbol: str
    now_utc: datetime
    h4: pd.DataFrame
    h1: pd.DataFrame
    m30: pd.DataFrame
    m15: pd.DataFrame
    m5: pd.DataFrame
    m1: pd.DataFrame
    current_price: float

@dataclass
class Signal:
    """Generated trading signal"""
    symbol_alias: str
    yf_symbol: str
    direction: str  # "buy" or "sell"
    time_generated_utc: datetime
    entry_price_at_signal: float
    initial_sl: float
    initial_tp: float
    strategy_name: str
    notes: str
    estimated_rr: float

class IFvgDetector:
    """Fair Value Gap detector"""
    
    def detect_fvgs(self, df: pd.DataFrame) -> list[dict]:
        """
        Detect FVGs in OHLC data.
        
        Returns list of FVG dictionaries with:
        - start_idx, end_idx
        - gap_high, gap_low
        - direction (bullish/bearish)
        """
        ...

class IOrderBlockDetector:
    """Order Block detector"""
    
    def detect_order_blocks(self, df: pd.DataFrame) -> list[dict]:
        """
        Detect Order Blocks in OHLC data.
        
        Returns list of OB dictionaries with:
        - start_idx, end_idx
        - ob_high, ob_low
        - direction (bullish/bearish)
        """
        ...

class Strategy(Protocol):
    """Protocol for trading strategies"""
    
    async def evaluate_new_signal(
        self,
        ctx: MultiTimeframeContext
    ) -> Optional[Signal]:
        """Evaluate if conditions exist for a new signal"""
        ...
    
    async def evaluate_open_trade(
        self,
        ctx: "TradeContext"
    ) -> Optional["TradeUpdateAction"]:
        """Evaluate if an open trade needs updates"""
        ...

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
        fvg_detector: IFvgDetector,
        ob_detector: IOrderBlockDetector
    ):
        self.fvg_detector = fvg_detector
        self.ob_detector = ob_detector
    
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
        """
        ...
    
    async def evaluate_open_trade(
        self,
        ctx: "TradeContext"
    ) -> Optional["TradeUpdateAction"]:
        """
        Evaluate if open trade needs adjustments.
        
        Checks:
        - Has SL been hit?
        - Has TP been hit?
        - Should SL be moved (BE or trail)?
        - Should TP be extended?
        - Should trade be closed early?
        """
        ...
```

### 4. SL/TP Estimation

```python
from typing import Protocol, Optional

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
    ) -> tuple[float, float]:
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
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def estimate_for_new_signal(
        self,
        ctx: SignalContext
    ) -> tuple[float, float]:
        """
        Estimate SL/TP for new signal.
        
        Steps:
        1. Compute ATR(14) on H4 and H1
        2. Identify nearest swing high/low
        3. Query DB for historical MAE/MFE for this symbol+direction
        4. Set SL: beyond structure + ATR buffer
        5. Set TP: based on median MFE
        """
        ...
    
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
        """
        ...
```

### 5. Trade State Machine

```python
from enum import Enum
from datetime import datetime

class TradeState(str, Enum):
    OPEN = "Open"
    CLOSED_BY_TP = "ClosedByTp"
    CLOSED_BY_SL = "ClosedBySl"
    CLOSED_MANUAL = "ClosedManual"
    EXPIRED = "Expired"

@dataclass
class TradeUpdateAction:
    """Action to apply to a trade"""
    action_type: str  # "close_by_tp", "close_by_sl", "close_manual", "update_sl_tp"
    new_state: Optional[TradeState]
    new_sl: Optional[float]
    new_tp: Optional[float]
    close_reason: Optional[str]
    close_price: Optional[float]

class TradeStateMachine:
    """
    Manages trade state transitions.
    
    State transition rules:
    - Open -> ClosedByTp: when price hits TP
    - Open -> ClosedBySl: when price hits SL
    - Open -> ClosedManual: when early close recommended
    - Open -> Expired: when trade expires (optional)
    
    Important: Once closed, no further TP notifications even if price hits old TP
    """
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def check_and_update_trade(
        self,
        trade_id: int,
        current_price: float,
        candle_high: float,
        candle_low: float
    ) -> Optional[TradeUpdateAction]:
        """
        Check if trade should be updated based on current price.
        
        Returns action if state change needed, None otherwise.
        """
        ...
    
    async def apply_action(
        self,
        trade_id: int,
        action: TradeUpdateAction
    ) -> None:
        """Apply the action to the trade in database"""
        ...
```

### 6. Notification Services

```python
from typing import Protocol

class NotificationService(Protocol):
    """Protocol for notification services"""
    
    async def send_signal_alert(self, signal: Signal, trade_id: int) -> None:
        ...
    
    async def send_update_alert(
        self,
        trade_id: int,
        old_sl: float,
        new_sl: float,
        old_tp: float,
        new_tp: float,
        reason: str
    ) -> None:
        ...
    
    async def send_close_alert(
        self,
        trade_id: int,
        close_type: str,  # "tp" or "sl"
        r_multiple: float
    ) -> None:
        ...
    
    async def send_heartbeat(
        self,
        symbol_alias: str,
        last_scan: datetime,
        open_trade_count: int,
        last_error: Optional[str]
    ) -> None:
        ...
    
    async def send_error_alert(
        self,
        component: str,
        severity: str,
        message: str,
        exception_type: str,
        symbol: Optional[str]
    ) -> None:
        ...

class TelegramNotificationService:
    """Telegram notification implementation"""
    
    def __init__(self, config: TelegramConfig, timezone: str):
        self.bot_token = config.bot_token
        self.chat_id = config.chat_id
        self.tz = timezone
    
    async def send_signal_alert(self, signal: Signal, trade_id: int) -> None:
        """
        Send [SIGNAL] message with format:
        
        [SIGNAL] {alias} ({yf_symbol}) {direction}
        • Time: {timestamp_CAT}
        • Mode: Pure signal (assumed entry at current price)
        • Entry price (signal): {entry_price}
        • Stop Loss: {sl}
        • Take Profit: {tp}
        • Estimated RR (data-based): {rr}
        • TFs: H4 bias, H1/M15 structure, M5/M1 confirmation
        • Strategy: H4 FVG / OB + structure
        • Session: {current_session}
        • Notes: {notes}
        
        ID: {signal_id}
        """
        ...

class EmailNotificationService:
    """Email notification implementation via SMTP"""
    
    def __init__(self, config: SmtpConfig, timezone: str):
        self.config = config
        self.tz = timezone
    
    async def send_summary_email(
        self,
        period_start: datetime,
        period_end: datetime,
        signals: list,
        trades_opened: list,
        trades_closed: list,
        updates: list,
        errors: list
    ) -> None:
        """Send periodic summary email"""
        ...
    
    async def send_error_email(
        self,
        component: str,
        severity: str,
        message: str,
        exception_type: str,
        symbol: Optional[str]
    ) -> None:
        """Send error alert email"""
        ...
```

### 7. Background Services

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class SymbolScannerService:
    """
    Main scanning service that runs periodically.
    
    Responsibilities:
    - Fetch/update market data for all symbols
    - Evaluate for new signals
    - Check open trades for SL/TP hits
    - Apply SL/TP adjustments
    - Send notifications
    """
    
    def __init__(
        self,
        config: ScannerConfig,
        data_provider: MarketDataProvider,
        strategy: Strategy,
        sl_tp_estimator: SlTpEstimator,
        state_machine: TradeStateMachine,
        notification_service: NotificationService,
        db_session
    ):
        self.config = config
        self.data_provider = data_provider
        self.strategy = strategy
        self.sl_tp_estimator = sl_tp_estimator
        self.state_machine = state_machine
        self.notification_service = notification_service
        self.db = db_session
    
    async def scan_symbol(self, alias: str, yf_symbol: str) -> None:
        """
        Scan a single symbol.
        
        Steps:
        1. Fetch/update candles for all timeframes
        2. Build MultiTimeframeContext
        3. Check if H4 candle closed since last scan
        4. If yes: evaluate for new signal
        5. For each open trade on this symbol:
           - Check for SL/TP hit
           - Evaluate for adjustments
        6. Send notifications as needed
        """
        ...
    
    async def run_scan_cycle(self) -> None:
        """Run one complete scan cycle for all symbols"""
        for alias, yf_symbol in self.config.symbols.items():
            try:
                await self.scan_symbol(alias, yf_symbol)
            except Exception as e:
                logger.error(f"Error scanning {alias}: {e}")
                await self.notification_service.send_error_alert(
                    component="SymbolScanner",
                    severity="ERROR",
                    message=str(e),
                    exception_type=type(e).__name__,
                    symbol=alias
                )

class HeartbeatService:
    """Periodic heartbeat service"""
    
    def __init__(
        self,
        notification_service: NotificationService,
        db_session
    ):
        self.notification_service = notification_service
        self.db = db_session
    
    async def send_heartbeats(self) -> None:
        """Send heartbeat for each symbol"""
        ...

class SummaryEmailService:
    """Periodic email summary service"""
    
    def __init__(
        self,
        email_service: EmailNotificationService,
        db_session
    ):
        self.email_service = email_service
        self.db = db_session
    
    async def send_summary(self) -> None:
        """Compile and send email summary"""
        ...
```

## Data Models

### Database Schema (SQLAlchemy)

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True)
    symbol_alias = Column(String, nullable=False, index=True)
    yf_symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # "buy" or "sell"
    time_generated_utc = Column(DateTime, nullable=False, index=True)
    entry_price_at_signal = Column(Float, nullable=False)
    initial_sl = Column(Float, nullable=False)
    initial_tp = Column(Float, nullable=False)
    strategy_name = Column(String, nullable=False)
    notes = Column(String)
    estimated_rr = Column(Float)
    
    # Relationship
    trade = relationship("Trade", back_populates="signal", uselist=False)

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    symbol_alias = Column(String, nullable=False, index=True)
    yf_symbol = Column(String, nullable=False)
    direction = Column(String, nullable=False)
    planned_entry_price = Column(Float, nullable=False)
    actual_entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    state = Column(Enum(TradeState), nullable=False, default=TradeState.OPEN, index=True)
    open_time_utc = Column(DateTime, nullable=False, index=True)
    close_time_utc = Column(DateTime, nullable=True)
    close_price = Column(Float, nullable=True)
    close_reason = Column(String, nullable=True)
    
    # Relationship
    signal = relationship("Signal", back_populates="trade")

class Heartbeat(Base):
    __tablename__ = "heartbeats"
    
    id = Column(Integer, primary_key=True)
    symbol_alias = Column(String, nullable=False, index=True)
    timestamp_utc = Column(DateTime, nullable=False, index=True)
    open_trade_count = Column(Integer, nullable=False)
    last_error = Column(String, nullable=True)

class ErrorLog(Base):
    __tablename__ = "error_logs"
    
    id = Column(Integer, primary_key=True)
    timestamp_utc = Column(DateTime, nullable=False, index=True)
    component = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    message = Column(String, nullable=False)
    exception_type = Column(String, nullable=True)
    symbol_alias = Column(String, nullable=True, index=True)
    stack_trace = Column(String, nullable=True)
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Symbol validation on startup

*For any* configured symbol mapping, when the Scanner Service starts, the system should attempt to fetch sample data from yfinance and validate the symbol is accessible.

**Validates: Requirements 1.1**

### Property 2: Error handling on invalid symbols

*For any* invalid symbol in the configuration, the system should log an error, send a Telegram [ERROR] message, and abort startup with a clear error message.

**Validates: Requirements 1.2**

### Property 3: Multi-timeframe data completeness

*For any* symbol fetch operation, the system should retrieve OHLC candles for all required timeframes (1m, 5m, 15m, 30m, 1h, 4h) or fail with an appropriate error.

**Validates: Requirements 1.4**

### Property 4: Incremental data fetching

*For any* symbol after initial historical data fetch, subsequent fetch operations should only request candles with timestamps newer than the last fetched timestamp.

**Validates: Requirements 1.5**

### Property 5: FVG and Order Block detection

*For any* H4 timeframe data containing Fair Value Gaps or Order Blocks, the detection algorithms should identify them and return their locations and directions.

**Validates: Requirements 2.1**

### Property 6: Structure detection across timeframes

*For any* H1, M30, or M15 timeframe data containing BOS, CHOCH, or liquidity sweep patterns, the structure detection should identify these patterns.

**Validates: Requirements 2.2**

### Property 7: Signal generation on H4 candle close

*For any* H4 candle close event, the system should evaluate multi-timeframe conditions and generate a Signal record if all conditions align.

**Validates: Requirements 2.4, 2.5**

### Property 8: ATR computation for signals

*For any* new signal generation, the system should compute ATR values from H4 and H1 timeframes over the configured lookback period.

**Validates: Requirements 3.1**

### Property 9: Swing point identification

*For any* new signal generation, the system should identify swing highs and lows from recent price structure near the entry zone.

**Validates: Requirements 3.2**

### Property 10: Historical MAE/MFE query

*For any* new signal generation, the system should query the database for historical closed trades matching the symbol and direction to compute typical MAE and MFE values.

**Validates: Requirements 3.3**

### Property 11: Stop-loss placement beyond structure

*For any* new signal, the stop-loss price should be placed beyond the nearest swing point (high for sell, low for buy) plus an ATR-based buffer.

**Validates: Requirements 3.4**

### Property 12: Take-profit based on MFE

*For any* new signal with available historical MFE data, the take-profit price should be calculated based on the median MFE value.

**Validates: Requirements 3.5**

### Property 13: Trade evaluation metrics

*For any* open trade evaluation, the system should compute current risk-reward ratio, analyze trend continuation signals, and calculate time in trade.

**Validates: Requirements 3.6**

### Property 14: Trade creation from signal

*For any* generated signal, the system should create a Trade record with state "Open", storing the planned entry price, stop-loss, and take-profit values.

**Validates: Requirements 4.1**

### Property 15: State transition on SL hit

*For any* open trade where the current price (or candle low for buy, candle high for sell) hits the stop-loss, the trade state should transition to "ClosedBySl" with close time and reason recorded.

**Validates: Requirements 4.2**

### Property 16: State transition on TP hit

*For any* open trade where the current price (or candle high for buy, candle low for sell) hits the take-profit, the trade state should transition to "ClosedByTp" with close time and reason recorded.

**Validates: Requirements 4.3**

### Property 17: Manual closure state transition

*For any* open trade where early closure is recommended and applied, the trade state should transition to "ClosedManual" with the closure reason recorded.

**Validates: Requirements 4.4**

### Property 18: No TP notification for closed trades

*For any* trade in a closed state (ClosedManual, ClosedBySl, Expired), if price later touches the original take-profit level, the system should NOT send a take-profit notification.

**Validates: Requirements 4.5**

### Property 19: TP notification on state transition

*For any* trade that transitions from "Open" to "ClosedByTp", the system should send exactly one congratulatory take-profit Telegram notification.

**Validates: Requirements 4.6**

### Property 20: Signal message completeness

*For any* new signal, the Telegram [SIGNAL] message should contain all required fields: symbol, direction, entry price, SL, TP, estimated RR, timeframe analysis, strategy name, session, notes, and signal ID.

**Validates: Requirements 5.1**

### Property 21: Update message format

*For any* SL or TP adjustment on an open trade, the Telegram [UPDATE] message should show old SL, new SL, old TP, new TP, current price, and adjustment reason.

**Validates: Requirements 5.2**

### Property 22: SL close message format

*For any* trade closed by stop-loss, the Telegram [CLOSE] message should include "SL HIT ❌", entry/exit prices, SL/TP levels, R multiple, and holding time.

**Validates: Requirements 5.3**

### Property 23: TP close message format

*For any* trade closed by take-profit, the Telegram [CLOSE] message should include "TP HIT 🎯", entry/exit prices, SL/TP levels, R multiple, and holding time.

**Validates: Requirements 5.4**

### Property 24: Telegram timestamp conversion

*For any* Telegram message containing timestamps, all times should be converted to Africa/Johannesburg timezone (CAT) before formatting.

**Validates: Requirements 5.5**

### Property 25: Email summary delivery

*For any* compiled email summary, the system should send it via SMTP to the configured recipient email address using the configured SMTP settings.

**Validates: Requirements 6.2**

### Property 26: Error email alerts

*For any* critical error in any system component, the system should send an email alert containing component name, severity, error message, exception type, and affected symbol (if applicable).

**Validates: Requirements 6.3**

### Property 27: SMTP configuration usage

*For any* email send operation, the system should use the SMTP server, port, credentials, and SSL settings loaded from environment variables.

**Validates: Requirements 6.4**

### Property 28: Email timestamp conversion

*For any* email content containing timestamps, all times should be converted to Africa/Johannesburg timezone (CAT) before formatting.

**Validates: Requirements 6.5**

### Property 29: Heartbeat Telegram messages

*For any* heartbeat record written to the database, the system should send a Telegram [HEARTBEAT] message for each monitored symbol showing last scan time, open trade count, and last error.

**Validates: Requirements 7.2**

### Property 30: Heartbeat timestamp conversion

*For any* heartbeat message, timestamps should be converted to Africa/Johannesburg timezone (CAT) before formatting.

**Validates: Requirements 7.3**

### Property 31: Risk amount calculation

*For any* new signal generation, the risk amount should equal the configured equity multiplied by the configured risk percentage.

**Validates: Requirements 8.1**

### Property 32: Lot size calculation

*For any* new signal, the suggested lot size should equal the risk amount divided by (stop-loss distance in points × point value per lot).

**Validates: Requirements 8.2**

### Property 33: Lot size in signal message

*For any* [SIGNAL] Telegram message, the message should include the suggested lot size and risk percentage.

**Validates: Requirements 8.3**

### Property 34: Configuration validation

*For any* configuration loaded from environment variables, the system should validate all required fields (Telegram token, SMTP settings, database credentials, symbol mappings) and fail with clear errors if validation fails.

**Validates: Requirements 9.2, 9.3**

### Property 35: Symbol mapping parsing

*For any* symbol mapping in environment variables following the format "SCANNER__SYMBOLS__ALIAS=yfinance_symbol", the system should correctly parse the alias and yfinance symbol.

**Validates: Requirements 9.4**

### Property 36: Timezone configuration usage

*For any* timestamp conversion operation, the system should use the timezone configured in APP_TIMEZONE environment variable.

**Validates: Requirements 9.5**

### Property 37: Automatic database migrations

*For any* Scanner Service startup with established database connection, the system should automatically run Alembic migrations to bring the schema up to date.

**Validates: Requirements 10.2**

### Property 38: Signal persistence

*For any* generated signal, the system should persist a Signal record to PostgreSQL with all required fields: symbol_alias, yf_symbol, direction, time_generated_utc, entry_price_at_signal, initial_sl, initial_tp, strategy_name, notes, estimated_rr.

**Validates: Requirements 10.3**

### Property 39: Trade persistence

*For any* trade creation or update operation, the system should persist the Trade record with current state, prices, timestamps, and foreign key relationship to the Signal record.

**Validates: Requirements 10.4**

### Property 40: Historical trade query filtering

*For any* MAE/MFE calculation query, the system should retrieve only closed trades (state != Open) filtered by the specified symbol and direction.

**Validates: Requirements 10.5**

### Property 41: PostgreSQL readiness wait

*For any* scanner-service container startup, the system should wait for PostgreSQL to be ready and accepting connections before attempting to run migrations or start the application.

**Validates: Requirements 11.4**

### Property 42: Data persistence across restarts

*For any* PostgreSQL data written before a container restart, the data should still be accessible after the container restarts due to persistent volume mounting.

**Validates: Requirements 11.5**

### Property 43: Health endpoint response

*For any* GET request to /health endpoint, the system should return a JSON response containing database reachability status, scheduler status, and last heartbeat timestamps.

**Validates: Requirements 12.2**

### Property 44: Health status codes

*For any* health check evaluation, the system should return HTTP 200 when all components are healthy and HTTP 503 when any component is unhealthy.

**Validates: Requirements 12.3**

### Property 45: Operation logging

*For any* system operation (data fetch, signal generation, trade update, notification send), the system should log the operation with an appropriate log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

**Validates: Requirements 13.1**

### Property 46: Structured log format

*For any* log output to stdout, the log entry should follow structured format including timestamp, log level, component name, and message.

**Validates: Requirements 13.2**

### Property 47: Exception logging completeness

*For any* exception that occurs, the system should log the full stack trace, exception type, exception message, and context information.

**Validates: Requirements 13.3**

### Property 48: Docker stdout logging

*For any* log generated when running in Docker environment, the log should be written to stdout for Docker log collection.

**Validates: Requirements 13.4**

### Property 49: 1-minute data period limitation

*For any* 1-minute timeframe data fetch request, the system should only request data for the recent period (e.g., last 7 days) to comply with yfinance limitations.

**Validates: Requirements 14.1**

### Property 50: Symbol fetch error isolation

*For any* data fetch failure for a specific symbol, the system should log the error, send an error alert, but continue processing remaining symbols in the scan cycle.

**Validates: Requirements 14.2**

### Property 51: Rate limit retry with backoff

*For any* yfinance rate limit error encountered, the system should implement exponential backoff retry logic before failing the operation.

**Validates: Requirements 14.3**

### Property 52: Insufficient data handling

*For any* analysis attempt with insufficient historical data, the system should skip signal generation for that symbol, log a warning, and continue with other symbols.

**Validates: Requirements 14.4**

## Error Handling

### Error Categories

1. **Startup Errors** (Fatal - abort startup):
   - Configuration validation failures
   - Database connection failures
   - Symbol validation failures
   - Missing required environment variables

2. **Runtime Errors** (Non-fatal - log and continue):
   - Individual symbol data fetch failures
   - yfinance rate limits
   - Telegram API failures
   - SMTP send failures

3. **Data Errors** (Non-fatal - skip and warn):
   - Insufficient historical data
   - Malformed candle data
   - Missing timeframe data

### Error Handling Strategy

```python
class ErrorHandler:
    """Centralized error handling"""
    
    def __init__(
        self,
        notification_service: NotificationService,
        db_session
    ):
        self.notification_service = notification_service
        self.db = db_session
    
    async def handle_startup_error(
        self,
        component: str,
        error: Exception
    ) -> None:
        """
        Handle fatal startup errors.
        
        Actions:
        1. Log error with full stack trace
        2. Send Telegram error alert
        3. Send email error alert
        4. Raise exception to abort startup
        """
        ...
    
    async def handle_runtime_error(
        self,
        component: str,
        error: Exception,
        symbol: Optional[str] = None
    ) -> None:
        """
        Handle non-fatal runtime errors.
        
        Actions:
        1. Log error with context
        2. Write to error_logs table
        3. Send Telegram error alert
        4. Continue execution
        """
        ...
    
    async def handle_data_error(
        self,
        symbol: str,
        error: Exception
    ) -> None:
        """
        Handle data-related errors.
        
        Actions:
        1. Log warning
        2. Skip current operation
        3. Continue with next symbol
        """
        ...
```

### Retry Logic

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class RetryableOperation:
    """Wrapper for operations that should be retried"""
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError))
    )
    async def fetch_with_retry(
        self,
        symbol: str,
        interval: str,
        lookback: timedelta
    ) -> pd.DataFrame:
        """Fetch data with exponential backoff retry"""
        ...
```

## Testing Strategy

### Unit Testing

Unit tests will verify specific examples and edge cases using pytest:

1. **Configuration Tests**:
   - Valid configuration loading
   - Invalid configuration rejection
   - Symbol mapping parsing
   - Environment variable precedence

2. **Data Provider Tests**:
   - Symbol validation with valid/invalid symbols
   - Candle fetching for different timeframes
   - Caching behavior
   - Error handling for API failures

3. **Strategy Component Tests**:
   - FVG detection with known patterns
   - Order Block detection with known patterns
   - ATR calculation accuracy
   - Swing point identification

4. **State Machine Tests**:
   - State transitions (Open → ClosedByTp, etc.)
   - SL/TP hit detection
   - No duplicate notifications for closed trades

5. **Notification Tests**:
   - Message formatting
   - Timezone conversion
   - Field completeness

6. **Database Tests**:
   - Signal persistence
   - Trade persistence
   - Historical query filtering
   - Migration execution

### Property-Based Testing

Property-based tests will verify universal properties using Hypothesis (Python PBT library):

**Configuration**:
- Each property test should run a minimum of 100 iterations
- Each test must be tagged with a comment referencing the design document property
- Tag format: `# Feature: trading-scanner-python, Property {number}: {property_text}`

**Property Test Examples**:

1. **Property 4: Incremental data fetching**
   ```python
   # Feature: trading-scanner-python, Property 4: Incremental data fetching
   @given(symbol=st.text(), initial_data=st.dataframes(...))
   @settings(max_examples=100)
   def test_incremental_fetching_only_requests_new_data(symbol, initial_data):
       """For any symbol after initial fetch, subsequent fetches should only request new candles"""
       ...
   ```

2. **Property 11: Stop-loss placement beyond structure**
   ```python
   # Feature: trading-scanner-python, Property 11: Stop-loss placement beyond structure
   @given(
       direction=st.sampled_from(["buy", "sell"]),
       entry_price=st.floats(min_value=1.0, max_value=100000.0),
       swing_points=st.lists(st.floats(min_value=1.0, max_value=100000.0)),
       atr=st.floats(min_value=0.1, max_value=1000.0)
   )
   @settings(max_examples=100)
   def test_sl_placement_beyond_structure(direction, entry_price, swing_points, atr):
       """For any signal, SL should be beyond nearest swing point plus ATR buffer"""
       ...
   ```

3. **Property 18: No TP notification for closed trades**
   ```python
   # Feature: trading-scanner-python, Property 18: No TP notification for closed trades
   @given(
       closed_state=st.sampled_from([TradeState.CLOSED_MANUAL, TradeState.CLOSED_BY_SL]),
       original_tp=st.floats(min_value=1.0, max_value=100000.0),
       current_price=st.floats(min_value=1.0, max_value=100000.0)
   )
   @settings(max_examples=100)
   def test_no_tp_notification_for_closed_trades(closed_state, original_tp, current_price):
       """For any closed trade, no TP notification should be sent even if price hits old TP"""
       ...
   ```

4. **Property 24: Telegram timestamp conversion**
   ```python
   # Feature: trading-scanner-python, Property 24: Telegram timestamp conversion
   @given(
       utc_timestamp=st.datetimes(
           min_value=datetime(2020, 1, 1),
           max_value=datetime(2030, 12, 31)
       )
   )
   @settings(max_examples=100)
   def test_telegram_timestamp_conversion_to_cat(utc_timestamp):
       """For any Telegram message with timestamps, times should be in CAT"""
       ...
   ```

5. **Property 35: Symbol mapping parsing**
   ```python
   # Feature: trading-scanner-python, Property 35: Symbol mapping parsing
   @given(
       alias=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
       yf_symbol=st.text(min_size=1, max_size=20)
   )
   @settings(max_examples=100)
   def test_symbol_mapping_parsing(alias, yf_symbol):
       """For any symbol mapping format, parsing should extract alias and yf_symbol correctly"""
       ...
   ```

6. **Property 50: Symbol fetch error isolation**
   ```python
   # Feature: trading-scanner-python, Property 50: Symbol fetch error isolation
   @given(
       symbols=st.lists(st.text(min_size=1), min_size=2, max_size=10),
       failing_symbol_index=st.integers(min_value=0, max_value=9)
   )
   @settings(max_examples=100)
   def test_symbol_fetch_error_isolation(symbols, failing_symbol_index):
       """For any symbol fetch failure, other symbols should continue processing"""
       ...
   ```

### Integration Testing

Integration tests will verify end-to-end workflows:

1. **Startup Integration**:
   - Full startup sequence with real PostgreSQL
   - Configuration loading → DB connection → migrations → service start

2. **Scan Cycle Integration**:
   - Complete scan cycle with mock yfinance data
   - Signal generation → trade creation → notification sending

3. **Trade Lifecycle Integration**:
   - Open trade → SL hit → state transition → notification
   - Open trade → TP hit → state transition → notification

4. **Notification Integration**:
   - Telegram API integration (with test bot)
   - SMTP integration (with test email server)

### Test Structure

```
/tests
  /unit
    /core
      test_strategy.py
      test_sl_tp_estimator.py
      test_state_machine.py
    /data
      test_yfinance_provider.py
      test_fvg_detector.py
      test_ob_detector.py
    /services
      test_scanner_service.py
      test_notification_service.py
    /db
      test_models.py
      test_queries.py
  /property
    test_properties_data.py
    test_properties_state.py
    test_properties_notifications.py
    test_properties_config.py
  /integration
    test_startup.py
    test_scan_cycle.py
    test_trade_lifecycle.py
  /fixtures
    sample_candles.py
    mock_config.py
```

## Deployment

### Docker Configuration

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Install timezone data
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=Africa/Johannesburg
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose health check port
EXPOSE 8000

# Run migrations and start application
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  scanner-postgres:
    image: postgres:16
    container_name: scanner-postgres
    env_file:
      - .env
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - scanner-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  scanner-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: scanner-service
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      scanner-postgres:
        condition: service_healthy
    networks:
      - scanner-network
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  scanner-pgadmin:
    image: dpage/pgadmin4
    container_name: scanner-pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}
    ports:
      - "5050:80"
    networks:
      - scanner-network
    depends_on:
      - scanner-postgres

networks:
  scanner-network:
    driver: bridge

volumes:
  postgres_data:
```

### Deployment Steps

1. **Clone repository**:
   ```bash
   git clone <repository-url>
   cd trading-scanner-python
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials (Telegram, SMTP already provided)
   ```

3. **Build and start services**:
   ```bash
   docker compose up -d --build
   ```

4. **View logs**:
   ```bash
   docker compose logs -f scanner-service
   ```

5. **Check health**:
   ```bash
   curl http://localhost:8000/health
   ```

6. **Access PgAdmin** (optional):
   - Navigate to http://localhost:5050
   - Login with credentials from .env
   - Add server: scanner-postgres:5432

### Monitoring

1. **Health Check Endpoint**: `/health` returns JSON with system status
2. **Docker Logs**: `docker compose logs -f scanner-service`
3. **Telegram Heartbeats**: Every 15 minutes per symbol
4. **Email Summaries**: Every 2 hours with activity report
5. **Error Alerts**: Immediate Telegram + email on critical errors

### Maintenance

1. **Update code**:
   ```bash
   git pull
   docker compose up -d --build
   ```

2. **View database**:
   - Use PgAdmin at http://localhost:5050
   - Or connect directly: `psql -h localhost -U scanner -d scanner_db`

3. **Backup database**:
   ```bash
   docker exec scanner-postgres pg_dump -U scanner scanner_db > backup.sql
   ```

4. **Restore database**:
   ```bash
   docker exec -i scanner-postgres psql -U scanner scanner_db < backup.sql
   ```

## Future Enhancements

### Phase 2 Features (Optional)

1. **Session Management**:
   - Implement session detection (Asia, London, NY)
   - Send session change alerts
   - NY equity open special alert at 16:30 CAT

2. **News Integration**:
   - Integrate economic calendar API
   - Daily news summary at 06:00 CAT
   - Pre-event alerts (e.g., "NFP in 30 minutes")

3. **Influencer Feed**:
   - Stub interface for future Twitter/X integration
   - Sentiment analysis from trading influencers

4. **Advanced Analytics**:
   - Win rate by symbol, session, timeframe
   - MAE/MFE distribution charts
   - Equity curve tracking

5. **Web Dashboard**:
   - Real-time trade monitoring
   - Historical performance charts
   - Manual trade management interface

6. **Multi-Strategy Support**:
   - Plug additional strategies alongside H4 FVG
   - Strategy performance comparison
   - Strategy ensemble voting

## Appendix

### Folder Structure

```
/trading-scanner-python
  /.kiro
    /specs
      /trading-scanner-python
        requirements.md
        design.md
        tasks.md
  /app
    /core
      /domain
        signal.py
        trade.py
        multi_timeframe_context.py
      /strategy
        strategy_protocol.py
        h4_fvg_strategy.py
        fvg_detector.py
        ob_detector.py
      /sl_tp
        sl_tp_estimator_protocol.py
        dynamic_sl_tp_estimator.py
      /state_machine
        trade_state_machine.py
    /data
      market_data_provider_protocol.py
      yfinance_provider.py
    /services
      scanner_service.py
      heartbeat_service.py
      summary_email_service.py
    /notifications
      notification_service_protocol.py
      telegram_service.py
      email_service.py
    /db
      /models
        signal.py
        trade.py
        heartbeat.py
        error_log.py
      /migrations
        (Alembic migration files)
      database.py
      session.py
    /api
      main.py
      health.py
    /config
      settings.py
      timezone.py
    /utils
      logging.py
      error_handler.py
      retry.py
  /tests
    (as described in Testing Strategy)
  /docker
    Dockerfile
    docker-compose.yml
  .env.example
  .env
  requirements.txt
  alembic.ini
  README.md
```

### Technology Versions

- Python: 3.11+
- PostgreSQL: 16
- FastAPI: 0.104+
- SQLAlchemy: 2.0+
- Alembic: 1.12+
- yfinance: 0.2.32+
- pandas: 2.1+
- numpy: 1.26+
- APScheduler: 3.10+
- Hypothesis: 6.92+ (for property-based testing)
- pytest: 7.4+
- python-telegram-bot: 20.7+ (or raw requests)
- aiosmtplib: 3.0+ (for async SMTP)
- pydantic: 2.5+
- pydantic-settings: 2.1+
- tenacity: 8.2+ (for retry logic)

### Environment Variable Reference

See `.env.example` in the requirements document for complete list of environment variables with actual values provided.
