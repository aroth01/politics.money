# Getting Started - Run Locally

Complete step-by-step guide to run the Utah Campaign Finance app locally.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (optional, if cloning from repository)

## Step-by-Step Setup

### 1. Install Dependencies

```bash
cd /Users/aaronroth/polstats
pip install -r requirements.txt
```

If you prefer to use a virtual environment (recommended):
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up the Database

Run migrations to create the database tables:

```bash
python3 manage.py makemigrations
python3 manage.py migrate
```

This creates a SQLite database file (`db.sqlite3`) in your project directory.

### 3. Create an Admin User (Optional but Recommended)

```bash
python3 manage.py createsuperuser
```

Follow the prompts:
- Username: (choose any username)
- Email: (can leave blank or enter email)
- Password: (choose a password)

### 4. Import Some Data

Start with a single report to test:

```bash
python3 manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198820
```

Expected output:
```
Fetching disclosure data from: https://disclosures.utah.gov/Search/PublicSearch/Report/198820
Report ID: 198820
Data fetched successfully
Creating new report 198820...
Importing X contributions...
Importing Y expenditures...

✓ Import completed successfully!

Report: Contributions and Expenditures For Political Party
  ID: 198820
  Contributions: X ($XXX,XXX.XX)
  Expenditures: Y ($XX,XXX.XX)
  Ending Balance: $XX,XXX.XX
```

### 5. Launch the Website

Start the Django development server:

```bash
python3 manage.py runserver
```

Expected output:
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
November 26, 2024 - 15:30:00
Django version 4.2.x, using settings 'polstats_project.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### 6. Access the Application

Open your browser and visit:

**Main Website:**
- **Homepage**: http://localhost:8000/
- **Reports List**: http://localhost:8000/reports/
- **Contributors**: http://localhost:8000/contributors/
- **Expenditures**: http://localhost:8000/expenditures/

**Admin Interface:**
- **Admin Panel**: http://localhost:8000/admin/
- Login with the superuser credentials you created in Step 3

## Import More Data

### Option A: Import Specific Reports

Import individual reports by ID:
```bash
# Import report 198821
python3 manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198821

# Import report 198822
python3 manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198822
```

### Option B: Batch Import Multiple Reports

Import a range of reports:
```bash
# Import reports 1-100 (good for testing)
python3 manage.py import_all_disclosures --start 1 --end 100

# This will take a few minutes and show progress:
# [1] Imported report 1: 45 contributions, 23 expenditures
# [2] Report 2 appears to be invalid (no data) (consecutive failures: 1)
# [3] Imported report 3: 12 contributions, 8 expenditures
# ...
```

### Option C: Import ALL Reports (Background Task)

Import all available reports (this will take a long time):
```bash
# Run in background (will take hours depending on number of reports)
python3 manage.py import_all_disclosures

# Or run with custom settings
python3 manage.py import_all_disclosures --delay 1.5 --max-consecutive-failures 10
```

**Tip**: Run this in a separate terminal window or in the background while the server is running.

To run in background on macOS/Linux:
```bash
nohup python3 manage.py import_all_disclosures > import.log 2>&1 &

# Check progress
tail -f import.log

# Stop if needed
ps aux | grep import_all_disclosures
kill <PID>
```

## Quick Test Workflow

Here's a quick workflow to test everything:

```bash
# 1. Install and setup
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py createsuperuser

# 2. Import a few test reports (runs in foreground)
python3 manage.py import_all_disclosures --start 198820 --end 198825

# 3. Start server
python3 manage.py runserver

# 4. In your browser, visit:
#    - http://localhost:8000/
#    - http://localhost:8000/reports/
#    - http://localhost:8000/admin/
```

## Development Tips

### Keep Server Running While Importing

Terminal 1 - Run server:
```bash
python3 manage.py runserver
```

Terminal 2 - Import data:
```bash
python3 manage.py import_all_disclosures --start 1 --end 100
```

The website will update automatically as new data is imported!

### Check What's in the Database

```bash
# Django shell
python3 manage.py shell
```

Then in the Python shell:
```python
from disclosures.models import DisclosureReport, Contribution, Expenditure

# Count records
print(f"Reports: {DisclosureReport.objects.count()}")
print(f"Contributions: {Contribution.objects.count()}")
print(f"Expenditures: {Expenditure.objects.count()}")

# View a report
report = DisclosureReport.objects.first()
print(f"Report: {report.organization_name}")
print(f"Type: {report.organization_type}")
print(f"Balance: ${report.ending_balance}")

# Exit shell
exit()
```

### View Logs

The import commands show progress in real-time:
```bash
python3 manage.py import_all_disclosures --start 1 --end 10

# Output:
# [1] Imported report 1: 45 contributions, 23 expenditures
# [2] Report 2 appears to be invalid (no data) (consecutive failures: 1)
# ...
#
# ============================================================
# IMPORT SUMMARY
# ============================================================
# Total reports imported: 8
# Total reports skipped: 0
# Total reports failed: 2
# Last ID processed: 10
# Time elapsed: 45.3s
# Average time per report: 5.66s
# ============================================================
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'django'"

Django isn't installed. Run:
```bash
pip install -r requirements.txt
```

### "django.db.utils.OperationalError: no such table"

You need to run migrations:
```bash
python3 manage.py migrate
```

### "Address already in use"

Port 8000 is already being used. Either:
- Stop the other server
- Use a different port: `python3 manage.py runserver 8001`

### Import is slow or timing out

Add a longer delay between requests:
```bash
python3 manage.py import_all_disclosures --delay 2
```

### Database is locked (SQLite)

If you get "database is locked" errors:
1. Stop all running servers and import processes
2. For production use, switch to PostgreSQL (see README.md)

### Charts not showing

Make sure you have an internet connection - the app uses CDN-hosted libraries (DaisyUI, D3.js).

## Next Steps

Once you have data imported:

1. **Explore the UI**:
   - Browse reports by organization type
   - View individual contributor histories
   - Check out the charts and visualizations

2. **Try the Admin Interface**:
   - Go to http://localhost:8000/admin/
   - Filter and search reports
   - Export data to CSV

3. **Query the Data**:
   ```bash
   python3 manage.py shell
   ```

   ```python
   from disclosures.models import *
   from django.db.models import Sum

   # Top contributors
   Contribution.objects.values('contributor_name')\
       .annotate(total=Sum('amount'))\
       .order_by('-total')[:10]
   ```

4. **Import More Data**:
   - Let the batch import run overnight
   - Check back to see thousands of reports analyzed

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

## Starting Fresh

To completely reset the database:

```bash
# Delete database
rm db.sqlite3

# Recreate tables
python3 manage.py migrate

# Recreate admin user
python3 manage.py createsuperuser

# Re-import data
python3 manage.py import_all_disclosures --start 1 --end 100
```

## Performance Notes

- **SQLite** (default): Good for development, testing, single user
- **PostgreSQL**: Recommended for production or multiple concurrent users
- Each report takes ~1-2 seconds to import (depends on network speed)
- Importing all reports can take several hours

See [README.md](README.md) for PostgreSQL setup instructions.
