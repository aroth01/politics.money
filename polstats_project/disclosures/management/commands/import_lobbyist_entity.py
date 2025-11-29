import sys
import os
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import datetime

# Add the parent directory to the path to import our parser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../'))

from lobbyist_entity_parser import parse_lobbyist_entity
from ...models import LobbyistRegistration, LobbyistPrincipal


class Command(BaseCommand):
    help = 'Import Utah lobbyist entity registration from a URL'

    def add_arguments(self, parser):
        parser.add_argument(
            'url',
            type=str,
            help='URL of the Utah lobbyist entity to import (e.g., https://lobbyist.utah.gov/Registration/EntityDetails/1410867)'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing entity if it already exists'
        )
        parser.add_argument(
            '--entity-id',
            type=str,
            help='Override entity ID (defaults to extracting from URL)'
        )

    def parse_date(self, date_str):
        """Parse date string in M/D/YYYY format."""
        if not date_str or date_str.strip() == '' or date_str == '--':
            return None

        date_str = date_str.strip()
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

    def extract_entity_id(self, url):
        """Extract entity ID from URL."""
        # URL format: https://lobbyist.utah.gov/Registration/EntityDetails/1410867
        parts = url.rstrip('/').split('/')
        if parts and parts[-1].isdigit():
            return parts[-1]
        return None

    def handle(self, *args, **options):
        url = options['url']
        update = options['update']
        entity_id = options.get('entity_id') or self.extract_entity_id(url)

        if not entity_id:
            raise CommandError('Could not extract entity ID from URL. Please provide --entity-id')

        self.stdout.write(f'Fetching lobbyist entity from: {url}')
        self.stdout.write(f'Entity ID: {entity_id}')

        # Check if entity already exists
        existing_entity = LobbyistRegistration.objects.filter(entity_id=entity_id).first()
        if existing_entity and not update:
            raise CommandError(
                f'Entity {entity_id} already exists. Use --update to overwrite.'
            )

        # Fetch and parse data
        try:
            entity_data = parse_lobbyist_entity(url)
        except Exception as e:
            raise CommandError(f'Error parsing lobbyist entity: {str(e)}')

        self.stdout.write(self.style.SUCCESS('Data fetched successfully'))

        # Import data in a transaction
        with transaction.atomic():
            # Create or update the entity
            if existing_entity and update:
                self.stdout.write(f'Updating existing entity {entity_id}...')
                entity = existing_entity
                # Delete existing principals
                entity.principals.all().delete()
            else:
                self.stdout.write(f'Creating new entity {entity_id}...')
                entity = LobbyistRegistration(entity_id=entity_id)

            # Set entity fields
            entity.source_url = entity_data.get('source_url', '')
            entity.name = entity_data.get('name', '')
            entity.first_name = entity_data.get('first_name', '')
            entity.last_name = entity_data.get('last_name', '')
            entity.phone = entity_data.get('phone', '')
            entity.registration_date = self.parse_date(entity_data.get('date_created'))

            # Organization info
            entity.organization_name = entity_data.get('organization_name', '')
            entity.organization_phone = entity_data.get('organization_phone', '')
            entity.street_address = entity_data.get('street_address', '')
            entity.city = entity_data.get('city', '')
            entity.state = entity_data.get('state', '')
            entity.zip_code = entity_data.get('zip_code', '')

            # Principal/client info
            entity.principal_name = entity_data.get('principal_name', '')
            entity.principal_phone = entity_data.get('principal_phone', '')
            entity.principal_address = entity_data.get('principal_address', '')
            entity.lobbying_purposes = entity_data.get('lobbying_purposes', '')

            entity.raw_data = entity_data.get('raw_data', {})
            entity.last_scraped_at = timezone.now()
            entity.save()

            # Import principals
            principals = entity_data.get('principals', [])
            if principals:
                self.stdout.write(f'Importing {len(principals)} principals...')
                for idx, principal_data in enumerate(principals):
                    principal = LobbyistPrincipal(
                        lobbyist=entity,
                        name=principal_data.get('name', ''),
                        contact=principal_data.get('contact', ''),
                        phone=principal_data.get('phone', ''),
                        address=principal_data.get('address', ''),
                        order=idx
                    )
                    principal.save()

        # Print summary
        self.stdout.write(self.style.SUCCESS('\n✓ Import completed successfully!'))
        self.stdout.write(f'\nEntity: {entity.name}')
        self.stdout.write(f'  ID: {entity.entity_id}')
        self.stdout.write(f'  Registration Date: {entity.registration_date}')
        if entity.organization_name:
            self.stdout.write(f'  Organization: {entity.organization_name}')
        if entity.street_address or entity.city:
            self.stdout.write(f'  Address: {entity.street_address}, {entity.city}, {entity.state} {entity.zip_code}')
        if principals:
            self.stdout.write(f'  Principals: {len(principals)}')
            for principal in entity.principals.all():
                self.stdout.write(f'    - {principal.name}')
