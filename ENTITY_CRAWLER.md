# Entity Crawler Service

Automated continuous crawler for Utah campaign finance entity registrations.

## Overview

The entity crawler automatically scrapes entity registration data from the Utah disclosures website. It runs continuously, discovering new entities and updating existing ones.

## Features

- **Continuous crawling**: Automatically discovers entities by incrementing IDs
- **Smart updates**: Re-scrapes entities older than 30 days with `--update-existing`
- **Rate limiting**: Configurable delay between requests (default 2 seconds)
- **Error handling**: Stops after N consecutive 404s (default 100)
- **Resumable**: Can be stopped and restarted at any time
- **Logging**: Comprehensive logging to file and stdout

## Files

### Scripts
- `scripts/entity-crawler.sh` - Main crawler wrapper script
- `scripts/install-entity-crawler-macos.sh` - macOS installation (launchd)
- `scripts/install-entity-crawler-service.sh` - Linux installation (systemd)

### Service Definitions
- `launchd/com.polstats.entity-crawler.plist` - macOS launchd service
- `systemd/polstats-entity-crawler.service` - Linux systemd service

### Django Management Command
- `polstats_project/disclosures/management/commands/crawl_entities.py` - Core crawler logic

## Installation

### macOS (using launchd)

```bash
# Install the service
./scripts/install-entity-crawler-macos.sh

# Check if running
launchctl list | grep polstats

# View logs
tail -f /tmp/polstats-entity-crawler.log
tail -f /tmp/polstats-entity-crawler-error.log
```

### Linux (using systemd)

```bash
# Install the service (requires sudo)
sudo ./scripts/install-entity-crawler-service.sh

# Start the service
sudo systemctl start polstats-entity-crawler

# Check status
sudo systemctl status polstats-entity-crawler

# View logs
sudo journalctl -u polstats-entity-crawler -f
tail -f /var/log/polstats/entity-crawler.log
```

## Manual Usage

You can also run the crawler manually without installing the service:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the crawler
python manage.py crawl_entities --help

# Basic usage
python manage.py crawl_entities --start-id 1

# With all options
python manage.py crawl_entities \
    --start-id 1 \
    --end-id 10000 \
    --delay 2.0 \
    --max-failures 100 \
    --update-existing
```

## Configuration Options

### Command Line Arguments

- `--start-id N` - Starting entity ID (default: 1)
- `--end-id N` - Ending entity ID (optional, runs continuously if not set)
- `--delay SECONDS` - Delay between requests in seconds (default: 2.0)
- `--max-failures N` - Max consecutive 404s before stopping (default: 50)
- `--update-existing` - Re-scrape entities older than 30 days

### Examples

```bash
# Crawl entities 1-1000
python manage.py crawl_entities --start-id 1 --end-id 1000

# Crawl with 3 second delay (be extra nice)
python manage.py crawl_entities --start-id 1 --delay 3.0

# Update old entities
python manage.py crawl_entities --start-id 1 --update-existing

# Resume from entity 500
python manage.py crawl_entities --start-id 500
```

## How It Works

1. **Sequential Discovery**: Starts at `--start-id` and increments
2. **Existence Check**: Checks if entity already exists in database
3. **Age Check**: With `--update-existing`, checks if entity needs refresh (>30 days old)
4. **HTTP Request**: Fetches entity page from Utah disclosures website
5. **Parsing**: Extracts entity details and officers using BeautifulSoup
6. **Database Save**: Saves entity and officers in atomic transaction
7. **Rate Limiting**: Waits for configured delay
8. **Error Handling**: Tracks consecutive 404s, stops after threshold

## Stopping Criteria

The crawler stops when:
- End ID is reached (if specified)
- Max consecutive 404s is reached
- User interrupts (Ctrl+C)
- Fatal error occurs

## Service Management

### macOS (launchd)

```bash
# Stop service
launchctl unload ~/Library/LaunchAgents/com.polstats.entity-crawler.plist

# Start service
launchctl load ~/Library/LaunchAgents/com.polstats.entity-crawler.plist

# Restart service
launchctl unload ~/Library/LaunchAgents/com.polstats.entity-crawler.plist
launchctl load ~/Library/LaunchAgents/com.polstats.entity-crawler.plist

# Remove service
launchctl unload ~/Library/LaunchAgents/com.polstats.entity-crawler.plist
rm ~/Library/LaunchAgents/com.polstats.entity-crawler.plist
```

### Linux (systemd)

```bash
# Stop service
sudo systemctl stop polstats-entity-crawler

# Start service
sudo systemctl start polstats-entity-crawler

# Restart service
sudo systemctl restart polstats-entity-crawler

# Disable service (don't start on boot)
sudo systemctl disable polstats-entity-crawler

# Enable service (start on boot)
sudo systemctl enable polstats-entity-crawler

# Remove service
sudo systemctl stop polstats-entity-crawler
sudo systemctl disable polstats-entity-crawler
sudo rm /etc/systemd/system/polstats-entity-crawler.service
sudo systemctl daemon-reload
```

## Logs

### macOS
- stdout: `/tmp/polstats-entity-crawler.log`
- stderr: `/tmp/polstats-entity-crawler-error.log`

### Linux
- stdout: `/var/log/polstats/entity-crawler.log`
- stderr: `/var/log/polstats/entity-crawler-error.log`
- systemd journal: `journalctl -u polstats-entity-crawler`

## Monitoring

Check crawler progress:

```bash
# View recent activity
tail -f /tmp/polstats-entity-crawler.log  # macOS
tail -f /var/log/polstats/entity-crawler.log  # Linux

# Check database for latest entity
python manage.py shell
>>> from disclosures.models import EntityRegistration
>>> EntityRegistration.objects.order_by('-entity_id').first()
>>> EntityRegistration.objects.count()
```

## Performance Considerations

- **Delay**: Keep delay at 2+ seconds to avoid overloading the Utah server
- **Update frequency**: Entities are re-scraped only if >30 days old
- **Database**: Uses atomic transactions for data integrity
- **Memory**: Processes entities one at a time (low memory usage)

## Troubleshooting

### Service won't start
- Check logs for errors
- Verify virtual environment path in script
- Ensure database is accessible
- Check file permissions

### High error rate
- Increase delay between requests
- Check internet connectivity
- Verify Utah disclosures website is accessible

### Service keeps restarting
- Check error logs
- Verify database configuration
- Check for Python errors in Django code

## Data Model

Scraped data is stored in two tables:

- `EntityRegistration` - Entity details (name, address, etc.)
- `EntityOfficer` - Officers/contacts for each entity

See `polstats_project/disclosures/models.py` for schema details.

## Contributing

To modify the crawler:

1. Edit `crawl_entities.py` management command
2. Test manually: `python manage.py crawl_entities --start-id 1 --end-id 10`
3. If changing service config, reinstall service
4. Monitor logs for issues

## Safety Features

- Rate limiting prevents server overload
- Atomic transactions prevent partial data
- Auto-restart on failure (service mode)
- Configurable stop conditions
- Comprehensive error logging
