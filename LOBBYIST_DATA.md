# Lobbyist Data Import Tools

Separate models and import tools for Utah lobbyist disclosure data.

## Models

### LobbyistReport
- Lobbyist expenditure reports (separate from campaign finance reports)
- Fields: principal_name, principal_phone, principal_address, total_expenditures
- No contributions or balance fields (lobbyists only report expenditures)

### LobbyistExpenditure
- Individual expenditures from lobbyist reports
- Fields: recipient_name, location, purpose, amount, date
- Location field separate from purpose (e.g., "Brussels, Belgium (official)")
- No in_kind or loan flags (not applicable to lobbyist reports)

### LobbyistRegistration
- Lobbyist entity registrations (separate from PAC/candidate entities)
- Fields: first_name, last_name, organization_name, principal_name, lobbying_purposes
- Includes both personal and organization information
- Registration date instead of date_created

### LobbyistPrincipal
- Principal/client organizations for lobbyists
- Multiple principals can be linked to one lobbyist
- Fields: name, contact, phone, address

## Import Commands

### Single Report
```bash
python manage.py import_lobbyist_report https://lobbyist.utah.gov/Search/PublicSearch/Report/174643
```

Options:
- `--update` - Update existing report if it already exists
- `--report-id ID` - Override report ID extraction

### Single Entity
```bash
python manage.py import_lobbyist_entity https://lobbyist.utah.gov/Registration/EntityDetails/1410867
```

Options:
- `--update` - Update existing entity if it already exists
- `--entity-id ID` - Override entity ID extraction

### Bulk Report Crawler
```bash
python manage.py crawl_lobbyist_reports --start-id 1 --delay 2.0 --skip-existing
```

Options:
- `--start-id N` - Starting report ID (default: 1)
- `--end-id N` - Ending report ID (optional)
- `--delay SECONDS` - Delay between requests (default: 2.0)
- `--max-failures N` - Max consecutive 404s before stopping (default: 100)
- `--skip-existing` - Skip reports that already exist
- `--update-existing` - Update reports older than 30 days

### Bulk Entity Crawler
```bash
python manage.py crawl_lobbyist_entities --start-id 1 --delay 2.0 --skip-existing
```

Same options as report crawler.

## Parsers

### lobbyist_parser.py
- Standalone parser for lobbyist expenditure reports
- Extracts: report info, balance summary, expenditure table
- Returns structured JSON data

### lobbyist_entity_parser.py
- Standalone parser for lobbyist entity registrations
- Extracts: personal info, organization info, principal info
- Returns structured JSON data

## Admin Interface

All lobbyist models are registered in Django admin:
- LobbyistReport - View/search/filter lobbyist reports
- LobbyistExpenditure - View individual expenditures with location
- LobbyistRegistration - View lobbyist entities with inline principals
- LobbyistPrincipal - View principal/client relationships

## Database

Separate tables from campaign finance data:
- `disclosures_lobbyistreport`
- `disclosures_lobbyistexpenditure`
- `disclosures_lobbyistregistration`
- `disclosures_lobbyistprincipal`

Migration: `0003_lobbyistregistration_lobbyistprincipal_and_more.py`

## Key Differences from Campaign Finance

1. **Reports**
   - No contributions (expenditures only)
   - No balance tracking (only total expenditures)
   - Principal information instead of organization
   - Location field for expenditures

2. **Entities**
   - Personal lobbyist information (first/last name)
   - Organization they work for
   - Principal/client they represent
   - Lobbying purposes description
   - Multiple principals per lobbyist

3. **URLs**
   - Reports: `lobbyist.utah.gov` (not `disclosures.utah.gov`)
   - Entities: `/Registration/EntityDetails/` path

## Example Usage

### Import a specific lobbyist report
```bash
python manage.py import_lobbyist_report https://lobbyist.utah.gov/Search/PublicSearch/Report/174643
```

Output:
```
✓ Import completed successfully!

Report: Expenditures For Principal
  ID: 174643
  Principal: Sutherland Institute
  Expenditures: 2 ($3,368.22)
```

### Import a specific lobbyist entity
```bash
python manage.py import_lobbyist_entity https://lobbyist.utah.gov/Registration/EntityDetails/1410867
```

### Bulk import all lobbyist reports
```bash
# Production - skip existing, polite 2 second delay
python manage.py crawl_lobbyist_reports --start-id 1 --delay 2.0 --skip-existing

# Development - faster, update old entries
python manage.py crawl_lobbyist_reports --start-id 1 --delay 1.0 --update-existing
```

### Bulk import all lobbyist entities
```bash
python manage.py crawl_lobbyist_entities --start-id 1 --delay 2.0 --skip-existing
```

## Production Deployment

The lobbyist crawlers can be set up as systemd services similar to the entity crawler:
1. Create service files in `deployment/`
2. Install with installation scripts
3. Enable auto-start on boot
4. Monitor with systemd/journalctl

## Data Separation Benefits

1. **Clean schema** - Lobbyist-specific fields without mixing with campaign finance
2. **Accurate queries** - No confusion between PACs and lobbyists
3. **Better performance** - Separate indexes optimized for each data type
4. **Easier maintenance** - Changes to one system don't affect the other
5. **Clear reporting** - Distinct admin sections and API endpoints
