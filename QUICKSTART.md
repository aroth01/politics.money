# Quick Start Guide

Get the Utah Campaign Finance Disclosures app running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- pip

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Database

```bash
# Run migrations to create database tables
python manage.py migrate
```

### 3. Create Admin User (Optional)

```bash
python manage.py createsuperuser
```

Follow the prompts to create your admin account.

### 4. Import Some Data

Import a single report to test:

```bash
python manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198820
```

Or start importing all reports (this will take a while):

```bash
# Import first 100 reports to get started quickly
python manage.py import_all_disclosures --start 1 --end 100
```

### 5. Start the Server

```bash
python manage.py runserver
```

### 6. Access the Application

Open your browser and navigate to:

- **Web Interface**: http://localhost:8000/
- **Django Admin**: http://localhost:8000/admin/

## What's Next?

### Import More Data

Continue importing reports in the background:

```bash
# Import all reports (will auto-detect when to stop)
python manage.py import_all_disclosures
```

### Explore the Data

- Browse reports on the homepage
- View detailed report information with interactive charts
- Search contributors and expenditure recipients
- Use the Django admin for advanced queries

### Customize

- Edit `polstats_project/settings.py` to configure database (PostgreSQL)
- Modify templates in `polstats_project/disclosures/templates/` to customize the UI
- Add new views and charts in `polstats_project/disclosures/views.py`

## Troubleshooting

### ImportError: No module named 'django'

Make sure you've installed the requirements:
```bash
pip install -r requirements.txt
```

### Database is locked

If using SQLite and getting "database is locked" errors, try:
1. Stop any running servers
2. Delete `db.sqlite3` and run migrations again
3. Consider switching to PostgreSQL for production use

### Charts not displaying

Make sure you have an internet connection - the app uses CDN-hosted libraries for DaisyUI and D3.js.

## Need Help?

See the full [README.md](README.md) for detailed documentation.
