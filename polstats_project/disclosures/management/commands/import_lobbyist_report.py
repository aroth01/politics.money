import sys
import os
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime
from decimal import Decimal

# Add the parent directory to the path to import our parser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../'))

from lobbyist_parser import parse_lobbyist_report
from ...models import LobbyistReport, LobbyistExpenditure


class Command(BaseCommand):
    help = 'Import Utah lobbyist expenditure report from a URL'

    def add_arguments(self, parser):
        parser.add_argument(
            'url',
            type=str,
            help='URL of the Utah lobbyist report to import (e.g., https://lobbyist.utah.gov/Search/PublicSearch/Report/174643)'
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
        # URL format: https://lobbyist.utah.gov/Search/PublicSearch/Report/174643
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

        self.stdout.write(f'Fetching lobbyist report from: {url}')
        self.stdout.write(f'Report ID: {report_id}')

        # Check if report already exists
        existing_report = LobbyistReport.objects.filter(report_id=report_id).first()
        if existing_report and not update:
            raise CommandError(
                f'Report {report_id} already exists. Use --update to overwrite.'
            )

        # Fetch and parse data
        try:
            data = parse_lobbyist_report(url)
        except Exception as e:
            raise CommandError(f'Error parsing lobbyist report: {str(e)}')

        self.stdout.write(self.style.SUCCESS('Data fetched successfully'))

        # Import data in a transaction
        with transaction.atomic():
            # Create or update the main report
            if existing_report and update:
                self.stdout.write(f'Updating existing report {report_id}...')
                report = existing_report
                # Delete existing expenditures
                report.expenditures.all().delete()
            else:
                self.stdout.write(f'Creating new report {report_id}...')
                report = LobbyistReport(report_id=report_id)

            # Set report fields
            report.source_url = url
            report_info = data.get('report_info', {})
            report.title = report_info.get('title', 'Lobbyist Expenditure Report')
            report.report_info = report_info

            # Set principal information
            report.principal_name = report_info.get('Principal Name', report_info.get('Name', ''))
            report.principal_phone = report_info.get('Principal Phone', report_info.get('Phone', ''))
            report.principal_street_address = report_info.get('Principal Street Address', '')
            report.principal_city = report_info.get('Principal City', '')
            report.principal_state = report_info.get('Principal State', '')
            report.principal_zip = report_info.get('Principal Zip', '')

            # Set report period information
            report.report_type = report_info.get('Report Type', 'Lobbyist Expenditure')
            report.begin_date = self.parse_date(report_info.get('Begin Date', ''))
            report.end_date = self.parse_date(report_info.get('End Date', ''))
            report.due_date = self.parse_date(report_info.get('Due Date', ''))
            report.submit_date = self.parse_date(report_info.get('Submit Date', ''))

            # Set balance summary
            balance = data.get('balance_summary', {})
            report.total_expenditures = self._get_decimal(
                balance.get('Total Expenditures Made')
            )

            report.last_scraped_at = timezone.now()
            report.save()

            # Import expenditures
            expenditures = data.get('expenditures', [])
            self.stdout.write(f'Importing {len(expenditures)} expenditures...')

            for exp_data in expenditures:
                expenditure = LobbyistExpenditure(
                    report=report,
                    date_raw=exp_data.get('date', ''),
                    date=self.parse_date(exp_data.get('date', '')),
                    recipient_name=exp_data.get('recipient_name', ''),
                    location=exp_data.get('location', ''),
                    purpose=exp_data.get('purpose', ''),
                    is_amendment=exp_data.get('amendment', False),
                    amount=Decimal(str(exp_data.get('amount', 0)))
                )
                expenditure.save()

        # Print summary
        self.stdout.write(self.style.SUCCESS('\n✓ Import completed successfully!'))
        self.stdout.write(f'\nReport: {report.title}')
        self.stdout.write(f'  ID: {report.report_id}')
        self.stdout.write(f'  Principal: {report.principal_name}')
        self.stdout.write(f'  Expenditures: {len(expenditures)} (${sum(e.get("amount", 0) for e in expenditures):,.2f})')

    def _get_decimal(self, value):
        """Convert value to Decimal, handling None."""
        if value is None or value == '':
            return None
        return Decimal(str(value))
