#!/bin/bash
# Setup script to run the trading scanner as a systemd service

set -e

echo "Setting up Trading Scanner Service..."

# Get the current directory
APP_DIR=$(pwd)
USER=$(whoami)

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Update database host in .env for local PostgreSQL
echo "Updating .env for local setup..."
sed -i 's/POSTGRES_HOST=scanner-postgres/POSTGRES_HOST=localhost/' .env

# Create systemd service file
echo "Creating systemd service..."
sudo tee /etc/systemd/system/trading-scanner.service > /dev/null <<EOF
[Unit]
Description=Trading Scanner Service
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable and start the service
echo "Enabling service..."
sudo systemctl enable trading-scanner.service

echo ""
echo "✓ Setup complete!"
echo ""
echo "To start the service:"
echo "  sudo systemctl start trading-scanner"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u trading-scanner -f"
echo ""
echo "To check status:"
echo "  sudo systemctl status trading-scanner"
echo ""
