# 🚀 Quick Start - 3 Easy Steps

## Option 1: Use the Startup Script (Easiest!)

### macOS/Linux:
```bash
./start.sh
```

### Windows:
```cmd
start.bat
```

The script will:
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Set up database
- ✅ Optionally create admin user
- ✅ Optionally import sample data
- ✅ Start the server

**Then visit**: http://localhost:8000/

---

## Option 2: Manual Setup (3 Commands)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Setup database
python3 manage.py migrate

# 3. Start server
python3 manage.py runserver
```

**Visit**: http://localhost:8000/

---

## Import Data

### Import one report (fast test):
```bash
python3 manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198820
```

### Import multiple reports (testing):
```bash
python3 manage.py import_all_disclosures --start 1 --end 100
```

### Import ALL reports (background, takes hours):
```bash
python3 manage.py import_all_disclosures
```

---

## Access Points

After starting the server:

- **🏠 Homepage**: http://localhost:8000/
- **📊 Reports**: http://localhost:8000/reports/
- **👥 Contributors**: http://localhost:8000/contributors/
- **💰 Expenditures**: http://localhost:8000/expenditures/
- **⚙️ Admin Panel**: http://localhost:8000/admin/

---

## Create Admin User

```bash
python3 manage.py createsuperuser
```

Follow prompts to set username and password.

---

## Common Commands

```bash
# Stop server: Press Ctrl+C

# Check database:
python3 manage.py shell
>>> from disclosures.models import *
>>> DisclosureReport.objects.count()

# Reset database:
rm db.sqlite3
python3 manage.py migrate

# Update code after pulling changes:
python3 manage.py migrate
python3 manage.py collectstatic
```

---

## Need More Help?

📖 **Full Documentation**:
- [GETTING_STARTED.md](GETTING_STARTED.md) - Detailed setup guide
- [README.md](README.md) - Complete documentation
- [FRONTEND.md](FRONTEND.md) - Frontend features
- [CONTRIBUTOR_TRACKING.md](CONTRIBUTOR_TRACKING.md) - Contributor analytics

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'django'"
```bash
pip install -r requirements.txt
```

### "no such table" error
```bash
python3 manage.py migrate
```

### Port 8000 already in use
```bash
python3 manage.py runserver 8001
```

---

## That's It! 🎉

The app is now running locally. Import some data and explore!
