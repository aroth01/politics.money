#!/bin/bash
#
# Backup script for Utah Campaign Finance Disclosures
#
# This script backs up:
# - SQLite database
# - Environment configuration
# - Uploaded media files (if any)
#

set -e  # Exit on error

# Configuration
PROJECT_DIR="/var/www/polstats"
BACKUP_DIR="/var/backups/polstats"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

echo "=============================================="
echo "Utah Campaign Finance - Backup Script"
echo "=============================================="
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup SQLite database
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    echo "Backing up database..."
    sqlite3 "$PROJECT_DIR/db.sqlite3" ".backup '$BACKUP_DIR/db_$DATE.sqlite3'"
    gzip "$BACKUP_DIR/db_$DATE.sqlite3"
    echo "✓ Database backed up: db_$DATE.sqlite3.gz"
else
    echo "⚠ No database found, skipping database backup"
fi

# Backup .env file
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "Backing up environment configuration..."
    cp "$PROJECT_DIR/.env" "$BACKUP_DIR/env_$DATE"
    echo "✓ Environment backed up: env_$DATE"
else
    echo "⚠ No .env file found, skipping"
fi

# Backup media files (if directory exists)
if [ -d "$PROJECT_DIR/media" ] && [ "$(ls -A $PROJECT_DIR/media)" ]; then
    echo "Backing up media files..."
    tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" -C "$PROJECT_DIR" media
    echo "✓ Media files backed up: media_$DATE.tar.gz"
else
    echo "⚠ No media files found, skipping"
fi

# Remove old backups
echo "Removing backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "db_*.sqlite3.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "env_*" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "media_*.tar.gz" -mtime +$RETENTION_DAYS -delete
echo "✓ Old backups removed"

# Calculate backup directory size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

echo ""
echo "=============================================="
echo "✓ Backup completed successfully!"
echo "=============================================="
echo "Backup location: $BACKUP_DIR"
echo "Backup size: $BACKUP_SIZE"
echo "Retention: $RETENTION_DAYS days"
echo ""

exit 0
