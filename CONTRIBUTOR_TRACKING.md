# Individual Contributor Tracking

## Overview

Yes! The system **fully tracks individual contributors** with comprehensive analytics and reporting capabilities. Every single contribution is captured with complete details.

## Data Captured Per Contribution

Each contribution record includes:
- **Contributor Name** - Full name as reported
- **Complete Address** - Street, city, state, zip
- **Amount** - Exact contribution amount
- **Date Received** - When the contribution was received
- **Associated Report** - Links to the disclosure report (with organization info)
- **Flags**:
  - In-Kind contribution
  - Loan
  - Amendment

## Features

### 1. Contributors List Page (`/contributors/`)

Aggregated view of all contributors:
- **Search** by contributor name or address
- **Pagination** (50 per page)
- **Sortable** columns
- Shows for each contributor:
  - Total amount contributed (across ALL reports/organizations)
  - Number of contributions
  - Date of last contribution
  - Address
- **Click any contributor name** to see detailed history

### 2. Individual Contributor Detail Page (`/contributors/<name>/`)

NEW! Comprehensive profile for each contributor showing:

**Summary Statistics:**
- Total amount contributed
- Number of contributions
- Average contribution size
- Date range (first to last contribution)

**Visualizations:**
- **Timeline Chart** - Shows all contributions over time with dates and amounts
- **By Organization Table** - Breakdown of contributions to each organization/candidate
- **By Year Table** - Annual contribution totals

**Complete History:**
- Table of all individual contributions
- Links to source reports
- Transaction dates
- Flags (in-kind, loan, amendment)

### 3. Django Admin Interface

Full admin capabilities:
- Search contributors by name or address
- Filter by:
  - Date range
  - Amount range
  - Report
  - Flags (in-kind, loan, amendment)
- Export to CSV
- Bulk operations

### 4. Programmatic Access (Django ORM)

Full API for custom queries:

```python
from disclosures.models import Contribution
from django.db.models import Sum, Count, Q

# Get all contributions from a specific person
johns_donations = Contribution.objects.filter(
    contributor_name__icontains='John Smith'
)

# Total amount donated by a person across all reports
from django.db.models import Sum
john_total = Contribution.objects.filter(
    contributor_name__icontains='John Smith'
).aggregate(total=Sum('amount'))
# Returns: {'total': Decimal('5000.00')}

# Find all contributors from a specific city
slc_contributors = Contribution.objects.filter(
    address__icontains='Salt Lake City'
).values('contributor_name').distinct()

# Get contribution history for a person
history = Contribution.objects.filter(
    contributor_name='John Smith'
).select_related('report').order_by('-date_received')

for contrib in history:
    print(f"{contrib.date_received}: ${contrib.amount} to {contrib.report.organization_name}")

# Find large contributors (over $1000 total)
from django.db.models import Sum
large_contributors = (
    Contribution.objects
    .values('contributor_name')
    .annotate(total=Sum('amount'))
    .filter(total__gte=1000)
    .order_by('-total')
)

# Find contributors who gave to multiple organizations
from django.db.models import Count
multi_org_donors = (
    Contribution.objects
    .values('contributor_name')
    .annotate(
        org_count=Count('report__organization_name', distinct=True),
        total=Sum('amount')
    )
    .filter(org_count__gt=1)
    .order_by('-total')
)

# Get contributors by address pattern
utah_county_contributors = Contribution.objects.filter(
    Q(address__icontains='Provo') |
    Q(address__icontains='Orem') |
    Q(address__icontains='Lehi')
).values('contributor_name', 'address').distinct()

# Monthly contribution analysis for a person
from django.db.models.functions import TruncMonth
monthly = (
    Contribution.objects
    .filter(contributor_name='John Smith')
    .annotate(month=TruncMonth('date_received'))
    .values('month')
    .annotate(
        total=Sum('amount'),
        count=Count('id')
    )
    .order_by('month')
)

# Find contributors to specific organization types
pac_contributors = Contribution.objects.filter(
    report__organization_type__icontains='Political Action Committee'
).values('contributor_name').annotate(
    total=Sum('amount')
).order_by('-total')
```

## Use Cases

### 1. Track Individual Donor Patterns
Monitor how much a specific person has contributed and to whom:
- Visit `/contributors/` and search for the name
- Click their name to see complete history
- View timeline chart to see donation patterns
- See which organizations they support

### 2. Find Large Donors
Identify top contributors across all organizations:
```python
top_donors = (
    Contribution.objects
    .values('contributor_name')
    .annotate(total=Sum('amount'))
    .order_by('-total')[:100]
)
```

### 3. Geographic Analysis
Analyze contributions by location:
```python
# By city
by_city = (
    Contribution.objects
    .filter(address__icontains='UT')
    .values('address')
    .annotate(
        total=Sum('amount'),
        count=Count('id')
    )
)
```

### 4. Cross-Organization Donor Analysis
Find donors who contribute to multiple organizations:
```python
# Donors who gave to both parties
cross_party = (
    Contribution.objects
    .filter(report__organization_name__icontains='Republican')
    .values('contributor_name')
    .intersection(
        Contribution.objects
        .filter(report__organization_name__icontains='Democrat')
        .values('contributor_name')
    )
)
```

### 5. Temporal Analysis
Track when contributions occur:
```python
from django.db.models.functions import ExtractMonth, ExtractYear

# Contributions by month across all years
by_month = (
    Contribution.objects
    .annotate(month=ExtractMonth('date_received'))
    .values('month')
    .annotate(total=Sum('amount'), count=Count('id'))
    .order_by('month')
)

# Election year analysis (2024)
election_year = Contribution.objects.filter(
    date_received__year=2024
).aggregate(
    total=Sum('amount'),
    count=Count('id')
)
```

### 6. Group Contributor Analysis
Analyze multiple contributors as a group:
```python
# Family contributions (same last name and address)
family_name = 'Smith'
family_contributions = (
    Contribution.objects
    .filter(
        contributor_name__icontains=family_name,
        address__icontains='123 Main St'
    )
    .aggregate(
        total=Sum('amount'),
        members=Count('contributor_name', distinct=True)
    )
)
```

## API Endpoints

### Get Contributor Timeline
```
GET /api/contributors/<contributor_name>/timeline/
```

Returns JSON array of daily contributions:
```json
[
  {
    "date": "2024-01-15",
    "amount": 500.00,
    "count": 1
  },
  ...
]
```

## Database Schema

### Contribution Model Fields
```python
class Contribution(models.Model):
    report = ForeignKey(DisclosureReport)  # Links to report (has organization info)
    date_received = DateField()            # Parsed date
    date_received_raw = CharField()        # Original date string
    contributor_name = CharField()         # Full name
    address = TextField()                  # Complete address
    is_in_kind = BooleanField()           # In-kind contribution flag
    is_loan = BooleanField()              # Loan flag
    is_amendment = BooleanField()         # Amendment flag
    amount = DecimalField()               # Contribution amount
    created_at = DateTimeField()          # When record was created
    updated_at = DateTimeField()          # Last update
```

### Indexes
The model includes database indexes on:
- `contributor_name` - Fast name lookups
- `amount` - Fast amount-based queries
- `date_received` - Fast date range queries
- `report` - Fast report-based queries

## Export Options

### CSV Export from Admin
1. Go to Django admin (`/admin/disclosures/contribution/`)
2. Select contributors using checkboxes
3. Choose "Export selected contributions" action
4. Download CSV with all fields

### Programmatic Export
```python
import csv
from disclosures.models import Contribution

# Export all John Smith contributions to CSV
contributions = Contribution.objects.filter(
    contributor_name='John Smith'
).select_related('report')

with open('john_smith_contributions.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Date', 'Organization', 'Amount', 'Address'])

    for c in contributions:
        writer.writerow([
            c.date_received,
            c.report.organization_name,
            c.amount,
            c.address
        ])
```

## Privacy & Compliance

- All data is sourced from Utah's public disclosure website
- Only publicly filed information is stored
- No additional personal information is collected
- Data can be deleted on request per GDPR/privacy regulations

## Advanced Analytics Examples

### Contribution Size Distribution
```python
from django.db.models import Count, Q

# Categorize by contribution size
size_distribution = {
    'under_100': Contribution.objects.filter(amount__lt=100).count(),
    '100_to_500': Contribution.objects.filter(amount__gte=100, amount__lt=500).count(),
    '500_to_1000': Contribution.objects.filter(amount__gte=500, amount__lt=1000).count(),
    'over_1000': Contribution.objects.filter(amount__gte=1000).count(),
}
```

### Recurring Donors
```python
# Find people who donated multiple times
recurring = (
    Contribution.objects
    .values('contributor_name')
    .annotate(contribution_count=Count('id'))
    .filter(contribution_count__gt=1)
    .order_by('-contribution_count')
)
```

### First-Time vs Returning Donors (by year)
```python
from django.db.models.functions import ExtractYear

# First time donors in 2024
first_time_2024 = (
    Contribution.objects
    .filter(date_received__year=2024)
    .values('contributor_name')
    .annotate(first_year=Min(ExtractYear('date_received')))
    .filter(first_year=2024)
    .count()
)
```

## Future Enhancements

Potential features that could be added:
- Contributor network graphs (showing connections)
- Automated duplicate detection (same person, different name variations)
- Address standardization and geocoding
- Email alerts for new contributions from specific people
- Contribution limit tracking
- Employer/occupation tracking (if available in source data)
