# Utah Campaign Finance Disclosures Parser

A Django application for parsing and storing Utah campaign finance disclosure data.

## 🚀 Quick Start

**New here?** See [START_HERE.md](START_HERE.md) for the fastest way to get running!

```bash
# macOS/Linux - One command start:
./start.sh

# Or manual setup:
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
# Visit http://localhost:8000/
```

See [GETTING_STARTED.md](GETTING_STARTED.md) for detailed instructions.

## Project Structure

```
polstats/
├── manage.py                          # Django management script
├── requirements.txt                   # Python dependencies
├── utah_disclosures_parser.py        # Standalone parser module
├── polstats_project/                 # Django project
│   ├── settings.py                   # Django settings
│   ├── urls.py                       # URL configuration
│   └── disclosures/                  # Disclosures app
│       ├── models.py                 # Database models
│       ├── admin.py                  # Django admin configuration
│       └── management/
│           └── commands/
│               ├── import_disclosure.py      # Single report import
│               └── import_all_disclosures.py # Batch import all reports
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Choose Your Database

**Option A: SQLite (default, easiest)**

No additional configuration needed. Database will be created automatically.

**Option B: PostgreSQL**

1. Create a PostgreSQL database:
```bash
createdb polstats
```

2. Edit `polstats_project/settings.py` and uncomment the PostgreSQL configuration:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'polstats',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Or use environment variables:
```bash
export DB_NAME=polstats
export DB_USER=your_username
export DB_PASSWORD=your_password
export DB_HOST=localhost
export DB_PORT=5432
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Create Admin User (optional)

```bash
python manage.py createsuperuser
```

## Usage

### Import Disclosure Data

#### Import a Single Report

Import a specific disclosure report from Utah's public disclosure website:

```bash
python manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198820
```

**Options:**

- `--update`: Update existing report if it already exists
- `--report-id`: Override the report ID (defaults to extracting from URL)

**Examples:**

```bash
# Import a new report
python manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198820

# Update an existing report
python manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198820 --update

# Specify custom report ID
python manage.py import_disclosure https://example.com/report --report-id 12345
```

#### Batch Import All Reports

Import all available disclosure reports by iterating through report IDs:

```bash
python manage.py import_all_disclosures
```

This command will:
- Start at report ID 1 (or a custom start ID)
- Increment through each report ID
- Automatically detect invalid reports (empty reports with no data)
- Stop after 10 consecutive invalid reports (indicating the end of available data)
- Add a delay between requests to avoid overwhelming the server

**Options:**

- `--start ID`: Starting report ID (default: 1)
- `--end ID`: Ending report ID (default: continue until invalid reports found)
- `--delay SECONDS`: Delay between requests in seconds (default: 1.0)
- `--skip-existing`: Skip reports that already exist in the database
- `--max-consecutive-failures N`: Stop after N consecutive invalid reports (default: 10)

**Examples:**

```bash
# Import all reports starting from ID 1
python manage.py import_all_disclosures

# Import reports 1000-2000 with 2 second delay
python manage.py import_all_disclosures --start 1000 --end 2000 --delay 2

# Resume import from ID 5000, skipping existing reports
python manage.py import_all_disclosures --start 5000 --skip-existing

# Import with faster requests (0.5 second delay)
python manage.py import_all_disclosures --delay 0.5

# Stop after 5 consecutive invalid reports
python manage.py import_all_disclosures --max-consecutive-failures 5
```

**Progress Tracking:**

The command displays real-time progress:
- `[ID]` prefix shows which report is being processed
- Green messages indicate successful imports
- Yellow warnings indicate skipped or invalid reports
- Tracks consecutive failures to detect the end of available reports
- Shows summary statistics when complete or interrupted (Ctrl+C)

**Resume Capability:**

If interrupted, you can resume by noting the last processed ID from the output and using `--start`:

```bash
# If interrupted at ID 1234
python manage.py import_all_disclosures --start 1235 --skip-existing
```

### Web Interface

The application includes a modern web interface built with DaisyUI and D3.js for data visualization.

1. Start the development server:
```bash
python manage.py runserver
```

2. Visit http://localhost:8000/ to access the web interface

**Features:**

- **Homepage** - Overview statistics, recent reports, top contributors, and global timeline chart
- **Reports List** - Browse all disclosure reports with search and sorting
- **Report Detail** - Detailed view with:
  - Balance summary statistics
  - Interactive timeline charts showing daily contributions and expenditures
  - Bar charts for top contributors and expenditure recipients
  - Full tables of all contributions and expenditures
- **Contributors** - Aggregated list of all contributors with totals
- **Expenditures** - Aggregated list of all expenditure recipients

### Access Django Admin

Visit http://localhost:8000/admin/ and login with your superuser credentials to access the Django admin interface for:
- Disclosure Reports
- Contributions
- Expenditures

### Use the Standalone Parser

You can also use the parser independently without Django:

```python
from utah_disclosures_parser import parse_utah_disclosure
import json

# Parse a disclosure report
data = parse_utah_disclosure("https://disclosures.utah.gov/Search/PublicSearch/Report/198820")

# Save to JSON
with open('output.json', 'w') as f:
    json.dump(data, f, indent=2)

# Access the data
print(f"Total contributions: {len(data['contributions'])}")
print(f"Total expenditures: {len(data['expenditures'])}")
print(f"Ending balance: ${data['balance_summary']['Ending Balance']}")
```

## Database Models

### DisclosureReport
Main report record containing:
- Report ID and metadata
- Balance summary (beginning balance, total contributions, total expenditures, ending balance)
- Source URL and title
- Timestamps

### Contribution
Individual contribution records:
- Contributor name and address
- Date received
- Amount
- Flags (in-kind, loan, amendment)

### Expenditure
Individual expenditure records:
- Recipient name
- Purpose
- Date
- Amount
- Flags (in-kind, loan, amendment)

## Database Queries

### Django ORM Examples

```python
from disclosures.models import DisclosureReport, Contribution, Expenditure

# Get a specific report
report = DisclosureReport.objects.get(report_id='198820')

# Get all contributions for a report
contributions = report.contributions.all()

# Find large contributions (over $1000)
large_contributions = Contribution.objects.filter(amount__gte=1000)

# Get top contributors
from django.db.models import Sum
top_contributors = (
    Contribution.objects
    .values('contributor_name')
    .annotate(total=Sum('amount'))
    .order_by('-total')[:10]
)

# Get all expenditures to a specific recipient
anedot_expenses = Expenditure.objects.filter(recipient_name__icontains='Anedot')

# Get monthly spending totals
from django.db.models.functions import TruncMonth
monthly_spending = (
    Expenditure.objects
    .annotate(month=TruncMonth('date'))
    .values('month')
    .annotate(total=Sum('amount'))
    .order_by('month')
)
```

## Development

### Run Tests

```bash
python manage.py test disclosures
```

### Create Migrations After Model Changes

```bash
python manage.py makemigrations
python manage.py migrate
```

### Shell Access

```bash
python manage.py shell
```

## License

MIT
