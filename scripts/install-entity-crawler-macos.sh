#!/bin/bash
# Install Entity Crawler on macOS using launchd
# This script installs the entity crawler as a launchd service

set -e

echo "=== Installing PolStats Entity Crawler Service (macOS) ==="

# Configuration
PLIST_NAME="com.polstats.entity-crawler.plist"
PLIST_SOURCE="/Users/aaronroth/polstats/launchd/${PLIST_NAME}"
PLIST_DEST="$HOME/Library/LaunchAgents/${PLIST_NAME}"
LOG_DIR="/tmp"

# Check if plist file exists
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "ERROR: Plist file not found at $PLIST_SOURCE"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Copy plist file
echo "Installing launchd plist..."
cp "$PLIST_SOURCE" "$PLIST_DEST"

# Unload if already loaded (ignore errors)
echo "Unloading any existing service..."
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the service
echo "Loading service..."
launchctl load "$PLIST_DEST"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "The entity crawler service has been installed and started."
echo ""
echo "To check if it's running:"
echo "  launchctl list | grep polstats"
echo ""
echo "To view logs:"
echo "  tail -f /tmp/polstats-entity-crawler.log"
echo "  tail -f /tmp/polstats-entity-crawler-error.log"
echo ""
echo "To stop the service:"
echo "  launchctl unload ~/Library/LaunchAgents/${PLIST_NAME}"
echo ""
echo "To start the service:"
echo "  launchctl load ~/Library/LaunchAgents/${PLIST_NAME}"
echo ""
echo "To restart the service:"
echo "  launchctl unload ~/Library/LaunchAgents/${PLIST_NAME}"
echo "  launchctl load ~/Library/LaunchAgents/${PLIST_NAME}"
echo ""
echo "To remove the service:"
echo "  launchctl unload ~/Library/LaunchAgents/${PLIST_NAME}"
echo "  rm ~/Library/LaunchAgents/${PLIST_NAME}"
echo ""
