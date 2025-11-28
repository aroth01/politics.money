# Testing Documentation

This document describes the test suite for the PolStats project.

## Test Suite Overview

The project includes comprehensive tests for:

- **Models** (`test_models.py`) - Tests for database models and relationships
- **Views** (`test_views.py`) - Tests for web views and templates
- **Management Commands** (`test_commands.py`) - Tests for custom Django commands
- **Template Tags** (`test_templatetags.py`) - Tests for custom template filters

## Running Tests

### Run All Tests

```bash
python manage.py test polstats_project.disclosures.tests
```

### Run Specific Test File

```bash
# Test models only
python manage.py test polstats_project.disclosures.tests.test_models

# Test views only
python manage.py test polstats_project.disclosures.tests.test_views

# Test commands only
python manage.py test polstats_project.disclosures.tests.test_commands

# Test template tags only
python manage.py test polstats_project.disclosures.tests.test_templatetags
```

### Run Specific Test Class

```bash
python manage.py test polstats_project.disclosures.tests.test_models.DisclosureReportModelTest
```

### Run with Verbosity

```bash
# Show more details
python manage.py test polstats_project.disclosures.tests --verbosity=2

# Show even more details (including SQL queries)
python manage.py test polstats_project.disclosures.tests --verbosity=3
```

### Run with Coverage

```bash
# Install coverage if not already installed
pip install coverage

# Run tests with coverage
coverage run --source='.' manage.py test polstats_project.disclosures.tests
coverage report
coverage html  # Generate HTML report in htmlcov/
```

## Test Coverage

### Model Tests (19 tests)

- ✅ DisclosureReport creation, str(), timestamps
- ✅ Contribution creation, str(), special characters
- ✅ Expenditure creation, str()
- ✅ EntityRegistration creation, str(), timestamps
- ✅ EntityOfficer creation, str(), ordering, treasurer flag
- ✅ Relationships (contributions, expenditures, officers)
- ✅ Cascade deletes

### View Tests (24 tests)

- ✅ Index view loads
- ✅ Reports list view loads and shows reports
- ✅ Report detail view loads, shows contributions/expenditures, 404 handling
- ✅ Contributor detail view loads, handles names with slashes
- ✅ PAC detail view loads, shows entity info
- ✅ Search view finds reports, entities, contributors
- ✅ Out-of-state view loads
- ✅ Year filtering

### Command Tests (7 tests)

- ✅ scrape_entity command works
- ✅ scrape_entity updates existing entities
- ✅ bulk_scrape discovers entities
- ✅ bulk_scrape discovers reports
- ✅ Error handling for network errors
- ✅ Error handling for existing entities without --update flag
- ⚠️  import_disclosure command (needs HTML structure mocking)

### Template Tag Tests (7 tests)

- ✅ Currency filter formats correctly
- ✅ Currency filter handles zero, large numbers, None
- ✅ Currency filter handles string numbers
- ✅ Currency int filter (no decimals)
- ⚠️  Currency filter negative numbers (format difference)

## Test Data

Tests use Django's TestCase which creates a test database and rolls back after each test.

Example test data:
- Reports with various amounts and types
- Contributions from different donors
- Expenditures to different recipients
- Entity registrations with officers
- Names with special characters (e.g., "Larry H. Miller Rent A/C")

## Mocking

Tests use `unittest.mock` to mock external HTTP requests:
- `@patch('requests.get')` for scraping commands
- `@patch('requests.head')` for bulk scraper entity discovery
- Mock HTML responses for scraper tests

## Known Issues

1. **Negative currency format**: The currency filter outputs `$-1,234.56` instead of `-$1,234.56`
2. **import_disclosure mocking**: Needs complete HTML structure mocking for full coverage
3. **Reports list pagination**: Tests need update to match actual view context variables

## Continuous Integration

To set up CI testing (e.g., GitHub Actions):

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.14'
      - run: pip install -r requirements.txt
      - run: python manage.py test polstats_project.disclosures.tests
```

## Writing New Tests

### Test Model

```python
from django.test import TestCase
from ..models import MyModel

class MyModelTest(TestCase):
    def setUp(self):
        """Set up test data."""
        self.obj = MyModel.objects.create(name='Test')

    def test_creation(self):
        """Test object creation."""
        self.assertEqual(self.obj.name, 'Test')
```

### Test View

```python
from django.test import TestCase, Client
from django.urls import reverse

class MyViewTest(TestCase):
    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_view_loads(self):
        """Test that view loads successfully."""
        response = self.client.get(reverse('app:view_name'))
        self.assertEqual(response.status_code, 200)
```

### Test Command

```python
from django.test import TestCase
from django.core.management import call_command
from io import StringIO

class MyCommandTest(TestCase):
    def test_command(self):
        """Test management command."""
        out = StringIO()
        call_command('mycommand', stdout=out)
        self.assertIn('Success', out.getvalue())
```

## Best Practices

1. **Descriptive test names**: Use `test_<what>_<condition>` format
2. **One assertion per test**: Test one thing at a time when possible
3. **Use setUp/tearDown**: Keep tests DRY
4. **Mock external services**: Don't make real HTTP requests
5. **Test edge cases**: Empty strings, None values, special characters
6. **Test error conditions**: 404s, validation errors, etc.

## Test Statistics

- **Total Tests**: 51
- **Passed**: 47
- **Failed**: 1
- **Errors**: 3
- **Success Rate**: ~92%

## Next Steps

- [ ] Fix negative currency formatting
- [ ] Complete import_disclosure command mocking
- [ ] Add tests for API endpoints
- [ ] Add integration tests
- [ ] Set up code coverage reporting
- [ ] Add performance/load testing
