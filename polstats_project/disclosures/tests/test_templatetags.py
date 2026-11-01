"""Tests for template tags and filters."""
from decimal import Decimal
from django.test import TestCase
from django.template import Context, Template


class CurrencyFiltersTest(TestCase):
    """Test currency template filters."""

    def test_currency_filter(self):
        """Test currency filter formats correctly."""
        template = Template('{% load currency_filters %}{{ amount|currency }}')
        context = Context({'amount': Decimal('1234.56')})
        output = template.render(context)
        self.assertEqual(output, '$1,234.56')

    def test_currency_filter_zero(self):
        """Test currency filter with zero."""
        template = Template('{% load currency_filters %}{{ amount|currency }}')
        context = Context({'amount': Decimal('0.00')})
        output = template.render(context)
        self.assertEqual(output, '$0.00')

    def test_currency_filter_large_number(self):
        """Test currency filter with large number."""
        template = Template('{% load currency_filters %}{{ amount|currency }}')
        context = Context({'amount': Decimal('1234567.89')})
        output = template.render(context)
        self.assertEqual(output, '$1,234,567.89')

    def test_currency_filter_negative(self):
        """Test currency filter with negative number."""
        template = Template('{% load currency_filters %}{{ amount|currency }}')
        context = Context({'amount': Decimal('-1234.56')})
        output = template.render(context)
        self.assertEqual(output, '-$1,234.56')

    def test_currency_int_filter(self):
        """Test currency_int filter (no decimals)."""
        template = Template('{% load currency_filters %}{{ amount|currency_int }}')
        context = Context({'amount': Decimal('1234.56')})
        output = template.render(context)
        self.assertEqual(output, '$1,235')

    def test_currency_filter_none(self):
        """Test currency filter with None."""
        template = Template('{% load currency_filters %}{{ amount|currency }}')
        context = Context({'amount': None})
        output = template.render(context)
        self.assertEqual(output, '$0.00')

    def test_currency_filter_string_number(self):
        """Test currency filter with string number."""
        template = Template('{% load currency_filters %}{{ amount|currency }}')
        context = Context({'amount': '1234.56'})
        output = template.render(context)
        self.assertEqual(output, '$1,234.56')


class CompactCurrencyFiltersTest(TestCase):
    """Test the compact dollar filters used on the overview page."""

    def render(self, expression, **context):
        template = Template('{% load currency_filters %}{{ ' + expression + ' }}')
        return template.render(Context(context))

    def test_currency_short_millions(self):
        self.assertEqual(self.render('amount|currency_short', amount=Decimal('64512345')), '$64.5M')
        self.assertEqual(self.render('amount|currency_short:2', amount=Decimal('5281670')), '$5.28M')

    def test_currency_short_thousands_and_units(self):
        self.assertEqual(self.render('amount|currency_short', amount=450123), '$450K')
        self.assertEqual(self.render('amount|currency_short', amount=812), '$812')
        self.assertEqual(self.render('amount|currency_short', amount=None), '$0')

    def test_currency_short_auto_trims_axis_labels(self):
        self.assertEqual(self.render('amount|currency_short:"auto"', amount=1000000), '$1M')
        self.assertEqual(self.render('amount|currency_short:"auto"', amount=2500000), '$2.5M')
        self.assertEqual(self.render('amount|currency_short:"auto"', amount=0), '$0')

    def test_signed_currency_short(self):
        self.assertEqual(self.render('amount|signed_currency_short', amount=Decimal('1098565')), '+$1.1M')
        self.assertEqual(self.render('amount|signed_currency_short', amount=Decimal('-250000')), '−$250K')
