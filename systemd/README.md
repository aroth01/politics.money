# PolStats Automated Scraper

This directory contains scripts and configuration for automated scraping of Utah campaign finance data.

## Overview

The bulk scraper can automatically discover and scrape:
- **Entity Registration Data** - Discovers entities by checking ID ranges (e.g., 1400000-1420000)
- **Campaign Finance Reports** - Discovers reports from the public search page
- Updates existing records with fresh data
- Runs on a scheduled basis (daily at 2:00 AM by default)

### How Discovery Works

**Entities (`--type=entities`):**
- Checks a range of entity IDs to see which ones exist (using HTTP HEAD requests)
- Starts from your highest existing ID and checks forward
- Also checks backwards 1000 IDs to catch any missed
- Stops after 100 consecutive non-existent IDs
- Then scrapes full details for each discovered entity

**Reports (`--type=reports`):**
- Scrapes the public search page with pagination
- Uses the `Skip` parameter to iterate through results
- Extracts report IDs from links on each page
- Stops after 3 consecutive pages with no results
- Then imports full details for each discovered report

**All (`--type=all` or no flag):**
- Runs both entity and report discovery sequentially
- **This is the default** - you don't need the `--type` flag unless you want only one type

## Files

- `bulk_scrape.py` - Django management command for bulk scraping
- `polstats-scraper.service` - Systemd service file (Linux)
- `polstats-scraper.timer` - Systemd timer file (Linux)
- `com.polstats.scraper.plist` - Launchd configuration (macOS)
- `install.sh` - Installation script for Linux
- `install-macos.sh` - Installation script for macOS
- `README.md` - This file

## Installation

### macOS (using launchd)

1. Navigate to this directory:
   ```bash
   cd /Users/aaronroth/polstats/systemd
   ```

2. Run the installation script:
   ```bash
   ./install-macos.sh
   ```

3. The scraper will automatically run daily at 2:00 AM

### Linux (using systemd)

1. Navigate to this directory:
   ```bash
   cd /path/to/polstats/systemd
   ```

2. Run the installation script:
   ```bash
   ./install.sh
   ```

3. The timer will be enabled and start running daily at 2:00 AM

## Manual Usage

You can run the bulk scraper manually with various options:

### Basic usage

```bash
cd /Users/aaronroth/polstats
source venv/bin/activate
python manage.py bulk_scrape
```

### Scrape only entities

```bash
python manage.py bulk_scrape --type=entities
```

### Scrape only reports

```bash
python manage.py bulk_scrape --type=reports
```

### Limit number of items (for testing)

```bash
python manage.py bulk_scrape --type=reports --limit=10
```

### Update existing records

```bash
python manage.py bulk_scrape --update-existing
```

### Scrape specific page range

```bash
python manage.py bulk_scrape --type=reports --start-page=1 --max-pages=5
```

### Adjust delay between requests

```bash
python manage.py bulk_scrape --delay=3.0
```

## Command Options

- `--type` - What to scrape: `entities`, `reports`, or `all` (default: all)
- `--limit` - Limit number of items to scrape
- `--start-page` - Starting page number for report scraping (default: 1)
- `--max-pages` - Maximum number of pages to scrape
- `--delay` - Delay in seconds between requests (default: 2.0)
- `--update-existing` - Update existing records instead of skipping them
- `--recent-only` - Only scrape items from the last 30 days

## Monitoring

### macOS

View logs:
```bash
tail -f /Users/aaronroth/polstats/logs/scraper.log
tail -f /Users/aaronroth/polstats/logs/scraper-error.log
```

Check if the agent is loaded:
```bash
launchctl list | grep polstats
```

Manually trigger the scraper:
```bash
cd /Users/aaronroth/polstats
source venv/bin/activate
python manage.py bulk_scrape --type=all
```

### Linux

View timer status:
```bash
sudo systemctl status polstats-scraper.timer
```

View service status:
```bash
sudo systemctl status polstats-scraper.service
```

View logs:
```bash
tail -f /path/to/polstats/logs/scraper.log
journalctl -u polstats-scraper.service -f
```

Manually trigger the scraper:
```bash
sudo systemctl start polstats-scraper.service
```

## Uninstallation

### macOS

```bash
launchctl unload ~/Library/LaunchAgents/com.polstats.scraper.plist
rm ~/Library/LaunchAgents/com.polstats.scraper.plist
```

### Linux

```bash
sudo systemctl stop polstats-scraper.timer
sudo systemctl disable polstats-scraper.timer
sudo rm /etc/systemd/system/polstats-scraper.service
sudo rm /etc/systemd/system/polstats-scraper.timer
sudo systemctl daemon-reload
```

## Customizing the Schedule

### macOS

Edit the plist file at `~/Library/LaunchAgents/com.polstats.scraper.plist`:

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>2</integer>  <!-- Change this -->
    <key>Minute</key>
    <integer>0</integer>   <!-- Change this -->
</dict>
```

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.polstats.scraper.plist
launchctl load ~/Library/LaunchAgents/com.polstats.scraper.plist
```

### Linux

Edit the timer file at `/etc/systemd/system/polstats-scraper.timer`:

```ini
[Timer]
OnCalendar=daily        # or use specific time like "Mon,Wed,Fri 03:00"
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart polstats-scraper.timer
```

## Troubleshooting

### Logs directory doesn't exist

```bash
mkdir -p /Users/aaronroth/polstats/logs
```

### Permission errors

Make sure the user running the scraper has write permissions to the project directory and logs.

### Virtual environment not found

Ensure the virtual environment is installed:
```bash
cd /Users/aaronroth/polstats
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database errors

Make sure migrations are up to date:
```bash
cd /Users/aaronroth/polstats
source venv/bin/activate
python manage.py migrate
```

## Best Practices

1. **Rate Limiting**: The default delay of 2 seconds between requests is respectful to the server. Don't reduce it below 1 second.

2. **Testing**: Always test with `--limit=5` first to ensure everything works before running a full scrape.

3. **Monitoring**: Regularly check the logs to ensure the scraper is running successfully.

4. **Updates**: Use `--update-existing` periodically to refresh data for existing records.

5. **Disk Space**: Monitor disk space as the database will grow over time.

## Support

For issues or questions, check the logs first. Common issues are usually related to:
- Network connectivity
- Changes to the source website structure
- Database permissions
- Disk space

## License

This scraper is part of the PolStats project.
