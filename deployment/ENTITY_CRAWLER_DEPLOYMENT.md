# Entity Crawler - Production Deployment Guide

This guide covers deploying the entity crawler service to your production server.

## Overview

The entity crawler is a systemd service that continuously scrapes entity registration data from the Utah disclosures website. It's designed to run alongside your main application on the production server.

## Files

- `deployment/entity-crawler.service` - systemd service definition
- `deployment/install-entity-crawler.sh` - installation script
- `polstats_project/disclosures/management/commands/crawl_entities.py` - core logic

## Prerequisites

- Ubuntu/Debian server with systemd
- Project deployed to `/var/www/polstats`
- User `polstats` with proper permissions
- Virtual environment at `/var/www/polstats/venv`
- `.env` file configured at `/var/www/polstats/.env`

## Installation

### 1. Deploy Latest Code

First, deploy your latest code to the server:

```bash
# On your server
cd /var/www/polstats
sudo -u polstats git pull
```

### 2. Install the Service

Run the installation script:

```bash
cd /var/www/polstats
sudo ./deployment/install-entity-crawler.sh
```

This will:
- Copy the service file to `/etc/systemd/system/`
- Create log directory at `/var/log/polstats/`
- Reload systemd
- Enable the service (start on boot)

### 3. Start the Service

```bash
sudo systemctl start entity-crawler
```

### 4. Verify It's Running

```bash
# Check status
sudo systemctl status entity-crawler

# View logs
sudo journalctl -u entity-crawler -f

# Or
tail -f /var/log/polstats/entity-crawler.log
```

## Configuration

The service is configured in `deployment/entity-crawler.service`:

```ini
ExecStart=/var/www/polstats/venv/bin/python manage.py crawl_entities \
    --start-id 1 \
    --delay 2.0 \
    --max-failures 100 \
    --update-existing
```

### Adjusting Settings

To change crawler settings:

1. Edit `deployment/entity-crawler.service`
2. Modify the `ExecStart` parameters:
   - `--start-id N` - Starting entity ID
   - `--delay SECONDS` - Delay between requests
   - `--max-failures N` - Max consecutive 404s before stopping
   - `--update-existing` - Re-scrape old entities (>30 days)

3. Reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart entity-crawler
```

## Management Commands

### Start/Stop/Restart

```bash
# Start
sudo systemctl start entity-crawler

# Stop
sudo systemctl stop entity-crawler

# Restart
sudo systemctl restart entity-crawler

# Reload configuration
sudo systemctl daemon-reload
sudo systemctl restart entity-crawler
```

### Enable/Disable Auto-Start

```bash
# Enable (start on boot)
sudo systemctl enable entity-crawler

# Disable (don't start on boot)
sudo systemctl disable entity-crawler
```

### View Logs

```bash
# Follow systemd journal
sudo journalctl -u entity-crawler -f

# Follow log file
tail -f /var/log/polstats/entity-crawler.log

# View errors
tail -f /var/log/polstats/entity-crawler-error.log

# View last 100 lines
sudo journalctl -u entity-crawler -n 100
```

### Check Status

```bash
# Service status
sudo systemctl status entity-crawler

# Is it running?
systemctl is-active entity-crawler

# Is it enabled?
systemctl is-enabled entity-crawler
```

## Integration with Deployment

The entity crawler is integrated into the main deployment script (`deployment/deploy.sh`).

When you run:

```bash
sudo ./deployment/deploy.sh
```

It will automatically restart the entity crawler if it's installed and enabled.

## Monitoring

### Check Progress

```bash
# View recent activity
tail -50 /var/log/polstats/entity-crawler.log

# Check database
sudo -u polstats /var/www/polstats/venv/bin/python manage.py shell
>>> from disclosures.models import EntityRegistration
>>> EntityRegistration.objects.count()
>>> EntityRegistration.objects.order_by('-entity_id').first()
```

### Statistics

The crawler logs statistics every 10 entities:

```
--- Stats: 50 scraped, 45 created, 5 updated, 0 skipped ---
```

### Performance

Expected performance:
- ~1,800 entities per hour (with 2 second delay)
- Low CPU usage
- Minimal memory (~100-200 MB)
- Low network usage (1 request per 2 seconds)

## Troubleshooting

### Service Won't Start

```bash
# Check service status for errors
sudo systemctl status entity-crawler

# View recent logs
sudo journalctl -u entity-crawler -n 50

# Check permissions
ls -la /var/www/polstats/manage.py
ls -la /var/www/polstats/.env

# Test manually
sudo -u polstats /var/www/polstats/venv/bin/python \
  /var/www/polstats/manage.py crawl_entities --start-id 1 --end-id 5
```

### High Error Rate

Check if Utah disclosures website is accessible:

```bash
curl -I https://disclosures.utah.gov/
```

If getting rate limited, increase delay:
```bash
# Edit service file
sudo nano /etc/systemd/system/entity-crawler.service
# Change --delay 2.0 to --delay 5.0

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart entity-crawler
```

### Service Keeps Restarting

Check error logs:
```bash
sudo journalctl -u entity-crawler -n 100
tail -100 /var/log/polstats/entity-crawler-error.log
```

Common issues:
- Database connection errors → Check `.env` file
- Permission errors → Check file ownership
- Python errors → Check virtual environment

### Database Issues

```bash
# Check database permissions
ls -la /var/www/polstats/db.sqlite3

# Ensure polstats user owns it
sudo chown polstats:polstats /var/www/polstats/db.sqlite3
```

## Uninstallation

To remove the entity crawler service:

```bash
# Stop the service
sudo systemctl stop entity-crawler

# Disable it
sudo systemctl disable entity-crawler

# Remove service file
sudo rm /etc/systemd/system/entity-crawler.service

# Reload systemd
sudo systemctl daemon-reload

# Reset failed state (if any)
sudo systemctl reset-failed
```

## Log Rotation

Logs will grow over time. Set up log rotation:

```bash
# Create log rotation config
sudo nano /etc/logrotate.d/polstats-entity-crawler
```

Add:
```
/var/log/polstats/entity-crawler*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 polstats polstats
    sharedscripts
    postrotate
        systemctl reload entity-crawler >/dev/null 2>&1 || true
    endscript
}
```

## Security Considerations

The service runs as the `polstats` user with these security features:

- `NoNewPrivileges=true` - Cannot gain new privileges
- `PrivateTmp=true` - Isolated /tmp directory
- No sudo access required
- Limited file system access

## Best Practices

1. **Monitor regularly** - Check logs weekly
2. **Review data quality** - Spot check scraped entities
3. **Update delay** - Adjust based on server load
4. **Log rotation** - Keep logs under control
5. **Backup database** - Before major changes
6. **Test updates** - Test in staging first

## Production Checklist

- [ ] Service installed and enabled
- [ ] Logs are being written
- [ ] Entities are being created in database
- [ ] No excessive errors in logs
- [ ] Service auto-starts on reboot
- [ ] Log rotation configured
- [ ] Monitoring/alerts set up
- [ ] Backup system includes entity data

## Support

For issues or questions:
1. Check logs first
2. Review this documentation
3. Test manually with the management command
4. Check Utah disclosures website status
