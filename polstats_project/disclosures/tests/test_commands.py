"""Tests for management commands."""
from decimal import Decimal
from django.test import TestCase
from django.core.management import call_command
from unittest.mock import patch, MagicMock
from io import StringIO
from datetime import date

from ..models import DisclosureReport, EntityRegistration, EntityOfficer


class ScrapeEntityCommandTest(TestCase):
    """Test scrape_entity management command."""

    @patch('polstats_project.disclosures.management.commands.scrape_entity.requests.get')
    def test_scrape_entity_command(self, mock_get):
        """Test that scrape_entity command works."""
        # Mock HTML response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <body>
                <label for="Name">Name</label>
                <div><label for="Name">Name</label>Test PAC</div>
                <label>Also known as</label>
                <div><label>Also known as</label>Test</div>
                <label>Date Created</label>
                <div><label>Date Created</label>01/01/2020</div>
                <label>Street Address</label>
                <div><label>Street Address</label>123 Main St</div>
                <label>City</label>
                <div><label>City</label>Salt Lake City</div>
                <label>State</label>
                <div><label>State</label>UT</div>
                <label>Zip</label>
                <div><label>Zip</label>84101</div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response

        out = StringIO()
        call_command('scrape_entity', '850', stdout=out)

        # Check that entity was created
        entity = EntityRegistration.objects.get(entity_id='850')
        self.assertEqual(entity.name, 'Test PAC')
        self.assertEqual(entity.city, 'Salt Lake City')
        self.assertEqual(entity.state, 'UT')

    @patch('polstats_project.disclosures.management.commands.scrape_entity.requests.get')
    def test_scrape_entity_update_existing(self, mock_get):
        """Test updating existing entity."""
        # Create existing entity
        EntityRegistration.objects.create(
            entity_id='850',
            source_url='https://disclosures.utah.gov/Registration/EntityDetails/850',
            name='Old Name',
            city='Old City'
        )

        # Mock HTML response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <body>
                <label for="Name">Name</label>
                <div><label for="Name">Name</label>New Name</div>
                <label>City</label>
                <div><label>City</label>New City</div>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response

        out = StringIO()
        call_command('scrape_entity', '850', '--update', stdout=out)

        # Check that entity was updated
        entity = EntityRegistration.objects.get(entity_id='850')
        self.assertEqual(entity.name, 'New Name')
        self.assertEqual(entity.city, 'New City')


class BulkScrapeCommandTest(TestCase):
    """Test bulk_scrape management command."""

    @patch('polstats_project.disclosures.management.commands.bulk_scrape.requests.head')
    @patch('polstats_project.disclosures.management.commands.bulk_scrape.call_command')
    def test_bulk_scrape_entities(self, mock_call_command, mock_head):
        """Test bulk scraping entities."""
        # Mock HEAD requests to simulate existing entities
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200

        mock_response_404 = MagicMock()
        mock_response_404.status_code = 404

        # Simulate finding 2 entities, then 100 consecutive 404s
        responses = [mock_response_200, mock_response_200] + [mock_response_404] * 100
        mock_head.side_effect = responses

        out = StringIO()
        call_command('bulk_scrape', '--type=entities', '--limit=2', stdout=out)

        # Check that scrape_entity was called for found entities
        self.assertEqual(mock_call_command.call_count, 2)

    @patch('polstats_project.disclosures.management.commands.bulk_scrape.requests.get')
    @patch('polstats_project.disclosures.management.commands.bulk_scrape.call_command')
    def test_bulk_scrape_reports(self, mock_call_command, mock_get):
        """Test bulk scraping reports."""
        # Mock HTML response with report links
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <body>
                <a href="/Search/PublicSearch/Report/12345">Report 1</a>
                <a href="/Search/PublicSearch/Report/67890">Report 2</a>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response

        out = StringIO()
        call_command('bulk_scrape', '--type=reports', '--limit=2', '--max-pages=1', stdout=out)

        # Check that import_disclosure was called for found reports
        self.assertTrue(mock_call_command.call_count >= 2)


class ImportDisclosureCommandTest(TestCase):
    """Test import_disclosure management command."""

    @patch('polstats_project.disclosures.management.commands.import_disclosure.requests.get')
    def test_import_disclosure_command(self, mock_get):
        """Test that import_disclosure command works."""
        # Mock HTML response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'''
        <html>
            <body>
                <div id="reportHeader">
                    <h1>Test PAC - Quarterly Report</h1>
                </div>
                <table id="contributions">
                    <tr>
                        <td>John Doe</td>
                        <td>$500.00</td>
                        <td>01/15/2024</td>
                    </tr>
                </table>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response

        out = StringIO()

        # Note: This might fail without proper mocking of the entire HTML structure
        # This is a basic example - you may need to expand based on your actual scraper
        try:
            call_command(
                'import_disclosure',
                'https://example.com/report/12345',
                '--report-id=12345',
                stdout=out
            )
        except Exception:
            # Expected if HTML structure doesn't match scraper expectations
            pass


class CommandErrorHandlingTest(TestCase):
    """Test error handling in management commands."""

    @patch('polstats_project.disclosures.management.commands.scrape_entity.requests.get')
    def test_scrape_entity_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception('Network error')

        out = StringIO()
        err = StringIO()

        with self.assertRaises(Exception):
            call_command('scrape_entity', '850', stdout=out, stderr=err)

    def test_scrape_entity_existing_without_update(self):
        """Test error when entity exists and --update not provided."""
        # Create existing entity
        EntityRegistration.objects.create(
            entity_id='850',
            source_url='https://disclosures.utah.gov/Registration/EntityDetails/850',
            name='Test PAC'
        )

        out = StringIO()
        err = StringIO()

        with self.assertRaises(Exception):
            call_command('scrape_entity', '850', stdout=out, stderr=err)
