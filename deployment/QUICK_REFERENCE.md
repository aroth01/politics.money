# Quick Reference Card

## Initial Setup (One Time)

```bash
# 1. Setup server
sudo bash deployment/setup_server.sh

# 2. Copy project files
sudo cp -r . /var/www/polstats

# 3. Install dependencies
sudo -u polstats /var/www/polstats/venv/bin/pip install -r deployment/requirements.production.txt

# 4. Configure environment
sudo cp .env.example /var/www/polstats/.env
sudo nano /var/www/polstats/.env  # Edit settings

# 5. Setup database
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py migrate
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py collectstatic

# 6. Install services
sudo cp deployment/*.service /etc/systemd/system/
sudo cp deployment/*.timer /etc/systemd/system/
sudo cp deployment/Caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile  # Set your domain

# 7. Start everything
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn scraper.timer backup.timer
sudo systemctl restart caddy
```

## Common Commands

### Deploy Updates
```bash
sudo /var/www/polstats/deployment/deploy.sh
```

### Restart Application
```bash
sudo systemctl restart gunicorn
```

### Run Scraper
```bash
# Manually trigger
sudo systemctl start scraper

# View next scheduled run
sudo systemctl list-timers
```

### Backups
```bash
# Manual backup
sudo /var/www/polstats/deployment/backup.sh

# View backups
ls -lh /var/backups/polstats/

# Restore database
gunzip /var/backups/polstats/db_YYYYMMDD_HHMMSS.sqlite3.gz
sudo cp /var/backups/polstats/db_YYYYMMDD_HHMMSS.sqlite3 /var/www/polstats/db.sqlite3
sudo chown polstats:polstats /var/www/polstats/db.sqlite3
sudo systemctl restart gunicorn
```

### View Logs
```bash
# Application logs
sudo journalctl -u gunicorn -f

# Scraper logs
sudo journalctl -u scraper -f
sudo tail -f /var/log/polstats/scraper.log

# Backup logs
sudo tail -f /var/log/polstats/backup.log

# Web server logs
sudo journalctl -u caddy -f
```

### Check Status
```bash
# All services
sudo systemctl status gunicorn scraper.timer backup.timer caddy

# Individual service
sudo systemctl status gunicorn
```

### Import Specific Report
```bash
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/123456
```

### Database Operations
```bash
# Run migrations
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py migrate

# Django shell
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py shell

# Security check
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py check --deploy
```

## File Locations

| Item | Location |
|------|----------|
| Application | `/var/www/polstats` |
| Database | `/var/www/polstats/db.sqlite3` |
| Environment | `/var/www/polstats/.env` |
| Static Files | `/var/www/polstats/staticfiles` |
| Logs | `/var/log/polstats/` |
| Backups | `/var/backups/polstats/` |
| Caddy Config | `/etc/caddy/Caddyfile` |
| Systemd Services | `/etc/systemd/system/` |

## Scheduled Tasks

| Task | Schedule | Command |
|------|----------|---------|
| Backup | Daily 2:00 AM | `backup.timer` |
| Scraper | Daily 3:00 AM | `scraper.timer` |

## Troubleshooting

### App won't start
```bash
sudo journalctl -u gunicorn -n 50
sudo systemctl restart gunicorn
```

### Static files missing
```bash
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py collectstatic --noinput
```

### Permission errors
```bash
sudo chown -R polstats:polstats /var/www/polstats
sudo chmod 600 /var/www/polstats/.env
```

### Test configuration
```bash
# Caddy
sudo caddy validate --config /etc/caddy/Caddyfile

# Django
sudo -u polstats /var/www/polstats/venv/bin/python /var/www/polstats/manage.py check
```

## Security Checklist

- [ ] `.env` file has unique `SECRET_KEY`
- [ ] `DEBUG=False` in production
- [ ] `ALLOWED_HOSTS` configured
- [ ] HTTPS enabled (automatic with Caddy)
- [ ] Backups running daily
- [ ] Firewall configured (only 80/443 open)
- [ ] Server packages updated
- [ ] Strong admin password set

## Emergency Contacts

| Issue | Action |
|-------|--------|
| Site down | Check `systemctl status gunicorn` |
| Database corrupted | Restore from `/var/backups/polstats/` |
| High CPU | Check scraper: `systemctl status scraper` |
| Disk full | Clean old backups: `sudo find /var/backups/polstats -mtime +30 -delete` |
