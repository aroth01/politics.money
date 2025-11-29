#!/bin/bash
# Entity Crawler Control Script
# Quick commands for managing the entity crawler service

set -e

PLIST_NAME="com.polstats.entity-crawler.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}"

function show_usage() {
    cat << EOF
Entity Crawler Control

Usage: $0 {start|stop|restart|status|logs|tail|install|uninstall}

Commands:
  start      - Start the crawler service
  stop       - Stop the crawler service
  restart    - Restart the crawler service
  status     - Show service status
  logs       - Show recent logs
  tail       - Follow logs in real-time
  install    - Install the service
  uninstall  - Remove the service

Examples:
  $0 start
  $0 tail
  $0 status
EOF
}

function check_installed() {
    if [ ! -f "$PLIST_PATH" ]; then
        echo "ERROR: Service not installed"
        echo "Run: $0 install"
        exit 1
    fi
}

case "$1" in
    start)
        check_installed
        echo "Starting entity crawler..."
        launchctl load "$PLIST_PATH" 2>/dev/null || echo "Service already running"
        sleep 1
        $0 status
        ;;

    stop)
        check_installed
        echo "Stopping entity crawler..."
        launchctl unload "$PLIST_PATH" 2>/dev/null || echo "Service not running"
        ;;

    restart)
        check_installed
        echo "Restarting entity crawler..."
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        sleep 1
        launchctl load "$PLIST_PATH"
        sleep 1
        $0 status
        ;;

    status)
        echo "=== Service Status ==="
        if launchctl list | grep -q "polstats.entity-crawler"; then
            echo "Status: RUNNING ✓"
            launchctl list | grep polstats.entity-crawler
        else
            echo "Status: STOPPED"
        fi
        echo ""
        echo "=== Recent Activity ==="
        if [ -f "/tmp/polstats-entity-crawler.log" ]; then
            tail -5 /tmp/polstats-entity-crawler.log
        else
            echo "No logs found"
        fi
        ;;

    logs)
        echo "=== Standard Output ==="
        if [ -f "/tmp/polstats-entity-crawler.log" ]; then
            tail -50 /tmp/polstats-entity-crawler.log
        else
            echo "No stdout log found"
        fi
        echo ""
        echo "=== Error Output ==="
        if [ -f "/tmp/polstats-entity-crawler-error.log" ]; then
            tail -50 /tmp/polstats-entity-crawler-error.log
        else
            echo "No stderr log found"
        fi
        ;;

    tail)
        echo "Following logs (Ctrl+C to stop)..."
        tail -f /tmp/polstats-entity-crawler*.log
        ;;

    install)
        echo "Installing entity crawler service..."
        /Users/aaronroth/polstats/scripts/install-entity-crawler-macos.sh
        ;;

    uninstall)
        if [ -f "$PLIST_PATH" ]; then
            echo "Uninstalling entity crawler service..."
            launchctl unload "$PLIST_PATH" 2>/dev/null || true
            rm "$PLIST_PATH"
            echo "Service uninstalled"
        else
            echo "Service not installed"
        fi
        ;;

    *)
        show_usage
        exit 1
        ;;
esac
