# Native Setup (Without Docker)

This guide will help you run the trading scanner directly on your VM without Docker.

## Prerequisites

- Ubuntu/Debian Linux
- Python 3.11+
- sudo access

## Step 1: Stop Docker Services

```bash
docker compose down
```

## Step 2: Install PostgreSQL

```bash
chmod +x install_postgres.sh
./install_postgres.sh
```

## Step 3: Install Python Dependencies

```bash
# Install pip if not already installed
sudo apt install -y python3-pip python3-venv

# Install dependencies
pip3 install -r requirements.txt
```

## Step 4: Update Environment Variables

Edit `.env` and change:
```
POSTGRES_HOST=scanner-postgres
```
to:
```
POSTGRES_HOST=localhost
```

## Step 5: Run Database Migrations

```bash
alembic upgrade head
```

## Step 6: Test the Application

```bash
# Run directly to test
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Check logs in another terminal
# Press Ctrl+C to stop when done testing
```

## Step 7: Set Up as System Service

```bash
chmod +x setup_service.sh
./setup_service.sh
```

## Step 8: Start the Service

```bash
# Start the service
sudo systemctl start trading-scanner

# Check status
sudo systemctl status trading-scanner

# View logs
sudo journalctl -u trading-scanner -f
```

## Managing the Service

```bash
# Start
sudo systemctl start trading-scanner

# Stop
sudo systemctl stop trading-scanner

# Restart
sudo systemctl restart trading-scanner

# View logs
sudo journalctl -u trading-scanner -f

# View last 100 lines
sudo journalctl -u trading-scanner -n 100

# Disable service
sudo systemctl disable trading-scanner
```

## Troubleshooting

### Check if PostgreSQL is running
```bash
sudo systemctl status postgresql
```

### Test database connection
```bash
psql -h localhost -U scanner -d scanner_db
# Password: scanner_password
```

### Check Python dependencies
```bash
pip3 list | grep -E "fastapi|uvicorn|sqlalchemy|yfinance"
```

### View application logs
```bash
sudo journalctl -u trading-scanner -f --no-pager
```

## Benefits of Native Setup

1. **Better network access** - No Docker network isolation
2. **Easier debugging** - Direct access to logs and processes
3. **Better performance** - No containerization overhead
4. **Simpler updates** - Just `git pull` and restart

## Reverting to Docker

If you want to go back to Docker:

```bash
# Stop the service
sudo systemctl stop trading-scanner
sudo systemctl disable trading-scanner

# Update .env back
sed -i 's/POSTGRES_HOST=localhost/POSTGRES_HOST=scanner-postgres/' .env

# Start Docker
docker compose up -d --build
```
