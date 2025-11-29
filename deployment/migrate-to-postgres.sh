#!/bin/bash
#
# PostgreSQL Migration Script
#
# This script:
# 1. Installs PostgreSQL
# 2. Creates database and user with random password
# 3. Updates Django settings
# 4. Migrates data from SQLite to PostgreSQL
# 5. Updates deployment configuration
#
# Usage: sudo ./deployment/migrate-to-postgres.sh
#

set -e

echo "=========================================="
echo "PostgreSQL Migration Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Configuration
PROJECT_DIR="/var/www/polstats"
DB_NAME="polstats"
DB_USER="polstats"
ENV_FILE="$PROJECT_DIR/.env"
BACKUP_DIR="$PROJECT_DIR/backups"

# Generate random password (32 characters, alphanumeric)
DB_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-32)

echo "=== Step 1: Installing PostgreSQL ==="
echo ""

# Install PostgreSQL
apt-get update
apt-get install -y postgresql postgresql-contrib python3-psycopg2

echo "✓ PostgreSQL installed"
echo ""

echo "=== Step 2: Creating Database and User ==="
echo ""

# Start PostgreSQL if not running
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql <<EOF
-- Drop database and user if they exist (for re-running script)
DROP DATABASE IF EXISTS $DB_NAME;
DROP USER IF EXISTS $DB_USER;

-- Create user with password
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Create database
CREATE DATABASE $DB_NAME OWNER $DB_USER;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Connect to database and grant schema privileges
\c $DB_NAME
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF

echo "✓ Database '$DB_NAME' created"
echo "✓ User '$DB_USER' created with random password"
echo ""

echo "=== Step 3: Installing Python PostgreSQL Adapter ==="
echo ""

# Install psycopg2 in virtualenv
sudo -u polstats $PROJECT_DIR/venv/bin/pip install psycopg2-binary

echo "✓ psycopg2-binary installed"
echo ""

echo "=== Step 4: Backing Up Current SQLite Database ==="
echo ""

# Create backup directory
mkdir -p $BACKUP_DIR
chown polstats:polstats $BACKUP_DIR

# Backup SQLite database
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SQLITE_BACKUP="$BACKUP_DIR/sqlite_backup_$TIMESTAMP.db"
cp $PROJECT_DIR/db.sqlite3 $SQLITE_BACKUP
chown polstats:polstats $SQLITE_BACKUP

echo "✓ SQLite database backed up to: $SQLITE_BACKUP"
echo ""

echo "=== Step 5: Updating .env File ==="
echo ""

# Create .env file if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    touch "$ENV_FILE"
    chown polstats:polstats "$ENV_FILE"
    chmod 600 "$ENV_FILE"
fi

# Backup existing .env
cp "$ENV_FILE" "$ENV_FILE.backup_$TIMESTAMP"

# Remove old database settings if they exist
sed -i '/^DB_ENGINE=/d' "$ENV_FILE"
sed -i '/^DB_NAME=/d' "$ENV_FILE"
sed -i '/^DB_USER=/d' "$ENV_FILE"
sed -i '/^DB_PASSWORD=/d' "$ENV_FILE"
sed -i '/^DB_HOST=/d' "$ENV_FILE"
sed -i '/^DB_PORT=/d' "$ENV_FILE"

# Add PostgreSQL settings
cat >> "$ENV_FILE" <<ENVEOF

# PostgreSQL Database Configuration (Added by migrate-to-postgres.sh)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=localhost
DB_PORT=5432
ENVEOF

chown polstats:polstats "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "✓ .env file updated with PostgreSQL credentials"
echo "✓ Password saved to .env file (keep this secure!)"
echo ""

echo "=== Step 6: Updating Django Settings ==="
echo ""

# Update settings.py to use environment variables
sudo -u polstats tee "$PROJECT_DIR/polstats_project/settings_postgres_temp.py" > /dev/null <<'SETTINGSEOF'
import os
from pathlib import Path

# Check if we should use PostgreSQL
USE_POSTGRES = os.environ.get('DB_ENGINE', '').startswith('django.db.backends.postgresql')

if USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.environ.get('DB_NAME', 'polstats'),
            'USER': os.environ.get('DB_USER', 'polstats'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
SETTINGSEOF

echo "✓ PostgreSQL settings template created"
echo ""

# Update actual settings.py
SETTINGS_FILE="$PROJECT_DIR/polstats_project/settings.py"
SETTINGS_BACKUP="$PROJECT_DIR/polstats_project/settings.py.backup_$TIMESTAMP"
cp "$SETTINGS_FILE" "$SETTINGS_BACKUP"

# Replace DATABASES section
sudo -u polstats python3 <<'PYTHONEOF'
import re

settings_file = '/var/www/polstats/polstats_project/settings.py'
with open(settings_file, 'r') as f:
    content = f.read()

# Find and replace DATABASES configuration
# Pattern matches from DATABASES = { to the closing }
pattern = r"DATABASES\s*=\s*\{[^}]*\}(?:\s*#[^\n]*)?"

replacement = """DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
        'OPTIONS': {
            'connect_timeout': 10,
        } if os.environ.get('DB_ENGINE', '').startswith('postgresql') else {}
    }
}"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Also update commented PostgreSQL section if it exists
content = re.sub(
    r'# DATABASES = \{[^}]*\}',
    '# Old SQLite/PostgreSQL configuration - now using environment variables',
    content,
    flags=re.DOTALL
)

with open(settings_file, 'w') as f:
    f.write(content)

print("✓ settings.py updated")
PYTHONEOF

echo ""

echo "=== Step 7: Running Migrations on PostgreSQL ==="
echo ""

# Run migrations on new PostgreSQL database
cd $PROJECT_DIR
sudo -u polstats $PROJECT_DIR/venv/bin/python manage.py migrate

echo "✓ PostgreSQL database schema created"
echo ""

echo "=== Step 8: Migrating Data from SQLite ==="
echo ""

# Use Django's dumpdata/loaddata for migration
echo "Exporting data from SQLite..."

# Temporarily switch back to SQLite for export
export DB_ENGINE="django.db.backends.sqlite3"

# Dump all data except contenttypes and auth.Permission (they'll be recreated)
sudo -u polstats DB_ENGINE="django.db.backends.sqlite3" \
    $PROJECT_DIR/venv/bin/python manage.py dumpdata \
    --natural-foreign \
    --natural-primary \
    --exclude auth.permission \
    --exclude contenttypes \
    --indent 2 \
    > $BACKUP_DIR/data_export_$TIMESTAMP.json

echo "✓ Data exported from SQLite"

# Load into PostgreSQL
echo "Importing data to PostgreSQL..."
unset DB_ENGINE  # Use .env values (PostgreSQL)

sudo -u polstats $PROJECT_DIR/venv/bin/python manage.py loaddata \
    $BACKUP_DIR/data_export_$TIMESTAMP.json

echo "✓ Data imported to PostgreSQL"
echo ""

echo "=== Step 9: Verifying Migration ==="
echo ""

# Get record counts
sudo -u polstats $PROJECT_DIR/venv/bin/python manage.py shell <<'SHELLEOF'
from disclosures.models import DisclosureReport, Contribution, Expenditure, EntityRegistration
from disclosures.models import LobbyistReport, LobbyistExpenditure, LobbyistRegistration

print("Record counts in PostgreSQL:")
print(f"  Reports: {DisclosureReport.objects.count()}")
print(f"  Contributions: {Contribution.objects.count()}")
print(f"  Expenditures: {Expenditure.objects.count()}")
print(f"  Entity Registrations: {EntityRegistration.objects.count()}")
print(f"  Lobbyist Reports: {LobbyistReport.objects.count()}")
print(f"  Lobbyist Expenditures: {LobbyistExpenditure.objects.count()}")
print(f"  Lobbyist Registrations: {LobbyistRegistration.objects.count()}")
SHELLEOF

echo ""

echo "=== Step 10: Optimizing PostgreSQL ==="
echo ""

# Create PostgreSQL optimization config
POSTGRES_VERSION=$(sudo -u postgres psql -tAc "SELECT version();" | grep -oP '\d+(?=\.\d+)' | head -1)
PG_CONF="/etc/postgresql/$POSTGRES_VERSION/main/postgresql.conf"

# Backup original config
cp "$PG_CONF" "$PG_CONF.backup_$TIMESTAMP"

# Raspberry Pi 5 16GB optimizations
cat >> "$PG_CONF" <<PGCONF

# ============================================================
# Raspberry Pi 5 16GB Optimizations (Added by migrate-to-postgres.sh)
# ============================================================

# Memory Settings (for 16GB RAM, allocate ~4GB to PostgreSQL)
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
work_mem = 16MB

# Checkpoint Settings (reduce writes to SD card/SSD)
checkpoint_completion_target = 0.9
wal_buffers = 16MB
max_wal_size = 2GB
min_wal_size = 1GB

# Query Planner
random_page_cost = 1.1
effective_io_concurrency = 200

# Parallelism (Raspberry Pi 5 has 4 cores)
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4

# Connection Settings
max_connections = 100

# Logging (for debugging)
log_min_duration_statement = 1000
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

PGCONF

# Restart PostgreSQL to apply settings
systemctl restart postgresql

echo "✓ PostgreSQL optimized for Raspberry Pi 5"
echo ""

echo "=== Step 11: Restarting Services ==="
echo ""

# Restart Gunicorn
systemctl restart gunicorn

# Restart entity crawler if running
if systemctl is-active --quiet entity-crawler; then
    systemctl restart entity-crawler
fi

echo "✓ Services restarted"
echo ""

echo "=========================================="
echo "✓ Migration Complete!"
echo "=========================================="
echo ""
echo "PostgreSQL Database Information:"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo "  Host: localhost"
echo "  Port: 5432"
echo ""
echo "IMPORTANT: Save this password! It's also stored in:"
echo "  $ENV_FILE"
echo ""
echo "Backups created:"
echo "  SQLite DB: $SQLITE_BACKUP"
echo "  Data JSON: $BACKUP_DIR/data_export_$TIMESTAMP.json"
echo "  .env backup: $ENV_FILE.backup_$TIMESTAMP"
echo "  settings.py backup: $SETTINGS_BACKUP"
echo ""
echo "Next steps:"
echo "  1. Verify the application is working: https://your-domain.com"
echo "  2. Test a few pages to ensure data migrated correctly"
echo "  3. Keep SQLite backup for at least 30 days"
echo "  4. Monitor PostgreSQL performance: systemctl status postgresql"
echo ""
echo "Useful commands:"
echo "  # Connect to database"
echo "  sudo -u postgres psql $DB_NAME"
echo ""
echo "  # Check database size"
echo "  sudo -u postgres psql -c \"\\l+ $DB_NAME\""
echo ""
echo "  # View active connections"
echo "  sudo -u postgres psql -c \"SELECT * FROM pg_stat_activity;\""
echo ""
echo "  # Database performance stats"
echo "  sudo -u postgres psql $DB_NAME -c \"SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;\""
echo ""

exit 0
