# Deployment Guide

This directory contains all the necessary files for deploying the Utah Campaign Finance Disclosures application to a production server.

## Quick Start

For a fresh Ubuntu/Debian server:

```bash
# 1. Run the server setup script
sudo bash deployment/setup_server.sh

# 2. Copy your project files to /var/www/polstats
sudo cp -r . /var/www/polstats

# 3. Install production requirements
sudo -u polstats /var/www/polstats/venv/bin/pip install -r /var/www/polstats/deployment/requirements.production.txt

# 4. Create and configure .env file
sudo cp .env.example /var/www/polstats/.env
sudo nano /var/www/polstats/.env  # Edit with your settings

# 5. Run migrations and collect static files
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py migrate
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py collectstatic --noinput

# 6. Install systemd services
sudo cp deployment/gunicorn.service /etc/systemd/system/
sudo cp deployment/scraper.service /etc/systemd/system/
sudo cp deployment/scraper.timer /etc/systemd/system/
sudo cp deployment/backup.service /etc/systemd/system/
sudo cp deployment/backup.timer /etc/systemd/system/

# 7. Configure Caddy
sudo cp deployment/Caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile  # Replace 'your-domain.com' with your domain

# 8. Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl enable scraper.timer
sudo systemctl start scraper.timer
sudo systemctl enable backup.timer
sudo systemctl start backup.timer
sudo systemctl restart caddy

# 9. Make scripts executable
sudo chmod +x /var/www/polstats/deployment/*.sh
```

## Files Overview

### Web Server Configuration

- **`Caddyfile`** - Caddy web server configuration (recommended)
  - Automatic HTTPS with Let's Encrypt
  - Reverse proxy to Gunicorn
  - Security headers configured
  - Static file serving

- **`nginx.conf`** - Nginx configuration (alternative to Caddy)
  - Use if you prefer Nginx over Caddy
  - Requires manual SSL setup with Certbot
  - High performance static file serving

- **`.htaccess`** - Apache configuration (alternative)
  - Use if you must use Apache
  - Less recommended than Caddy or Nginx

### Application Services

- **`gunicorn.service`** - Systemd service for running Django with Gunicorn
  - Runs the web application
  - 4 worker processes
  - Auto-restart on failure
  - Security hardening enabled

### Scheduled Tasks

- **`scraper.service`** - Systemd service for running the bulk scraper
  - One-shot service triggered by timer
  - Logs to `/var/log/polstats/scraper.log`

- **`scraper.timer`** - Systemd timer for daily scraping
  - Runs daily at 3:00 AM
  - Randomized 10-minute delay
  - Persistent (catches up on missed runs)

- **`backup.service`** - Systemd service for database backups
  - One-shot service triggered by timer
  - Backs up database, .env, and media files

- **`backup.timer`** - Systemd timer for daily backups
  - Runs daily at 2:00 AM (before scraper)
  - 30-day retention policy

### Deployment Scripts

- **`setup_server.sh`** - Initial server setup
  - Installs system dependencies
  - Creates dedicated user
  - Installs Caddy
  - Sets up directory structure

- **`deploy.sh`** - Deployment script for updates
  - Pulls latest code (if using git)
  - Installs dependencies
  - Runs migrations
  - Collects static files
  - Restarts services

- **`backup.sh`** - Manual backup script
  - Backs up SQLite database
  - Backs up .env configuration
  - Backs up media files
  - Compresses and stores in `/var/backups/polstats`
  - Removes backups older than 30 days

### Other Files

- **`requirements.production.txt`** - Python dependencies for production
  - Includes Django, Gunicorn, and all necessary packages
  - Use this instead of the main requirements.txt

## Deployment Checklist

Before deploying to production:

- [ ] Update `.env` with production settings (see `SECURITY_FIXES.md`)
- [ ] Generate a new `SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Update domain in `Caddyfile` or `nginx.conf`
- [ ] Set up database backups (timer is configured for daily 2 AM)
- [ ] Configure scraper schedule (timer is configured for daily 3 AM)
- [ ] Review security settings in `settings.py`
- [ ] Run Django's security check: `python manage.py check --deploy`
- [ ] Consider using PostgreSQL instead of SQLite for production
- [ ] Set up monitoring/error tracking (optional)

## Server Requirements

**Minimum:**
- Ubuntu 20.04+ or Debian 11+
- 1 GB RAM
- 10 GB disk space
- Python 3.9+

**Recommended:**
- Ubuntu 22.04 LTS
- 2 GB RAM
- 20 GB disk space
- Python 3.10+

## Monitoring Services

Check service status:
```bash
# Gunicorn (web app)
sudo systemctl status gunicorn

# Scraper timer
sudo systemctl status scraper.timer

# Backup timer
sudo systemctl status backup.timer

# Caddy
sudo systemctl status caddy
```

View logs:
```bash
# Gunicorn logs
sudo journalctl -u gunicorn -f

# Scraper logs
sudo journalctl -u scraper -f
sudo tail -f /var/log/polstats/scraper.log

# Backup logs
sudo tail -f /var/log/polstats/backup.log

# Caddy logs
sudo journalctl -u caddy -f
```

## Manual Operations

### Deploy updates:
```bash
sudo /var/www/polstats/deployment/deploy.sh
```

### Run scraper manually:
```bash
sudo systemctl start scraper
```

### Run backup manually:
```bash
sudo /var/www/polstats/deployment/backup.sh
```

### Restart web application:
```bash
sudo systemctl restart gunicorn
```

### Import a specific report:
```bash
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py import_disclosure <url>
```

## Troubleshooting

### Application won't start
```bash
# Check Gunicorn logs
sudo journalctl -u gunicorn -n 50

# Check if port 8000 is in use
sudo lsof -i :8000

# Verify .env file exists and is readable
sudo ls -la /var/www/polstats/.env
```

### Static files not loading
```bash
# Recollect static files
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py collectstatic --noinput

# Verify static files directory
ls -la /var/www/polstats/staticfiles

# Check Caddy/Nginx configuration
sudo caddy validate --config /etc/caddy/Caddyfile
```

### Database issues
```bash
# Check database file permissions
sudo ls -la /var/www/polstats/db.sqlite3

# Run migrations
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py migrate

# Restore from backup
sudo cp /var/backups/polstats/db_YYYYMMDD_HHMMSS.sqlite3.gz /tmp/
gunzip /tmp/db_YYYYMMDD_HHMMSS.sqlite3.gz
sudo cp /tmp/db_YYYYMMDD_HHMMSS.sqlite3 /var/www/polstats/db.sqlite3
sudo chown polstats:polstats /var/www/polstats/db.sqlite3
```

### Scraper not running
```bash
# Check timer status
sudo systemctl status scraper.timer

# View scheduled runs
sudo systemctl list-timers

# Run manually to test
sudo systemctl start scraper

# View logs
sudo journalctl -u scraper -n 50
```

## Security Notes

1. **File Permissions**: The deploy script sets appropriate permissions. Database and .env should only be readable by the `polstats` user.

2. **Firewall**: Only ports 80 (HTTP) and 443 (HTTPS) should be open to the public. Port 8000 (Gunicorn) should only accept connections from localhost.

3. **Updates**: Keep the server and Django updated:
   ```bash
   sudo apt-get update && sudo apt-get upgrade
   sudo -u polstats /var/www/polstats/venv/bin/pip install --upgrade Django
   ```

4. **Backups**: Backups are stored locally in `/var/backups/polstats`. Consider copying them to remote storage for disaster recovery.

5. **Monitoring**: Set up uptime monitoring (like UptimeRobot) and error tracking (like Sentry) for production.

## Alternative: Docker Deployment

If you prefer Docker, you can create a `Dockerfile` and `docker-compose.yml` based on these configuration files. The systemd services can be replaced with Docker containers.

## Support

For issues or questions:
- Check the logs first
- Review Django's deployment checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
- Consult the main project README.md
