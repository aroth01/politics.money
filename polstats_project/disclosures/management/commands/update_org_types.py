"""Management command to update organization types for existing reports."""
import sys
import os
from django.core.management.base import BaseCommand
from django.db import transaction

# Add the parent directory to the path to import our parser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../'))

from utah_disclosures_parser import parse_utah_disclosure
from polstats_project.disclosures.models import DisclosureReport


class Command(BaseCommand):
    help = 'Update organization type and title for all existing reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of reports to update (for testing)'
        )

    def handle(self, *args, **options):
        limit = options.get('limit')

        # Get all reports that don't have an organization type
        reports = DisclosureReport.objects.filter(
            organization_type__isnull=True
        ) | DisclosureReport.objects.filter(
            organization_type=''
        )

        if limit:
            reports = reports[:limit]

        total = reports.count()
        self.stdout.write(f'Found {total} reports to update')

        updated = 0
        failed = 0

        for report in reports:
            try:
                # Re-parse the report to get the organization type
                url = f"https://disclosures.utah.gov/Search/PublicSearch/Report/{report.report_id}"
                data = parse_utah_disclosure(url)

                report_info = data.get('report_info', {})

                # Update organization type and title
                report.organization_type = report_info.get('organization_type', '')
                report.title = report_info.get('title', '')
                report.save(update_fields=['organization_type', 'title'])

                updated += 1
                if updated % 100 == 0:
                    self.stdout.write(f'Updated {updated}/{total} reports...')

            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f'Failed to update report {report.report_id}: {str(e)}')
                )

        self.stdout.write(self.style.SUCCESS(f'\nCompleted!'))
        self.stdout.write(f'  Updated: {updated}')
        self.stdout.write(f'  Failed: {failed}')
