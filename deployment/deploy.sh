#!/bin/bash
#
# Deployment script for Utah Campaign Finance Disclosures
#
# This script handles the deployment process including:
# - Pulling latest code
# - Installing dependencies
# - Running migrations
# - Collecting static files
# - Restarting services
#

set -e  # Exit on error

# Configuration
PROJECT_DIR="/var/www/polstats"
VENV_DIR="$PROJECT_DIR/venv"
USER="polstats"
GROUP="polstats"

echo "=========================================="
echo "Utah Campaign Finance - Deployment Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Navigate to project directory
cd "$PROJECT_DIR"
echo "✓ Changed to project directory: $PROJECT_DIR"

# Pull latest code from git (if using git)
if [ -d .git ]; then
    echo "Pulling latest code from git..."
    sudo -u "$USER" git pull
    echo "✓ Code updated"
else
    echo "⚠ Not a git repository, skipping git pull"
fi

# Activate virtual environment and install dependencies
echo "Installing Python dependencies..."
sudo -u "$USER" "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u "$USER" "$VENV_DIR/bin/pip" install -r requirements.txt
echo "✓ Dependencies installed"

# Run database migrations
echo "Running database migrations..."
sudo -u "$USER" "$VENV_DIR/bin/python" manage.py migrate --noinput
echo "✓ Migrations complete"

# Collect static files
echo "Collecting static files..."
sudo -u "$USER" "$VENV_DIR/bin/python" manage.py collectstatic --noinput --clear
echo "✓ Static files collected"

# Set correct permissions
echo "Setting file permissions..."
chown -R "$USER:$GROUP" "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"
chmod 600 "$PROJECT_DIR/.env"
chmod 644 "$PROJECT_DIR/db.sqlite3" 2>/dev/null || true
echo "✓ Permissions set"

# Restart Gunicorn service
echo "Restarting Gunicorn service..."
systemctl restart gunicorn
echo "✓ Gunicorn restarted"

# Check service status
if systemctl is-active --quiet gunicorn; then
    echo "✓ Gunicorn is running"
else
    echo "✗ Error: Gunicorn failed to start"
    systemctl status gunicorn
    exit 1
fi

# Restart entity crawler (if enabled)
if systemctl list-unit-files | grep -q entity-crawler; then
    echo "Restarting entity crawler..."
    systemctl restart entity-crawler
    if systemctl is-active --quiet entity-crawler; then
        echo "✓ Entity crawler restarted"
    else
        echo "⚠ Warning: Entity crawler failed to start (this is non-critical)"
    fi
fi

# Restart Caddy (if using Caddy)
if systemctl list-unit-files | grep -q caddy; then
    echo "Restarting Caddy..."
    systemctl restart caddy
    echo "✓ Caddy restarted"
fi

echo ""
echo "=========================================="
echo "✓ Deployment completed successfully!"
echo "=========================================="
echo ""
echo "Services status:"
systemctl status gunicorn --no-pager -l 0
echo ""

# Show recent logs
echo "Recent Gunicorn logs:"
journalctl -u gunicorn -n 20 --no-pager

exit 0
