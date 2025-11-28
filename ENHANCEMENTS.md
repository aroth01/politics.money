# Enhanced Organization Type Tracking

## Summary

The scraper and database have been enhanced to capture and display organization type information (Political Party, Political Action Committee, Candidate, etc.) from disclosure reports.

## Changes Made

### 1. Parser Enhancements ([utah_disclosures_parser.py](utah_disclosures_parser.py))

Enhanced the `parse_report_info()` function to extract:
- **Organization Type**: Extracted from the report title (e.g., "Contributions and Expenditures For Political Party")
- **Report Period Details**: Begin Date, End Date, Due Date, Submit Date, Report Type
- **Organization Metadata**: Name, Phone, Address, etc.

### 2. Database Model Updates ([polstats_project/disclosures/models.py](polstats_project/disclosures/models.py))

Added new fields to the `DisclosureReport` model:

**Organization Information:**
- `organization_name` - Name of the organization (e.g., "Utah Republican Party (State)")
- `organization_type` - Type of organization (e.g., "Political Party", "Political Action Committee")

**Report Period Information:**
- `report_type` - Type of report (e.g., "2024 Convention Report")
- `begin_date` - Report period start date
- `end_date` - Report period end date
- `due_date` - Report due date
- `submit_date` - Date report was submitted

All new fields are:
- Indexed for fast queries
- Searchable in the admin interface
- Displayed in the frontend

### 3. Import Commands Updated

Both import commands now populate the new fields:
- [import_disclosure.py](polstats_project/disclosures/management/commands/import_disclosure.py)
- [import_all_disclosures.py](polstats_project/disclosures/management/commands/import_all_disclosures.py)

### 4. Admin Interface Improvements ([polstats_project/disclosures/admin.py](polstats_project/disclosures/admin.py))

- Added organization_type and organization_name to list display
- Added filters for organization type and report type
- Added search by organization name and type
- Organized detail view into logical fieldsets

### 5. Frontend Enhancements

**Reports List Page:**
- Organization name displayed prominently
- Organization type shown as badge
- Filter dropdown for organization types
- Search includes organization name
- Additional sorting options by organization name

**Report Detail Page:**
- Organization name as main heading
- Organization type badge displayed
- Report period dates shown
- Submit date displayed

## Usage

### After Updating

1. **Create and run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Re-import existing data** (optional, to populate new fields):
   ```bash
   # Re-import a specific report
   python manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198820 --update

   # Or re-import all reports (will skip existing, update with new fields)
   python manage.py import_all_disclosures --start 1 --skip-existing
   ```

### Querying by Organization Type

**Django ORM:**
```python
from disclosures.models import DisclosureReport

# Get all Political Party reports
party_reports = DisclosureReport.objects.filter(organization_type__icontains='Political Party')

# Get all PAC reports
pac_reports = DisclosureReport.objects.filter(organization_type__icontains='Political Action Committee')

# Get reports for a specific organization
utah_gop = DisclosureReport.objects.filter(organization_name__icontains='Utah Republican')

# Get reports by date range
recent = DisclosureReport.objects.filter(submit_date__gte='2024-01-01')
```

**In the Web Interface:**
- Visit `/reports/`
- Use the "Organization Type" dropdown to filter
- Search by organization name

**In Django Admin:**
- Use the organization type filter in the sidebar
- Search for organizations by name

## Data Structure Example

```json
{
  "report_id": "198820",
  "organization_name": "Utah Republican Party (State)",
  "organization_type": "Political Party",
  "report_type": "2024 Convention Report",
  "begin_date": "2024-01-01",
  "end_date": "2024-04-17",
  "due_date": "2024-04-22",
  "submit_date": "2024-04-22",
  "title": "Contributions and Expenditures For Political Party",
  "balance_beginning": 37003.86,
  "total_contributions": 107206.35,
  "total_expenditures": 82750.01,
  "ending_balance": 61459.20
}
```

## Benefits

1. **Better Organization** - Easily filter and analyze reports by organization type
2. **Improved Search** - Find reports by organization name
3. **Enhanced Analytics** - Compare spending across different organization types
4. **Better UX** - Users can quickly identify what type of organization filed each report
5. **Complete Metadata** - All important report details are now captured and searchable

## Organization Types You'll See

Based on Utah's disclosure system, expect these organization types:
- **Political Party** - State and local party committees
- **Political Action Committee** - PACs of various types
- **Candidate** - Individual candidate committees
- **Political Issues Committee** - Issue advocacy organizations
- **Corporation** - Corporate political spending
- **Other** - Miscellaneous filers

## Migration Notes

- Existing reports in the database will have empty organization fields until re-imported
- The `report_info` JSON field still contains all raw metadata as backup
- New fields are nullable and blank-able to handle edge cases
- Database indexes ensure queries remain fast even with large datasets
