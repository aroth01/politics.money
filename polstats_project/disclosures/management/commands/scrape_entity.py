import re
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from decouple import config

from ...models import EntityRegistration, EntityOfficer

# Load custom User-Agent from environment
USER_AGENT = config('USER_AGENT', default='PolStatsBot/1.0 (Utah Political Finance Data Aggregator)')


class Command(BaseCommand):
    help = 'Scrape entity registration data from Utah disclosures website'

    def add_arguments(self, parser):
        parser.add_argument(
            'entity_id',
            type=str,
            help='Entity ID to scrape (e.g., 1414358)'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing entity if it already exists'
        )

    def parse_date(self, date_str):
        """Parse date string in M/D/YYYY format."""
        if not date_str or date_str.strip() == '' or date_str == '--':
            return None

        date_str = date_str.strip()
        try:
            return datetime.strptime(date_str, '%m/%d/%Y').date()
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.WARNING(f'Could not parse date: {date_str}')
                )
                return None

    def clean_text(self, text):
        """Clean whitespace from text."""
        if not text:
            return ''
        return ' '.join(text.strip().split())

    def parse_address(self, address_text):
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

    def scrape_entity(self, entity_id):
        """Scrape entity registration page."""
        url = f'https://disclosures.utah.gov/Registration/EntityDetails/{entity_id}'

        self.stdout.write(f'Fetching entity data from: {url}')

        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise CommandError(f'Error fetching entity page: {str(e)}')

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract entity data
        entity_data = {
            'entity_id': entity_id,
            'source_url': url,
            'raw_data': {}
        }

        # Find all labels and get their values
        # Strategy: use FIRST occurrence of each field (PAC info comes before officer/affiliated org info)
        all_labels = soup.find_all('label')

        for label in all_labels:
            label_text = self.clean_text(label.get_text())
            label_for = label.get('for', '')

            # Find the value - it's in the parent div's text, excluding the label
            parent_div = label.find_parent('div')
            if parent_div:
                # Get all text from parent, then remove label text
                full_text = self.clean_text(parent_div.get_text())
                # Remove the label text from the beginning
                if full_text.startswith(label_text):
                    field_value = full_text[len(label_text):].strip()
                else:
                    field_value = full_text

                # Store in raw_data (only if not already present - first wins)
                if label_text not in entity_data['raw_data']:
                    entity_data['raw_data'][label_text] = field_value

                # Map specific fields - use FIRST occurrence only
                if label_for == 'Name' or (label_text == 'Name' and 'name' not in entity_data):
                    entity_data['name'] = field_value
                elif (label_for == 'AlsoKnownAs' or label_text == 'Also known as') and 'also_known_as' not in entity_data:
                    entity_data['also_known_as'] = field_value
                elif (label_for == 'DateCreated' or label_text == 'Date Created') and 'date_created' not in entity_data:
                    entity_data['date_created'] = self.parse_date(field_value)
                elif (label_text == 'Type' or label_text == 'Entity Type' or label_text == 'Registration Type') and 'entity_type' not in entity_data:
                    entity_data['entity_type'] = field_value
                elif (label_text == 'Status') and 'status' not in entity_data:
                    entity_data['status'] = field_value
                elif label_text == 'Street Address' and 'street_address' not in entity_data:
                    entity_data['street_address'] = field_value
                elif label_text == 'Suite/PO Box' and 'suite_po_box' not in entity_data:
                    entity_data['suite_po_box'] = field_value
                elif label_text == 'City' and 'city' not in entity_data:
                    entity_data['city'] = field_value
                elif label_text == 'State' and 'state' not in entity_data:
                    entity_data['state'] = field_value
                elif label_text == 'Zip' and 'zip_code' not in entity_data:
                    entity_data['zip_code'] = field_value

        # Extract officers by looking for span tags with bold text
        officers = []
        officer_idx = 0

        all_spans = soup.find_all('span', style=lambda value: value and 'font-weight: bold' in value)

        for span in all_spans:
            span_text = self.clean_text(span.get_text())

            # Look for officer section headers
            if 'Name of Primary Officer' in span_text or 'Name of additional' in span_text or 'Name of the PAC Chief Financial Officer' in span_text:
                officer_data = {
                    'order': officer_idx,
                    'is_treasurer': 'Chief Financial Officer' in span_text or 'Treasurer' in span_text
                }
                officer_idx += 1

                # Find the div containing this span
                parent_div = span.find_parent('div')
                if not parent_div:
                    continue

                # Look for labels in subsequent divs
                current_elem = parent_div
                for _ in range(20):  # Check next 20 elements
                    next_div = current_elem.find_next('div')
                    if not next_div:
                        break

                    # Stop if we hit another officer section
                    next_span = next_div.find('span', style=lambda value: value and 'font-weight: bold' in value)
                    if next_span and ('Name of' in next_span.get_text()):
                        break

                    # Look for labels in this div
                    labels_in_div = next_div.find_all('label')
                    for label in labels_in_div:
                        label_text = self.clean_text(label.get_text())
                        label_for = label.get('for', '')

                        # Get value from parent div
                        label_parent = label.find_parent('div')
                        if label_parent:
                            full_text = self.clean_text(label_parent.get_text())
                            if full_text.startswith(label_text):
                                field_value = full_text[len(label_text):].strip()
                            else:
                                field_value = full_text

                            # Map officer fields - collect name parts separately
                            if 'First' in label_text:
                                officer_data['first_name'] = field_value
                            elif 'Middle' in label_text:
                                officer_data['middle_name'] = field_value
                            elif 'Last' in label_text:
                                officer_data['last_name'] = field_value
                            elif label_text == 'Title':
                                officer_data['title'] = field_value
                            elif label_text == 'Phone':
                                officer_data['phone'] = field_value
                            elif label_text == 'Email':
                                officer_data['email'] = field_value
                            elif 'Address' in label_text:
                                # Parse address
                                addr_parts = self.parse_address(field_value)
                                officer_data.update(addr_parts)

                    current_elem = next_div

                # Assemble full name from parts
                name_parts = []
                if 'first_name' in officer_data and officer_data['first_name']:
                    name_parts.append(officer_data['first_name'])
                if 'middle_name' in officer_data and officer_data['middle_name']:
                    name_parts.append(officer_data['middle_name'])
                if 'last_name' in officer_data and officer_data['last_name']:
                    name_parts.append(officer_data['last_name'])

                if name_parts:
                    officer_data['name'] = ' '.join(name_parts)
                    officers.append(officer_data)

        return entity_data, officers

    def handle(self, *args, **options):
        entity_id = options['entity_id']
        update = options['update']

        # Check if entity already exists
        existing_entity = EntityRegistration.objects.filter(entity_id=entity_id).first()
        if existing_entity and not update:
            raise CommandError(
                f'Entity {entity_id} already exists. Use --update to overwrite.'
            )

        # Scrape entity data
        try:
            entity_data, officers_data = self.scrape_entity(entity_id)
        except Exception as e:
            raise CommandError(f'Error scraping entity: {str(e)}')

        self.stdout.write(self.style.SUCCESS('Data scraped successfully'))

        # Import data in a transaction
        with transaction.atomic():
            # Create or update the entity
            if existing_entity and update:
                self.stdout.write(f'Updating existing entity {entity_id}...')
                entity = existing_entity
                # Delete existing officers
                entity.officers.all().delete()
            else:
                self.stdout.write(f'Creating new entity {entity_id}...')
                entity = EntityRegistration(entity_id=entity_id)

            # Set entity fields
            entity.source_url = entity_data.get('source_url', '')
            entity.name = entity_data.get('name', '')
            entity.also_known_as = entity_data.get('also_known_as', '')
            entity.date_created = entity_data.get('date_created')
            entity.street_address = entity_data.get('street_address', '')
            entity.suite_po_box = entity_data.get('suite_po_box', '')
            entity.city = entity_data.get('city', '')
            entity.state = entity_data.get('state', '')
            entity.zip_code = entity_data.get('zip_code', '')
            entity.raw_data = entity_data.get('raw_data', {})
            entity.last_scraped_at = timezone.now()
            entity.save()

            # Import officers
            self.stdout.write(f'Importing {len(officers_data)} officers...')
            for officer_data in officers_data:
                officer = EntityOfficer(
                    entity=entity,
                    name=officer_data.get('name', ''),
                    title=officer_data.get('title', ''),
                    occupation=officer_data.get('occupation', ''),
                    phone=officer_data.get('phone', ''),
                    email=officer_data.get('email', ''),
                    street_address=officer_data.get('street_address', ''),
                    suite_po_box=officer_data.get('suite_po_box', ''),
                    city=officer_data.get('city', ''),
                    state=officer_data.get('state', ''),
                    zip_code=officer_data.get('zip_code', ''),
                    order=officer_data.get('order', 0),
                    is_treasurer=officer_data.get('is_treasurer', False)
                )
                officer.save()

        # Print summary
        self.stdout.write(self.style.SUCCESS('\n✓ Import completed successfully!'))
        self.stdout.write(f'\nEntity: {entity.name}')
        self.stdout.write(f'  ID: {entity.entity_id}')
        self.stdout.write(f'  Date Created: {entity.date_created}')
        self.stdout.write(f'  Address: {entity.street_address}, {entity.city}, {entity.state} {entity.zip_code}')
        self.stdout.write(f'  Officers: {len(officers_data)}')
        for officer in entity.officers.all():
            self.stdout.write(f'    - {officer.name} ({officer.title})')
