#!/usr/bin/env python3
"""
Utah Lobbyist Entity Registration Parser

This script fetches lobbyist entity registration data from Utah's lobbyist disclosure website
and converts the data into structured JSON format.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import os
from typing import Dict, List, Any
from decouple import config

# Load custom User-Agent from environment (defaults to a descriptive bot identifier)
USER_AGENT = config('USER_AGENT', default='PolStatsBot/1.0 (Utah Political Finance Data Aggregator)')


def clean_text(text: str) -> str:
    """Clean whitespace from text."""
    if not text:
        return ''
    return ' '.join(text.strip().split())


def parse_address(address_text: str) -> Dict[str, str]:
    """Parse address into components."""
    if not address_text:
        return {}

    parts = [p.strip() for p in address_text.split(',')]

    result = {
        'street_address': '',
        'city': '',
        'state': '',
        'zip_code': ''
    }

    if len(parts) >= 3:
        result['street_address'] = parts[0]
        result['city'] = parts[1]

        # Parse state and zip from last part
        state_zip = parts[2].strip()
        match = re.match(r'([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', state_zip)
        if match:
            result['state'] = match.group(1)
            result['zip_code'] = match.group(2)
    elif len(parts) == 2:
        result['city'] = parts[0]
        state_zip = parts[1].strip()
        match = re.match(r'([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', state_zip)
        if match:
            result['state'] = match.group(1)
            result['zip_code'] = match.group(2)

    return result


def parse_lobbyist_entity(url: str) -> Dict[str, Any]:
    """
    Main parser function that fetches and parses a Utah lobbyist entity registration.

    Args:
        url: URL of the lobbyist entity registration page

    Returns:
        Dictionary containing all parsed entity data
    """
    # Fetch the page with custom User-Agent
    headers = {
        'User-Agent': USER_AGENT
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract entity ID from URL
    entity_id = url.rstrip('/').split('/')[-1]

    # Extract entity data
    entity_data = {
        'entity_id': entity_id,
        'source_url': url,
        'entity_type': 'Lobbyist',
        'raw_data': {}
    }

    # Find all labels and get their values
    all_labels = soup.find_all('label')

    for label in all_labels:
        label_text = clean_text(label.get_text())
        label_for = label.get('for', '')

        # Find the value - it's in the parent div's text, excluding the label
        parent_div = label.find_parent('div')
        if parent_div:
            # Get all text from parent, then remove label text
            full_text = clean_text(parent_div.get_text())
            # Remove the label text from the beginning
            if full_text.startswith(label_text):
                field_value = full_text[len(label_text):].strip()
            else:
                field_value = full_text

            # Store in raw_data (only if not already present - first wins)
            if label_text and field_value and label_text not in entity_data['raw_data']:
                entity_data['raw_data'][label_text] = field_value

            # Map specific fields for lobbyist entity
            # Lobbyist personal info
            if 'First Name' in label_text and 'first_name' not in entity_data:
                entity_data['first_name'] = field_value
            elif 'Last Name' in label_text and 'last_name' not in entity_data:
                entity_data['last_name'] = field_value
            elif label_text == 'Telephone' and 'phone' not in entity_data:
                entity_data['phone'] = field_value
            elif 'Registration Date' in label_text and 'date_created' not in entity_data:
                entity_data['date_created'] = field_value

            # Business/Organization info
            elif 'Organization Name' in label_text and 'organization_name' not in entity_data:
                entity_data['organization_name'] = field_value
            elif label_text == 'Street Address' and 'street_address' not in entity_data:
                entity_data['street_address'] = field_value
            elif label_text == 'City' and 'city' not in entity_data:
                entity_data['city'] = field_value
            elif label_text == 'State' and 'state' not in entity_data:
                entity_data['state'] = field_value
            elif label_text == 'Zip' and 'zip_code' not in entity_data:
                entity_data['zip_code'] = field_value

            # Principal/Client info
            elif 'Principal Name' in label_text and 'principal_name' not in entity_data:
                entity_data['principal_name'] = field_value
            elif 'General Purposes' in label_text or 'Nature' in label_text:
                if 'lobbying_purposes' not in entity_data:
                    entity_data['lobbying_purposes'] = field_value

    # Construct full name if we have first/last
    if 'first_name' in entity_data and 'last_name' in entity_data:
        entity_data['name'] = f"{entity_data['first_name']} {entity_data['last_name']}"
    elif 'organization_name' in entity_data:
        entity_data['name'] = entity_data['organization_name']
    elif 'principal_name' in entity_data:
        entity_data['name'] = entity_data['principal_name']

    # Look for additional principals/affiliated organizations in tables
    principals = []
    tables = soup.find_all('table')

    for table in tables:
        # Check if this is a principals/affiliates table
        thead = table.find('thead')
        if thead and 'Principal' in thead.get_text():
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        principal = {
                            'name': clean_text(cells[0].get_text()),
                            'contact': clean_text(cells[1].get_text()) if len(cells) > 1 else ''
                        }
                        if principal['name']:
                            principals.append(principal)

    if principals:
        entity_data['principals'] = principals

    return entity_data


def main():
    """Main entry point."""
    # Example usage
    url = "https://lobbyist.utah.gov/Registration/EntityDetails/1410867"

    print(f"Fetching lobbyist entity from {url}...")
    data = parse_lobbyist_entity(url)

    # Convert to JSON
    json_output = json.dumps(data, indent=2)

    # Save to file
    output_file = 'lobbyist_entity_data.json'
    with open(output_file, 'w') as f:
        f.write(json_output)

    print(f"\nData successfully parsed!")
    print(f"Saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Entity ID: {data.get('entity_id')}")
    print(f"  Name: {data.get('name', 'N/A')}")
    print(f"  Type: {data.get('entity_type', 'N/A')}")
    if 'principals' in data:
        print(f"  Principals: {len(data['principals'])}")


if __name__ == '__main__':
    main()
