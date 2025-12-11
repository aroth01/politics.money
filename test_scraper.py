#!/usr/bin/env python3
"""Diagnostic script to test Utah disclosures website scraping."""

import requests
from bs4 import BeautifulSoup

USER_AGENT = 'PolStatsBot/1.0 (Utah Political Finance Data Aggregator)'

# Test the public search page
url = 'https://disclosures.utah.gov/Search/PublicSearch?Skip=0'

print(f"Testing URL: {url}")
print(f"User-Agent: {USER_AGENT}\n")

try:
    headers = {'User-Agent': USER_AGENT}
    response = requests.get(url, headers=headers, timeout=30)

    print(f"Status Code: {response.status_code}")
    print(f"Content Length: {len(response.content)} bytes\n")

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Look for report links
        report_links = soup.find_all('a', href=lambda href: href and '/Report/' in href)
        print(f"Found {len(report_links)} links with '/Report/' in href")

        if report_links:
            print("\nFirst 5 report links:")
            for i, link in enumerate(report_links[:5], 1):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                print(f"  {i}. {href} - '{text}'")
        else:
            # Debug: show all links on the page
            all_links = soup.find_all('a', href=True)
            print(f"\nNo report links found. Total links on page: {len(all_links)}")

            if all_links:
                print("\nFirst 10 links on the page:")
                for i, link in enumerate(all_links[:10], 1):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)[:50]
                    print(f"  {i}. {href} - '{text}'")

            # Check if there's a table or other structure
            tables = soup.find_all('table')
            print(f"\nFound {len(tables)} tables on the page")

            # Look for any elements with 'report' in class or id
            report_elements = soup.find_all(class_=lambda x: x and 'report' in x.lower())
            report_elements += soup.find_all(id=lambda x: x and 'report' in x.lower())
            print(f"Found {len(report_elements)} elements with 'report' in class/id")

            # Save HTML for inspection
            with open('/tmp/disclosures_page.html', 'w') as f:
                f.write(response.text)
            print("\nSaved full HTML to /tmp/disclosures_page.html for inspection")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
