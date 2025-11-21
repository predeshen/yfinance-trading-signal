#!/bin/bash
# Install and configure PostgreSQL locally

set -e

echo "Installing PostgreSQL..."

# Install PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
echo "Creating database and user..."
sudo -u postgres psql <<EOF
CREATE DATABASE scanner_db;
CREATE USER scanner WITH PASSWORD 'scanner_password';
GRANT ALL PRIVILEGES ON DATABASE scanner_db TO scanner;
\q
EOF

echo ""
echo "✓ PostgreSQL installed and configured!"
echo ""
echo "Database: scanner_db"
echo "User: scanner"
echo "Password: scanner_password"
echo ""
