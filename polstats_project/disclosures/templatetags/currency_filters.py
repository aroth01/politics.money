"""Custom template filters for currency formatting."""
from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def currency(value):
    """
    Format a number as currency with commas and 2 decimal places.
    Example: 1234.56 -> $1,234.56
    """
    if value is None:
        return '$0.00'

    try:
        # Convert to Decimal for precise handling
        if isinstance(value, str):
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            value = Decimal(str(value))

        # Format with commas and 2 decimal places
        return '${:,.2f}'.format(value)
    except (ValueError, TypeError, InvalidOperation):
        return '$0.00'


@register.filter
def currency_int(value):
    """
    Format a number as currency with commas, no decimal places.
    Example: 1234.56 -> $1,235
    """
    if value is None:
        return '$0'

    try:
        # Convert to Decimal for precise handling
        if isinstance(value, str):
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            value = Decimal(str(value))

        # Round and format with commas, no decimal places
        return '${:,.0f}'.format(value)
    except (ValueError, TypeError, InvalidOperation):
        return '$0'


@register.filter
def city_state(address):
    """
    Extract city and state from a full address, censoring street address.
    Example: "123 Main St, Salt Lake City, UT 84101" -> "Salt Lake City, UT"
    """
    if not address:
        return 'N/A'

    import re

    # US state abbreviations
    states = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    ]

    # Try to find a state abbreviation in the address
    # Pattern: looks for state code optionally followed by zip code
    state_pattern = r'\b(' + '|'.join(states) + r')(?:\s+\d{5}(?:-\d{4})?)?\s*$'
    match = re.search(state_pattern, address, re.IGNORECASE)

    if not match:
        # No recognizable state found, return as-is or N/A
        return 'N/A'

    state = match.group(1).upper()

    # Get everything before the state match
    before_state = address[:match.start()].strip()

    # Split by comma to find city
    parts = [p.strip() for p in before_state.split(',')]

    if len(parts) >= 2:
        # Last part before state is likely the city
        city = parts[-1]
    elif len(parts) == 1:
        # Only one part - could be "Street Address City" format
        # Try to extract just the city by removing typical street patterns
        # Look for patterns like "123 Street Name" and remove them
        words = parts[0].split()

        # If it starts with a number or contains common street indicators,
        # try to find where the city name likely starts
        # This is a simple heuristic: take last 2-3 words as city name
        if len(words) > 3:
            city = ' '.join(words[-2:])  # Take last 2 words as city
        else:
            city = parts[0]
    else:
        city = 'Unknown'

    # Clean up city name - remove trailing/leading special chars
    city = re.sub(r'^[^a-zA-Z]+|[^a-zA-Z]+$', '', city).strip()

    if not city:
        return f"{state}"

    return f"{city}, {state}"
