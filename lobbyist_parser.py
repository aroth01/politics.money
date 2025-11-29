#!/usr/bin/env python3
"""
Utah Lobbyist Disclosures Parser

This script fetches lobbyist expenditure reports from Utah's lobbyist disclosure website
and converts the data into structured JSON format.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, List, Any


def parse_currency(value: str) -> float:
    """Convert currency string to float."""
    if not value or value == '--':
        return 0.0
    # Remove $, commas, and convert to float
    clean_value = re.sub(r'[$,]', '', value.strip())
    try:
        return float(clean_value)
    except ValueError:
        return 0.0


def parse_balance_summary(soup: BeautifulSoup) -> Dict[str, float]:
    """Parse the balance summary table."""
    balance_data = {}

    # Find the "Balance Summary" h1 and get the table after it
    balance_heading = soup.find('h1', string=re.compile('Balance Summary', re.IGNORECASE))
    if not balance_heading:
        return balance_data

    # Find the table that follows the heading
    balance_table = balance_heading.find_next('table')
    if not balance_table:
        return balance_data

    # Parse table rows
    rows = balance_table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')

        # Balance tables can have different formats:
        # Format 1 (newer): 2 cells - [label, value]
        # Format 2 (older): 4 cells - [line_number, label, value1, value2]
        if len(cells) == 2:
            label = cells[0].get_text(strip=True).rstrip(':')
            value = parse_currency(cells[1].get_text(strip=True))
            if label and not label.isdigit():  # Skip if label is just a number
                # Clean up label - remove parenthetical notes
                label = re.sub(r'\([^)]*\)', '', label).strip()
                balance_data[label] = value
        elif len(cells) >= 3:
            # Try format with line number, label, value
            line_num = cells[0].get_text(strip=True)
            label = cells[1].get_text(strip=True).rstrip(':')
            value = parse_currency(cells[2].get_text(strip=True))
            if label and not label.isdigit():  # Skip if label is just a number
                # Clean up label - remove parenthetical notes
                label = re.sub(r'\([^)]*\)', '', label).strip()
                balance_data[label] = value

    return balance_data


def parse_expenditures(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Parse the itemized expenditures table for lobbyist reports."""
    expenditures = []

    # Find all tables with class 'dis-table'
    tables = soup.find_all('table', class_='dis-table')

    # Find the table that has "Expenditure" in its headers
    exp_table = None
    for table in tables:
        thead = table.find('thead')
        if thead:
            header_text = thead.get_text()
            if 'Expenditure' in header_text:
                exp_table = table
                break

    if not exp_table:
        return expenditures

    # Find the tbody
    tbody = exp_table.find('tbody')
    if not tbody:
        return expenditures

    # Parse each row in the table
    rows = tbody.find_all('tr')
    for row in rows:
        cells = row.find_all('td')

        # Lobbyist expenditure format (6 cells): Date, Recipient Name, Location, Purpose, Amendment, Amount
        if len(cells) >= 6:
            # Determine which cell has the amount (should be last cell with $ sign)
            amount_cell_idx = -1
            for i in range(len(cells) - 1, -1, -1):
                cell_text = cells[i].get_text(strip=True)
                if '$' in cell_text or cell_text.replace(',', '').replace('.', '').isdigit():
                    amount_cell_idx = i
                    break

            if amount_cell_idx == -1:
                amount_cell_idx = len(cells) - 1  # Default to last cell

            # Amendment flag is the cell before amount
            amendment_idx = amount_cell_idx - 1

            expenditure = {
                'date': cells[0].get_text(strip=True),
                'recipient_name': cells[1].get_text(strip=True),
                'location': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                'purpose': cells[3].get_text(strip=True) if len(cells) > 3 else '',
                'amendment': bool(cells[amendment_idx].find('a', class_='anchorLink') and cells[amendment_idx].get_text(strip=True)) if amendment_idx >= 0 else False,
                'amount': parse_currency(cells[amount_cell_idx].get_text(strip=True))
            }
            expenditures.append(expenditure)

    return expenditures


def parse_report_info(soup: BeautifulSoup) -> Dict[str, str]:
    """Parse basic report information from the lobbyist page."""
    info = {}

    # Try to extract report title from page title element
    title_elem = soup.find('title')
    if title_elem:
        # Title format: "Lieutenant Governor's Office - Expenditures For Principal"
        full_title = title_elem.get_text(strip=True)
        if ' - ' in full_title:
            # Remove the "Lieutenant Governor's Office - " prefix
            report_title = full_title.split(' - ', 1)[1]
            info['title'] = report_title
            info['organization_type'] = 'Lobbyist/Principal'

    # Parse fieldset elements that contain structured data
    fieldsets = soup.find_all('fieldset')
    for fieldset in fieldsets:
        # Get legend to identify the section
        legend = fieldset.find('legend')
        legend_text = legend.get_text(strip=True) if legend else ''

        # Find all divs with class 'dis-cell' that contain labels
        dis_cells = fieldset.find_all('div', class_='dis-cell')
        for cell in dis_cells:
            label = cell.find('label')
            if label:
                label_text = label.get_text(strip=True).rstrip(':')
                # The value is in the same div, after the label
                # Get all text from the div and remove the label text
                full_text = cell.get_text(strip=True)
                value_text = full_text.replace(label_text, '').strip()
                if label_text and value_text:
                    # Prefix with section name if it's principal info
                    if 'Principal' in legend_text:
                        info[f'Principal {label_text}'] = value_text
                    else:
                        info[label_text] = value_text

    # Also look for divs with class patterns used in the report
    rows = soup.find_all('div', class_='row')
    for row in rows:
        # Try to find label-value pairs in col-md patterns
        label_divs = row.find_all('div', class_=re.compile(r'col-md-\d'))
        if len(label_divs) >= 2:
            for i in range(0, len(label_divs) - 1, 2):
                label_text = label_divs[i].get_text(strip=True).rstrip(':')
                value_text = label_divs[i + 1].get_text(strip=True)
                if label_text and value_text and ':' not in value_text:
                    info[label_text] = value_text

    return info


def parse_lobbyist_report(url: str) -> Dict[str, Any]:
    """
    Main parser function that fetches and parses a Utah lobbyist expenditure report.

    Args:
        url: URL of the lobbyist report

    Returns:
        Dictionary containing all parsed data in structured format
    """
    # Fetch the page
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract all data
    data = {
        'source_url': url,
        'report_type': 'lobbyist',
        'report_info': parse_report_info(soup),
        'balance_summary': parse_balance_summary(soup),
        'expenditures': parse_expenditures(soup)
    }

    # Add summary statistics
    data['summary'] = {
        'total_expenditures': len(data['expenditures']),
        'total_expenditure_amount': sum(e['amount'] for e in data['expenditures'])
    }

    return data


def main():
    """Main entry point."""
    # Example usage
    url = "https://lobbyist.utah.gov/Search/PublicSearch/Report/174643"

    print(f"Fetching lobbyist data from {url}...")
    data = parse_lobbyist_report(url)

    # Convert to JSON
    json_output = json.dumps(data, indent=2)

    # Save to file
    output_file = 'lobbyist_report_data.json'
    with open(output_file, 'w') as f:
        f.write(json_output)

    print(f"\nData successfully parsed!")
    print(f"Saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Expenditures: {data['summary']['total_expenditures']} (${data['summary']['total_expenditure_amount']:,.2f})")


if __name__ == '__main__':
    main()
