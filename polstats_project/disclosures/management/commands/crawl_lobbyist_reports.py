import sys
import os
import time
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils import timezone
from datetime import datetime, timedelta

# Add the parent directory to the path to import our parser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../'))

from ...models import LobbyistReport


class Command(BaseCommand):
    help = 'Crawl lobbyist expenditure reports by incrementing report IDs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-id',
            type=int,
            default=1,
            help='Starting report ID (default: 1)'
        )
        parser.add_argument(
            '--end-id',
            type=int,
            help='Ending report ID (optional, will run until max failures)'
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
            default=100,
            help='Max consecutive 404s before stopping (default: 100)'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip reports that already exist in database'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing reports that are older than 30 days'
        )

    def handle(self, *args, **options):
        start_id = options['start_id']
        end_id = options['end_id']
        delay = options['delay']
        max_failures = options['max_failures']
        skip_existing = options['skip_existing']
        update_existing = options['update_existing']

        self.stdout.write(self.style.SUCCESS('=== Lobbyist Report Crawler ==='))
        self.stdout.write(f'Starting from report ID: {start_id}')
        if end_id:
            self.stdout.write(f'Ending at report ID: {end_id}')
        self.stdout.write(f'Delay between requests: {delay}s')
        self.stdout.write(f'Max consecutive failures: {max_failures}')
        self.stdout.write('')

        current_id = start_id
        consecutive_failures = 0
        total_scraped = 0
        total_created = 0
        total_updated = 0
        total_skipped = 0

        while True:
            # Check if we've reached the end
            if end_id and current_id > end_id:
                self.stdout.write(self.style.SUCCESS(f'\nReached end ID {end_id}'))
                break

            # Check if we've had too many consecutive failures
            if consecutive_failures >= max_failures:
                self.stdout.write(
                    self.style.WARNING(
                        f'\nStopping after {consecutive_failures} consecutive failures'
                    )
                )
                break

            # Build URL
            url = f'https://lobbyist.utah.gov/Search/PublicSearch/Report/{current_id}'

            # Check if report exists
            existing = LobbyistReport.objects.filter(report_id=str(current_id)).first()

            if existing:
                if skip_existing:
                    self.stdout.write(f'[{current_id}] Already exists - skipping')
                    total_skipped += 1
                    current_id += 1
                    consecutive_failures = 0
                    continue
                elif update_existing:
                    # Check if it's old enough to update
                    age = timezone.now() - existing.last_scraped_at
                    if age < timedelta(days=30):
                        self.stdout.write(
                            f'[{current_id}] Updated {age.days} days ago - skipping'
                        )
                        total_skipped += 1
                        current_id += 1
                        consecutive_failures = 0
                        continue

            # Try to scrape this report
            try:
                self.stdout.write(f'[{current_id}] Scraping...', ending=' ')

                # Call the import command
                call_command(
                    'import_lobbyist_report',
                    url,
                    '--update' if (existing and update_existing) else '',
                    verbosity=0
                )

                if existing:
                    self.stdout.write(self.style.SUCCESS('✓ Updated'))
                    total_updated += 1
                else:
                    self.stdout.write(self.style.SUCCESS('✓ Created'))
                    total_created += 1

                total_scraped += 1
                consecutive_failures = 0

            except CommandError as e:
                error_msg = str(e)

                # Check if it's a 404 or similar
                if 'already exists' in error_msg:
                    self.stdout.write(self.style.WARNING('Already exists'))
                    total_skipped += 1
                    consecutive_failures = 0
                elif '404' in error_msg or 'not found' in error_msg.lower():
                    self.stdout.write('✗ 404')
                    consecutive_failures += 1
                else:
                    self.stdout.write(self.style.ERROR(f'✗ Error: {error_msg}'))
                    consecutive_failures += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
                consecutive_failures += 1

            # Print stats every 10 reports
            if total_scraped > 0 and total_scraped % 10 == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n--- Stats: {total_scraped} scraped, '
                        f'{total_created} created, {total_updated} updated, '
                        f'{total_skipped} skipped ---\n'
                    )
                )

            # Move to next report
            current_id += 1

            # Delay before next request
            if delay > 0:
                time.sleep(delay)

        # Final stats
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Crawl Complete ==='))
        self.stdout.write(f'Total scraped: {total_scraped}')
        self.stdout.write(f'Created: {total_created}')
        self.stdout.write(f'Updated: {total_updated}')
        self.stdout.write(f'Skipped: {total_skipped}')
        self.stdout.write(f'Final report ID: {current_id - 1}')
