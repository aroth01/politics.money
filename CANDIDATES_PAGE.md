# Candidates & Office Holders Pages

New feature to display campaign finance data aggregated by candidate/office holder.

## Files Created

### Views (polstats_project/disclosures/views.py)

**1. `candidates_list()` - Lines 1036-1076**
- Lists all candidates sorted by total contributions raised
- Aggregates data across all reports for each candidate
- Shows: total raised, total spent, report count, latest report date
- Pagination: 50 candidates per page
- Summary statistics for all candidates
- Year filtering support

**2. `candidate_detail()` - Lines 1079-1179**
- Detailed view for individual candidate
- Shows all reports, contributions, and expenditures
- Top 20 contributors with totals
- Top 20 expenditures by recipient
- Monthly contribution/expenditure timeline charts
- Cash on hand from latest report
- Summary statistics (total raised, spent, contributor count, etc.)

### Templates

**1. candidates_list.html**
- Clean table layout with sortable columns
- Color-coded financial metrics (green for raised, orange for spent)
- Summary statistics cards at top
- Pagination controls
- Year filter integration
- Links to individual candidate detail pages

**2. candidate_detail.html**
- Breadcrumb navigation
- 4 summary stat cards (raised, spent, cash on hand, contributors)
- Chart.js timeline charts for contributions and expenditures over time
- Top contributors table (name, address, total, count)
- Top expenditures table (recipient, purpose, total, count)
- Recent reports list (latest 10)
- All data year-filterable

### URL Routes (polstats_project/disclosures/urls.py)

Added two new routes:
```python
path('candidates/', views.candidates_list, name='candidates_list'),
path('candidates/<path:candidate_name>/', views.candidate_detail, name='candidate_detail'),
```

### Navigation (polstats_project/disclosures/templates/base.html)

Added "Candidates" link to both mobile and desktop navigation menus.

## Key Features

### Candidates List Page
- **URL**: `/candidates/`
- **Aggregated Data**: Combines all reports per candidate
- **Sorting**: By total raised (descending)
- **Statistics**:
  - Total candidates count
  - Total raised across all candidates
  - Total spent across all candidates
  - Total reports filed

### Candidate Detail Page
- **URL**: `/candidates/<name>/`
- **Comprehensive View**:
  - Financial summary (raised, spent, cash on hand)
  - Contributor analysis (count, top contributors)
  - Expenditure analysis (top recipients)
  - Timeline visualizations (monthly trends)
  - Report history (all filings)

### Performance Optimizations
- Uses database-level aggregation (not Python loops)
- Pagination to avoid loading all records
- `.values()` and `.annotate()` for efficient queries
- Compatible with existing year filtering system

## Database Schema

Uses existing models:
- **DisclosureReport**: Filtered by `organization_type='Candidates & Office Holders'`
- **Contribution**: Related contributions for each candidate
- **Expenditure**: Related expenditures for each candidate

No new models or migrations required.

## Usage Examples

### List All Candidates
```
GET /candidates/
GET /candidates/?year=2024
```

### View Specific Candidate
```
GET /candidates/Huntsman,%20Jr.,%20Jon%20M/
GET /candidates/Huntsman,%20Jr.,%20Jon%20M/?year=2024
```

## Data Insights Provided

1. **Top Fundraisers**: See which candidates raised the most money
2. **Spending Patterns**: Compare how much candidates spend vs raise
3. **Contributor Base**: Identify major donors to candidates
4. **Campaign Expenses**: Understand where campaign money goes
5. **Financial Trends**: Track contribution/spending patterns over time
6. **Cash Position**: Current cash on hand for active campaigns

## Technical Details

### Query Optimization
```python
# Efficient aggregation at database level
candidates = (
    candidate_reports
    .values('organization_name')
    .annotate(
        total_raised=Sum('total_contributions'),
        total_spent=Sum('total_expenditures'),
        report_count=Count('id'),
        latest_report_date=Max('end_date'),
        first_report_date=Min('end_date')
    )
    .order_by('-total_raised')
)
```

### Timeline Charts
- Built with Chart.js 4.4.0
- Monthly aggregation using `TruncMonth()`
- Separate charts for contributions and expenditures
- Interactive tooltips with formatted currency

### URL Encoding
- Candidate names in URLs are properly URL-encoded
- `unquote()` used in detail view to decode names
- Handles special characters and spaces in names

## Example Output

**Top Candidates by Total Raised:**
1. Huntsman, Jr., Jon M: $1,282,513.69 (6 reports)
2. Karras, Nolan E: $1,256,477.26 (5 reports)
3. Shurtleff, Mark Leonard: $640,552.50 (5 reports)
4. Niederhauser, Wayne: $301,966.00 (7 reports)
5. Killpack, Sheldon L.: $289,628.81 (9 reports)

## Testing

Verified functionality:
- ✅ Database queries work correctly
- ✅ Aggregation logic accurate
- ✅ URL routing configured
- ✅ Navigation links added
- ✅ Year filtering compatible
- ✅ Django checks pass (no errors)

## Future Enhancements (Optional)

1. **Search/Filter**: Add candidate name search
2. **Sort Options**: Allow sorting by spent, report count, etc.
3. **Party Affiliation**: Add party information if available
4. **Office Sought**: Show what office candidate is running for
5. **Election Cycle**: Group by election cycle
6. **Comparison Tool**: Side-by-side candidate comparison
7. **Export**: Download candidate data as CSV
8. **Race View**: Group candidates by race/office

## Integration with Existing Features

- Uses same year filtering as other pages
- Same navigation structure and theme
- Consistent styling with PACs and Contributors pages
- Compatible with search functionality
- Works with existing performance optimizations
