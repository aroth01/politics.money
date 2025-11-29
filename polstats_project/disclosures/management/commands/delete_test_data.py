from django.core.management.base import BaseCommand
from django.db import transaction
from ...models import DisclosureReport, Contribution, Expenditure


class Command(BaseCommand):
    help = 'Delete test data from production database (exact match on "test")'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete the data (required for real deletion)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']

        if not dry_run and not confirm:
            self.stdout.write(
                self.style.ERROR('Error: You must use either --dry-run or --confirm')
            )
            self.stdout.write('Use --dry-run to preview what would be deleted')
            self.stdout.write('Use --confirm to actually delete the data')
            return

        self.stdout.write(self.style.WARNING('=== Searching for Test Data ==='))
        self.stdout.write('')

        # Find reports with "test" in organization name (case-insensitive exact match)
        test_reports = DisclosureReport.objects.filter(organization_name__iexact='test')

        # Find contributions with "test" in contributor name (case-insensitive exact match)
        test_contributions = Contribution.objects.filter(contributor_name__iexact='test')

        # Find expenditures with "test" in recipient name (case-insensitive exact match)
        test_expenditures = Expenditure.objects.filter(recipient_name__iexact='test')

        # Display what was found
        self.stdout.write(f'Found {test_reports.count()} reports with organization_name="test"')
        if test_reports.exists():
            for report in test_reports:
                self.stdout.write(f'  - Report {report.report_id}: {report.organization_name} ({report.title})')
                contrib_count = report.contributions.count()
                exp_count = report.expenditures.count()
                self.stdout.write(f'    ({contrib_count} contributions, {exp_count} expenditures)')

        self.stdout.write('')
        self.stdout.write(f'Found {test_contributions.count()} contributions with contributor_name="test"')
        if test_contributions.exists():
            for contrib in test_contributions[:10]:  # Show first 10
                self.stdout.write(f'  - {contrib.contributor_name} - ${contrib.amount} (Report {contrib.report.report_id})')
            if test_contributions.count() > 10:
                self.stdout.write(f'  ... and {test_contributions.count() - 10} more')

        self.stdout.write('')
        self.stdout.write(f'Found {test_expenditures.count()} expenditures with recipient_name="test"')
        if test_expenditures.exists():
            for exp in test_expenditures[:10]:  # Show first 10
                self.stdout.write(f'  - {exp.recipient_name} - ${exp.amount} (Report {exp.report.report_id})')
            if test_expenditures.count() > 10:
                self.stdout.write(f'  ... and {test_expenditures.count() - 10} more')

        # Calculate totals
        total_items = test_reports.count() + test_contributions.count() + test_expenditures.count()

        if total_items == 0:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('No test data found!'))
            return

        # Display deletion plan
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=== Deletion Plan ==='))
        self.stdout.write(f'Will delete:')
        self.stdout.write(f'  - {test_reports.count()} reports (and all their related contributions/expenditures)')
        self.stdout.write(f'  - {test_contributions.count()} standalone contributions with name "test"')
        self.stdout.write(f'  - {test_expenditures.count()} standalone expenditures with name "test"')

        # Perform deletion if confirmed
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('DRY RUN - No data was deleted'))
            self.stdout.write('Run with --confirm to actually delete this data')
        else:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DELETING DATA...'))

            with transaction.atomic():
                # Delete contributions first
                contrib_deleted = test_contributions.count()
                test_contributions.delete()
                self.stdout.write(f'✓ Deleted {contrib_deleted} test contributions')

                # Delete expenditures
                exp_deleted = test_expenditures.count()
                test_expenditures.delete()
                self.stdout.write(f'✓ Deleted {exp_deleted} test expenditures')

                # Delete reports (this will cascade delete their contributions/expenditures)
                reports_deleted = test_reports.count()
                test_reports.delete()
                self.stdout.write(f'✓ Deleted {reports_deleted} test reports (and all related data)')

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✓ Test data deletion completed successfully!'))
