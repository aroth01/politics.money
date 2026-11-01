"""Tests for disclosure views."""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from datetime import date

from ..models import (
    DisclosureReport,
    Contribution,
    Expenditure,
    EntityRegistration,
    EntityOfficer
)


class IndexViewTest(TestCase):
    """Test index view."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_index_view_loads(self):
        """Test that index view loads successfully."""
        response = self.client.get(reverse('disclosures:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disclosures/index.html')

    def test_index_view_empty_database(self):
        """Overview renders with zeroed figures when nothing is imported."""
        response = self.client.get(reverse('disclosures:index'))
        self.assertEqual(response.context['stats']['total_filers'], 0)
        self.assertEqual(response.context['fundraisers']['rows'], [])
        self.assertEqual(response.context['in_state_cents'], 0)
        self.assertContains(response, 'No reports on file yet')


class OverviewFiguresTest(TestCase):
    """Test the aggregates behind the overview page."""

    def setUp(self):
        self.client = Client()
        self.candidate = DisclosureReport.objects.create(
            report_id='CAND-1',
            source_url='https://example.com/report/1',
            organization_name='Jane Candidate',
            organization_type='Candidates & Office Holders',
            total_contributions=Decimal('30000.00'),
            total_expenditures=Decimal('40000.00'),
            end_date=date(2024, 6, 30),
        )
        self.pac = DisclosureReport.objects.create(
            report_id='PAC-1',
            source_url='https://example.com/report/2',
            organization_name='Good Government PAC',
            organization_type='Political Action Committee',
            total_contributions=Decimal('10000.00'),
            total_expenditures=Decimal('5000.00'),
            end_date=date(2023, 12, 31),
        )
        gifts = [
            ('Small Donor', '10 Main St, Provo, UT 84601', '25.00', date(2024, 1, 5)),
            ('Mid Donor', '20 Main St, Ogden, UT 84401', '100.00', date(2024, 2, 5)),
            ('Large Donor', '30 Market St, San Francisco, CA 94105', '10000.00', date(2024, 3, 5)),
            ('Mystery Donor', '', '500.00', date(2024, 3, 9)),
        ]
        for name, address, amount, received in gifts:
            Contribution.objects.create(
                report=self.candidate,
                contributor_name=name,
                address=address,
                amount=Decimal(amount),
                date_received=received,
            )
        Contribution.objects.create(
            report=self.pac,
            contributor_name='Capital Donor',
            address='1 K St NW, Washington, DC 20001',
            amount=Decimal('2000.00'),
            date_received=date(2023, 11, 1),
        )
        Expenditure.objects.create(
            report=self.candidate,
            recipient_name='Print Shop',
            amount=Decimal('750.00'),
            date=date(2024, 3, 20),
        )

    def test_key_figures(self):
        response = self.client.get(reverse('disclosures:index'))
        stats = response.context['stats']
        self.assertEqual(stats['total_reports'], 2)
        self.assertEqual(stats['total_filers'], 2)
        self.assertEqual(stats['total_contributions'], 5)
        self.assertEqual(stats['total_contribution_amount'], Decimal('12625.00'))
        self.assertEqual(stats['total_expenditures'], 1)
        self.assertEqual(stats['total_expenditure_amount'], Decimal('750.00'))

    def test_gift_size_bands(self):
        response = self.client.get(reverse('disclosures:index'))
        bands = response.context['gift_bands']
        self.assertEqual([b['count'] for b in bands], [1, 1, 1, 1, 1])
        self.assertEqual(bands[0]['count_pct'], 20.0)
        self.assertEqual(bands[-1]['dollar_pct'], 79.2)
        self.assertEqual(response.context['large_gift_count'], 1)
        self.assertEqual(response.context['small_gift_share'], 20.0)
        self.assertContains(response, 'Where Utah')

    def test_top_fundraisers(self):
        response = self.client.get(reverse('disclosures:index'))
        fundraisers = response.context['fundraisers']
        self.assertEqual([r['name'] for r in fundraisers['rows']], ['Jane Candidate', 'Good Government PAC'])
        top = fundraisers['rows'][0]
        self.assertEqual(top['detail_url_name'], 'disclosures:candidate_detail')
        self.assertEqual(top['spent_pct'], 80.0)
        self.assertEqual(fundraisers['rows'][1]['detail_url_name'], 'disclosures:pac_detail')
        self.assertEqual(fundraisers['biggest_overspend']['name'], 'Jane Candidate')
        self.assertEqual(fundraisers['ticks'][-1]['value'], 50000.0)
        self.assertContains(response, reverse('disclosures:candidate_detail', args=['Jane Candidate']))

    def test_geography(self):
        response = self.client.get(reverse('disclosures:index'))
        tiles = {t['code']: t for t in response.context['tiles']}
        self.assertEqual(tiles['UT']['value'], Decimal('125.00'))
        self.assertEqual(tiles['CA']['value'], Decimal('10000.00'))
        self.assertEqual(tiles['DC']['value'], Decimal('2000.00'))
        self.assertEqual(tiles['NY']['value'], Decimal('0'))
        self.assertEqual(response.context['top_state_code'], 'CA')
        self.assertEqual(response.context['in_state_cents'], 1)
        self.assertEqual(response.context['out_of_state_total'], Decimal('12000.00'))
        self.assertEqual(response.context['other_state_count'], 1)
        self.assertTrue(response.context['has_dc'])
        self.assertEqual(response.context['unreadable_share'], 4)

    def test_year_filter_applies_to_overview(self):
        response = self.client.get(reverse('disclosures:index'), {'year': '2023'})
        self.assertEqual(response.context['stats']['total_reports'], 1)
        self.assertEqual(response.context['stats']['total_contribution_amount'], Decimal('2000.00'))
        self.assertEqual([r['name'] for r in response.context['fundraisers']['rows']], ['Good Government PAC'])
        self.assertEqual(response.context['top_state_code'], 'DC')

    def test_global_timeline_respects_year(self):
        all_years = self.client.get(reverse('disclosures:api_global_timeline')).json()
        self.assertEqual(len(all_years['contributions']), 4)
        self.assertEqual(all_years['contributions'][0]['date'], '2023-11-01')
        one_year = self.client.get(reverse('disclosures:api_global_timeline'), {'year': '2024'}).json()
        self.assertEqual([m['date'] for m in one_year['contributions']], ['2024-01-01', '2024-02-01', '2024-03-01'])
        self.assertEqual(one_year['contributions'][2]['amount'], 10500.0)
        self.assertEqual(one_year['contributions'][2]['count'], 2)
        self.assertEqual(len(one_year['expenditures']), 1)


class ReportsListViewTest(TestCase):
    """Test reports list view."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()

        # Create test reports
        for i in range(5):
            DisclosureReport.objects.create(
                report_id=f'REPORT{i}',
                source_url=f'https://example.com/report/{i}',
                organization_name=f'Test PAC {i}',
                organization_type='Political Action Committee',
                total_contributions=Decimal('1000.00') * (i + 1),
                total_expenditures=Decimal('500.00') * (i + 1)
            )

    def test_reports_list_view_loads(self):
        """Test that reports list view loads successfully."""
        response = self.client.get(reverse('disclosures:reports_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disclosures/reports_list.html')

    def test_reports_list_shows_reports(self):
        """Test that reports are displayed."""
        response = self.client.get(reverse('disclosures:reports_list'))
        self.assertEqual(len(response.context['reports']), 5)


class ReportDetailViewTest(TestCase):
    """Test report detail view."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()

        self.report = DisclosureReport.objects.create(
            report_id='12345',
            source_url='https://example.com/report/12345',
            organization_name='Test PAC',
            organization_type='Political Action Committee',
            total_contributions=Decimal('10000.00'),
            total_expenditures=Decimal('5000.00')
        )

        # Add contributions
        Contribution.objects.create(
            report=self.report,
            contributor_name='John Doe',
            amount=Decimal('500.00'),
            date_received=date(2024, 1, 15)
        )

        # Add expenditures
        Expenditure.objects.create(
            report=self.report,
            recipient_name='ABC Consulting',
            amount=Decimal('250.00'),
            date=date(2024, 1, 20)
        )

    def test_report_detail_view_loads(self):
        """Test that report detail view loads successfully."""
        response = self.client.get(
            reverse('disclosures:report_detail', args=['12345'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disclosures/report_detail.html')

    def test_report_detail_shows_contributions(self):
        """Test that contributions are displayed."""
        response = self.client.get(
            reverse('disclosures:report_detail', args=['12345'])
        )
        self.assertContains(response, 'John Doe')
        self.assertContains(response, '$500.00')

    def test_report_detail_shows_expenditures(self):
        """Test that expenditures are displayed."""
        response = self.client.get(
            reverse('disclosures:report_detail', args=['12345'])
        )
        self.assertContains(response, 'ABC Consulting')
        self.assertContains(response, '$250.00')

    def test_report_not_found(self):
        """Test 404 for non-existent report."""
        response = self.client.get(
            reverse('disclosures:report_detail', args=['99999'])
        )
        self.assertEqual(response.status_code, 404)


class ContributorDetailViewTest(TestCase):
    """Test contributor detail view."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()

        self.report = DisclosureReport.objects.create(
            report_id='12345',
            source_url='https://example.com/report/12345',
            organization_name='Test PAC',
            organization_type='Political Action Committee'
        )

        # Add contributions from same contributor
        Contribution.objects.create(
            report=self.report,
            contributor_name='John Doe',
            amount=Decimal('500.00'),
            date_received=date(2024, 1, 15)
        )
        Contribution.objects.create(
            report=self.report,
            contributor_name='John Doe',
            amount=Decimal('300.00'),
            date_received=date(2024, 2, 15)
        )

    def test_contributor_detail_view_loads(self):
        """Test that contributor detail view loads successfully."""
        response = self.client.get(
            reverse('disclosures:contributor_detail', args=['John Doe'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disclosures/contributor_detail.html')

    def test_contributor_with_slash_in_name(self):
        """Test contributor with forward slash in name."""
        Contribution.objects.create(
            report=self.report,
            contributor_name='Larry H. Miller Rent A/C',
            amount=Decimal('1000.00'),
            date_received=date(2024, 1, 15)
        )

        response = self.client.get(
            reverse('disclosures:contributor_detail', args=['Larry H. Miller Rent A/C'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Larry H. Miller Rent A/C')


class PACDetailViewTest(TestCase):
    """Test PAC detail view."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()

        # Create reports for the same PAC
        for i in range(3):
            report = DisclosureReport.objects.create(
                report_id=f'REPORT{i}',
                source_url=f'https://example.com/report/{i}',
                organization_name='Test PAC',
                organization_type='Political Action Committee',
                total_contributions=Decimal('1000.00'),
                total_expenditures=Decimal('500.00')
            )

            Contribution.objects.create(
                report=report,
                contributor_name=f'Donor {i}',
                amount=Decimal('100.00')
            )

        # Create entity registration
        self.entity = EntityRegistration.objects.create(
            entity_id='850',
            source_url='https://disclosures.utah.gov/Registration/EntityDetails/850',
            name='Test PAC',
            city='Salt Lake City',
            state='UT'
        )

        EntityOfficer.objects.create(
            entity=self.entity,
            name='Test Officer',
            title='Chair',
            order=0
        )

    def test_pac_detail_view_loads(self):
        """Test that PAC detail view loads successfully."""
        response = self.client.get(
            reverse('disclosures:pac_detail', args=['Test PAC'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disclosures/pac_detail.html')

    def test_pac_detail_shows_entity_info(self):
        """Test that entity registration info is displayed."""
        response = self.client.get(
            reverse('disclosures:pac_detail', args=['Test PAC'])
        )
        self.assertContains(response, 'Organization Details')
        self.assertContains(response, '850')
        self.assertContains(response, 'Test Officer')


class SearchViewTest(TestCase):
    """Test global search view."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()

        self.report = DisclosureReport.objects.create(
            report_id='12345',
            source_url='https://example.com/report/12345',
            organization_name='Utah Test PAC',
            organization_type='Political Action Committee'
        )

        self.entity = EntityRegistration.objects.create(
            entity_id='850',
            source_url='https://disclosures.utah.gov/Registration/EntityDetails/850',
            name='Utah Association Of Realtors'
        )

        Contribution.objects.create(
            report=self.report,
            contributor_name='John Smith',
            amount=Decimal('500.00')
        )

    def test_search_view_loads(self):
        """Test that search view loads successfully."""
        response = self.client.get(reverse('disclosures:search'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disclosures/search.html')

    def test_search_finds_reports(self):
        """Test that search finds reports."""
        response = self.client.get(
            reverse('disclosures:search'),
            {'q': 'Utah Test'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.report, response.context['reports'])

    def test_search_finds_entities(self):
        """Test that search finds entities."""
        response = self.client.get(
            reverse('disclosures:search'),
            {'q': 'Realtors'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.entity, response.context['entities'])

    def test_search_finds_contributors(self):
        """Test that search finds contributors."""
        response = self.client.get(
            reverse('disclosures:search'),
            {'q': 'John Smith'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['contributors']) > 0)

    def test_empty_search(self):
        """Test search with no query."""
        response = self.client.get(reverse('disclosures:search'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_results'], 0)


class OutOfStateViewTest(TestCase):
    """Test out-of-state contributions view."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()

        self.report = DisclosureReport.objects.create(
            report_id='12345',
            source_url='https://example.com/report/12345',
            organization_name='Test PAC',
            organization_type='Political Action Committee'
        )

        # Add out-of-state contributions
        Contribution.objects.create(
            report=self.report,
            contributor_name='California Donor',
            address='123 Main St, Los Angeles, CA 90001',
            amount=Decimal('1000.00')
        )

        # Add in-state contribution
        Contribution.objects.create(
            report=self.report,
            contributor_name='Utah Donor',
            address='456 State St, Salt Lake City, UT 84101',
            amount=Decimal('500.00')
        )

    def test_out_of_state_view_loads(self):
        """Test that out-of-state view loads successfully."""
        response = self.client.get(reverse('disclosures:out_of_state'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disclosures/out_of_state.html')


class YearFilteringTest(TestCase):
    """Test year filtering functionality."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()

        # Create reports from different years
        DisclosureReport.objects.create(
            report_id='2023-REPORT',
            source_url='https://example.com/report/2023',
            organization_name='Test PAC',
            organization_type='Political Action Committee',
            end_date=date(2023, 12, 31)
        )

        DisclosureReport.objects.create(
            report_id='2024-REPORT',
            source_url='https://example.com/report/2024',
            organization_name='Test PAC',
            organization_type='Political Action Committee',
            end_date=date(2024, 12, 31)
        )

    def test_year_filter_on_reports_list(self):
        """Test year filtering on reports list."""
        response = self.client.get(
            reverse('disclosures:reports_list'),
            {'year': '2024'}
        )
        self.assertEqual(response.status_code, 200)
        # Should only show 2024 report
        reports = response.context['reports']
        self.assertTrue(all(
            report.end_date and report.end_date.year == 2024
            for report in reports
            if report.end_date
        ))
