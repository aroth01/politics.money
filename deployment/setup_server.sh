#!/bin/bash
#
# Initial Server Setup Script for Utah Campaign Finance Disclosures
#
# This script sets up a fresh Ubuntu/Debian server for deployment
#

set -e  # Exit on error

echo "=============================================="
echo "Utah Campaign Finance - Server Setup Script"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Configuration
PROJECT_NAME="polstats"
PROJECT_DIR="/var/www/$PROJECT_NAME"
USER="polstats"
GROUP="polstats"

echo "This script will:"
echo "  - Install system dependencies"
echo "  - Create dedicated user: $USER"
echo "  - Set up project directory: $PROJECT_DIR"
echo "  - Install Python, pip, and virtualenv"
echo "  - Install and configure Caddy"
echo "  - Set up systemd services"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Update system packages
echo "Updating system packages..."
apt-get update
apt-get upgrade -y
echo "✓ System updated"

# Install system dependencies
echo "Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    build-essential \
    libpq-dev \
    sqlite3
echo "✓ Dependencies installed"

# Install Caddy
echo "Installing Caddy..."
if ! command -v caddy &> /dev/null; then
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update
    apt-get install -y caddy
    echo "✓ Caddy installed"
else
    echo "✓ Caddy already installed"
fi

# Create dedicated user
echo "Creating user $USER..."
if ! id "$USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$PROJECT_DIR" -m "$USER"
    echo "✓ User created"
else
    echo "✓ User already exists"
fi

# Create project directory structure
echo "Creating project directories..."
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p /var/log/polstats
chown -R "$USER:$GROUP" "$PROJECT_DIR"
chown -R "$USER:$GROUP" /var/log/polstats
echo "✓ Directories created"

# Create virtual environment
echo "Creating Python virtual environment..."
sudo -u "$USER" python3 -m venv "$PROJECT_DIR/venv"
echo "✓ Virtual environment created"

# Install Gunicorn in virtual environment
echo "Installing Gunicorn..."
sudo -u "$USER" "$PROJECT_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$USER" "$PROJECT_DIR/venv/bin/pip" install gunicorn
echo "✓ Gunicorn installed"

echo ""
echo "=============================================="
echo "✓ Server setup completed!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Copy your Django project to: $PROJECT_DIR"
echo "  2. Create .env file with your configuration"
echo "  3. Install requirements.txt:"
echo "     sudo -u $USER $PROJECT_DIR/venv/bin/pip install -r $PROJECT_DIR/requirements.txt"
echo "  4. Run migrations:"
echo "     sudo -u $USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py migrate"
echo "  5. Collect static files:"
echo "     sudo -u $USER $PROJECT_DIR/venv/bin/python $PROJECT_DIR/manage.py collectstatic"
echo "  6. Copy systemd service files:"
echo "     cp deployment/gunicorn.service /etc/systemd/system/"
echo "     cp deployment/scraper.service /etc/systemd/system/"
echo "     cp deployment/scraper.timer /etc/systemd/system/"
echo "  7. Copy and configure Caddyfile:"
echo "     cp deployment/Caddyfile /etc/caddy/Caddyfile"
echo "     # Edit /etc/caddy/Caddyfile and replace 'your-domain.com'"
echo "  8. Enable and start services:"
echo "     systemctl daemon-reload"
echo "     systemctl enable gunicorn"
echo "     systemctl start gunicorn"
echo "     systemctl enable scraper.timer"
echo "     systemctl start scraper.timer"
echo "     systemctl restart caddy"
echo ""

exit 0
