import sys
import os
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
    help = 'Import Utah campaign finance disclosure data from a URL'

    def add_arguments(self, parser):
        parser.add_argument(
            'url',
            type=str,
            help='URL of the Utah disclosure report to import'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing report if it already exists'
        )
        parser.add_argument(
            '--report-id',
            type=str,
            help='Override report ID (defaults to extracting from URL)'
        )

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
                self.stdout.write(
                    self.style.WARNING(f'Could not parse date: {date_str}')
                )
                return None

    def extract_report_id(self, url):
        """Extract report ID from URL."""
        # URL format: https://disclosures.utah.gov/Search/PublicSearch/Report/198820
        parts = url.rstrip('/').split('/')
        if parts and parts[-1].isdigit():
            return parts[-1]
        return None

    def handle(self, *args, **options):
        url = options['url']
        update = options['update']
        report_id = options.get('report_id') or self.extract_report_id(url)

        if not report_id:
            raise CommandError('Could not extract report ID from URL. Please provide --report-id')

        self.stdout.write(f'Fetching disclosure data from: {url}')
        self.stdout.write(f'Report ID: {report_id}')

        # Check if report already exists
        existing_report = DisclosureReport.objects.filter(report_id=report_id).first()
        if existing_report and not update:
            raise CommandError(
                f'Report {report_id} already exists. Use --update to overwrite.'
            )

        # Fetch and parse data
        try:
            data = parse_utah_disclosure(url)
        except Exception as e:
            raise CommandError(f'Error parsing disclosure: {str(e)}')

        self.stdout.write(self.style.SUCCESS('Data fetched successfully'))

        # Import data in a transaction
        with transaction.atomic():
            # Create or update the main report
            if existing_report and update:
                self.stdout.write(f'Updating existing report {report_id}...')
                report = existing_report
                # Delete existing contributions and expenditures
                report.contributions.all().delete()
                report.expenditures.all().delete()
            else:
                self.stdout.write(f'Creating new report {report_id}...')
                report = DisclosureReport(report_id=report_id)

            # Set report fields
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
            contributions = data.get('contributions', [])
            self.stdout.write(f'Importing {len(contributions)} contributions...')

            for contrib_data in contributions:
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
            expenditures = data.get('expenditures', [])
            self.stdout.write(f'Importing {len(expenditures)} expenditures...')

            for exp_data in expenditures:
                expenditure = Expenditure(
                    report=report,
                    date_raw=exp_data.get('date', ''),
                    date=self.parse_date(exp_data.get('date', '')),
                    recipient_name=exp_data.get('recipient_name', ''),
                    address=exp_data.get('address', ''),  # Location/venue for lobbyist expenditures
                    purpose=exp_data.get('purpose', ''),
                    is_in_kind=exp_data.get('in_kind', False),
                    is_loan=exp_data.get('loan', False),
                    is_amendment=exp_data.get('amendment', False),
                    amount=Decimal(str(exp_data.get('amount', 0)))
                )
                expenditure.save()

        # Print summary
        self.stdout.write(self.style.SUCCESS('\n✓ Import completed successfully!'))
        self.stdout.write(f'\nReport: {report.title}')
        self.stdout.write(f'  ID: {report.report_id}')
        self.stdout.write(f'  Contributions: {contributions.__len__()} (${sum(c.get("amount", 0) for c in contributions):,.2f})')
        self.stdout.write(f'  Expenditures: {expenditures.__len__()} (${sum(e.get("amount", 0) for e in expenditures):,.2f})')
        ending_bal = report.ending_balance if report.ending_balance is not None else 0
        self.stdout.write(f'  Ending Balance: ${ending_bal:,.2f}')

    def _get_decimal(self, value):
        """Convert value to Decimal, handling None."""
        if value is None or value == '':
            return None
        return Decimal(str(value))
