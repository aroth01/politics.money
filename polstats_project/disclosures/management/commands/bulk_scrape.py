import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import transaction, models
from datetime import datetime, timedelta
from decouple import config

from ...models import DisclosureReport, EntityRegistration

# Load custom User-Agent from environment
USER_AGENT = config('USER_AGENT', default='PolStatsBot/1.0 (Utah Political Finance Data Aggregator)')


class Command(BaseCommand):
    help = 'Bulk scrape entities and reports from Utah disclosures website'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['entities', 'reports', 'all'],
            default='all',
            help='What to scrape: entities, reports, or all'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of items to scrape (for testing)'
        )
        parser.add_argument(
            '--start-page',
            type=int,
            default=1,
            help='Starting page number for report scraping'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            help='Maximum number of pages to scrape for reports'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Delay in seconds between requests (default: 2.0)'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing records'
        )
        parser.add_argument(
            '--recent-only',
            action='store_true',
            help='Only scrape entities/reports from the last 30 days'
        )

    def scrape_entity_list(self):
        """Scrape list of all registered entities by iterating through entity IDs."""
        self.stdout.write('Discovering entities by ID range...')

        entities = []

        # Strategy: Try a range of entity IDs to discover what exists
        # Most entity IDs seem to be in a sequential range
        # We'll check which IDs exist by trying to access them

        # First, find the current maximum entity ID in our database
        max_existing_id = EntityRegistration.objects.aggregate(
            max_id=models.Max('entity_id')
        )['max_id']

        if max_existing_id:
            start_id = int(max_existing_id)
            self.stdout.write(f'Starting from existing max ID: {start_id}')
        else:
            # Start from a reasonable ID if we have none
            start_id = 1400000  # Based on the example ID 1414358
            self.stdout.write(f'No existing entities, starting from: {start_id}')

        # Also check some older IDs we might have missed
        # Sample backwards from start_id
        test_range = list(range(max(1, start_id - 1000), start_id)) + list(range(start_id, start_id + 5000))

        self.stdout.write(f'Testing {len(test_range)} potential entity IDs...')

        consecutive_failures = 0
        max_consecutive_failures = 100  # Stop after 100 consecutive non-existent IDs

        for entity_id in test_range:
            url = f'https://disclosures.utah.gov/Registration/EntityDetails/{entity_id}'

            try:
                # Use GET instead of HEAD - some servers don't respond well to HEAD
                headers = {'User-Agent': USER_AGENT}
                response = requests.get(url, headers=headers, timeout=30, allow_redirects=False)

                if response.status_code == 200:
                    # Entity exists!
                    consecutive_failures = 0
                    entities.append({
                        'entity_id': str(entity_id),
                        'name': f'Entity {entity_id}'  # Name will be fetched during scraping
                    })

                    if len(entities) % 10 == 0:
                        self.stdout.write(f'Found {len(entities)} entities so far...')

                elif response.status_code == 404:
                    # Entity doesn't exist
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        self.stdout.write(f'Stopped after {max_consecutive_failures} consecutive non-existent IDs')
                        break

                time.sleep(self.delay)  # Use full delay for GET requests

            except requests.Timeout:
                self.stdout.write(
                    self.style.WARNING(f'Timeout checking entity {entity_id} - skipping')
                )
                # Don't count timeouts as consecutive failures - the server might just be slow
                time.sleep(self.delay * 2)  # Wait longer after timeout
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error checking entity {entity_id}: {str(e)}')
                )
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    break
                time.sleep(self.delay)

        self.stdout.write(f'Entity discovery complete. Found {len(entities)} entities.')

        return entities

    def scrape_report_list(self, start_page=1, max_pages=None):
        """Discover reports by iterating through report IDs.

        Note: This just returns a list for compatibility, but actual scraping
        happens in bulk_scrape_reports() which scrapes as it discovers.
        """
        # This is now just a placeholder - actual work is done in bulk_scrape_reports
        return []

    def bulk_scrape_entities(self, limit=None, update_existing=False):
        """Bulk scrape entities."""
        self.stdout.write(self.style.SUCCESS('\n=== Starting Entity Scraping ===\n'))

        entities = self.scrape_entity_list()

        if limit:
            entities = entities[:limit]

        self.stdout.write(f'Will scrape {len(entities)} entities')

        success_count = 0
        error_count = 0
        skipped_count = 0

        for idx, entity in enumerate(entities, 1):
            entity_id = entity['entity_id']
            entity_name = entity.get('name', 'Unknown')

            # Check if already exists
            if not update_existing:
                if EntityRegistration.objects.filter(entity_id=entity_id).exists():
                    self.stdout.write(f'[{idx}/{len(entities)}] Skipping {entity_name} (ID: {entity_id}) - already exists')
                    skipped_count += 1
                    continue

            self.stdout.write(f'[{idx}/{len(entities)}] Scraping {entity_name} (ID: {entity_id})...')

            try:
                # Call the scrape_entity command
                call_command(
                    'scrape_entity',
                    entity_id,
                    update=update_existing,
                    stdout=self.stdout if self.verbosity >= 2 else None
                )
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Success'))

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))

            # Rate limiting
            time.sleep(self.delay)

        self.stdout.write(self.style.SUCCESS(f'\n=== Entity Scraping Complete ==='))
        self.stdout.write(f'Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}')

    def bulk_scrape_reports(self, limit=None, update_existing=False):
        """Bulk scrape reports by ID incrementing - discover and scrape in one pass."""
        self.stdout.write(self.style.SUCCESS('\n=== Starting Report Scraping ===\n'))

        # Find the current maximum report ID in our database
        max_existing_id = DisclosureReport.objects.aggregate(
            max_id=models.Max('report_id')
        )['max_id']

        if max_existing_id:
            start_id = int(max_existing_id)
            self.stdout.write(f'Starting from existing max ID: {start_id}')
        else:
            # Start from a reasonable ID if we have none
            start_id = 180000
            self.stdout.write(f'No existing reports, starting from: {start_id}')

        # Hard limit at 300000
        max_report_id = 300000
        self.stdout.write(f'Will check report IDs from {start_id} to {max_report_id}')

        success_count = 0
        error_count = 0
        skipped_count = 0

        for report_id in range(start_id, max_report_id + 1):
            # Check limit
            if limit and (success_count + skipped_count) >= limit:
                self.stdout.write(f'Reached limit of {limit} reports')
                break

            url = f'https://disclosures.utah.gov/Search/PublicSearch/Report/{report_id}'

            # Check if already exists
            if not update_existing:
                if DisclosureReport.objects.filter(report_id=str(report_id)).exists():
                    skipped_count += 1
                    if skipped_count % 100 == 0:
                        self.stdout.write(f'Skipped {skipped_count} existing reports...')
                    continue

            try:
                # Try to scrape the report
                headers = {'User-Agent': USER_AGENT}
                response = requests.head(url, headers=headers, timeout=10, allow_redirects=False)

                # If page exists, scrape it
                if response.status_code == 200:
                    self.stdout.write(f'Scraping Report {report_id}...')

                    try:
                        call_command(
                            'import_disclosure',
                            url,
                            update=update_existing,
                            report_id=str(report_id),
                            stdout=self.stdout if self.verbosity >= 2 else None
                        )
                        success_count += 1
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Success ({success_count} total)'))

                    except CommandError as e:
                        # Check if this is a blank report (should be skipped, not an error)
                        if 'is blank' in str(e):
                            skipped_count += 1
                            if self.verbosity >= 1:
                                self.stdout.write(f'  - Blank report, skipping')
                        else:
                            error_count += 1
                            self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))

                    # Rate limiting after successful scrape
                    time.sleep(self.delay)

            except requests.Timeout:
                self.stdout.write(self.style.WARNING(f'Timeout checking report {report_id} - skipping'))
                time.sleep(self.delay * 2)
            except Exception as e:
                # Silently skip connection errors, etc
                pass

        self.stdout.write(self.style.SUCCESS(f'\n=== Report Scraping Complete ==='))
        self.stdout.write(f'Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}')

    def handle(self, *args, **options):
        scrape_type = options['type']
        limit = options.get('limit')
        update_existing = options['update_existing']
        self.delay = options['delay']
        self.verbosity = options['verbosity']

        start_time = datetime.now()

        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('  BULK SCRAPER - Utah Campaign Finance Disclosures'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f'Started at: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'Scrape type: {scrape_type}')
        self.stdout.write(f'Limit: {limit or "None"}')
        self.stdout.write(f'Update existing: {update_existing}')
        self.stdout.write(f'Delay: {self.delay}s')
        self.stdout.write('')

        try:
            if scrape_type in ['entities', 'all']:
                self.bulk_scrape_entities(
                    limit=limit,
                    update_existing=update_existing
                )

            if scrape_type in ['reports', 'all']:
                self.bulk_scrape_reports(
                    limit=limit,
                    update_existing=update_existing
                )

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nScraping interrupted by user'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n\nFatal error: {str(e)}'))
            raise

        end_time = datetime.now()
        duration = end_time - start_time

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f'Completed at: {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write(f'Total duration: {duration}')
        self.stdout.write(self.style.SUCCESS('='*70))
