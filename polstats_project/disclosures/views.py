from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import models
from django.db.models import Sum, Count, Q, Min, Max
from django.db.models.functions import TruncMonth, TruncDay, ExtractYear
from django.core.paginator import Paginator
from django_ratelimit.decorators import ratelimit
from .models import DisclosureReport, Contribution, Expenditure
from decimal import Decimal
from urllib.parse import unquote
import math
import re


# US state and district codes, used to read a state from a contributor address.
STATE_CODES = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
]

STATE_NAMES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois',
    'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana',
    'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
    'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon',
    'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
    'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia',
    'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
}

# Tile map layout for the overview page: (state code, row, column), zero-based.
STATE_TILES = [
    ('AK', 0, 0), ('ME', 0, 10), ('WI', 1, 5), ('VT', 1, 9), ('NH', 1, 10),
    ('WA', 2, 0), ('ID', 2, 1), ('MT', 2, 2), ('ND', 2, 3), ('MN', 2, 4), ('IL', 2, 5),
    ('MI', 2, 6), ('NY', 2, 8), ('MA', 2, 9),
    ('OR', 3, 0), ('NV', 3, 1), ('WY', 3, 2), ('SD', 3, 3), ('IA', 3, 4), ('IN', 3, 5),
    ('OH', 3, 6), ('PA', 3, 7), ('NJ', 3, 8), ('CT', 3, 9), ('RI', 3, 10),
    ('CA', 4, 0), ('UT', 4, 1), ('CO', 4, 2), ('NE', 4, 3), ('MO', 4, 4), ('KY', 4, 5),
    ('WV', 4, 6), ('VA', 4, 7), ('MD', 4, 8), ('DE', 4, 9),
    ('AZ', 5, 1), ('NM', 5, 2), ('KS', 5, 3), ('AR', 5, 4), ('TN', 5, 5), ('NC', 5, 6),
    ('SC', 5, 7), ('DC', 5, 8),
    ('OK', 6, 3), ('LA', 6, 4), ('MS', 6, 5), ('AL', 6, 6), ('GA', 6, 7),
    ('HI', 7, 0), ('TX', 7, 3), ('FL', 7, 8),
]

# Sequential "sand" ramp shared by the overview charts, lightest to darkest,
# with a text color that passes contrast on each step.
SAND_RAMP = ['#DE9A60', '#D5753A', '#C45218', '#A33810', '#7B2815']
SAND_RAMP_TEXT = ['#1B2423', '#1B2423', '#FFFFFF', '#FFFFFF', '#FFFFFF']

# Gift size bands: (label, inclusive lower bound, exclusive upper bound).
GIFT_SIZE_BANDS = [
    ('Under $50', None, Decimal('50')),
    ('$50–249', Decimal('50'), Decimal('250')),
    ('$250–999', Decimal('250'), Decimal('1000')),
    ('$1,000–9,999', Decimal('1000'), Decimal('10000')),
    ('$10,000 and up', Decimal('10000'), None),
]

# Dollar thresholds for the state tile map shading.
STATE_MAP_BINS = [10000, 50000, 150000, 500000]


def compact_dollars(value):
    """10000 -> '10K', 2500000 -> '2.5M', for legend labels."""
    value = float(value)
    if value >= 1_000_000:
        return f'{value / 1_000_000:g}M'
    if value >= 1_000:
        return f'{value / 1_000:g}K'
    return f'{value:g}'


def bin_labels(thresholds):
    """Legend labels for threshold bins: ['< $10K', '$10–50K', ..., '$500K+']."""
    labels = []
    for i in range(len(thresholds) + 1):
        low = thresholds[i - 1] if i > 0 else None
        high = thresholds[i] if i < len(thresholds) else None
        if low is None:
            labels.append(f'< ${compact_dollars(high)}')
        elif high is None:
            labels.append(f'${compact_dollars(low)}+')
        else:
            low_text, high_text = compact_dollars(low), compact_dollars(high)
            if low_text[-1] == high_text[-1] and low_text[-1] in 'KM':
                labels.append(f'${low_text[:-1]}–{high_text}')
            else:
                labels.append(f'${low_text}–${high_text}')
    return labels


def get_year_filtered_reports(request):
    """Get reports filtered by year from query params."""
    reports = DisclosureReport.objects.all()
    year = request.GET.get('year')
    if year:
        try:
            year = int(year)
            reports = reports.filter(end_date__year=year)
        except (ValueError, TypeError):
            pass
    return reports


def get_year_filtered_contributions(request):
    """Get contributions filtered by year from query params."""
    year = request.GET.get('year')
    if year:
        try:
            year = int(year)
            return Contribution.objects.filter(report__end_date__year=year)
        except (ValueError, TypeError):
            pass
    return Contribution.objects.all()


def get_year_filtered_expenditures(request):
    """Get expenditures filtered by year from query params."""
    year = request.GET.get('year')
    if year:
        try:
            year = int(year)
            return Expenditure.objects.filter(report__end_date__year=year)
        except (ValueError, TypeError):
            pass
    return Expenditure.objects.all()


def about(request):
    """About page."""
    return render(request, 'disclosures/about.html')


def pct(part, whole):
    """Percentage of whole, rounded to one decimal, safe for zero."""
    if not whole:
        return 0.0
    return round(float(part) / float(whole) * 100, 1)


def nice_scale(max_value, ticks=5):
    """Return (tick values, top) for an axis that covers max_value in round steps."""
    max_value = float(max_value or 0)
    if max_value <= 0:
        return [0.0], 1.0
    raw = max_value / ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    step = magnitude
    for multiplier in (1, 2, 2.5, 5, 10):
        step = multiplier * magnitude
        if step * ticks >= max_value:
            break
    return [step * i for i in range(ticks + 1)], step * ticks


def gift_size_breakdown(contributions):
    """Count and sum contributions in each gift size band, with their shares."""
    aggregates = {}
    for i, (label, low, high) in enumerate(GIFT_SIZE_BANDS):
        condition = Q()
        if low is not None:
            condition &= Q(amount__gte=low)
        if high is not None:
            condition &= Q(amount__lt=high)
        aggregates[f'count_{i}'] = Count('id', filter=condition)
        aggregates[f'total_{i}'] = Sum('amount', filter=condition)
    totals = contributions.aggregate(**aggregates)

    bands = []
    for i, (label, low, high) in enumerate(GIFT_SIZE_BANDS):
        bands.append({
            'label': label,
            'color': SAND_RAMP[i],
            'text_color': SAND_RAMP_TEXT[i],
            'count': totals[f'count_{i}'] or 0,
            'total': totals[f'total_{i}'] or Decimal('0'),
        })

    all_count = sum(b['count'] for b in bands)
    all_total = sum(b['total'] for b in bands)
    count_cursor = 0.0
    dollar_cursor = 0.0
    for band in bands:
        band['count_pct'] = pct(band['count'], all_count)
        band['dollar_pct'] = pct(band['total'], all_total)
        # Ribbon polygon joining the two bars: a 1000 x 80 viewBox.
        count_end = count_cursor + band['count_pct'] * 10
        dollar_end = dollar_cursor + band['dollar_pct'] * 10
        band['ribbon_points'] = '{:.1f},0 {:.1f},0 {:.1f},80 {:.1f},80'.format(
            count_cursor, count_end, dollar_end, dollar_cursor
        )
        count_cursor = count_end
        dollar_cursor = dollar_end
    return bands


def top_fundraisers(reports, limit=10):
    """Filers ranked by money raised, with spending placed on the same scale."""
    rows = list(
        reports
        .exclude(organization_name='')
        .values('organization_name')
        .annotate(
            raised=Sum('total_contributions'),
            spent=Sum('total_expenditures'),
            org_type=Max('organization_type'),
        )
        .order_by('-raised')[:limit]
    )
    for row in rows:
        row['raised'] = row['raised'] or Decimal('0')
        row['spent'] = row['spent'] or Decimal('0')

    max_value = max([max(r['raised'], r['spent']) for r in rows] or [0])
    ticks, top = nice_scale(max_value)

    filers = []
    biggest_overspend = None
    for row in rows:
        raised_pct = pct(row['raised'], top)
        spent_pct = pct(row['spent'], top)
        diff = row['spent'] - row['raised']
        org_type = row['org_type'] or ''
        if org_type == 'Candidates & Office Holders':
            detail_url_name = 'disclosures:candidate_detail'
        elif 'Political Action Committee' in org_type:
            detail_url_name = 'disclosures:pac_detail'
        else:
            detail_url_name = ''
        filer = {
            'name': row['organization_name'],
            'detail_url_name': detail_url_name,
            'raised': row['raised'],
            'spent': row['spent'],
            'raised_pct': raised_pct,
            'spent_pct': spent_pct,
            'gap_left': min(raised_pct, spent_pct),
            'gap_width': abs(raised_pct - spent_pct),
            'diff': diff,
            'show_diff': abs(raised_pct - spent_pct) >= 8,
        }
        filers.append(filer)
        if diff > 0 and (biggest_overspend is None or diff > biggest_overspend['diff']):
            biggest_overspend = filer

    return {
        'rows': filers,
        'ticks': [{'value': t, 'frac': '{:.2f}'.format(t / top if top else 0)} for t in ticks],
        'biggest_overspend': biggest_overspend,
    }


def contributions_by_state(contributions):
    """Total dollars per state code, read from contributor addresses.

    Utah is totalled with one database query; the smaller out-of-state set is
    grouped in Python, matching the out-of-state map API.
    """
    addressed = contributions.exclude(address='').exclude(address=None)

    utah_total = addressed.filter(
        Q(address__iregex=r'[,\s]UT(?:\s+\d{5}(?:-\d{4})?)?\s*$') |
        Q(address__iregex=r'[,\s]Utah(?:\s+\d{5}(?:-\d{4})?)?\s*$')
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    out_of_state_codes = [code for code in STATE_CODES if code != 'UT']
    state_pattern = r'[,\s](' + '|'.join(out_of_state_codes) + r')(?:\s+\d{5}(?:-\d{4})?)?\s*$'
    compiled = re.compile(state_pattern, re.IGNORECASE)

    states = {}
    for contrib in addressed.filter(address__iregex=state_pattern).values('address', 'amount'):
        match = compiled.search(contrib['address'])
        if match:
            code = match.group(1).upper()
            states[code] = states.get(code, Decimal('0')) + (contrib['amount'] or Decimal('0'))

    out_of_state_total = sum(states.values(), Decimal('0'))
    return {
        'utah': utah_total,
        'states': states,
        'out_of_state_total': out_of_state_total,
        'readable_total': utah_total + out_of_state_total,
    }


def state_tiles(geography):
    """Tile map cells for the overview page, shaded by dollars contributed."""
    states = geography['states']
    out_of_state_total = geography['out_of_state_total']
    tiles = []
    for code, row, col in STATE_TILES:
        if code == 'UT':
            value = geography['utah']
            share = pct(value, geography['readable_total'])
            note = f'home state — {share:g}% of traceable dollars'
            color, text_color = '#0F2E2B', '#F3EFE6'
        else:
            value = states.get(code, Decimal('0'))
            share = pct(value, out_of_state_total)
            note = f'{share:g}% of all out-of-state money'
            shade = sum(1 for threshold in STATE_MAP_BINS if float(value) >= threshold)
            color, text_color = SAND_RAMP[shade], SAND_RAMP_TEXT[shade]
        tiles.append({
            'code': code,
            'name': STATE_NAMES[code],
            'row': row + 1,
            'col': col + 1,
            'value': value,
            'note': note,
            'color': color,
            'text_color': text_color,
        })
    return tiles


def index(request):
    """Overview page: headline figures, gift sizes, top fundraisers and geography."""
    reports = get_year_filtered_reports(request)
    contributions = get_year_filtered_contributions(request)
    expenditures = get_year_filtered_expenditures(request)

    contribution_totals = contributions.aggregate(total=Sum('amount'), count=Count('id'))
    expenditure_totals = expenditures.aggregate(total=Sum('amount'), count=Count('id'))

    stats = {
        'total_reports': reports.count(),
        'total_filers': reports.exclude(organization_name='').values('organization_name').distinct().count(),
        'total_contributions': contribution_totals['count'] or 0,
        'total_expenditures': expenditure_totals['count'] or 0,
        'total_contribution_amount': contribution_totals['total'] or Decimal('0'),
        'total_expenditure_amount': expenditure_totals['total'] or Decimal('0'),
    }

    gift_bands = gift_size_breakdown(contributions)
    small_gifts = gift_bands[0]
    large_gifts = gift_bands[-1]

    geography = contributions_by_state(contributions)
    tiles = state_tiles(geography)
    other_states = [code for code in geography['states'] if code != 'DC']
    top_state = max(
        (t for t in tiles if t['code'] != 'UT'),
        key=lambda t: t['value'],
        default=None,
    )

    context = {
        'stats': stats,
        'small_gift_share': small_gifts['count_pct'],
        'small_gifts_majority': round(small_gifts['count_pct']) >= 50,
        'large_gift_count': large_gifts['count'],
        'large_gift_share': large_gifts['dollar_pct'],
        'gift_bands': gift_bands,
        'fundraisers': top_fundraisers(reports),
        'tiles': tiles,
        'top_state_code': top_state['code'] if top_state and top_state['value'] else 'UT',
        'in_state_cents': int(round(pct(geography['utah'], geography['readable_total']))),
        'out_of_state_total': geography['out_of_state_total'],
        'other_state_count': len(other_states),
        'has_dc': 'DC' in geography['states'],
        'unreadable_share': int(round(100 - pct(geography['readable_total'], stats['total_contribution_amount']))) if stats['total_contribution_amount'] else 0,
        'state_map_legend': list(zip(SAND_RAMP, bin_labels(STATE_MAP_BINS))),
        'sand_ramp': SAND_RAMP,
    }

    return render(request, 'disclosures/index.html', context)


def reports_list(request):
    """List all disclosure reports with search and pagination."""
    reports = get_year_filtered_reports(request)

    # Filter by organization type
    org_type = request.GET.get('org_type', '')
    if org_type:
        reports = reports.filter(organization_type__icontains=org_type)

    # Search
    search = request.GET.get('search', '')
    if search:
        reports = reports.filter(
            Q(title__icontains=search) |
            Q(report_id__icontains=search) |
            Q(organization_name__icontains=search)
        )

    # Sorting
    sort = request.GET.get('sort', '-created_at')
    if sort in ['created_at', '-created_at', 'ending_balance', '-ending_balance', 'report_id', '-report_id', 'organization_name', '-organization_name']:
        reports = reports.order_by(sort)

    # Get distinct organization types for filter dropdown
    org_types = DisclosureReport.objects.exclude(organization_type='').values_list('organization_type', flat=True).distinct().order_by('organization_type')

    # Pagination
    paginator = Paginator(reports, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'sort': sort,
        'org_type': org_type,
        'org_types': org_types,
    }

    return render(request, 'disclosures/reports_list.html', context)


def report_detail(request, report_id):
    """Detailed view of a single disclosure report."""
    report = get_object_or_404(DisclosureReport, report_id=report_id)

    # Get contributions and expenditures
    contributions = report.contributions.all()[:100]
    expenditures = report.expenditures.all()[:100]

    # Summary stats
    contrib_stats = report.contributions.aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    # Calculate average separately to avoid aggregate() error with ternary
    if contrib_stats['count'] and contrib_stats['count'] > 0:
        contrib_stats['avg'] = (contrib_stats['total'] or Decimal('0')) / contrib_stats['count']
    else:
        contrib_stats['avg'] = Decimal('0')

    exp_stats = report.expenditures.aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    # Calculate average separately to avoid aggregate() error with ternary
    if exp_stats['count'] and exp_stats['count'] > 0:
        exp_stats['avg'] = (exp_stats['total'] or Decimal('0')) / exp_stats['count']
    else:
        exp_stats['avg'] = Decimal('0')

    context = {
        'report': report,
        'contributions': contributions,
        'expenditures': expenditures,
        'contrib_stats': contrib_stats,
        'exp_stats': exp_stats,
    }

    return render(request, 'disclosures/report_detail.html', context)


def contributors_list(request):
    """List all contributors with aggregated totals."""
    # Get year-filtered contributions
    contributions = get_year_filtered_contributions(request)

    # Aggregate by contributor name
    contributors = (
        contributions
        .values('contributor_name', 'address')
        .annotate(
            total_amount=Sum('amount'),
            contribution_count=Count('id'),
            last_contribution=Max('date_received')
        )
        .order_by('-total_amount')
    )

    # Search
    search = request.GET.get('search', '')
    if search:
        contributors = contributors.filter(
            Q(contributor_name__icontains=search) |
            Q(address__icontains=search)
        )

    # Pagination
    paginator = Paginator(contributors, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
    }

    return render(request, 'disclosures/contributors_list.html', context)


def expenditures_list(request):
    """List all expenditures with aggregated totals by recipient."""
    # Get year-filtered expenditures
    expenditures = get_year_filtered_expenditures(request)

    # Aggregate by recipient name
    recipients = (
        expenditures
        .values('recipient_name', 'purpose')
        .annotate(
            total_amount=Sum('amount'),
            expenditure_count=Count('id'),
            last_expenditure=Max('date')
        )
        .order_by('-total_amount')
    )

    # Search
    search = request.GET.get('search', '')
    if search:
        recipients = recipients.filter(
            Q(recipient_name__icontains=search) |
            Q(purpose__icontains=search)
        )

    # Pagination
    paginator = Paginator(recipients, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
    }

    return render(request, 'disclosures/expenditures_list.html', context)


# API endpoints for charts
@ratelimit(key='ip', rate='100/h', method='GET')
def api_report_timeline(request, report_id):
    """API endpoint for contribution/expenditure timeline data."""
    report = get_object_or_404(DisclosureReport, report_id=report_id)

    # Daily contributions
    daily_contributions = (
        report.contributions
        .exclude(date_received=None)
        .annotate(day=TruncDay('date_received'))
        .values('day')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('day')
    )

    # Daily expenditures
    daily_expenditures = (
        report.expenditures
        .exclude(date=None)
        .annotate(day=TruncDay('date'))
        .values('day')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('day')
    )

    data = {
        'contributions': [
            {
                'date': item['day'].isoformat(),
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in daily_contributions
        ],
        'expenditures': [
            {
                'date': item['day'].isoformat(),
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in daily_expenditures
        ]
    }

    return JsonResponse(data)


@ratelimit(key='ip', rate='100/h', method='GET')
def api_report_top_contributors(request, report_id):
    """API endpoint for top contributors chart data."""
    report = get_object_or_404(DisclosureReport, report_id=report_id)

    top_contributors = (
        report.contributions
        .values('contributor_name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:10]
    )

    data = [
        {
            'name': item['contributor_name'],
            'amount': float(item['total'])
        }
        for item in top_contributors
    ]

    return JsonResponse(data, safe=False)


@ratelimit(key="ip", rate="100/h", method="GET")
def api_report_top_expenditures(request, report_id):
    """API endpoint for top expenditure recipients chart data."""
    report = get_object_or_404(DisclosureReport, report_id=report_id)

    top_recipients = (
        report.expenditures
        .values('recipient_name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:10]
    )

    data = [
        {
            'name': item['recipient_name'],
            'amount': float(item['total'])
        }
        for item in top_recipients
    ]

    return JsonResponse(data, safe=False)


@ratelimit(key="ip", rate="100/h", method="GET")
def api_global_timeline(request):
    """API endpoint for global contribution/expenditure timeline, by month."""
    # Monthly contributions (respects the ?year= filter like the pages do)
    monthly_contributions = (
        get_year_filtered_contributions(request)
        .exclude(date_received=None)
        .annotate(month=TruncMonth('date_received'))
        .values('month')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('month')
    )

    # Monthly expenditures
    monthly_expenditures = (
        get_year_filtered_expenditures(request)
        .exclude(date=None)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('month')
    )

    data = {
        'contributions': [
            {
                'date': item['month'].isoformat(),
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in monthly_contributions
        ],
        'expenditures': [
            {
                'date': item['month'].isoformat(),
                'amount': float(item['total']),
                'count': item['count']
            }
            for item in monthly_expenditures
        ]
    }

    return JsonResponse(data)


def contributor_detail(request, contributor_name):
    """Detailed view of a single contributor's donation history."""
    # URL decode the contributor name
    contributor_name = unquote(contributor_name)

    # Get all contributions from this contributor
    contributions = Contribution.objects.filter(
        contributor_name=contributor_name
    ).select_related('report').order_by('-date_received')

    if not contributions.exists():
        from django.http import Http404
        raise Http404("Contributor not found")

    # Get first contribution for address info
    first_contrib = contributions.first()

    # Calculate statistics
    stats = contributions.aggregate(
        total_amount=Sum('amount'),
        contribution_count=Count('id'),
        avg_amount=Sum('amount') / Count('id') if contributions.count() > 0 else 0,
        first_contribution=Min('date_received'),
        last_contribution=Max('date_received')
    )

    # Get breakdown by organization/report
    by_organization = (
        contributions
        .values('report__organization_name', 'report__organization_type')
        .annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('-total')
    )

    # Get breakdown by year
    by_year = (
        contributions
        .exclude(date_received=None)
        .annotate(year=ExtractYear('date_received'))
        .values('year')
        .annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('-year')
    )

    context = {
        'contributor_name': contributor_name,
        'address': first_contrib.address,
        'contributions': contributions[:100],  # Limit to 100 for display
        'stats': stats,
        'by_organization': by_organization,
        'by_year': by_year,
    }

    return render(request, 'disclosures/contributor_detail.html', context)


@ratelimit(key="ip", rate="100/h", method="GET")
def api_contributor_timeline(request, contributor_name):
    """API endpoint for contributor donation timeline."""
    contributor_name = unquote(contributor_name)

    # Get daily contributions by this contributor
    daily_contributions = (
        Contribution.objects
        .filter(contributor_name=contributor_name)
        .exclude(date_received=None)
        .annotate(day=TruncDay('date_received'))
        .values('day')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('day')
    )

    data = [
        {
            'date': item['day'].isoformat(),
            'amount': float(item['total']),
            'count': item['count']
        }
        for item in daily_contributions
    ]

    return JsonResponse(data, safe=False)


def pacs_list(request):
    """List all Political Action Committees."""
    # Get year-filtered reports
    reports = get_year_filtered_reports(request)

    # Filter to only PACs
    pac_reports = reports.filter(organization_type__icontains='Political Action Committee')

    # Calculate aggregate stats
    aggregate_stats = pac_reports.aggregate(
        total_contributions=Sum('total_contributions'),
        total_expenditures=Sum('total_expenditures')
    )

    # Aggregate by organization name
    pacs = (
        pac_reports
        .values('organization_name', 'organization_type')
        .annotate(
            total_contributions=Sum('total_contributions'),
            total_expenditures=Sum('total_expenditures'),
            report_count=Count('id'),
            latest_report=Max('end_date')
        )
        .order_by('-total_contributions')
    )

    # Search
    search = request.GET.get('search', '')
    if search:
        pacs = pacs.filter(Q(organization_name__icontains=search))

    # Pagination
    paginator = Paginator(list(pacs), 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'pacs': page_obj.object_list,
        'total_pacs': paginator.count,
        'total_contributions': aggregate_stats['total_contributions'] or Decimal('0'),
        'total_expenditures': aggregate_stats['total_expenditures'] or Decimal('0'),
        'search': search,
    }

    return render(request, 'disclosures/pacs_list.html', context)


def pac_detail(request, organization_name):
    """Detailed view of a specific PAC with Sankey diagram."""
    organization_name = unquote(organization_name)

    # First check if this PAC exists at all (without year filter)
    all_pac_reports = DisclosureReport.objects.filter(
        organization_name=organization_name,
        organization_type__icontains='Political Action Committee'
    )

    if not all_pac_reports.exists():
        from django.http import Http404
        raise Http404("PAC not found")

    # Get first report for organization info (from all reports, not year-filtered)
    first_report = all_pac_reports.first()

    # Now get year-filtered reports for stats
    reports = get_year_filtered_reports(request)
    pac_reports = reports.filter(
        organization_name=organization_name,
        organization_type__icontains='Political Action Committee'
    )

    # Calculate statistics
    stats = pac_reports.aggregate(
        total_contributions=Sum('total_contributions'),
        total_expenditures=Sum('total_expenditures'),
        report_count=Count('id'),
        earliest_report=Min('begin_date'),
        latest_report=Max('end_date')
    )

    # Get all contributions and expenditures for this PAC
    contributions = get_year_filtered_contributions(request).filter(
        report__in=pac_reports
    )
    expenditures = get_year_filtered_expenditures(request).filter(
        report__in=pac_reports
    )

    # Top contributors
    top_contributors = (
        contributions
        .values('contributor_name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:10]
    )

    # Top recipients
    top_recipients = (
        expenditures
        .values('recipient_name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:10]
    )

    # Contribution/Expenditure breakdown
    contrib_stats = contributions.aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    # Calculate average separately to avoid aggregate() error with ternary
    if contrib_stats['count'] and contrib_stats['count'] > 0:
        contrib_stats['avg'] = (contrib_stats['total'] or Decimal('0')) / contrib_stats['count']
    else:
        contrib_stats['avg'] = Decimal('0')

    exp_stats = expenditures.aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    # Calculate average separately to avoid aggregate() error with ternary
    if exp_stats['count'] and exp_stats['count'] > 0:
        exp_stats['avg'] = (exp_stats['total'] or Decimal('0')) / exp_stats['count']
    else:
        exp_stats['avg'] = Decimal('0')

    # Calculate net balance
    net_balance = (stats['total_contributions'] or Decimal('0')) - (stats['total_expenditures'] or Decimal('0'))

    # Get all contributions and expenditures ordered by date
    all_contributions = contributions.order_by('-date_received')
    all_expenditures = expenditures.order_by('-date')

    # Try to find entity registration data
    # Try exact match first, then case-insensitive
    from .models import EntityRegistration
    entity = EntityRegistration.objects.filter(name__iexact=organization_name).first()

    context = {
        'organization_name': organization_name,
        'organization_type': first_report.organization_type,
        'stats': stats,
        'net_balance': net_balance,
        'pac_reports': pac_reports[:10],  # Recent reports
        'top_contributors': top_contributors,
        'top_recipients': top_recipients,
        'contrib_stats': contrib_stats,
        'exp_stats': exp_stats,
        'all_contributions': all_contributions,
        'all_expenditures': all_expenditures,
        'entity': entity,  # Add entity registration data
    }

    return render(request, 'disclosures/pac_detail.html', context)


@ratelimit(key="ip", rate="100/h", method="GET")
def api_pac_sankey(request, organization_name):
    """API endpoint for PAC Sankey diagram data."""
    organization_name = unquote(organization_name)

    # Get year-filtered reports
    reports = get_year_filtered_reports(request)

    # Get reports for this PAC
    pac_reports = reports.filter(
        organization_name=organization_name,
        organization_type__icontains='Political Action Committee'
    )

    # Get contributions (inflows) - exclude self-contributions
    contributions = (
        get_year_filtered_contributions(request)
        .filter(report__in=pac_reports)
        .exclude(contributor_name=organization_name)  # Exclude circular references
        .values('contributor_name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:15]  # Top 15 contributors
    )

    # Get expenditures (outflows) - exclude self-expenditures
    expenditures = (
        get_year_filtered_expenditures(request)
        .filter(report__in=pac_reports)
        .exclude(recipient_name=organization_name)  # Exclude circular references
        .values('recipient_name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:15]  # Top 15 recipients
    )

    # Build nodes and links for Sankey diagram
    nodes = []
    links = []

    # Get names from both lists
    contributor_names = set(c['contributor_name'] for c in contributions)
    recipient_names = set(r['recipient_name'] for r in expenditures)

    # Find entities that appear in both lists (would create cycles if not handled)
    circular_entities = contributor_names & recipient_names

    # Build node map
    node_map = {}
    node_index = 0

    # Add contributor nodes (sources)
    # For circular entities, append " (Contributor)" to make them unique
    for contrib in contributions:
        base_name = contrib['contributor_name']
        if base_name in circular_entities:
            node_name = f"{base_name} (Contributor)"
        else:
            node_name = base_name

        if node_name not in node_map:
            node_map[node_name] = node_index
            nodes.append({'name': node_name})
            node_index += 1

    # Add PAC node (middle)
    pac_node_index = node_index
    node_map[organization_name] = pac_node_index
    nodes.append({'name': organization_name})
    node_index += 1

    # Add recipient nodes (targets)
    # For circular entities, append " (Recipient)" to make them unique
    for exp in expenditures:
        base_name = exp['recipient_name']
        if base_name in circular_entities:
            node_name = f"{base_name} (Recipient)"
        else:
            node_name = base_name

        if node_name not in node_map:
            node_map[node_name] = node_index
            nodes.append({'name': node_name})
            node_index += 1

    # Add links from contributors to PAC
    for contrib in contributions:
        base_name = contrib['contributor_name']
        if base_name in circular_entities:
            source_name = f"{base_name} (Contributor)"
        else:
            source_name = base_name

        links.append({
            'source': node_map[source_name],
            'target': pac_node_index,
            'value': float(contrib['total'])
        })

    # Add links from PAC to recipients
    for exp in expenditures:
        base_name = exp['recipient_name']
        if base_name in circular_entities:
            target_name = f"{base_name} (Recipient)"
        else:
            target_name = base_name

        links.append({
            'source': pac_node_index,
            'target': node_map[target_name],
            'value': float(exp['total'])
        })

    data = {
        'nodes': nodes,
        'links': links
    }

    return JsonResponse(data)


def out_of_state(request):
    """Out-of-state contribution statistics with map visualization."""
    import re

    # Get year-filtered contributions (exclude empty addresses at database level)
    contributions = get_year_filtered_contributions(request).exclude(
        address=''
    ).exclude(address=None)

    # Filter out Utah addresses at database level (much faster than Python)
    # This uses database-level regex for better performance
    out_of_state_contributions = contributions.exclude(
        Q(address__iregex=r',?\s+UT\s+\d{5}') |
        Q(address__iregex=r',?\s+Utah\s+\d{5}') |
        Q(address__iendswith=' UT') |
        Q(address__iendswith=', UT')
    )

    # US state abbreviations
    states = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    ]

    # Pattern to find state abbreviation in address (end of string)
    state_pattern = r'\b(' + '|'.join(states) + r')(?:\s+\d{5}(?:-\d{4})?)?\s*$'

    # Group contributions by state
    # NOTE: We still need Python loop here because SQLite doesn't have good regex extraction
    # But we've reduced the dataset by filtering at database level first
    state_data = {}

    for contrib in out_of_state_contributions.only('address', 'amount', 'contributor_name'):
        # Try to extract state from address
        match = re.search(state_pattern, contrib.address, re.IGNORECASE)
        if match:
            state = match.group(1).upper()

            # Only include non-Utah states (double-check)
            if state != 'UT':
                # Add to state totals
                if state not in state_data:
                    state_data[state] = {
                        'state': state,
                        'total_amount': Decimal('0'),
                        'contribution_count': 0,
                        'contributors': set()
                    }

                state_data[state]['total_amount'] += contrib.amount or Decimal('0')
                state_data[state]['contribution_count'] += 1
                state_data[state]['contributors'].add(contrib.contributor_name)

    # Convert to list and calculate contributor counts
    state_list = []
    for state, data in state_data.items():
        state_list.append({
            'state': state,
            'total_amount': data['total_amount'],
            'contribution_count': data['contribution_count'],
            'contributor_count': len(data['contributors'])
        })

    # Sort by total amount descending
    state_list.sort(key=lambda x: x['total_amount'], reverse=True)

    # Get top out-of-state contributors (database aggregation)
    top_out_of_state = (
        out_of_state_contributions
        .values('contributor_name', 'address')
        .annotate(
            total_amount=Sum('amount'),
            contribution_count=Count('id')
        )
        .order_by('-total_amount')[:20]
    )

    # Calculate total stats (single database query)
    stats = out_of_state_contributions.aggregate(
        total=Sum('amount'),
        count=Count('id')
    )

    context = {
        'state_list': state_list,
        'top_out_of_state': top_out_of_state,
        'total_out_of_state_amount': stats['total'] or Decimal('0'),
        'total_out_of_state_count': stats['count'] or 0,
    }

    return render(request, 'disclosures/out_of_state.html', context)


@ratelimit(key="ip", rate="100/h", method="GET")
def api_out_of_state_map(request):
    """API endpoint for out-of-state contribution map data."""
    from django.db.models import Sum, Value
    from django.db.models.functions import Upper, Substr
    import re

    # Get year-filtered contributions that have addresses
    contributions = get_year_filtered_contributions(request).exclude(address='')

    # US state abbreviations (excluding UT)
    out_of_state_codes = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    ]

    # Use database regex to filter - much faster than Python loops
    # Pattern matches state code preceded by space/comma, followed by optional zip at end of address
    # PostgreSQL-compatible: uses [,\s] instead of \b for word boundaries
    state_pattern = r'[,\s](' + '|'.join(out_of_state_codes) + r')(?:\s+\d{5}(?:-\d{4})?)?\s*$'

    # Filter contributions to those with out-of-state addresses
    out_of_state_contribs = contributions.filter(address__iregex=state_pattern)

    # Now extract states and aggregate in Python (smaller dataset after filtering)
    state_data = {}
    for contrib in out_of_state_contribs.values('address', 'amount'):
        match = re.search(state_pattern, contrib['address'], re.IGNORECASE)
        if match:
            state = match.group(1).upper()
            if state not in state_data:
                state_data[state] = 0
            state_data[state] += float(contrib['amount'] or 0)

    # Return as array of {state, amount} objects
    data = [
        {'state': state, 'amount': amount}
        for state, amount in state_data.items()
    ]

    return JsonResponse(data, safe=False)


@ratelimit(key="ip", rate="100/h", method="GET")
def api_state_contributions(request, state_code):
    """API endpoint to get all contributions from a specific state."""
    from django.db.models import Sum, Q
    import re

    # Get year-filtered contributions with addresses
    contributions = get_year_filtered_contributions(request).exclude(address='')

    # US state abbreviations
    states = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    ]

    # Pattern to find THIS specific state at end of address
    # Use database regex first to narrow down results
    state_pattern = r'\b' + state_code.upper() + r'(?:\s+\d{5}(?:-\d{4})?)?\s*$'

    # Filter in database first (much faster than Python loop)
    state_contributions = contributions.filter(
        address__iregex=state_pattern
    ).select_related('report').order_by('-date_received', '-amount')

    # Calculate totals using database aggregation
    aggregation = state_contributions.aggregate(
        total_amount=Sum('amount'),
        total_count=models.Count('id')
    )

    # Get top 100 for display
    contributions_data = []
    for contrib in state_contributions[:100]:
        contributions_data.append({
            'contributor_name': contrib.contributor_name,
            'address': contrib.address,
            'amount': float(contrib.amount) if contrib.amount else 0,
            'date': contrib.date_received.strftime('%Y-%m-%d') if contrib.date_received else '',
            'organization': contrib.report.organization_name if contrib.report else '',
            'report_id': contrib.report.report_id if contrib.report else '',
        })

    return JsonResponse({
        'state': state_code,
        'contributions': contributions_data,
        'total_amount': float(aggregation['total_amount'] or 0),
        'total_count': aggregation['total_count'] or 0,
    })


def global_search(request):
    """Global search across all data."""
    query = request.GET.get('q', '').strip()

    if not query:
        context = {
            'query': '',
            'reports': [],
            'entities': [],
            'contributors': [],
            'expenditures': [],
            'total_results': 0
        }
        return render(request, 'disclosures/search.html', context)

    # Import the models we need
    from .models import EntityRegistration

    # Search reports
    reports = DisclosureReport.objects.filter(
        Q(report_id__icontains=query) |
        Q(title__icontains=query) |
        Q(organization_name__icontains=query)
    )[:20]

    # Search entities
    entities = EntityRegistration.objects.filter(
        Q(entity_id__icontains=query) |
        Q(name__icontains=query) |
        Q(also_known_as__icontains=query)
    )[:20]

    # Search contributors
    contributors = (
        Contribution.objects
        .filter(
            Q(contributor_name__icontains=query) |
            Q(address__icontains=query)
        )
        .values('contributor_name', 'address')
        .annotate(
            total_amount=Sum('amount'),
            contribution_count=Count('id')
        )
        .order_by('-total_amount')[:20]
    )

    # Search expenditures
    expenditures = (
        Expenditure.objects
        .filter(
            Q(recipient_name__icontains=query) |
            Q(purpose__icontains=query)
        )
        .values('recipient_name', 'purpose')
        .annotate(
            total_amount=Sum('amount'),
            expenditure_count=Count('id')
        )
        .order_by('-total_amount')[:20]
    )

    total_results = (
        reports.count() +
        entities.count() +
        len(contributors) +
        len(expenditures)
    )

    context = {
        'query': query,
        'reports': reports,
        'entities': entities,
        'contributors': contributors,
        'expenditures': expenditures,
        'total_results': total_results
    }

    return render(request, 'disclosures/search.html', context)


def candidates_list(request):
    """List of all candidates and office holders with campaign finance data."""
    # Get year-filtered reports
    reports = get_year_filtered_reports(request)

    # Filter to only candidates (organization_type = 'Candidates & Office Holders')
    candidate_reports = reports.filter(organization_type='Candidates & Office Holders')

    # Aggregate by organization name (candidate name)
    candidates = (
        candidate_reports
        .values('organization_name')
        .annotate(
            total_raised=Sum('total_contributions'),
            total_spent=Sum('total_expenditures'),
            report_count=Count('id'),
            latest_report_date=Max('end_date'),
            first_report_date=Min('end_date'),
            first_year=ExtractYear(Min('end_date')),
            last_year=ExtractYear(Max('end_date'))
        )
        .order_by('-total_raised')
    )

    # Pagination
    paginator = Paginator(candidates, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate summary stats
    stats = candidate_reports.aggregate(
        total_candidates=Count('organization_name', distinct=True),
        total_raised=Sum('total_contributions'),
        total_spent=Sum('total_expenditures'),
        total_reports=Count('id')
    )

    context = {
        'page_obj': page_obj,
        'stats': stats,
    }

    return render(request, 'disclosures/candidates_list.html', context)


def candidate_detail(request, candidate_name):
    """Detail page for a specific candidate showing all their reports and financial activity."""
    # URL decode the candidate name
    candidate_name = unquote(candidate_name)

    # Get year-filtered reports
    reports = get_year_filtered_reports(request)

    # Get all reports for this candidate
    candidate_reports = reports.filter(
        organization_type='Candidates & Office Holders',
        organization_name=candidate_name
    ).order_by('-end_date')

    if not candidate_reports.exists():
        from django.http import Http404
        raise Http404("Candidate not found")

    # Get contributions and expenditures across all reports
    contributions = Contribution.objects.filter(
        report__in=candidate_reports
    )
    expenditures = Expenditure.objects.filter(
        report__in=candidate_reports
    )

    # Top contributors
    top_contributors = (
        contributions
        .values('contributor_name', 'address')
        .annotate(
            total_amount=Sum('amount'),
            contribution_count=Count('id')
        )
        .order_by('-total_amount')[:20]
    )

    # Top expenditures by recipient
    top_expenditures = (
        expenditures
        .values('recipient_name', 'purpose')
        .annotate(
            total_amount=Sum('amount'),
            expenditure_count=Count('id')
        )
        .order_by('-total_amount')[:20]
    )

    # Monthly contribution trends
    monthly_contributions = (
        contributions
        .annotate(month=TruncMonth('date_received'))
        .values('month')
        .annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('month')
    )

    # Monthly expenditure trends
    monthly_expenditures = (
        expenditures
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('month')
    )

    # Summary statistics
    stats = {
        'total_raised': contributions.aggregate(total=Sum('amount'))['total'] or Decimal('0'),
        'total_spent': expenditures.aggregate(total=Sum('amount'))['total'] or Decimal('0'),
        'contribution_count': contributions.count(),
        'expenditure_count': expenditures.count(),
        'contributor_count': contributions.values('contributor_name').distinct().count(),
        'report_count': candidate_reports.count(),
    }

    # Calculate cash on hand (most recent report's ending balance)
    latest_report = candidate_reports.first()
    if latest_report and latest_report.ending_balance:
        stats['cash_on_hand'] = latest_report.ending_balance
    else:
        stats['cash_on_hand'] = Decimal('0')

    # Get campaign years from report dates
    year_range = candidate_reports.aggregate(
        first_year=ExtractYear(Min('end_date')),
        last_year=ExtractYear(Max('end_date'))
    )

    # Get all unique years
    campaign_years = sorted(set(
        candidate_reports.annotate(year=ExtractYear('end_date'))
        .values_list('year', flat=True)
        .distinct()
    ))

    # Extract office/position information from report_info JSON
    # Get the most common values across all reports
    from collections import Counter
    offices = []
    districts = []
    parties = []
    counties = []

    for report in candidate_reports:
        if report.report_info:
            if 'Office' in report.report_info:
                offices.append(report.report_info['Office'])
            if 'District' in report.report_info:
                districts.append(report.report_info['District'])
            if 'Party' in report.report_info:
                parties.append(report.report_info['Party'])
            if 'County' in report.report_info:
                counties.append(report.report_info['County'])

    # Get most common values and track all unique offices
    office_info = {}

    if offices:
        office_counter = Counter(offices)
        # Get all unique offices with their counts, sorted by count (descending)
        all_offices = office_counter.most_common()
        office_info['office'] = all_offices[0][0]  # Most common
        # If multiple offices, include them all
        if len(all_offices) > 1:
            office_info['all_offices'] = [
                {'name': office, 'count': count}
                for office, count in all_offices
            ]

    if districts:
        district_counter = Counter(districts)
        all_districts = district_counter.most_common()
        office_info['district'] = all_districts[0][0]
        # If multiple districts, include them
        if len(all_districts) > 1:
            office_info['all_districts'] = [dist for dist, count in all_districts]

    if parties:
        office_info['party'] = Counter(parties).most_common(1)[0][0]

    if counties:
        county = Counter(counties).most_common(1)[0][0]
        # Only include county if it's meaningful (not Multi- or Statewide)
        if county not in ['Multi-', 'Statewide', '']:
            office_info['county'] = county

    context = {
        'candidate_name': candidate_name,
        'reports': candidate_reports[:10],  # Show latest 10 reports
        'all_reports_count': candidate_reports.count(),
        'top_contributors': top_contributors,
        'top_expenditures': top_expenditures,
        'monthly_contributions': monthly_contributions,
        'monthly_expenditures': monthly_expenditures,
        'stats': stats,
        'campaign_years': campaign_years,
        'year_range': year_range,
        'office_info': office_info,
    }

    return render(request, 'disclosures/candidate_detail.html', context)


def api_candidate_sankey(request, candidate_name):
    """API endpoint for Candidate Sankey diagram showing: Contributors → Candidate and Contributors → PAC → Candidate."""
    candidate_name = unquote(candidate_name)

    # Get year-filtered reports
    reports = get_year_filtered_reports(request)

    # Get reports for this candidate
    candidate_reports = reports.filter(
        organization_name=candidate_name,
        organization_type='Candidates & Office Holders'
    )

    # Get direct contributions to candidate - top 10
    direct_contributions = list(
        get_year_filtered_contributions(request)
        .filter(report__in=candidate_reports)
        .exclude(contributor_name=candidate_name)
        .values('contributor_name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:10]
    )

    # Identify PACs that contributed to the candidate
    # Check if contributor has reports filed as a PAC (more reliable than name matching)
    pac_contributors = []
    non_pac_contributors = []

    for contrib in direct_contributions:
        contrib_name = contrib['contributor_name']

        # Check if this contributor has reports filed as a PAC
        # Try exact match first
        has_pac_reports = reports.filter(
            organization_name=contrib_name,
            organization_type__icontains='Political Action Committee'
        ).exists()

        # If no exact match, try fuzzy matching by removing common suffixes and matching on key words
        if not has_pac_reports:
            from django.db.models import Q
            clean_name = contrib_name.replace(' PAC', '').replace(' Committee', '').replace(' Fund', '').strip()

            # Split into words and create a query that matches all significant words
            words = [w for w in clean_name.split() if len(w) > 2]  # Only words longer than 2 chars
            if words:
                q = Q(organization_type__icontains='Political Action Committee')
                for word in words:
                    q &= Q(organization_name__icontains=word)
                has_pac_reports = reports.filter(q).exists()

        if has_pac_reports:
            pac_contributors.append(contrib)
        else:
            non_pac_contributors.append(contrib)

    # Build nodes and links for Sankey diagram
    nodes = []
    links = []
    node_map = {}
    node_index = 0

    # For each PAC that contributed to the candidate, get its contributors
    pac_contributor_data = {}
    for pac_contrib in pac_contributors:
        pac_name = pac_contrib['contributor_name']

        # Get reports for this PAC - try exact match first, then fuzzy match
        # Handle cases where contributor name might be "Friends of Gary Herbert PAC"
        # but org name is "Friends Of Gary R. Herbert"
        pac_reports = reports.filter(
            organization_name=pac_name,
            organization_type__icontains='Political Action Committee'
        )

        # If no exact match, try fuzzy matching using key words
        if not pac_reports.exists():
            from django.db.models import Q
            clean_name = pac_name.replace(' PAC', '').replace(' Committee', '').replace(' Fund', '').strip()

            # Split into words and create a query that matches all significant words
            words = [w for w in clean_name.split() if len(w) > 2]
            if words:
                q = Q(organization_type__icontains='Political Action Committee')
                for word in words:
                    q &= Q(organization_name__icontains=word)
                pac_reports = reports.filter(q)

        if pac_reports.exists():
            # Use the actual organization name from the reports (not the contributor name)
            # This avoids duplication when multiple contributor names match the same PAC
            actual_pac_name = pac_reports.first().organization_name

            # Only add if we haven't already processed this PAC
            if actual_pac_name not in pac_contributor_data:
                # Get top 5 contributors to this PAC
                pac_contributors_list = list(
                    get_year_filtered_contributions(request)
                    .filter(report__in=pac_reports)
                    .exclude(contributor_name__in=[pac_name, candidate_name, actual_pac_name])
                    .values('contributor_name')
                    .annotate(total=Sum('amount'))
                    .order_by('-total')[:5]
                )
                if pac_contributors_list:
                    # Store using actual PAC name and include the original contributor name and amount
                    pac_contributor_data[actual_pac_name] = {
                        'contributors': pac_contributors_list,
                        'contribution_to_candidate': pac_contrib['total']
                    }

    # Add contributor nodes to PACs (leftmost layer)
    for pac_name, pac_data in pac_contributor_data.items():
        for contrib in pac_data['contributors']:
            contrib_name = contrib['contributor_name']
            if contrib_name not in node_map:
                node_map[contrib_name] = node_index
                nodes.append({'name': contrib_name})
                node_index += 1

    # Add non-PAC direct contributor nodes (leftmost layer)
    for contrib in non_pac_contributors:
        contrib_name = contrib['contributor_name']
        if contrib_name not in node_map:
            node_map[contrib_name] = node_index
            nodes.append({'name': contrib_name})
            node_index += 1

    # Add PAC nodes (middle layer) - only those with contributor data
    pac_nodes = {}
    for pac_name in pac_contributor_data.keys():
        if pac_name not in node_map:
            node_map[pac_name] = node_index
            nodes.append({'name': pac_name})
            pac_nodes[pac_name] = node_index
            node_index += 1

    # Add candidate node (rightmost - target)
    candidate_node_index = node_index
    node_map[candidate_name] = candidate_node_index
    nodes.append({'name': candidate_name})
    node_index += 1

    # Add links: Contributors → PAC
    for pac_name, pac_data in pac_contributor_data.items():
        for contrib in pac_data['contributors']:
            links.append({
                'source': node_map[contrib['contributor_name']],
                'target': node_map[pac_name],
                'value': float(contrib['total'])
            })

    # Add links: PAC → Candidate
    for pac_name, pac_data in pac_contributor_data.items():
        links.append({
            'source': node_map[pac_name],
            'target': candidate_node_index,
            'value': float(pac_data['contribution_to_candidate'])
        })

    # Add links: Non-PAC contributors → Candidate (direct)
    for contrib in non_pac_contributors:
        links.append({
            'source': node_map[contrib['contributor_name']],
            'target': candidate_node_index,
            'value': float(contrib['total'])
        })

    data = {
        'nodes': nodes,
        'links': links
    }

    return JsonResponse(data)

def extract_state_from_address(address):
    """Extract state code from address string."""
    if not address:
        return None

    import re
    # Look for state code pattern: 2 uppercase letters followed by optional space and zip
    # Common patterns: "UT 84116", "UT84116", ", UT 84116", "Utah 84116"
    match = re.search(r',\s*([A-Z]{2})\s+\d{5}', address)
    if match:
        return match.group(1)

    # Try end of string
    match = re.search(r'\b([A-Z]{2})\s*\d{5}', address)
    if match:
        return match.group(1)

    return None


@ratelimit(key='ip', rate='100/m', method='GET')
def api_pac_instate_percentage(request, organization_name):
    """API endpoint for PAC in-state contribution percentage."""
    organization_name = unquote(organization_name)

    # Get year-filtered reports
    reports = get_year_filtered_reports(request)
    pac_reports = reports.filter(
        organization_name=organization_name,
        organization_type__icontains='Political Action Committee'
    )

    if not pac_reports.exists():
        return JsonResponse({'error': 'PAC not found'}, status=404)

    # Get all contributions to this PAC
    contributions = get_year_filtered_contributions(request).filter(
        report__in=pac_reports
    )

    # Calculate in-state vs out-of-state
    instate_total = Decimal('0')
    outstate_total = Decimal('0')
    unknown_total = Decimal('0')

    for contrib in contributions:
        state = extract_state_from_address(contrib.address)
        if state == 'UT':
            instate_total += contrib.amount
        elif state:
            outstate_total += contrib.amount
        else:
            unknown_total += contrib.amount

    total = instate_total + outstate_total + unknown_total

    if total == 0:
        instate_percentage = 0
        outstate_percentage = 0
        unknown_percentage = 0
    else:
        instate_percentage = float((instate_total / total) * 100)
        outstate_percentage = float((outstate_total / total) * 100)
        unknown_percentage = float((unknown_total / total) * 100)

    return JsonResponse({
        'instate_percentage': round(instate_percentage, 1),
        'outstate_percentage': round(outstate_percentage, 1),
        'unknown_percentage': round(unknown_percentage, 1),
        'instate_amount': float(instate_total),
        'outstate_amount': float(outstate_total),
        'unknown_amount': float(unknown_total),
        'total_amount': float(total)
    })


@ratelimit(key='ip', rate='100/m', method='GET')
def api_candidate_instate_percentage(request, candidate_name):
    """
    API endpoint for candidate in-state contribution percentage.
    Accounts for PAC contributions by weighting them by the PAC's own in-state percentage.
    """
    candidate_name = unquote(candidate_name)

    # Get year-filtered reports
    reports = get_year_filtered_reports(request)
    candidate_reports = reports.filter(
        organization_name=candidate_name,
        organization_type='Candidates & Office Holders'
    )

    if not candidate_reports.exists():
        return JsonResponse({'error': 'Candidate not found'}, status=404)

    # Get all contributions to candidate
    contributions = get_year_filtered_contributions(request).filter(
        report__in=candidate_reports
    )

    # Track weighted totals
    instate_total = Decimal('0')
    outstate_total = Decimal('0')
    unknown_total = Decimal('0')

    for contrib in contributions:
        contrib_name = contrib.contributor_name
        contrib_amount = contrib.amount

        # Check if this contributor is a PAC
        # Try exact match first
        pac_reports = reports.filter(
            organization_name=contrib_name,
            organization_type__icontains='Political Action Committee'
        )

        # If no exact match, try fuzzy matching
        if not pac_reports.exists():
            clean_name = contrib_name.replace(' PAC', '').replace(' Committee', '').replace(' Fund', '').strip()
            words = [w for w in clean_name.split() if len(w) > 2]
            if words:
                q = Q(organization_type__icontains='Political Action Committee')
                for word in words:
                    q &= Q(organization_name__icontains=word)
                pac_reports = reports.filter(q)

        if pac_reports.exists():
            # This is a PAC - get the PAC's in-state percentage
            pac_contributions = get_year_filtered_contributions(request).filter(
                report__in=pac_reports
            )

            pac_instate = Decimal('0')
            pac_outstate = Decimal('0')
            pac_unknown = Decimal('0')

            for pac_contrib in pac_contributions:
                state = extract_state_from_address(pac_contrib.address)
                if state == 'UT':
                    pac_instate += pac_contrib.amount
                elif state:
                    pac_outstate += pac_contrib.amount
                else:
                    pac_unknown += pac_contrib.amount

            pac_total = pac_instate + pac_outstate + pac_unknown

            if pac_total > 0:
                # Weight the contribution by PAC's percentages
                instate_total += contrib_amount * (pac_instate / pac_total)
                outstate_total += contrib_amount * (pac_outstate / pac_total)
                unknown_total += contrib_amount * (pac_unknown / pac_total)
            else:
                # PAC has no contributions data, treat as unknown
                unknown_total += contrib_amount
        else:
            # Direct contribution - check state
            state = extract_state_from_address(contrib.address)
            if state == 'UT':
                instate_total += contrib_amount
            elif state:
                outstate_total += contrib_amount
            else:
                unknown_total += contrib_amount

    total = instate_total + outstate_total + unknown_total

    if total == 0:
        instate_percentage = 0
        outstate_percentage = 0
        unknown_percentage = 0
    else:
        instate_percentage = float((instate_total / total) * 100)
        outstate_percentage = float((outstate_total / total) * 100)
        unknown_percentage = float((unknown_total / total) * 100)

    return JsonResponse({
        'instate_percentage': round(instate_percentage, 1),
        'outstate_percentage': round(outstate_percentage, 1),
        'unknown_percentage': round(unknown_percentage, 1),
        'instate_amount': float(instate_total),
        'outstate_amount': float(outstate_total),
        'unknown_amount': float(unknown_total),
        'total_amount': float(total)
    })
