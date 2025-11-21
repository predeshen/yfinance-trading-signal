# Trading Scanner Python

A production-ready trading scanner service that monitors multiple financial instruments using smart-money concepts (H4 FVG/Order Block strategy) with multi-timeframe analysis.

## Features

- **Multi-Instrument Monitoring**: US30, US30_FT, US100, NAS100, XAUUSD, DAX
- **Smart Money Strategy**: H4 FVG/Order Block with multi-timeframe confirmation (1m, 5m, 15m, 30m, 1h, 4h)
- **Pure Signal Mode**: No broker execution - entry price = price at signal time
- **Dynamic SL/TP**: Based on ATR, structure, and historical MAE/MFE
- **Real-time Alerts**: Telegram notifications for signals, updates, and closures
- **Email Summaries**: Periodic summaries every 2 hours
- **Trade Lifecycle**: State machine tracking (Open, ClosedByTp, ClosedBySl, ClosedManual, Expired)
- **24/7 Operation**: Dockerized service ready for cloud deployment

## Requirements

- Docker
- Docker Compose
- Git

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd trading-scanner-python
```

### 2. Configure Environment

```bash
cp .env.example .env
```

The `.env.example` file already contains working credentials for Telegram and SMTP. You can use them as-is or update with your own:

- `TELEGRAM__BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM__CHAT_ID`: Your Telegram chat ID
- `SMTP__*`: SMTP server configuration for email alerts

### 3. Start Services

```bash
docker compose up -d --build
```

This will start:
- `scanner-service`: Main Python application
- `scanner-postgres`: PostgreSQL database
- `scanner-pgadmin`: PgAdmin web interface (optional)

### 4. View Logs

```bash
# Follow scanner service logs
docker compose logs -f scanner-service

# View all logs
docker compose logs
```

### 5. Check Health

```bash
curl http://localhost:8000/health
```

## Configuration

All configuration is managed through environment variables in `.env`:

### Symbol Mappings

```env
SCANNER__SYMBOLS__DAX=^GDAXI
SCANNER__SYMBOLS__US100=^NDX
SCANNER__SYMBOLS__NAS100=^NDX
SCANNER__SYMBOLS__US30=^DJI
SCANNER__SYMBOLS__US30_FT=^DJI
SCANNER__SYMBOLS__XAUUSD=XAUUSD=X
```

### Scanner Settings

```env
SCANNER__SCAN_INTERVAL_SECONDS=60
SCANNER__HEARTBEAT_INTERVAL_MINUTES=15
SCANNER__EMAIL_SUMMARY_INTERVAL_HOURS=2
SCANNER__RISK_PERCENTAGE=0.01
SCANNER__DEFAULT_EQUITY=10000
```

### Database

```env
POSTGRES_USER=scanner
POSTGRES_PASSWORD=scanner_password
POSTGRES_DB=scanner_db
POSTGRES_HOST=scanner-postgres
POSTGRES_PORT=5432
```

## Monitoring

### Telegram Alerts

The system sends real-time Telegram messages for:
- **[SIGNAL]**: New trading signals
- **[UPDATE]**: SL/TP adjustments
- **[CLOSE]**: Trade closures (TP hit 🎯 or SL hit ❌)
- **[HEARTBEAT]**: Periodic health checks (every 15 minutes)
- **[ERROR]**: Critical errors

### Email Summaries

Every 2 hours, you'll receive an email summary containing:
- Signals generated
- Trades opened/closed
- SL/TP updates
- Errors encountered
- Heartbeat status

### PgAdmin

Access the database GUI at http://localhost:5050

- Email: `admin@scanner.local`
- Password: `admin`

Add server connection:
- Host: `scanner-postgres`
- Port: `5432`
- Database: `scanner_db`
- Username: `scanner`
- Password: `scanner_password`

## Project Structure

```
trading-scanner-python/
├── app/
│   ├── api/              # FastAPI endpoints
│   ├── config/           # Configuration management
│   ├── core/             # Domain logic
│   │   ├── domain/       # Data models
│   │   ├── sl_tp/        # SL/TP estimation
│   │   ├── state_machine/# Trade state machine
│   │   └── strategy/     # Trading strategy
│   ├── data/             # Market data providers
│   ├── db/               # Database models & migrations
│   ├── notifications/    # Telegram & Email services
│   ├── services/         # Background services
│   └── utils/            # Utilities
├── tests/                # Test suite
│   ├── property/         # Property-based tests
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Container definition
├── requirements.txt      # Python dependencies
├── alembic.ini           # Database migrations config
└── .env                  # Environment configuration
```

## Development

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run specific test suite
pytest tests/property/
pytest tests/unit/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Maintenance

### View Logs

```bash
docker compose logs -f scanner-service
```

### Restart Service

```bash
docker compose restart scanner-service
```

### Update Code

```bash
git pull
docker compose up -d --build
```

### Backup Database

```bash
docker exec scanner-postgres pg_dump -U scanner scanner_db > backup.sql
```

### Restore Database

```bash
docker exec -i scanner-postgres psql -U scanner scanner_db < backup.sql
```

## Troubleshooting

### Service Won't Start

1. Check logs: `docker compose logs scanner-service`
2. Verify `.env` file exists and has correct values
3. Ensure PostgreSQL is healthy: `docker compose ps`

### No Telegram Messages

1. Verify `TELEGRAM__BOT_TOKEN` and `TELEGRAM__CHAT_ID` in `.env`
2. Check logs for Telegram errors
3. Test bot token with Telegram Bot API

### No Email Summaries

1. Verify SMTP settings in `.env`
2. Check logs for SMTP errors
3. Test SMTP connection manually

### Database Connection Errors

1. Wait for PostgreSQL to be ready (check with `docker compose ps`)
2. Verify database credentials in `.env`
3. Check PostgreSQL logs: `docker compose logs scanner-postgres`

### Symbol Validation Failures

1. Check internet connection
2. Verify symbol mappings in `.env` use correct yfinance symbols
3. Check yfinance service status

## Architecture

The system follows clean architecture principles:

1. **Data Layer**: yfinance provider with intelligent caching
2. **Domain Layer**: Strategy logic, FVG/OB detection, SL/TP estimation
3. **Service Layer**: Background scanners, heartbeat, email summaries
4. **Infrastructure Layer**: Database, notifications, logging
5. **API Layer**: FastAPI health endpoints

## Strategy

The H4 FVG/Order Block strategy uses:

- **H4 Timeframe**: FVG and OB detection for overall bias
- **H1/M30/M15**: Structure analysis (BOS, CHOCH, liquidity sweeps)
- **M5/M1**: Entry confirmation (wick rejection, micro structure)

SL/TP are dynamically calculated using:
- ATR for volatility
- Recent swing highs/lows for structure
- Historical MAE/MFE for realistic targets

## License

Proprietary - All rights reserved

## Support

For issues or questions, check the logs first:
```bash
docker compose logs -f scanner-service
```

Common log locations:
- Application logs: stdout (captured by Docker)
- Database logs: `docker compose logs scanner-postgres`
- Error logs: Stored in database `error_logs` table
