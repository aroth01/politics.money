#!/bin/bash
# Installation script for PolStats systemd timer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  PolStats Scraper Timer Installation  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running on macOS or Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${YELLOW}Detected macOS${NC}"
    echo -e "${YELLOW}Note: macOS uses launchd instead of systemd${NC}"
    echo -e "${YELLOW}Would you like to create a launchd plist instead? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Creating launchd configuration..."
        # This will be handled separately
        ./install-macos.sh
        exit 0
    else
        echo "Installation cancelled"
        exit 1
    fi
fi

# Get the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Get current username
CURRENT_USER=$(whoami)

echo "Project directory: $PROJECT_DIR"
echo "Current user: $CURRENT_USER"
echo ""

# Create logs directory if it doesn't exist
LOGS_DIR="$PROJECT_DIR/logs"
if [ ! -d "$LOGS_DIR" ]; then
    echo "Creating logs directory..."
    mkdir -p "$LOGS_DIR"
fi

# Update the service file with correct paths and username
echo "Updating service file with correct paths..."
sed -i.bak "s|YOUR_USERNAME|$CURRENT_USER|g" polstats-scraper.service
sed -i.bak "s|/Users/aaronroth/polstats|$PROJECT_DIR|g" polstats-scraper.service
sed -i.bak "s|/Users/aaronroth/polstats|$PROJECT_DIR|g" polstats-scraper.timer

# Copy service and timer files to systemd directory
echo "Installing systemd service and timer..."
sudo cp polstats-scraper.service /etc/systemd/system/
sudo cp polstats-scraper.timer /etc/systemd/system/

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable and start the timer
echo "Enabling timer..."
sudo systemctl enable polstats-scraper.timer

echo "Starting timer..."
sudo systemctl start polstats-scraper.timer

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Timer status:"
sudo systemctl status polstats-scraper.timer --no-pager
echo ""
echo "Useful commands:"
echo "  View timer status:        sudo systemctl status polstats-scraper.timer"
echo "  View service status:      sudo systemctl status polstats-scraper.service"
echo "  View logs:                tail -f $LOGS_DIR/scraper.log"
echo "  View error logs:          tail -f $LOGS_DIR/scraper-error.log"
echo "  Run scraper manually:     sudo systemctl start polstats-scraper.service"
echo "  Stop timer:               sudo systemctl stop polstats-scraper.timer"
echo "  Disable timer:            sudo systemctl disable polstats-scraper.timer"
echo ""
