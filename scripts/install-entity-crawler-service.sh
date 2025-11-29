#!/bin/bash
# Install Entity Crawler systemd Service
# This script installs the entity crawler as a systemd service

set -e

echo "=== Installing PolStats Entity Crawler Service ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Configuration
SERVICE_NAME="polstats-entity-crawler"
SERVICE_FILE="/Users/aaronroth/polstats/systemd/${SERVICE_NAME}.service"
SYSTEMD_DIR="/Library/LaunchDaemons"  # macOS location
LOG_DIR="/var/log/polstats"

# For Linux systems, use this instead:
# SYSTEMD_DIR="/etc/systemd/system"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "ERROR: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Create log directory
echo "Creating log directory..."
mkdir -p "$LOG_DIR"
chown aaronroth:staff "$LOG_DIR"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS - using launchd instead of systemd"
    echo ""
    echo "Note: macOS doesn't use systemd. Instead, you can:"
    echo "1. Use launchd (recommended for macOS)"
    echo "2. Run manually: /Users/aaronroth/polstats/scripts/entity-crawler.sh"
    echo ""
    echo "To create a launchd plist, see: scripts/create-launchd-plist.sh"
    exit 0
fi

# Install service file (Linux)
echo "Installing service file..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/"
chmod 644 "$SYSTEMD_DIR/${SERVICE_NAME}.service"

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable "${SERVICE_NAME}.service"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "The service has been installed but not started."
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
echo "To disable the service:"
echo "  sudo systemctl disable ${SERVICE_NAME}"
echo ""
