"""Context processors for disclosures app."""
from django.db.models.functions import ExtractYear
from django.conf import settings
from .models import DisclosureReport


def year_filter(request):
    """Add year filter data to all templates."""
    # Get all available years from end_date field
    available_years = (
        DisclosureReport.objects
        .filter(end_date__isnull=False)
        .annotate(year=ExtractYear('end_date'))
        .values_list('year', flat=True)
        .distinct()
        .order_by('-year')
    )

    # Get selected year from query params
    selected_year = request.GET.get('year')
    if selected_year:
        try:
            selected_year = int(selected_year)
        except (ValueError, TypeError):
            selected_year = None

    # Get last updated timestamp (most recent report scraped)
    last_report = DisclosureReport.objects.order_by('-last_scraped_at').first()
    last_updated = last_report.last_scraped_at if last_report else None

    return {
        'available_years': list(available_years),
        'selected_year': selected_year,
        'last_updated': last_updated,
        'site_title': settings.SITE_TITLE,
    }
