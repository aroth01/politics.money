# Entity Crawler - Quick Start Guide

## Installation (macOS)

```bash
# Make sure you're in the polstats directory
cd /Users/aaronroth/polstats

# Install the service
./scripts/install-entity-crawler-macos.sh
```

## Quick Commands

Use the control script for easy management:

```bash
# Start the crawler
./scripts/entity-crawler-ctl.sh start

# Check status
./scripts/entity-crawler-ctl.sh status

# View logs in real-time
./scripts/entity-crawler-ctl.sh tail

# View recent logs
./scripts/entity-crawler-ctl.sh logs

# Stop the crawler
./scripts/entity-crawler-ctl.sh stop

# Restart the crawler
./scripts/entity-crawler-ctl.sh restart

# Uninstall
./scripts/entity-crawler-ctl.sh uninstall
```

## What It Does

The entity crawler:
1. Continuously scrapes entity data from https://disclosures.utah.gov
2. Starts at entity ID 1 and increments sequentially
3. Saves entity details and officers to the database
4. Waits 2 seconds between requests (to be nice to the server)
5. Re-scrapes entities older than 30 days
6. Stops after 100 consecutive 404s (no more entities found)

## Monitoring Progress

### Check the logs
```bash
tail -f /tmp/polstats-entity-crawler.log
```

### Check the database
```bash
# Activate virtual environment
source venv/bin/activate

# Open Django shell
python manage.py shell

# Check latest entities
>>> from disclosures.models import EntityRegistration
>>> EntityRegistration.objects.count()
>>> EntityRegistration.objects.order_by('-entity_id').first()
```

## Manual Run (Testing)

If you want to test before installing the service:

```bash
source venv/bin/activate

# Test on first 10 entities
python manage.py crawl_entities --start-id 1 --end-id 10

# Run continuously from ID 1
python manage.py crawl_entities --start-id 1

# Resume from a specific ID
python manage.py crawl_entities --start-id 500
```

## Log Locations

- Standard output: `/tmp/polstats-entity-crawler.log`
- Error output: `/tmp/polstats-entity-crawler-error.log`

## Troubleshooting

### Service won't start
```bash
# Check if already running
./scripts/entity-crawler-ctl.sh status

# Check logs for errors
./scripts/entity-crawler-ctl.sh logs
```

### Want to change settings
Edit `/Users/aaronroth/polstats/scripts/entity-crawler.sh` and modify:
- `--start-id` - Where to start
- `--delay` - Seconds between requests
- `--max-failures` - Max consecutive 404s

Then restart:
```bash
./scripts/entity-crawler-ctl.sh restart
```

## Safety Features

- ✓ 2 second delay between requests (won't overload server)
- ✓ Auto-restarts if it crashes
- ✓ Skips already-scraped entities
- ✓ Only updates entities older than 30 days
- ✓ Stops automatically after too many 404s
- ✓ All database writes are atomic (no partial data)

## Performance

- **Speed**: ~1,800 entities per hour (with 2 second delay)
- **Memory**: Very low (processes one entity at a time)
- **Database**: Grows ~1-2 KB per entity
- **Network**: Minimal (1 request per 2 seconds)

## Next Steps

1. Install the service: `./scripts/install-entity-crawler-macos.sh`
2. Check it's running: `./scripts/entity-crawler-ctl.sh status`
3. Watch the logs: `./scripts/entity-crawler-ctl.sh tail`
4. Let it run!

For more details, see [ENTITY_CRAWLER.md](ENTITY_CRAWLER.md)
