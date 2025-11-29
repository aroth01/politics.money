#!/bin/bash
#
# Install Entity Crawler Service
#
# This script installs the entity crawler as a systemd service
#

set -e

echo "=========================================="
echo "Installing Entity Crawler Service"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Configuration
PROJECT_DIR="/var/www/polstats"
SERVICE_NAME="entity-crawler"
SERVICE_FILE="$PROJECT_DIR/deployment/${SERVICE_NAME}.service"
SYSTEMD_DIR="/etc/systemd/system"
LOG_DIR="/var/log/polstats"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Create log directory
echo "Creating log directory..."
mkdir -p "$LOG_DIR"
chown polstats:polstats "$LOG_DIR"
echo "✓ Log directory created"

# Copy service file
echo "Installing service file..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/${SERVICE_NAME}.service"
chmod 644 "$SYSTEMD_DIR/${SERVICE_NAME}.service"
echo "✓ Service file installed"

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload
echo "✓ Systemd reloaded"

# Enable service
echo "Enabling service to start on boot..."
systemctl enable "${SERVICE_NAME}.service"
echo "✓ Service enabled"

echo ""
echo "=========================================="
echo "✓ Installation Complete!"
echo "=========================================="
echo ""
echo "The entity crawler service has been installed but not started."
echo ""
echo "To start the service:"
echo "  sudo systemctl start ${SERVICE_NAME}"
echo ""
echo "To check status:"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
echo "  tail -f /var/log/polstats/entity-crawler.log"
echo ""
echo "To stop the service:"
echo "  sudo systemctl stop ${SERVICE_NAME}"
echo ""
echo "To disable the service (prevent auto-start):"
echo "  sudo systemctl disable ${SERVICE_NAME}"
echo ""

exit 0
