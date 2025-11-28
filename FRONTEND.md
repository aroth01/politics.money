# Frontend Documentation

The Utah Campaign Finance Disclosures application features a modern, responsive web interface built with:

- **DaisyUI** - Beautiful, accessible UI components based on Tailwind CSS
- **D3.js** - Interactive data visualizations
- **Responsive Design** - Works on desktop, tablet, and mobile devices

## Pages Overview

### 1. Homepage (`/`)

The homepage provides an at-a-glance overview of the entire dataset:

**Features:**
- **Statistics Cards**: Total reports, contributions amount, expenditures amount
- **Recent Reports Table**: Latest 10 disclosure reports
- **Top Contributors**: Top 10 contributors by total amount
- **Top Recipients**: Top 10 expenditure recipients
- **Global Timeline Chart**: Line chart showing contributions and expenditures over time (monthly aggregation)

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

- **Primary**: Blue (`#3b82f6`) - Used for contributions, primary actions
- **Secondary**: Various DaisyUI theme colors
- **Success/Green**: Used for positive values (contributions)
- **Error/Red**: Used for expenditures
- **Base Colors**: DaisyUI neutral palette for backgrounds and text

### Typography

- **Headers**: Bold, large font sizes (text-4xl for h1)
- **Body**: Standard readable font size
- **Monospace**: Used for monetary values and IDs for clarity

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

DaisyUI supports multiple themes. To change the theme, edit `base.html`:

```html
<html lang="en" data-theme="dark">  <!-- Change to: dark, cupcake, cyberpunk, etc. -->
```

Available themes: light, dark, cupcake, bumblebee, emerald, corporate, synthwave, retro, cyberpunk, valentine, halloween, garden, forest, aqua, lofi, pastel, fantasy, wireframe, black, luxury, dracula

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
