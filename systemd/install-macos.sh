#!/bin/bash
# Installation script for PolStats launchd (macOS)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  PolStats Scraper (macOS) Installation  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

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

# LaunchAgents directory
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
if [ ! -d "$LAUNCH_AGENTS_DIR" ]; then
    echo "Creating LaunchAgents directory..."
    mkdir -p "$LAUNCH_AGENTS_DIR"
fi

# Update the plist file with correct paths
PLIST_FILE="com.polstats.scraper.plist"
TEMP_PLIST="/tmp/$PLIST_FILE"

echo "Updating plist file with correct paths..."
sed "s|/Users/aaronroth/polstats|$PROJECT_DIR|g" "$PLIST_FILE" > "$TEMP_PLIST"

# Copy plist to LaunchAgents
echo "Installing launchd agent..."
cp "$TEMP_PLIST" "$LAUNCH_AGENTS_DIR/$PLIST_FILE"

# Load the agent
echo "Loading launchd agent..."
launchctl unload "$LAUNCH_AGENTS_DIR/$PLIST_FILE" 2>/dev/null || true
launchctl load "$LAUNCH_AGENTS_DIR/$PLIST_FILE"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "The scraper will run daily at 2:00 AM"
echo ""
echo "Useful commands:"
echo "  Run scraper manually:     cd $PROJECT_DIR && source venv/bin/activate && python manage.py bulk_scrape --type=all"
echo "  View logs:                tail -f $LOGS_DIR/scraper.log"
echo "  View error logs:          tail -f $LOGS_DIR/scraper-error.log"
echo "  Check if loaded:          launchctl list | grep polstats"
echo "  Unload agent:             launchctl unload $LAUNCH_AGENTS_DIR/$PLIST_FILE"
echo "  Reload agent:             launchctl unload $LAUNCH_AGENTS_DIR/$PLIST_FILE && launchctl load $LAUNCH_AGENTS_DIR/$PLIST_FILE"
echo ""
echo "To run the scraper immediately (for testing):"
echo "  cd $PROJECT_DIR"
echo "  source venv/bin/activate"
echo "  python manage.py bulk_scrape --type=reports --limit=5"
echo ""
