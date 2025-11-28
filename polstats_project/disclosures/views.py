from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, Min, Max
from django.db.models.functions import TruncMonth, TruncDay, ExtractYear
from django.core.paginator import Paginator
from django_ratelimit.decorators import ratelimit
from .models import DisclosureReport, Contribution, Expenditure
from decimal import Decimal
from urllib.parse import unquote


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


def index(request):
    """Homepage with overview statistics."""
    # Get year-filtered querysets
    reports = get_year_filtered_reports(request)
    contributions = get_year_filtered_contributions(request)
    expenditures = get_year_filtered_expenditures(request)

    stats = {
        'total_reports': reports.count(),
        'total_contributions': contributions.count(),
        'total_expenditures': expenditures.count(),
        'total_contribution_amount': contributions.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0'),
        'total_expenditure_amount': expenditures.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0'),
    }

    # Recent reports
    recent_reports = reports[:10]

    # Top contributors
    top_contributors = (
        contributions
        .values('contributor_name')
        .annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('-total')[:10]
    )

    # Top recipients
    top_recipients = (
        expenditures
        .values('recipient_name')
        .annotate(
            total=Sum('amount'),
            count=Count('id')
        )
        .order_by('-total')[:10]
    )

    context = {
        'stats': stats,
        'recent_reports': recent_reports,
        'top_contributors': top_contributors,
        'top_recipients': top_recipients,
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
    paginator = Paginator(list(contributors), 50)
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
    paginator = Paginator(list(recipients), 50)
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
    """API endpoint for global contribution/expenditure timeline."""
    # Monthly contributions
    monthly_contributions = (
        Contribution.objects
        .exclude(date_received=None)
        .annotate(month=TruncMonth('date_received'))
        .values('month')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('month')
    )

    # Monthly expenditures
    monthly_expenditures = (
        Expenditure.objects
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

    # Find entities that appear in both lists (these would create cycles)
    circular_entities = contributor_names & recipient_names

    # Filter out circular entities from contributions and expenditures
    filtered_contributions = [c for c in contributions if c['contributor_name'] not in circular_entities]
    filtered_expenditures = [e for e in expenditures if e['recipient_name'] not in circular_entities]

    # Build node map
    node_map = {}
    node_index = 0

    # Add contributor nodes (sources)
    for contrib in filtered_contributions:
        node_name = contrib['contributor_name']
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
    for exp in filtered_expenditures:
        node_name = exp['recipient_name']
        if node_name not in node_map:
            node_map[node_name] = node_index
            nodes.append({'name': node_name})
            node_index += 1

    # Add links from contributors to PAC
    for contrib in filtered_contributions:
        links.append({
            'source': node_map[contrib['contributor_name']],
            'target': pac_node_index,
            'value': float(contrib['total'])
        })

    # Add links from PAC to recipients
    for exp in filtered_expenditures:
        links.append({
            'source': pac_node_index,
            'target': node_map[exp['recipient_name']],
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

    # Get year-filtered contributions
    contributions = get_year_filtered_contributions(request)

    # US state abbreviations
    states = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    ]

    # Pattern to find state abbreviation in address
    state_pattern = r'\b(' + '|'.join(states) + r')(?:\s+\d{5}(?:-\d{4})?)?\s*$'

    # Group contributions by state
    state_data = {}
    out_of_state_contributors = []

    for contrib in contributions:
        if not contrib.address:
            continue

        # Try to extract state from address
        match = re.search(state_pattern, contrib.address, re.IGNORECASE)
        if match:
            state = match.group(1).upper()

            # Only include non-Utah states
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

    # Get top out-of-state contributors
    out_of_state_contributions = contributions.exclude(
        Q(address__icontains=' UT ') |
        Q(address__icontains=', UT') |
        Q(address__icontains=' Utah') |
        Q(address__iendswith=' UT') |
        Q(address__iendswith=', UT')
    ).exclude(address='').exclude(address=None)

    top_out_of_state = (
        out_of_state_contributions
        .values('contributor_name', 'address')
        .annotate(
            total_amount=Sum('amount'),
            contribution_count=Count('id')
        )
        .order_by('-total_amount')[:20]
    )

    # Calculate total stats
    total_out_of_state_amount = out_of_state_contributions.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    total_out_of_state_count = out_of_state_contributions.count()

    context = {
        'state_list': state_list,
        'top_out_of_state': top_out_of_state,
        'total_out_of_state_amount': total_out_of_state_amount,
        'total_out_of_state_count': total_out_of_state_count,
    }

    return render(request, 'disclosures/out_of_state.html', context)


@ratelimit(key="ip", rate="100/h", method="GET")
def api_out_of_state_map(request):
    """API endpoint for out-of-state contribution map data."""
    import re

    # Get year-filtered contributions
    contributions = get_year_filtered_contributions(request)

    # US state abbreviations
    states = [
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    ]

    # Pattern to find state abbreviation in address
    state_pattern = r'\b(' + '|'.join(states) + r')(?:\s+\d{5}(?:-\d{4})?)?\s*$'

    # Group contributions by state
    state_data = {}

    for contrib in contributions:
        if not contrib.address:
            continue

        # Try to extract state from address
        match = re.search(state_pattern, contrib.address, re.IGNORECASE)
        if match:
            state = match.group(1).upper()

            # Only include non-Utah states
            if state != 'UT':
                if state not in state_data:
                    state_data[state] = 0

                state_data[state] += float(contrib.amount or 0)

    # Return as array of {state, amount} objects
    data = [
        {'state': state, 'amount': amount}
        for state, amount in state_data.items()
    ]

    return JsonResponse(data, safe=False)


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
