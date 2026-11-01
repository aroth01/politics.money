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


@register.filter
def currency_short(value, decimals=1):
    """
    Format a number as a compact dollar figure for headlines and axes.
    Example: 64512345 -> $64.5M, 450123 -> $450K, 812 -> $812
    Pass "auto" as the argument to trim trailing zeros for axis labels:
    1000000 -> $1M, 2500000 -> $2.5M
    """
    trim = decimals == 'auto'
    try:
        number = float(value or 0)
        decimals = 2 if trim else int(decimals)
    except (ValueError, TypeError):
        return '$0'

    sign = '-' if number < 0 else ''
    number = abs(number)
    if number >= 1_000_000:
        text = f'{number / 1_000_000:,.{decimals}f}'
        if trim and '.' in text:
            text = text.rstrip('0').rstrip('.')
        return f'{sign}${text}M'
    if number >= 1_000:
        return f'{sign}${number / 1_000:,.0f}K'
    return f'{sign}${number:,.0f}'


@register.filter
def signed_currency_short(value):
    """Compact dollar figure with an explicit sign, for differences: +$1.1M, −$250K."""
    try:
        number = float(value or 0)
    except (ValueError, TypeError):
        return '$0'
    text = currency_short(abs(number))
    if number < 0:
        return '−' + text
    return '+' + text
