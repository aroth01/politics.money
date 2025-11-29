# PolStats Services Overview

Quick reference for all systemd services in the PolStats deployment.

## Services

### 1. Gunicorn (Web Server)
**File:** `deployment/gunicorn.service`
**Purpose:** Serves the Django web application

```bash
# Manage
sudo systemctl start|stop|restart gunicorn
sudo systemctl status gunicorn

# Logs
sudo journalctl -u gunicorn -f
```

### 2. Entity Crawler
**File:** `deployment/entity-crawler.service`
**Purpose:** Continuously crawls entity registration data

```bash
# Install
sudo ./deployment/install-entity-crawler.sh

# Manage
sudo systemctl start|stop|restart entity-crawler
sudo systemctl status entity-crawler

# Logs
tail -f /var/log/polstats/entity-crawler.log
sudo journalctl -u entity-crawler -f
```

**Configuration:**
- Starts at entity ID 1
- 2 second delay between requests
- Stops after 100 consecutive 404s
- Updates entities older than 30 days

### 3. Scraper (One-shot)
**File:** `deployment/scraper.service`
**Purpose:** One-time bulk import of disclosure reports

```bash
# Run once
sudo systemctl start scraper

# Check status
sudo systemctl status scraper

# Logs
tail -f /var/log/polstats/scraper.log
```

### 4. Report Scraper (Scheduled)
**File:** `deployment/scraper-reports.service`
**Purpose:** Scheduled scraping of new reports

### 5. Backup Service
**File:** `deployment/backup.service`
**Purpose:** Automated database backups

## Service States

### Check All Services

```bash
# List all polstats services
systemctl list-units | grep polstats

# Status of key services
sudo systemctl status gunicorn entity-crawler
```

### Service Persistence

Services configured to auto-start on boot:
- ✓ Gunicorn
- ✓ Entity Crawler (if enabled)
- ✗ Scraper (one-shot, doesn't auto-start)

## Common Tasks

### Deploy New Code

```bash
cd /var/www/polstats
sudo ./deployment/deploy.sh
```

This will:
1. Pull latest code
2. Install dependencies
3. Run migrations
4. Collect static files
5. Restart gunicorn
6. Restart entity-crawler (if installed)

### View All Logs

```bash
# Gunicorn
sudo journalctl -u gunicorn -f

# Entity Crawler
tail -f /var/log/polstats/entity-crawler.log

# Scraper
tail -f /var/log/polstats/scraper.log

# All at once
tail -f /var/log/polstats/*.log
```

### Restart All Services

```bash
sudo systemctl restart gunicorn
sudo systemctl restart entity-crawler
```

### Enable/Disable Services

```bash
# Enable (start on boot)
sudo systemctl enable entity-crawler

# Disable (don't start on boot)
sudo systemctl disable entity-crawler

# Check if enabled
systemctl is-enabled entity-crawler
```

## Service Dependencies

```
network.target
    │
    ├─→ gunicorn.service (web app)
    │
    └─→ entity-crawler.service (data collection)
```

## Log Files

| Service | Log Location |
|---------|-------------|
| Gunicorn | `journalctl -u gunicorn` |
| Entity Crawler | `/var/log/polstats/entity-crawler.log` |
| Scraper | `/var/log/polstats/scraper.log` |
| Backup | `/var/log/polstats/backup.log` |

## Performance Monitoring

### Resource Usage

```bash
# Check memory/CPU
top -p $(pgrep -f gunicorn)
top -p $(pgrep -f crawl_entities)

# Or use systemd
systemd-cgtop
```

### Database Size

```bash
ls -lh /var/www/polstats/db.sqlite3
```

### Entity Crawler Progress

```bash
# Check latest entity
sudo -u polstats /var/www/polstats/venv/bin/python manage.py shell
>>> from disclosures.models import EntityRegistration
>>> EntityRegistration.objects.order_by('-entity_id').first()
>>> EntityRegistration.objects.count()
```

## Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status <service-name>

# View recent logs
sudo journalctl -u <service-name> -n 50

# Check for errors
sudo journalctl -u <service-name> -p err

# Reset failed state
sudo systemctl reset-failed
```

### High CPU/Memory

```bash
# Check resource usage
systemctl status <service-name>

# View process tree
systemctl status <service-name> -l
```

### Permission Errors

```bash
# Fix ownership
sudo chown -R polstats:polstats /var/www/polstats

# Fix permissions
sudo chmod -R 755 /var/www/polstats
sudo chmod 600 /var/www/polstats/.env
```

## Quick Reference

| Task | Command |
|------|---------|
| Deploy | `sudo ./deployment/deploy.sh` |
| Install Entity Crawler | `sudo ./deployment/install-entity-crawler.sh` |
| Start Service | `sudo systemctl start <service>` |
| Stop Service | `sudo systemctl stop <service>` |
| Restart Service | `sudo systemctl restart <service>` |
| View Status | `sudo systemctl status <service>` |
| View Logs | `sudo journalctl -u <service> -f` |
| Enable Auto-start | `sudo systemctl enable <service>` |
| Disable Auto-start | `sudo systemctl disable <service>` |

## Documentation

- Main deployment: `deployment/deploy.sh`
- Entity crawler deployment: `deployment/ENTITY_CRAWLER_DEPLOYMENT.md`
- Entity crawler usage: `ENTITY_CRAWLER.md`
- Quick start: `QUICKSTART_ENTITY_CRAWLER.md`
