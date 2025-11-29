#!/bin/bash
# Entity Crawler Service Script
# This script runs the Django entity crawler continuously

set -e

# Configuration
PROJECT_DIR="/Users/aaronroth/polstats"
VENV_DIR="$PROJECT_DIR/venv"
MANAGE_PY="$PROJECT_DIR/manage.py"
LOG_DIR="/var/log/polstats"
LOG_FILE="$LOG_DIR/entity-crawler.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Activate virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "ERROR: Virtual environment not found at $VENV_DIR" >&2
    exit 1
fi

# Change to project directory
cd "$PROJECT_DIR"

# Run the crawler
# --start-id: Start from entity ID 1
# --delay: 2 second delay between requests (be nice to the server)
# --max-failures: Stop after 100 consecutive 404s
# --update-existing: Re-scrape entities older than 30 days
exec python3 "$MANAGE_PY" crawl_entities \
    --start-id 1 \
    --delay 2.0 \
    --max-failures 100 \
    --update-existing \
    >> "$LOG_FILE" 2>&1
