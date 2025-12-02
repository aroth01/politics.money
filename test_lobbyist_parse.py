#!/usr/bin/env python
"""Test parsing a lobbyist report."""
import os
import sys
import django

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'polstats_project.settings')
django.setup()

import requests
from bs4 import BeautifulSoup
from decouple import config

# Fetch and examine table structure
url = "https://disclosures.utah.gov/Search/PublicSearch/Report/108481"
print(f"Fetching lobbyist report: {url}\n")

USER_AGENT = config('USER_AGENT', default='PolStatsBot/1.0 (Utah Political Finance Data Aggregator)')
headers = {'User-Agent': USER_AGENT}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')

# Find the expenditures table
tables = soup.find_all('table', class_='dis-table')
for table in tables:
    thead = table.find('thead')
    if thead and 'Expenditure' in thead.get_text():
        print('=== EXPENDITURE TABLE HEADERS ===')
        headers = thead.find_all('th')
        for i, th in enumerate(headers):
            print(f'Column {i}: {th.get_text(strip=True)}')

        print(f'\n=== FIRST ROW (total {len(headers)} columns) ===')
        tbody = table.find('tbody')
        if tbody:
            first_row = tbody.find('tr')
            if first_row:
                cells = first_row.find_all('td')
                print(f'Number of cells: {len(cells)}')
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    if len(text) > 100:
                        text = text[:100] + '...'
                    print(f'Cell {i}: {text}')
        break

# Now parse with the parser
print("\n\n=== PARSER OUTPUT ===")
from utah_disclosures_parser import parse_utah_disclosure

data = parse_utah_disclosure(url)
print(f"Report: {data['report_info'].get('title', 'Unknown')}")
print(f"Organization: {data['report_info'].get('Name', 'Unknown')}")
print(f"Expenditures: {len(data['expenditures'])}")

if data['expenditures']:
    print("\nFirst expenditure:")
    exp = data['expenditures'][0]
    for key, value in exp.items():
        print(f"  {key}: {value}")

    # Check if address field is captured
    if 'address' in exp and exp['address']:
        print(f"\n✓ Location field captured: {exp['address'][:100]}...")
    else:
        print("\n✗ No location field captured")
