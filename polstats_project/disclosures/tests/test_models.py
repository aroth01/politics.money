"""Tests for disclosure models."""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta

from ..models import (
    DisclosureReport,
    Contribution,
    Expenditure,
    EntityRegistration,
    EntityOfficer
)


class DisclosureReportModelTest(TestCase):
    """Test DisclosureReport model."""

    def setUp(self):
        """Set up test data."""
        self.report = DisclosureReport.objects.create(
            report_id='12345',
            source_url='https://example.com/report/12345',
            organization_name='Test PAC',
            organization_type='Political Action Committee',
            title='Test Report',
            report_type='Quarterly',
            begin_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            total_contributions=Decimal('10000.00'),
            total_expenditures=Decimal('5000.00'),
            ending_balance=Decimal('5000.00')
        )

    def test_report_creation(self):
        """Test that a report can be created."""
        self.assertEqual(self.report.report_id, '12345')
        self.assertEqual(self.report.organization_name, 'Test PAC')
        self.assertEqual(self.report.total_contributions, Decimal('10000.00'))

    def test_report_str(self):
        """Test string representation."""
        expected = 'Report 12345 - Test PAC'
        self.assertEqual(str(self.report), expected)

    def test_report_timestamps(self):
        """Test that timestamps are set."""
        self.assertIsNotNone(self.report.created_at)
        self.assertIsNotNone(self.report.updated_at)


class ContributionModelTest(TestCase):
    """Test Contribution model."""

    def setUp(self):
        """Set up test data."""
        self.report = DisclosureReport.objects.create(
            report_id='12345',
            source_url='https://example.com/report/12345',
            organization_name='Test PAC',
            organization_type='Political Action Committee'
        )

        self.contribution = Contribution.objects.create(
            report=self.report,
            contributor_name='John Doe',
            address='123 Main St, Salt Lake City, UT 84101',
            amount=Decimal('500.00'),
            date_received=date(2024, 2, 15)
        )

    def test_contribution_creation(self):
        """Test that a contribution can be created."""
        self.assertEqual(self.contribution.contributor_name, 'John Doe')
        self.assertEqual(self.contribution.amount, Decimal('500.00'))
        self.assertEqual(self.contribution.report, self.report)

    def test_contribution_str(self):
        """Test string representation."""
        expected = 'John Doe - $500.00 on 2024-02-15'
        self.assertEqual(str(self.contribution), expected)

    def test_contribution_with_special_characters(self):
        """Test contribution with special characters in name."""
        contrib = Contribution.objects.create(
            report=self.report,
            contributor_name='Larry H. Miller Rent A/C',
            amount=Decimal('1000.00'),
            date_received=date(2024, 2, 15)
        )
        self.assertEqual(contrib.contributor_name, 'Larry H. Miller Rent A/C')


class ExpenditureModelTest(TestCase):
    """Test Expenditure model."""

    def setUp(self):
        """Set up test data."""
        self.report = DisclosureReport.objects.create(
            report_id='12345',
            source_url='https://example.com/report/12345',
            organization_name='Test PAC',
            organization_type='Political Action Committee'
        )

        self.expenditure = Expenditure.objects.create(
            report=self.report,
            recipient_name='ABC Consulting',
            purpose='Campaign consulting',
            amount=Decimal('2500.00'),
            date=date(2024, 3, 10)
        )

    def test_expenditure_creation(self):
        """Test that an expenditure can be created."""
        self.assertEqual(self.expenditure.recipient_name, 'ABC Consulting')
        self.assertEqual(self.expenditure.amount, Decimal('2500.00'))
        self.assertEqual(self.expenditure.purpose, 'Campaign consulting')

    def test_expenditure_str(self):
        """Test string representation."""
        expected = 'ABC Consulting - $2500.00 on 2024-03-10'
        self.assertEqual(str(self.expenditure), expected)


class EntityRegistrationModelTest(TestCase):
    """Test EntityRegistration model."""

    def setUp(self):
        """Set up test data."""
        self.entity = EntityRegistration.objects.create(
            entity_id='850',
            source_url='https://disclosures.utah.gov/Registration/EntityDetails/850',
            name='Utah Association Of Realtors',
            also_known_as='RPAC',
            date_created=date(2008, 12, 22),
            street_address='230 West Towne Ridge Pkwy',
            suite_po_box='Ste. 500',
            city='Sandy',
            state='UT',
            zip_code='84070'
        )

    def test_entity_creation(self):
        """Test that an entity can be created."""
        self.assertEqual(self.entity.entity_id, '850')
        self.assertEqual(self.entity.name, 'Utah Association Of Realtors')
        self.assertEqual(self.entity.city, 'Sandy')

    def test_entity_str(self):
        """Test string representation."""
        expected = 'Utah Association Of Realtors (ID: 850)'
        self.assertEqual(str(self.entity), expected)

    def test_entity_timestamps(self):
        """Test that timestamps are set."""
        self.assertIsNotNone(self.entity.created_at)
        self.assertIsNotNone(self.entity.updated_at)


class EntityOfficerModelTest(TestCase):
    """Test EntityOfficer model."""

    def setUp(self):
        """Set up test data."""
        self.entity = EntityRegistration.objects.create(
            entity_id='850',
            source_url='https://disclosures.utah.gov/Registration/EntityDetails/850',
            name='Test PAC'
        )

        self.officer = EntityOfficer.objects.create(
            entity=self.entity,
            name='Lerron Little',
            title='Chair',
            phone='(801) 437-4555',
            email='test@example.com',
            is_treasurer=False,
            order=0
        )

    def test_officer_creation(self):
        """Test that an officer can be created."""
        self.assertEqual(self.officer.name, 'Lerron Little')
        self.assertEqual(self.officer.title, 'Chair')
        self.assertEqual(self.officer.entity, self.entity)

    def test_officer_str(self):
        """Test string representation."""
        expected = 'Lerron Little - Chair (Test PAC)'
        self.assertEqual(str(self.officer), expected)

    def test_officer_ordering(self):
        """Test that officers are ordered correctly."""
        officer2 = EntityOfficer.objects.create(
            entity=self.entity,
            name='Jacob Jaggi',
            title='Accountant',
            is_treasurer=True,
            order=1
        )

        officers = EntityOfficer.objects.filter(entity=self.entity)
        self.assertEqual(officers[0], self.officer)
        self.assertEqual(officers[1], officer2)

    def test_treasurer_flag(self):
        """Test treasurer flag."""
        treasurer = EntityOfficer.objects.create(
            entity=self.entity,
            name='Test Treasurer',
            title='Treasurer',
            is_treasurer=True,
            order=2
        )
        self.assertTrue(treasurer.is_treasurer)
        self.assertFalse(self.officer.is_treasurer)


class ModelRelationshipsTest(TestCase):
    """Test model relationships."""

    def setUp(self):
        """Set up test data."""
        self.report = DisclosureReport.objects.create(
            report_id='12345',
            source_url='https://example.com/report/12345',
            organization_name='Test PAC',
            organization_type='Political Action Committee'
        )

        self.entity = EntityRegistration.objects.create(
            entity_id='850',
            source_url='https://disclosures.utah.gov/Registration/EntityDetails/850',
            name='Test PAC'
        )

    def test_report_contributions_relationship(self):
        """Test that contributions are linked to reports."""
        contrib1 = Contribution.objects.create(
            report=self.report,
            contributor_name='Donor 1',
            amount=Decimal('100.00')
        )
        contrib2 = Contribution.objects.create(
            report=self.report,
            contributor_name='Donor 2',
            amount=Decimal('200.00')
        )

        self.assertEqual(self.report.contributions.count(), 2)
        self.assertIn(contrib1, self.report.contributions.all())
        self.assertIn(contrib2, self.report.contributions.all())

    def test_report_expenditures_relationship(self):
        """Test that expenditures are linked to reports."""
        exp1 = Expenditure.objects.create(
            report=self.report,
            recipient_name='Vendor 1',
            amount=Decimal('150.00')
        )
        exp2 = Expenditure.objects.create(
            report=self.report,
            recipient_name='Vendor 2',
            amount=Decimal('250.00')
        )

        self.assertEqual(self.report.expenditures.count(), 2)
        self.assertIn(exp1, self.report.expenditures.all())
        self.assertIn(exp2, self.report.expenditures.all())

    def test_entity_officers_relationship(self):
        """Test that officers are linked to entities."""
        officer1 = EntityOfficer.objects.create(
            entity=self.entity,
            name='Officer 1',
            title='Chair',
            order=0
        )
        officer2 = EntityOfficer.objects.create(
            entity=self.entity,
            name='Officer 2',
            title='Vice Chair',
            order=1
        )

        self.assertEqual(self.entity.officers.count(), 2)
        self.assertIn(officer1, self.entity.officers.all())
        self.assertIn(officer2, self.entity.officers.all())

    def test_cascade_delete(self):
        """Test that related objects are deleted on cascade."""
        contrib = Contribution.objects.create(
            report=self.report,
            contributor_name='Test Donor',
            amount=Decimal('100.00')
        )

        self.report.delete()
        self.assertEqual(Contribution.objects.filter(id=contrib.id).count(), 0)
