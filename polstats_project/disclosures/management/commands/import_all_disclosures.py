import sys
import os
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime
from decimal import Decimal

# Add the parent directory to the path to import our parser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../'))

from utah_disclosures_parser import parse_utah_disclosure
from ...models import DisclosureReport, Contribution, Expenditure


class Command(BaseCommand):
    help = 'Batch import all Utah campaign finance disclosure reports by iterating through IDs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start',
            type=int,
            default=1,
            help='Starting report ID (default: 1)'
        )
        parser.add_argument(
            '--end',
            type=int,
            default=None,
            help='Ending report ID (default: continue until invalid report found)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay in seconds between requests to avoid overwhelming the server (default: 1.0)'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip reports that already exist in the database'
        )
        parser.add_argument(
            '--max-consecutive-failures',
            type=int,
            default=10,
            help='Stop after this many consecutive failures (default: 10)'
        )
        parser.add_argument(
            '--ignore-consecutive-failures',
            action='store_true',
            help='Never stop due to consecutive failures (useful when there are gaps in report IDs)'
        )

    def is_valid_report(self, data):
        """
        Check if the report contains real data.
        Invalid reports have $0.00 balances and dates like "1/1/0001".
        """
        # Check if balance summary has any non-zero values
        balance = data.get('balance_summary', {})

        # If all balance values are 0, it's likely invalid
        has_balance_data = any(
            v > 0 for v in balance.values()
            if v is not None and isinstance(v, (int, float))
        )

        # Check if there are any contributions or expenditures
        has_transactions = (
            len(data.get('contributions', [])) > 0 or
            len(data.get('expenditures', [])) > 0
        )

        return has_balance_data or has_transactions

    def parse_date(self, date_str):
        """Parse date string in M/D/YYYY format."""
        if not date_str or date_str == '--':
            return None

        try:
            return datetime.strptime(date_str, '%m/%d/%Y').date()
        except ValueError:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return None

    def import_report(self, report_id, skip_existing=False):
        """
        Import a single report by ID.
        Returns: (success: bool, message: str, is_invalid: bool)
        """
        url = f"https://disclosures.utah.gov/Search/PublicSearch/Report/{report_id}"

        # Check if report already exists (always check, regardless of skip_existing flag)
        if DisclosureReport.objects.filter(report_id=str(report_id)).exists():
            if skip_existing:
                return True, f"Report {report_id} already exists (skipped)", False
            else:
                # If not explicitly skipping, still skip but don't count as success
                return True, f"Report {report_id} already exists (skipped)", False

        # Fetch and parse data
        try:
            data = parse_utah_disclosure(url)
        except Exception as e:
            return False, f"Error parsing report {report_id}: {str(e)}", False

        # Check if report is valid
        if not self.is_valid_report(data):
            return False, f"Report {report_id} appears to be invalid (no data)", True

        # Import data in a transaction
        try:
            with transaction.atomic():
                # Create the report
                report = DisclosureReport(report_id=str(report_id))
                report.source_url = url
                report_info = data.get('report_info', {})
                report.title = report_info.get('title', '')
                report.report_info = report_info

                # Set organization information
                report.organization_name = report_info.get('Name', '')
                report.organization_type = report_info.get('organization_type', '')

                # Set report period information
                report.report_type = report_info.get('Report Type', '')
                report.begin_date = self.parse_date(report_info.get('Begin Date', ''))
                report.end_date = self.parse_date(report_info.get('End Date', ''))
                report.due_date = self.parse_date(report_info.get('Due Date', ''))
                report.submit_date = self.parse_date(report_info.get('Submit Date', ''))

                # Set balance summary fields
                balance = data.get('balance_summary', {})
                report.balance_beginning = self._get_decimal(
                    balance.get('Balance at Beginning of Reporting Period')
                )
                report.total_contributions = self._get_decimal(
                    balance.get('Total Contributions Received')
                )
                report.total_expenditures = self._get_decimal(
                    balance.get('Total Expenditures Made')
                )
                report.ending_balance = self._get_decimal(
                    balance.get('Ending Balance')
                )

                report.last_scraped_at = timezone.now()
                report.save()

                # Import contributions
                for contrib_data in data.get('contributions', []):
                    contribution = Contribution(
                        report=report,
                        date_received_raw=contrib_data.get('date_received', ''),
                        date_received=self.parse_date(contrib_data.get('date_received', '')),
                        contributor_name=contrib_data.get('contributor_name', ''),
                        address=contrib_data.get('address', ''),
                        is_in_kind=contrib_data.get('in_kind', False),
                        is_loan=contrib_data.get('loan', False),
                        is_amendment=contrib_data.get('amendment', False),
                        amount=Decimal(str(contrib_data.get('amount', 0)))
                    )
                    contribution.save()

                # Import expenditures
                for exp_data in data.get('expenditures', []):
                    expenditure = Expenditure(
                        report=report,
                        date_raw=exp_data.get('date', ''),
                        date=self.parse_date(exp_data.get('date', '')),
                        recipient_name=exp_data.get('recipient_name', ''),
                        purpose=exp_data.get('purpose', ''),
                        is_in_kind=exp_data.get('in_kind', False),
                        is_loan=exp_data.get('loan', False),
                        is_amendment=exp_data.get('amendment', False),
                        amount=Decimal(str(exp_data.get('amount', 0)))
                    )
                    expenditure.save()

                contrib_count = len(data.get('contributions', []))
                exp_count = len(data.get('expenditures', []))
                return True, f"Imported report {report_id}: {contrib_count} contributions, {exp_count} expenditures", False

        except Exception as e:
            return False, f"Error saving report {report_id}: {str(e)}", False

    def handle(self, *args, **options):
        start_id = options['start']
        end_id = options['end']
        delay = options['delay']
        skip_existing = options['skip_existing']
        max_consecutive_failures = options['max_consecutive_failures']
        ignore_consecutive_failures = options['ignore_consecutive_failures']

        self.stdout.write(self.style.SUCCESS(f'\nStarting batch import from ID {start_id}'))
        if end_id:
            self.stdout.write(f'Will stop at ID {end_id}')
        else:
            if ignore_consecutive_failures:
                self.stdout.write('Will continue indefinitely (ignoring consecutive failures)')
            else:
                self.stdout.write(f'Will continue until {max_consecutive_failures} consecutive invalid reports')
        self.stdout.write(f'Delay between requests: {delay}s\n')

        current_id = start_id
        consecutive_failures = 0
        total_imported = 0
        total_skipped = 0
        total_failed = 0
        start_time = time.time()

        try:
            while True:
                # Check if we've reached the end ID
                if end_id and current_id > end_id:
                    self.stdout.write(self.style.SUCCESS(f'\nReached end ID {end_id}'))
                    break

                # Check if we've had too many consecutive failures (unless ignored)
                if not ignore_consecutive_failures and consecutive_failures >= max_consecutive_failures:
                    self.stdout.write(
                        self.style.WARNING(
                            f'\nStopping after {consecutive_failures} consecutive invalid reports'
                        )
                    )
                    break

                # Import the report
                success, message, is_invalid = self.import_report(current_id, skip_existing)

                if success:
                    if 'skipped' in message:
                        total_skipped += 1
                        self.stdout.write(self.style.WARNING(f'[{current_id}] {message}'))
                    else:
                        total_imported += 1
                        consecutive_failures = 0  # Reset counter on success
                        self.stdout.write(self.style.SUCCESS(f'[{current_id}] {message}'))
                else:
                    total_failed += 1
                    if is_invalid:
                        consecutive_failures += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'[{current_id}] {message} (consecutive failures: {consecutive_failures})'
                            )
                        )
                    else:
                        # Don't count parsing errors as consecutive failures
                        self.stdout.write(self.style.ERROR(f'[{current_id}] {message}'))

                # Move to next ID
                current_id += 1

                # Delay before next request
                if delay > 0:
                    time.sleep(delay)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nImport interrupted by user'))

        # Print summary
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('IMPORT SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f'Total reports imported: {total_imported}')
        self.stdout.write(f'Total reports skipped: {total_skipped}')
        self.stdout.write(f'Total reports failed: {total_failed}')
        self.stdout.write(f'Last ID processed: {current_id - 1}')
        self.stdout.write(f'Time elapsed: {elapsed_time:.1f}s')
        self.stdout.write(f'Average time per report: {elapsed_time / max(1, total_imported):.2f}s')
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

    def _get_decimal(self, value):
        """Convert value to Decimal, handling None."""
        if value is None or value == '':
            return None
        return Decimal(str(value))
