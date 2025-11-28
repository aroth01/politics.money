#!/bin/bash
#
# Quick script to create the polstats user if it doesn't exist
#

set -e

if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

USER="polstats"
GROUP="polstats"
PROJECT_DIR="/var/www/polstats"

echo "Creating user and setting up permissions..."

# Create user if it doesn't exist
if ! id "$USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$PROJECT_DIR" "$USER"
    echo "✓ User $USER created"
else
    echo "✓ User $USER already exists"
fi

# Create necessary directories
mkdir -p "$PROJECT_DIR/logs"
mkdir -p /var/log/polstats
mkdir -p /var/backups/polstats

# Set ownership
chown -R "$USER:$GROUP" "$PROJECT_DIR"
chown -R "$USER:$GROUP" /var/log/polstats
chown -R root:root /var/backups/polstats
chmod 755 /var/backups/polstats

# Secure sensitive files
if [ -f "$PROJECT_DIR/.env" ]; then
    chmod 600 "$PROJECT_DIR/.env"
    echo "✓ Secured .env file"
fi

if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    chmod 644 "$PROJECT_DIR/db.sqlite3"
    echo "✓ Secured database file"
fi

echo "✓ User and permissions configured"
echo ""
echo "Next steps:"
echo "  1. Create virtual environment:"
echo "     sudo -u $USER python3 -m venv $PROJECT_DIR/venv"
echo "  2. Install dependencies:"
echo "     sudo -u $USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/deployment/requirements.production.txt"
echo "  3. Run deploy script:"
echo "     sudo $PROJECT_DIR/deployment/deploy.sh"
