"""
Entity crawler for Utah campaign finance disclosures.
Continuously crawls entity registrations from the Utah disclosures website.
"""
import re
import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
from decouple import config

from ...models import EntityRegistration, EntityOfficer

# Set up logging
logger = logging.getLogger(__name__)

# Load custom User-Agent from environment
USER_AGENT = config('USER_AGENT', default='PolStatsBot/1.0 (Utah Political Finance Data Aggregator)')


class Command(BaseCommand):
    help = 'Continuously crawl entity registration data from Utah disclosures website'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-id',
            type=int,
            default=1,
            help='Starting entity ID (default: 1)'
        )
        parser.add_argument(
            '--end-id',
            type=int,
            help='Ending entity ID (optional, if not set will run continuously)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Delay between requests in seconds (default: 2.0)'
        )
        parser.add_argument(
            '--max-failures',
            type=int,
            default=50,
            help='Maximum consecutive 404s before stopping (default: 50)'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update entities that were last scraped more than 30 days ago'
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
                logger.warning(f'Could not parse date: {date_str}')
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

        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(url, headers=headers, timeout=30)

            # Handle 404s
            if response.status_code == 404:
                return None

            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f'Error fetching entity {entity_id}: {str(e)}')
            return False

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract entity data
        entity_data = {
            'entity_id': entity_id,
            'source_url': url,
            'raw_data': {}
        }

        # Find all labels and get their values
        all_labels = soup.find_all('label')

        for label in all_labels:
            label_text = self.clean_text(label.get_text())
            label_for = label.get('for', '')

            # Find the value - it's in the parent div's text, excluding the label
            parent_div = label.find_parent('div')
            if parent_div:
                full_text = self.clean_text(parent_div.get_text())
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

        # Extract officers
        officers = []
        officer_idx = 0

        all_spans = soup.find_all('span', style=lambda value: value and 'font-weight: bold' in value)

        for span in all_spans:
            span_text = self.clean_text(span.get_text())

            if 'Name of Primary Officer' in span_text or 'Name of additional' in span_text or 'Name of the PAC Chief Financial Officer' in span_text:
                officer_data = {
                    'order': officer_idx,
                    'is_treasurer': 'Chief Financial Officer' in span_text or 'Treasurer' in span_text
                }
                officer_idx += 1

                parent_div = span.find_parent('div')
                if not parent_div:
                    continue

                current_elem = parent_div
                for _ in range(20):
                    next_div = current_elem.find_next('div')
                    if not next_div:
                        break

                    next_span = next_div.find('span', style=lambda value: value and 'font-weight: bold' in value)
                    if next_span and ('Name of' in next_span.get_text()):
                        break

                    labels_in_div = next_div.find_all('label')
                    for label in labels_in_div:
                        label_text = self.clean_text(label.get_text())

                        label_parent = label.find_parent('div')
                        if label_parent:
                            full_text = self.clean_text(label_parent.get_text())
                            if full_text.startswith(label_text):
                                field_value = full_text[len(label_text):].strip()
                            else:
                                field_value = full_text

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
                                addr_parts = self.parse_address(field_value)
                                officer_data.update(addr_parts)

                    current_elem = next_div

                # Assemble full name
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

    def save_entity(self, entity_data, officers_data):
        """Save entity and officers to database."""
        with transaction.atomic():
            entity, created = EntityRegistration.objects.get_or_create(
                entity_id=entity_data['entity_id'],
                defaults={
                    'source_url': entity_data.get('source_url', ''),
                    'name': entity_data.get('name', ''),
                    'also_known_as': entity_data.get('also_known_as', ''),
                    'entity_type': entity_data.get('entity_type', ''),
                    'status': entity_data.get('status', ''),
                    'date_created': entity_data.get('date_created'),
                    'street_address': entity_data.get('street_address', ''),
                    'suite_po_box': entity_data.get('suite_po_box', ''),
                    'city': entity_data.get('city', ''),
                    'state': entity_data.get('state', ''),
                    'zip_code': entity_data.get('zip_code', ''),
                    'raw_data': entity_data.get('raw_data', {}),
                    'last_scraped_at': timezone.now()
                }
            )

            if not created:
                # Update existing entity
                entity.source_url = entity_data.get('source_url', '')
                entity.name = entity_data.get('name', '')
                entity.also_known_as = entity_data.get('also_known_as', '')
                entity.entity_type = entity_data.get('entity_type', '')
                entity.status = entity_data.get('status', '')
                entity.date_created = entity_data.get('date_created')
                entity.street_address = entity_data.get('street_address', '')
                entity.suite_po_box = entity_data.get('suite_po_box', '')
                entity.city = entity_data.get('city', '')
                entity.state = entity_data.get('state', '')
                entity.zip_code = entity_data.get('zip_code', '')
                entity.raw_data = entity_data.get('raw_data', {})
                entity.last_scraped_at = timezone.now()
                entity.save()

                # Delete old officers
                entity.officers.all().delete()

            # Create officers
            for officer_data in officers_data:
                EntityOfficer.objects.create(
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

            return entity, created

    def handle(self, *args, **options):
        start_id = options['start_id']
        end_id = options['end_id']
        delay = options['delay']
        max_failures = options['max_failures']
        update_existing = options['update_existing']

        consecutive_failures = 0
        current_id = start_id
        total_scraped = 0
        total_created = 0
        total_updated = 0
        total_skipped = 0

        logger.info(f'Starting entity crawler from ID {start_id}')
        self.stdout.write(self.style.SUCCESS(f'Starting entity crawler from ID {start_id}'))

        if end_id:
            self.stdout.write(f'Will stop at ID {end_id}')
        else:
            self.stdout.write('Running continuously (no end ID specified)')

        try:
            while True:
                # Check if we should stop
                if end_id and current_id > end_id:
                    self.stdout.write(self.style.SUCCESS(f'\nReached end ID {end_id}'))
                    break

                # Check if entity already exists
                existing = EntityRegistration.objects.filter(entity_id=current_id).first()

                if existing and not update_existing:
                    self.stdout.write(f'  Skipping {current_id} (already exists)')
                    total_skipped += 1
                    current_id += 1
                    continue

                if existing and update_existing:
                    # Check if it needs updating (older than 30 days)
                    if existing.last_scraped_at and existing.last_scraped_at > timezone.now() - timedelta(days=30):
                        self.stdout.write(f'  Skipping {current_id} (recently updated)')
                        total_skipped += 1
                        current_id += 1
                        continue

                # Scrape entity
                self.stdout.write(f'Scraping entity {current_id}...', ending='')
                result = self.scrape_entity(current_id)

                if result is None:
                    # 404 - entity doesn't exist
                    consecutive_failures += 1
                    self.stdout.write(self.style.WARNING(f' 404 (consecutive: {consecutive_failures})'))

                    if consecutive_failures >= max_failures:
                        self.stdout.write(self.style.WARNING(
                            f'\nStopping after {max_failures} consecutive 404s'
                        ))
                        break

                    current_id += 1
                    time.sleep(delay)
                    continue

                if result is False:
                    # Error occurred
                    self.stdout.write(self.style.ERROR(' ERROR'))
                    current_id += 1
                    time.sleep(delay)
                    continue

                # Successfully scraped
                consecutive_failures = 0
                entity_data, officers_data = result

                # Save to database
                try:
                    entity, created = self.save_entity(entity_data, officers_data)
                    total_scraped += 1

                    if created:
                        total_created += 1
                        self.stdout.write(self.style.SUCCESS(
                            f' ✓ Created: {entity.name} ({len(officers_data)} officers)'
                        ))
                    else:
                        total_updated += 1
                        self.stdout.write(self.style.SUCCESS(
                            f' ✓ Updated: {entity.name} ({len(officers_data)} officers)'
                        ))

                    logger.info(f'Scraped entity {current_id}: {entity.name}')

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f' ERROR saving: {str(e)}'))
                    logger.error(f'Error saving entity {current_id}: {str(e)}')

                # Move to next
                current_id += 1
                time.sleep(delay)

                # Print stats every 10 entities
                if total_scraped % 10 == 0:
                    self.stdout.write(self.style.SUCCESS(
                        f'\n--- Stats: {total_scraped} scraped, {total_created} created, '
                        f'{total_updated} updated, {total_skipped} skipped ---\n'
                    ))

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nStopped by user'))

        # Final stats
        self.stdout.write(self.style.SUCCESS('\n=== Final Statistics ==='))
        self.stdout.write(f'Total scraped: {total_scraped}')
        self.stdout.write(f'Total created: {total_created}')
        self.stdout.write(f'Total updated: {total_updated}')
        self.stdout.write(f'Total skipped: {total_skipped}')
        self.stdout.write(f'Last ID: {current_id - 1}')
