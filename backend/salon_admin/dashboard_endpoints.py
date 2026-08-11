from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, DateField, Max, F
from django.db.models.functions import TruncDate, ExtractHour, ExtractYear, ExtractMonth, Cast, ExtractWeekDay
from datetime import datetime, timedelta, date as date_type
import calendar

from billing.models import Invoice, InvoiceItem, Payment, AdvancePayment
from appointments.models import Appointment
from clients.models import Client
from staff.models import StaffMember, ServiceLog
from services.models import ServiceMaster
from marketing.models import Membership, Package
from inventory.models import Product

def _apply_security(request, queryset, model_type='invoice'):
    user = request.user
    perms = getattr(user.role, 'permissions', {}) or {}
    is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
    
    if not is_owner and not perms.get('all_centers', False):
        if user.centers.exists():
            if model_type == 'staff':
                queryset = queryset.filter(center__in=user.centers.all())
            else:
                queryset = queryset.filter(center__in=user.centers.all())
        elif hasattr(user, 'center') and user.center:
            if model_type == 'staff':
                queryset = queryset.filter(center=user.center)
            else:
                queryset = queryset.filter(center=user.center)
    
    center_id = request.GET.get('center_id')
    if center_id and center_id != 'null':
        queryset = queryset.filter(center_id=center_id)
        
    return queryset

def _apply_dates(request, queryset, date_field='created_at', is_datetime=True):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    if start_date_str and end_date_str:
        try:
            if is_datetime:
                # For DateTimeField: use exclusive upper bound (next day)
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date() + timedelta(days=1)
                queryset = queryset.filter(**{f"{date_field}__gte": start_date_str, f"{date_field}__lt": end_date_obj})
            else:
                # For DateField: use inclusive upper bound
                queryset = queryset.filter(**{f"{date_field}__gte": start_date_str, f"{date_field}__lte": end_date_str})
        except ValueError:
            pass
    return queryset

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    invoices = Invoice.objects.filter(status__in=['paid', 'partial']).select_related('client')
    invoices = _apply_security(request, invoices)
    invoices = _apply_dates(request, invoices, 'created_at')
    
    clients = Client.objects.all()
    clients = _apply_security(request, clients)
    clients_period = _apply_dates(request, clients, 'created_at')
    
    total_revenue = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Dynamic Monthly Target based on selected center(s)
    from salon_admin.models import Center
    centers_qs = Center.objects.all()
    user = request.user
    is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
    perms = getattr(user.role, 'permissions', {}) or {}
    
    if not is_owner and not perms.get('all_centers', False):
        if user.centers.exists():
            centers_qs = centers_qs.filter(id__in=user.centers.values_list('id', flat=True))
        elif hasattr(user, 'center') and user.center:
            centers_qs = centers_qs.filter(id=user.center.id)
            
    center_id = request.GET.get('center_id')
    if center_id and center_id != 'null':
        centers_qs = centers_qs.filter(id=center_id)
        
    target_month_key = None
    start_date_str = request.GET.get('start_date')
    if start_date_str:
        try:
            target_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            target_month_key = target_date.strftime('%b-%Y') # e.g. "Jul-2026"
        except Exception:
            pass
            
    monthly_target = 0
    for center in centers_qs:
        history = center.monthly_targets_history or {}
        val = 0
        if target_month_key and target_month_key in history:
            try:
                val = Decimal(str(history[target_month_key]))
            except (ValueError, TypeError):
                pass
                
        if val == 0:
            val = Decimal(str(center.monthly_target or 0))
            
        monthly_target += val
    projected = Decimal(str(total_revenue))
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    if start_date_str and end_date_str and total_revenue > 0:
        try:
            sd = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            ed = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            today = date_type.today()
            if ed < today:
                projected = Decimal(str(total_revenue))
            else:
                days_elapsed = max((today - sd).days, 1)
                days_in_month = calendar.monthrange(sd.year, sd.month)[1]
                if (ed - sd).days >= 28:
                    days_in_month = (ed - sd).days + 1
                projected = (Decimal(str(total_revenue)) / Decimal(str(days_elapsed))) * Decimal(str(days_in_month)) if days_elapsed > 0 else Decimal("0")
        except Exception:
            pass
    
    # Client metrics based strictly on invoiced clients
    invoiced_clients = clients.filter(id__in=invoices.values('client').distinct())
    total_invoiced_clients = invoiced_clients.count()
    
    start_date = request.GET.get('start_date', '2000-01-01')
    end_date = request.GET.get('end_date', '2099-12-31')
    new_clients = invoiced_clients.filter(created_at__date__gte=start_date, created_at__date__lte=end_date).count()
    repeat_clients = total_invoiced_clients - new_clients
    
    # Inventory - use DB aggregation instead of Python loop
    from django.db.models import F
    from django.db.models.functions import Coalesce
    products = Product.objects.all()
    products = _apply_security(request, products)
    inv_agg = products.aggregate(
        amount=Sum(Coalesce(F('current_stock'), 0) * Coalesce(F('price'), Decimal('0.0'))),
        count=Sum('current_stock')
    )
    inv_amount = Decimal(str(inv_agg['amount'] or 0))
    inv_count = int(inv_agg['count'] or 0)
    
    # Invoices over weekdays (Sun-Sat)
    invoices_period = _apply_dates(request, invoices, 'created_at')
    weekday_inv = invoices_period.annotate(dow=ExtractWeekDay('created_at')).values('dow').annotate(count=Count('id')).order_by('dow')
    weekday_counts_list = [0]*7
    for item in weekday_inv:
        dow = item.get('dow')
        if dow and 1 <= dow <= 7:
            weekday_counts_list[dow-1] = item['count']
            
    # Revenue Breakdown
    items_period = InvoiceItem.objects.filter(invoice__in=invoices_period).select_related('content_type')
    breakdown_qs = items_period.values('content_type__model').annotate(revenue=Sum('total_price'))
    revenue_breakdown = { 'service': 0, 'product': 0, 'membership': 0, 'package': 0, 'card': 0 }
    for b in breakdown_qs:
        model = b['content_type__model']
        if model == 'servicemaster': revenue_breakdown['service'] += Decimal(str(b['revenue'] or 0))
        elif model == 'product': revenue_breakdown['product'] += Decimal(str(b['revenue'] or 0))
        elif model == 'membership': revenue_breakdown['membership'] += Decimal(str(b['revenue'] or 0))
        elif model == 'package': revenue_breakdown['package'] += Decimal(str(b['revenue'] or 0))
        elif model == 'valuecard': revenue_breakdown['card'] += Decimal(str(b['revenue'] or 0))
        
    # Balances and Memberships
    from clients.models import ClientValueCard, ClientPackage, ClientMembership
    from billing.models import AdvancePayment
    
    centers_ids = centers_qs.values_list('id', flat=True)
    
    active_vcs = ClientValueCard.objects.filter(is_active=True, client__center_id__in=centers_ids)
    vc_agg = active_vcs.aggregate(total=Sum('balance'), count=Count('id'))
    
    active_pkgs = ClientPackage.objects.filter(is_active=True, client__center_id__in=centers_ids)
    pkg_agg = active_pkgs.aggregate(total=Sum('package__price'), count=Count('id'))
    
    advances_agg = AdvancePayment.objects.filter(client__center_id__in=centers_ids).aggregate(total=Sum('amount'), count=Count('id'))
    
    memberships_this_month = ClientMembership.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date, client__center_id__in=centers_ids).count()
    
    balances = {
        'value_cards': {'count': vc_agg['count'] or 0, 'amount': Decimal(str(vc_agg['total'] or 0))},
        'services': {'count': pkg_agg['count'] or 0, 'amount': Decimal(str(pkg_agg['total'] or 0))},
        'advances': {'count': advances_agg['count'] or 0, 'amount': Decimal(str(advances_agg['total'] or 0))},
        'memberships': memberships_this_month
    }
    
    # Top Staff this month
    from staff.models import ServiceLog
    logs_period = ServiceLog.objects.filter(invoice__status__in=['paid', 'partial'], date__gte=start_date, date__lte=end_date, center_id__in=centers_ids)
    top_staff_qs = logs_period.values('staff__first_name', 'staff__last_name').annotate(revenue=Sum('price')).order_by('-revenue')[:5]
    top_staff = [{'name': f"{s['staff__first_name']} {s['staff__last_name'] or ''}".strip(), 'revenue': Decimal(str(s['revenue'] or 0))} for s in top_staff_qs]

    
    # Top Services / Products — batch name lookup to avoid N+1 queries
    invoice_items = InvoiceItem.objects.filter(invoice__in=invoices).select_related('content_type')

    services_qs = (
        invoice_items.filter(content_type__model='servicemaster')
        .values('object_id')
        .annotate(count=Sum('quantity'), revenue=Sum('total_price'), description=Max('description'))
        .order_by('-count')[:20]
    )
    top_services = [
        {'name': s['description'] or f'Service #{s["object_id"]}', 'count': int(s['count'] or 0), 'revenue': Decimal(str(s['revenue'] or 0))}
        for s in services_qs
    ]

    products_qs = (
        invoice_items.filter(content_type__model='product')
        .values('object_id')
        .annotate(count=Sum('quantity'), revenue=Sum('total_price'), description=Max('description'))
        .order_by('-count')[:20]
    )
    top_products = [
        {'name': p['description'] or f'Product #{p["object_id"]}', 'count': int(p['count'] or 0), 'revenue': Decimal(str(p['revenue'] or 0))}
        for p in products_qs
    ]

    memberships_qs = (
        invoice_items.filter(content_type__model='membership')
        .values('object_id')
        .annotate(count=Sum('quantity'), revenue=Sum('total_price'), description=Max('description'))
        .order_by('-count')[:20]
    )
    top_memberships = [
        {'name': m['description'] or f'Membership #{m["object_id"]}', 'count': int(m['count'] or 0), 'revenue': Decimal(str(m['revenue'] or 0))}
        for m in memberships_qs
    ]

    packages_qs = (
        invoice_items.filter(content_type__model='package')
        .values('object_id')
        .annotate(count=Sum('quantity'), revenue=Sum('total_price'), description=Max('description'))
        .order_by('-count')[:20]
    )
    top_packages = [
        {'name': p['description'] or f'Package #{p["object_id"]}', 'count': int(p['count'] or 0), 'revenue': Decimal(str(p['revenue'] or 0))}
        for p in packages_qs
    ]

    # Avg Client Spend — calculated in Python to avoid DB-level division errors with NULL clients
    total_agg = invoices.aggregate(total=Sum('total_amount'), clients=Count('client', distinct=True))
    all_spend = (Decimal(str(total_agg['total'] or 0)) / max(total_agg['clients'] or 1, 1))
    
    female_agg = invoices.filter(client__gender__iexact='Female').aggregate(total=Sum('total_amount'), clients=Count('client', distinct=True))
    female_spend = (Decimal(str(female_agg['total'] or 0)) / max(female_agg['clients'] or 1, 1))
    
    male_agg = invoices.filter(client__gender__iexact='Male').aggregate(total=Sum('total_amount'), clients=Count('client', distinct=True))
    male_spend = (Decimal(str(male_agg['total'] or 0)) / max(male_agg['clients'] or 1, 1))
    
    unknown_agg = invoices.exclude(client__gender__iexact='Female').exclude(client__gender__iexact='Male').aggregate(total=Sum('total_amount'), clients=Count('client', distinct=True))
    unknown_spend = (Decimal(str(unknown_agg['total'] or 0)) / max(unknown_agg['clients'] or 1, 1))

    tax_agg = invoices.aggregate(cgst=Sum('cgst'), sgst=Sum('sgst'))
    tax_total = (tax_agg['cgst'] or 0) + (tax_agg['sgst'] or 0)
    revenue_without_tax = total_revenue - tax_total

    return Response({
        'revenue': total_revenue,
        'revenue_without_tax': revenue_without_tax,
        'target': monthly_target,
        'projected': projected,
        'new_clients': new_clients,
        'repeat_clients': repeat_clients,
        'total_clients': total_invoiced_clients,
        'inventory': {
            'amount': inv_amount,
            'count': inv_count
        },
        'weekday_counts': weekday_counts_list,
        'revenue_breakdown': revenue_breakdown,
        'balances': balances,
        'top_staff': top_staff,
        'top_services': top_services,
        'top_products': top_products,
        'top_memberships': top_memberships,
        'top_packages': top_packages,
        'avg_spend': {
            'all': Decimal(str(all_spend)),
            'female': Decimal(str(female_spend)),
            'male': Decimal(str(male_spend)),
            'unknown': Decimal(str(unknown_spend))
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_revenues(request):
    invoices = Invoice.objects.filter(status__in=['paid', 'partial'])
    invoices = _apply_security(request, invoices)
    
    # 6 months of monthly revenue — ExtractYear+ExtractMonth avoids TruncMonth crash on USE_TZ=False
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    if start_date_str:
        try:
            trend_start = datetime.strptime(start_date_str, '%Y-%m-%d')
        except:
            trend_start = datetime.now() - timedelta(days=180)
    else:
        trend_start = datetime.now() - timedelta(days=180)

    if end_date_str:
        try:
            trend_end = datetime.strptime(end_date_str, '%Y-%m-%d')
        except:
            trend_end = datetime.now()
    else:
        trend_end = datetime.now()

    six_months_ago = trend_start

    monthly_raw = (
        invoices
        .filter(created_at__gte=six_months_ago, created_at__lte=trend_end + timedelta(days=1))
        .annotate(year=ExtractYear('created_at'), month_num=ExtractMonth('created_at'))
        .values('year', 'month_num')
        .annotate(revenue=Sum('total_amount'))
        .order_by('year', 'month_num')
    )
    monthly_dict = {
        f"{calendar.month_abbr[item['month_num']]}-{item['year']}": Decimal(str(item['revenue'] or 0))
        for item in monthly_raw
    }
    monthly_data = []
    curr_m = six_months_ago
    target_end_m = trend_end.replace(day=1)
    months_keys = []
    while curr_m.replace(day=1) <= target_end_m:
        months_keys.append(f"{calendar.month_abbr[curr_m.month]}-{curr_m.year}")
        nm = curr_m.month + 1
        ny = curr_m.year
        if nm > 12:
            nm = 1
            ny += 1
        curr_m = curr_m.replace(year=ny, month=nm, day=1)
        if len(months_keys) > 24: # safety break
            break

    for mk in months_keys:
        monthly_data.append({'month': mk, 'revenue': monthly_dict.get(mk, 0)})
    
    # Daily for selected period
    invoices_period = _apply_dates(request, invoices, 'created_at')
    daily = invoices_period.annotate(day=Cast('created_at', DateField())).values('day').annotate(revenue=Sum('total_amount')).order_by('day')
    daily_dict = {item['day'].strftime('%Y-%m-%d') if hasattr(item['day'], 'strftime') else str(item['day']): Decimal(str(item['revenue'] or 0)) for item in daily if item['day']}
    
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    daily_data = []
    if start_date_str and end_date_str:
        try:
            s_d = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            e_d = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if (e_d - s_d).days <= 366:
                curr = s_d
                while curr <= e_d:
                    ds = curr.strftime('%Y-%m-%d')
                    daily_data.append({'day': ds, 'revenue': daily_dict.get(ds, 0)})
                    curr += timedelta(days=1)
            else:
                daily_data = [{'day': k, 'revenue': v} for k, v in daily_dict.items()]
        except Exception:
            daily_data = [{'day': k, 'revenue': v} for k, v in daily_dict.items()]
    else:
        daily_data = [{'day': k, 'revenue': v} for k, v in daily_dict.items()]
    
    # Hourly across the selected period
    hourly = invoices_period.annotate(hour=ExtractHour('created_at')).values('hour').annotate(revenue=Sum('total_amount')).order_by('hour')
    hourly_dict = {item['hour']: Decimal(str(item['revenue'] or 0)) for item in hourly if item['hour'] is not None}
    hourly_data = [{'hour': f"{h:02d}:00", 'revenue': hourly_dict.get(h, 0)} for h in range(24)]

    return Response({
        'monthly': monthly_data,
        'daily': daily_data,
        'hourly': hourly_data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_clients(request):
    clients = Client.objects.all()
    clients = _apply_security(request, clients)
    
    # 6 Months Trend — use ExtractYear+ExtractMonth (safe with USE_TZ=False)
    # 6 Months Trend - ignore start_date to always show full trend (like revenues)
    now = datetime.now()
    trend_start = now - timedelta(days=180)
    trend_end = now


    six_months_ago = trend_start

    invoices = Invoice.objects.filter(status__in=['paid', 'partial'], created_at__gte=six_months_ago, created_at__lte=trend_end + timedelta(days=1)).select_related('client')
    invoices = _apply_security(request, invoices)

    monthly_raw = (
        invoices
        .annotate(year=ExtractYear('created_at'), month_num=ExtractMonth('created_at'))
        .values('year', 'month_num', 'client__gender')
        .annotate(revenue=Sum('total_amount'), count=Count('client', distinct=True))
        .order_by('year', 'month_num')
    )

    trends = {}
    curr_m = six_months_ago
    target_end_m = trend_end.replace(day=1)
    months_keys = []
    while curr_m.replace(day=1) <= target_end_m:
        months_keys.append(f"{calendar.month_abbr[curr_m.month]}-{curr_m.year}")
        nm = curr_m.month + 1
        ny = curr_m.year
        if nm > 12:
            nm = 1
            ny += 1
        curr_m = curr_m.replace(year=ny, month=nm, day=1)
        if len(months_keys) > 24: # safety break
            break

    for mk in months_keys:
        trends[mk] = {
            'female': {'revenue': 0, 'count': 0, 'new': 0, 'repeat': 0}, 
            'male': {'revenue': 0, 'count': 0, 'new': 0, 'repeat': 0}, 
            'unknown': {'revenue': 0, 'count': 0, 'new': 0, 'repeat': 0}
        }

    for item in monthly_raw:
        m = f"{calendar.month_abbr[item['month_num']]}-{item['year']}"
        if m not in trends:
            trends[m] = {
                'female': {'revenue': 0, 'count': 0, 'new': 0, 'repeat': 0}, 
                'male': {'revenue': 0, 'count': 0, 'new': 0, 'repeat': 0}, 
                'unknown': {'revenue': 0, 'count': 0, 'new': 0, 'repeat': 0}
            }

        g = (item['client__gender'] or '').lower()
        if g == 'female':
            trends[m]['female']['revenue'] += Decimal(str(item['revenue'] or 0))
            trends[m]['female']['count'] += item['count']
        elif g == 'male':
            trends[m]['male']['revenue'] += Decimal(str(item['revenue'] or 0))
            trends[m]['male']['count'] += item['count']
        else:
            trends[m]['unknown']['revenue'] += Decimal(str(item['revenue'] or 0))
            trends[m]['unknown']['count'] += item['count']

    # Monthly footfall matrix
    invoices_period = _apply_dates(request, invoices, 'created_at')
    
    start_date = request.GET.get('start_date', '2000-01-01')
    end_date = request.GET.get('end_date', '2099-12-31')
    
    invoiced_clients = clients.filter(id__in=invoices_period.values('client').distinct())
    
    female_invoiced = invoiced_clients.filter(gender__iexact='Female')
    male_invoiced = invoiced_clients.filter(gender__iexact='Male')
    
    female_total = female_invoiced.count()
    female_new = female_invoiced.filter(created_at__date__gte=start_date, created_at__date__lte=end_date).count()
    female_repeat = female_total - female_new
    
    male_total = male_invoiced.count()
    male_new = male_invoiced.filter(created_at__date__gte=start_date, created_at__date__lte=end_date).count()
    male_repeat = male_total - male_new

    unknown_invoiced = invoiced_clients.exclude(gender__iexact='Female').exclude(gender__iexact='Male')
    unknown_total = unknown_invoiced.count()
    unknown_new = unknown_invoiced.filter(created_at__date__gte=start_date, created_at__date__lte=end_date).count()
    unknown_repeat = unknown_total - unknown_new

    footfall = {
        'new': {'female': female_new, 'male': male_new, 'unknown': unknown_new, 'total': female_new + male_new + unknown_new},
        'repeat': {'female': female_repeat, 'male': male_repeat, 'unknown': unknown_repeat, 'total': female_repeat + male_repeat + unknown_repeat},
        'total': {'female': female_total, 'male': male_total, 'unknown': unknown_total, 'total': female_total + male_total + unknown_total}
    }
    
    monthly_stats = invoices.annotate(
        year=ExtractYear('created_at'), 
        month_num=ExtractMonth('created_at'),
        client_year=ExtractYear('client__created_at'),
        client_month=ExtractMonth('client__created_at')
    ).values('year', 'month_num').annotate(
        total_invoices=Count('id', distinct=True),
        member_invoices=Count('id', filter=Q(client__memberships__is_active=True), distinct=True),
        new_clients=Count('client', filter=Q(client_year=F('year'), client_month=F('month_num')), distinct=True),
        total_clients=Count('client', distinct=True)
    )
    
    monthly_breakdown = {}
    for mk in months_keys:
        monthly_breakdown[mk] = {'new': 0, 'repeat': 0, 'member': 0, 'non_member': 0}
        
    for stat in monthly_stats:
        m = f"{calendar.month_abbr[stat['month_num']]}-{stat['year']}"
        if m in monthly_breakdown:
            monthly_breakdown[m]['new'] = stat['new_clients']
            monthly_breakdown[m]['repeat'] = stat['total_clients'] - stat['new_clients']
            monthly_breakdown[m]['member'] = stat['member_invoices']
            monthly_breakdown[m]['non_member'] = stat['total_invoices'] - stat['member_invoices']
            
    # Gender-specific trends (New vs Repeat)
    gender_stats = invoices.annotate(
        year=ExtractYear('created_at'), 
        month_num=ExtractMonth('created_at'),
        client_year=ExtractYear('client__created_at'),
        client_month=ExtractMonth('client__created_at')
    ).values('year', 'month_num', 'client__gender').annotate(
        new_clients=Count('client', filter=Q(client_year=F('year'), client_month=F('month_num')), distinct=True),
        total_clients=Count('client', distinct=True)
    )
    
    for stat in gender_stats:
        m = f"{calendar.month_abbr[stat['month_num']]}-{stat['year']}"
        if m in trends:
            g = (stat['client__gender'] or '').lower()
            if g not in ['female', 'male']:
                g = 'unknown'
            
            trends[m][g]['new'] += stat['new_clients']
            trends[m][g]['repeat'] += stat['total_clients'] - stat['new_clients']

    # Daily footfall
    from django.db.models.functions import TruncDate
    daily_footfall_qs = (
        invoices_period
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('client', distinct=True))
        .order_by('date')
    )
    daily_footfall = [{'day': d['date'].strftime('%Y-%m-%d'), 'count': d['count']} for d in daily_footfall_qs]

    return Response({
        'trends': trends,
        'footfall': footfall,
        'monthly_breakdown': monthly_breakdown,
        'daily_footfall': daily_footfall
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_finance(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Originally this just fetched 6 months unconditionally. We should ideally respect dates, 
    # but let's stick to the 7-month approach they had to not break existing logic if they rely on it.
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    if start_date_str:
        try:
            trend_start = datetime.strptime(start_date_str, '%Y-%m-%d')
        except:
            trend_start = datetime.now() - timedelta(days=180)
    else:
        trend_start = datetime.now() - timedelta(days=180)

    if end_date_str:
        try:
            trend_end = datetime.strptime(end_date_str, '%Y-%m-%d')
        except:
            trend_end = datetime.now()
    else:
        trend_end = datetime.now()

    six_months_ago = trend_start

    invoices = Invoice.objects.filter(status__in=['paid', 'partial'], created_at__gte=six_months_ago, created_at__lte=trend_end + timedelta(days=1))
    invoices = _apply_security(request, invoices)

    items = InvoiceItem.objects.filter(invoice__in=invoices).select_related('content_type')
    
    monthly_raw = (
        items
        .annotate(year=ExtractYear('invoice__created_at'), month_num=ExtractMonth('invoice__created_at'))
        .values('year', 'month_num', 'content_type__model')
        .annotate(revenue=Sum('total_price'), count=Count('id'))
        .order_by('year', 'month_num')
    )

    sources = {}
    curr_m = six_months_ago
    target_end_m = trend_end.replace(day=1)
    months_keys = []
    while curr_m.replace(day=1) <= target_end_m:
        months_keys.append(f"{calendar.month_abbr[curr_m.month]}-{curr_m.year}")
        nm = curr_m.month + 1
        ny = curr_m.year
        if nm > 12:
            nm = 1
            ny += 1
        curr_m = curr_m.replace(year=ny, month=nm, day=1)
        if len(months_keys) > 24: # safety break
            break

    for mk in months_keys:
        sources[mk] = {
            'services': {'revenue': 0, 'count': 0},
            'products': {'revenue': 0, 'count': 0},
            'memberships': {'revenue': 0, 'count': 0},
            'packages': {'revenue': 0, 'count': 0},
            'value_cards': {'revenue': 0, 'count': 0},
            'advances': {'revenue': 0, 'count': 0}
        }

    for item in monthly_raw:
        m = f"{calendar.month_abbr[item['month_num']]}-{item['year']}"
        if m not in sources:
            continue

        model = item['content_type__model']
        rev = Decimal(str(item['revenue'] or 0))
        cnt = item['count'] or 0
        
        if model == 'servicemaster': 
            sources[m]['services']['revenue'] += rev
            sources[m]['services']['count'] += cnt
        elif model == 'product': 
            sources[m]['products']['revenue'] += rev
            sources[m]['products']['count'] += cnt
        elif model == 'membership': 
            sources[m]['memberships']['revenue'] += rev
            sources[m]['memberships']['count'] += cnt
        elif model == 'package': 
            sources[m]['packages']['revenue'] += rev
            sources[m]['packages']['count'] += cnt
        elif model == 'valuecard':
            sources[m]['value_cards']['revenue'] += rev
            sources[m]['value_cards']['count'] += cnt

    # Advance Payments
    # Need to apply security if possible, using staff__center or invoice__center
    advances_qs = AdvancePayment.objects.filter(created_at__gte=six_months_ago, created_at__lte=trend_end + timedelta(days=1))
    
    # We try to scope by center if center_id is present
    user = request.user
    perms = getattr(user.role, 'permissions', {}) or {}
    is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
    center_id = request.GET.get('center_id')
    if center_id and center_id != 'null':
        # advances might not have center directly, but their invoice does, or staff does
        advances_qs = advances_qs.filter(Q(invoice__center_id=center_id) | Q(staff__center_id=center_id))
    elif not is_owner and not perms.get('all_centers', False):
        if user.centers.exists():
            advances_qs = advances_qs.filter(Q(invoice__center__in=user.centers.all()) | Q(staff__center__in=user.centers.all()))
        elif hasattr(user, 'center') and user.center:
            advances_qs = advances_qs.filter(Q(invoice__center=user.center) | Q(staff__center=user.center))

    adv_raw = (
        advances_qs
        .annotate(year=ExtractYear('created_at'), month_num=ExtractMonth('created_at'))
        .values('year', 'month_num')
        .annotate(revenue=Sum('amount'), count=Count('id'))
        .order_by('year', 'month_num')
    )

    for item in adv_raw:
        m = f"{calendar.month_abbr[item['month_num']]}-{item['year']}"
        if m in sources:
            sources[m]['advances']['revenue'] += Decimal(str(item['revenue'] or 0))
            sources[m]['advances']['count'] += item['count'] or 0

    return Response(sources)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_staff(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    if start_date_str:
        try:
            trend_start = datetime.strptime(start_date_str, '%Y-%m-%d')
        except:
            trend_start = datetime.now() - timedelta(days=180)
    else:
        trend_start = datetime.now() - timedelta(days=180)

    if end_date_str:
        try:
            trend_end = datetime.strptime(end_date_str, '%Y-%m-%d')
        except:
            trend_end = datetime.now()
    else:
        trend_end = datetime.now()

    six_months_ago = trend_start


    logs = ServiceLog.objects.filter(invoice__status__in=['paid', 'partial'], date__gte=six_months_ago.date(), date__lte=trend_end.date()).select_related('staff', 'invoice', 'invoice__client')
    # ServiceLog has no direct 'center' FK — scope via staff__center
    user = request.user
    role = getattr(user, 'role', None)
    perms = getattr(role, 'permissions', {}) if role else {}
    is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
    if not is_owner and not perms.get('all_centers', False):
        if user.centers.exists():
            logs = logs.filter(staff__center__in=user.centers.all())
        elif hasattr(user, 'center') and user.center:
            logs = logs.filter(staff__center=user.center)
    center_id = request.GET.get('center_id')
    if center_id and center_id != 'null':
        logs = logs.filter(staff__center_id=center_id)

    # Trends: group by year+month on DateField — safe with USE_TZ=False
    monthly_raw = (
        logs
        .annotate(year=ExtractYear('date'), month_num=ExtractMonth('date'))
        .values('year', 'month_num')
        .annotate(revenue=Sum('price'))
        .order_by('year', 'month_num')
    )
    trends_dict = {
        f"{calendar.month_abbr[item['month_num']]}-{item['year']}": Decimal(str(item['revenue'] or 0))
        for item in monthly_raw
    }
    trends = []
    curr_m = six_months_ago
    target_end_m = trend_end.replace(day=1)
    months_keys = []
    while curr_m.replace(day=1) <= target_end_m:
        months_keys.append(f"{calendar.month_abbr[curr_m.month]}-{curr_m.year}")
        nm = curr_m.month + 1
        ny = curr_m.year
        if nm > 12:
            nm = 1
            ny += 1
        curr_m = curr_m.replace(year=ny, month=nm, day=1)
        if len(months_keys) > 24: # safety break
            break

    for mk in months_keys:
        trends.append({'month': mk, 'revenue': trends_dict.get(mk, 0)})
    
    # Table (for period)
    logs_period = _apply_dates(request, logs, 'date', is_datetime=False)
    staff_data = logs_period.values('staff__first_name', 'staff__last_name').annotate(
        revenue=Sum('price'), clients=Count('invoice__client', distinct=True)
    ).order_by('-revenue')
    
    table = []
    for s in staff_data:
        name = f"{s['staff__first_name']} {s['staff__last_name'] or ''}".strip()
        rev = Decimal(str(s['revenue'] or 0))
        clients = s['clients']
        avg = rev / clients if clients > 0 else 0
        table.append({
            'name': name,
            'revenue': rev,
            'clients': clients,
            'avg': avg
        })
        
    return Response({
        'trends': trends,
        'table': table
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_services_products(request):
    invoices = Invoice.objects.filter(status__in=['paid', 'partial'])
    invoices = _apply_security(request, invoices)
    invoices = _apply_dates(request, invoices, 'created_at')

    # Use DB-level aggregation instead of Python iteration to avoid N+1 queries
    from django.db.models import F as DbF
    items_qs = (
        InvoiceItem.objects
        .filter(invoice__in=invoices)
        .select_related('content_type')
    )

    services_raw = (
        items_qs.filter(content_type__app_label='services')
        .values(cat=DbF('description'))  # use description as category proxy
        .annotate(count=Sum('quantity'), revenue=Sum('total_price'))
        .order_by('-revenue')
    )
    # Re-aggregate by service category using content_type model name
    from billing.models import InvoiceItem as II
    from django.contrib.contenttypes.models import ContentType
    try:
        svc_ct = ContentType.objects.get(app_label='services', model='servicemaster')
        prod_ct = ContentType.objects.get(app_label='inventory', model='product')
    except ContentType.DoesNotExist:
        return Response({'services': [], 'products': []})

    # Services — group by object_id
    svc_agg = (
        InvoiceItem.objects.filter(invoice__in=invoices, content_type=svc_ct)
        .values('object_id')
        .annotate(count=Sum('quantity'), revenue=Sum('total_price'))
        .order_by('-revenue')
    )
    from services.models import ServiceMaster
    svc_map = ServiceMaster.objects.in_bulk([s['object_id'] for s in svc_agg if s['object_id']])
    services_list = []
    for s in svc_agg:
        oid = s['object_id']
        name = svc_map[oid].name if oid and oid in svc_map else 'Unknown'
        services_list.append({'name': name, 'count': int(s['count'] or 0), 'revenue': Decimal(str(s['revenue'] or 0))})

    # Products — group by object_id
    prod_agg = (
        InvoiceItem.objects.filter(invoice__in=invoices, content_type=prod_ct)
        .values('object_id')
        .annotate(count=Sum('quantity'), revenue=Sum('total_price'))
        .order_by('-revenue')
    )
    from inventory.models import Product
    prod_map = Product.objects.in_bulk([p['object_id'] for p in prod_agg if p['object_id']])
    products_list = []
    for p in prod_agg:
        oid = p['object_id']
        name = prod_map[oid].name if oid and oid in prod_map else 'Unknown'
        products_list.append({'name': name, 'count': int(p['count'] or 0), 'revenue': Decimal(str(p['revenue'] or 0))})

    return Response({
        'services': services_list,
        'products': products_list
    })
