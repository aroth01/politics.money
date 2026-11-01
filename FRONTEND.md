# Frontend Documentation

The Utah Campaign Finance Disclosures application features a modern, responsive web interface built with:

- **DaisyUI** - Accessible UI components based on Tailwind CSS, themed to the site palette (`data-theme="ledger"` in `base.html`)
- **D3.js** - Interactive data visualizations
- **Responsive Design** - Works on desktop, tablet, and mobile devices

The look follows the "Ledger × Canyon" design: a deep pine masthead with a double-rule title bar and
condensed uppercase navigation, year filter chips, a cream paper body set in Newsreader with Barlow
Condensed labels and figures, a sand/rust sequential ramp for quantities, and a "How we count" footer.

## Pages Overview

### 1. Overview (`/`)

The homepage is an editorial overview of the whole dataset (or of one year when a year chip is selected):

**Features:**
- **Headline and lede**: Share of gifts under $50 and the share of dollars from gifts of $10,000 or more
- **Key figures**: Total raised, total spent with payment count, report count, distinct filers
- **The election-year surge**: Monthly raised/spent line chart with hover tooltip and peak-month annotations
- **When the money moves**: Calendar heatmap of monthly fundraising with a detail panel on hover
- **The many and the few**: Share of contributions vs. share of dollars in five gift size bands
- **Raised, then spent**: Dumbbell chart of the ten biggest fundraisers, linked to their detail pages
- **Money from beyond Utah**: Tile map of contributions by state with in-state share and a hover detail

The monthly chart and heatmap load from `/api/global/timeline/` (which honours `?year=`); everything
else is aggregated in `views.index` and rendered server-side.

**URL:** http://localhost:8000/

---

### 2. Reports List (`/reports/`)

Browse all disclosure reports with advanced filtering:

**Features:**
- **Search**: Find reports by title or ID
- **Sorting Options**:
  - Newest/Oldest first
  - Highest/Lowest balance
  - Report ID (ascending/descending)
- **Pagination**: 25 reports per page
- **Table Columns**:
  - Report ID (clickable link)
  - Title
  - Beginning Balance
  - Total Contributions (green)
  - Total Expenditures (red)
  - Ending Balance (bold)
  - Created Date

**URL:** http://localhost:8000/reports/

---

### 3. Report Detail (`/reports/<id>/`)

Detailed view of a single disclosure report with visualizations:

**Features:**

**Statistics Section:**
- Beginning Balance
- Total Contributions with transaction count and average
- Total Expenditures with transaction count and average
- Ending Balance

**Interactive Charts:**
1. **Daily Activity Timeline** - Dual-line chart showing contributions (blue) and expenditures (red) over time
2. **Top Contributors Bar Chart** - Top 10 contributors by amount
3. **Top Expenditure Recipients Bar Chart** - Top 10 recipients by amount

**Data Tables:**
- **Contributions Tab**:
  - Date, Contributor Name, Address, Amount
  - Badges for In-Kind, Loan, Amendment flags
  - Shows first 100, with indicator if more exist

- **Expenditures Tab**:
  - Date, Recipient, Purpose, Amount
  - Badges for In-Kind, Loan, Amendment flags
  - Shows first 100, with indicator if more exist

**URL:** http://localhost:8000/reports/198820/

---

### 4. Contributors List (`/contributors/`)

Aggregated view of all contributors across all reports:

**Features:**
- **Search**: Find contributors by name or address
- **Pagination**: 50 contributors per page
- **Table Columns**:
  - Name
  - Address
  - Total Contributed (aggregated across all reports)
  - Number of Contributions
  - Date of Last Contribution

**URL:** http://localhost:8000/contributors/

---

### 5. Expenditures List (`/expenditures/`)

Aggregated view of all expenditure recipients:

**Features:**
- **Search**: Find recipients by name or purpose
- **Pagination**: 50 recipients per page
- **Table Columns**:
  - Recipient Name
  - Purpose
  - Total Spent (aggregated across all reports)
  - Number of Transactions
  - Date of Last Expenditure

**URL:** http://localhost:8000/expenditures/

---

## Design System

### Color Palette

Defined as CSS custom properties in `base.html` and mirrored in the `ledger` DaisyUI theme:

- **Pine** (`#0F2E2B`) - Masthead, footer, primary buttons and links; Utah on the map
- **Paper** (`#F4F2ED` / `#FBFAF7`) - Page and panel backgrounds
- **Sand → Rust ramp** (`#DE9A60` → `#7B2815`) - Sequential shading for heatmaps, bands and the tile map
- **Sand** (`#CF7D24`) - Money raised, the active year chip
- **Teal** (`#35A7A1` / `#0D9293`) - Money spent, success values
- **Ink** (`#1B2423`) with muted greys for secondary text

### Typography

- **Newsreader** (serif) - Body text and headlines
- **Barlow Condensed** - Kickers, navigation, chips, axis labels and big figures
- **Monospace**: Used for monetary values and IDs in tables

### Components

- **Cards**: Elevated cards with shadows for content grouping
- **Tables**: Zebra-striped tables with hover effects
- **Buttons**: DaisyUI button styles (primary, ghost, outline)
- **Badges**: Small colored labels for flags (in-kind, loan, amendment)
- **Stats**: Special stat cards for key metrics
- **Pagination**: Join-style pagination controls

### Responsive Behavior

- **Desktop**: Full multi-column layouts with side-by-side charts
- **Tablet**: Stacked columns, reduced padding
- **Mobile**: Single column, hamburger menu navigation, simplified tables

---

## API Endpoints

The frontend consumes JSON API endpoints for chart data:

### Report-Specific APIs

- `GET /api/reports/<id>/timeline/` - Daily contributions and expenditures
  ```json
  {
    "contributions": [{"date": "2024-01-15", "amount": 1500.00, "count": 5}],
    "expenditures": [{"date": "2024-01-16", "amount": 750.00, "count": 3}]
  }
  ```

- `GET /api/reports/<id>/top-contributors/` - Top 10 contributors
  ```json
  [{"name": "John Doe", "amount": 5000.00}, ...]
  ```

- `GET /api/reports/<id>/top-expenditures/` - Top 10 expenditure recipients
  ```json
  [{"name": "Vendor Inc", "amount": 3000.00}, ...]
  ```

### Global APIs

- `GET /api/global/timeline/` - Monthly contributions and expenditures across all reports
  ```json
  {
    "contributions": [{"date": "2024-01", "amount": 15000.00, "count": 50}],
    "expenditures": [{"date": "2024-01", "amount": 7500.00, "count": 30}]
  }
  ```

---

## Customization

### Changing the Theme

The site uses a custom DaisyUI theme named `ledger`, defined as oklch variables in `base.html`
alongside the CSS custom properties (`--pine`, `--sand`, `--paper`, ...). Change the colors there to
restyle both the custom chrome and the DaisyUI components on the inner pages. The masthead, footer
and overview page use the custom properties directly.

### Adding New Charts

1. Create a new API endpoint in `views.py`
2. Add a div container in the template
3. Write D3.js code in the `{% block extra_scripts %}` section
4. Fetch data and render using D3.js

### Modifying Styles

- Use Tailwind CSS utility classes directly in templates
- DaisyUI components: https://daisyui.com/components/
- Custom CSS can be added to `<style>` tags in `base.html`

---

## Performance Notes

- **CDN Assets**: DaisyUI, Tailwind, React, and D3.js are loaded from CDNs
- **Pagination**: Large datasets are paginated to prevent slow page loads
- **Chart Data**: API endpoints return aggregated data for efficient rendering
- **Database Indexes**: Models include indexes on frequently queried fields

---

## Accessibility

- Semantic HTML elements
- ARIA labels on interactive elements
- Keyboard navigation support (DaisyUI components)
- Color contrast ratios meet WCAG AA standards
- Responsive text sizing

---

## Browser Support

Tested and working on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Requires JavaScript enabled for charts and interactive features.
