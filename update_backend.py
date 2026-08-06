import os

with open('backend/salon_admin/dashboard_endpoints.py', 'a', encoding='utf-8') as f:
    f.write('''
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_services_products(request):
    invoices = Invoice.objects.filter(status__in=['paid', 'partial'])
    invoices = _apply_security(request, invoices)
    invoices = _apply_dates(request, invoices, 'created_at')

    # Get all items from these invoices
    items = InvoiceItem.objects.filter(invoice__in=invoices).select_related('content_type')

    services_dict = {}
    products_dict = {}

    for item in items:
        ctype = item.content_type
        if not ctype:
            continue
            
        obj = item.content_object
        if not obj:
            continue
            
        revenue = float(item.unit_price) * int(item.quantity)
        count = int(item.quantity)

        if ctype.app_label == 'services':
            cat = getattr(obj, 'category', '') or 'Uncategorized'
            if cat not in services_dict:
                services_dict[cat] = {'name': cat, 'count': 0, 'revenue': 0}
            services_dict[cat]['count'] += count
            services_dict[cat]['revenue'] += revenue
            
        elif ctype.app_label == 'inventory':
            brand = getattr(obj, 'brand', '')
            if not brand:
                brand = getattr(obj, 'category', '')
            if not brand:
                brand = 'Unbranded'
                
            if brand not in products_dict:
                products_dict[brand] = {'name': brand, 'count': 0, 'revenue': 0}
            products_dict[brand]['count'] += count
            products_dict[brand]['revenue'] += revenue

    services_list = sorted(list(services_dict.values()), key=lambda x: x['revenue'], reverse=True)
    products_list = sorted(list(products_dict.values()), key=lambda x: x['revenue'], reverse=True)

    return Response({
        'services': services_list,
        'products': products_list
    })
''')

with open('backend/salon_admin/urls.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'dashboard_finance, dashboard_staff',
    'dashboard_finance, dashboard_staff, dashboard_services_products'
)
content = content.replace(
    "path('api/dashboard/staff/', dashboard_staff, name='dashboard-staff'),",
    "path('api/dashboard/staff/', dashboard_staff, name='dashboard-staff'),\n    path('api/dashboard/services_products/', dashboard_services_products, name='dashboard-services-products'),"
)

with open('backend/salon_admin/urls.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Backend endpoints configured successfully.')
