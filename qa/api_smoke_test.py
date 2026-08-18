#!/usr/bin/env python
"""Exhaustive API smoke test for the Chilli Potato POS backend.

Hits every registered endpoint: CRUD for every resource, custom actions,
dashboard/report endpoints, mobile-app endpoints, plus an edge-case battery
(malformed input, bad pagination, bad dates, missing auth, injection-ish
strings, unknown IDs, wrong types).

Exit code 0 = no 5xx errors (bugs); warnings are listed but tolerated.
Run against a live server:
    python qa/api_smoke_test.py --base http://127.0.0.1:8000
"""
import argparse
import json
import sys
import time
import traceback
import random
PH = str(random.randint(100000, 999999))

import requests

PASS = 0
WARN = 1
FAIL = 2

results = []


def record(name, ok, status, extra=''):
    level = PASS if ok else FAIL
    results.append((name, level, status, extra))


class ApiTester:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.s = requests.Session()
        self.token = None
        self.ids = {}  # resource -> [ids]

    # ── helpers ─────────────────────────────────────────────────────────
    def login(self, email, password):
        r = self.s.post(f'{self.base}/accounts/api/login/',
                        json={'username': email, 'password': password}, timeout=30)
        data = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
        return r.status_code, data

    def auth(self, token):
        self.s.headers['Authorization'] = f'Token {token}'

    # ── resource CRUD helper ────────────────────────────────────────────
    def crud(self, label, list_path, create_payload, patch_payload=None,
             detail_pk=None, delete=True, list_expected=(200, 201)):
        # GET list
        st, body = self.req('GET', list_path, expected=list_expected, name=f'GET {label} list')
        # create
        st, body = self.req('POST', list_path, expected=(200, 201, 400),
                            json_body=create_payload, name=f'POST {label}')
        obj_id = None
        if st in (200, 201) and isinstance(body, dict):
            obj_id = body.get('id') or (body.get('data') or {}).get('id')
            if obj_id:
                self.ids.setdefault(label, []).append(obj_id)
        if obj_id is None:
            # try to find an id from the list response
            if isinstance(body, list) and body:
                obj_id = body[0].get('id')
            if obj_id is None and detail_pk:
                obj_id = detail_pk
        if obj_id is None:
            record(f'GET {label} detail', False, '-', 'no id available (create likely failed)')
        else:
            st, _ = self.req('GET', f'{list_path}{obj_id}/', expected=(200,), name=f'GET {label} detail')
            if patch_payload is not None:
                self.req('PATCH', f'{list_path}{obj_id}/', expected=(200,),
                         json_body=patch_payload, name=f'PATCH {label}')
            if delete:
                self.req('DELETE', f'{list_path}{obj_id}/', expected=(204, 200),
                         name=f'DELETE {label}')
        return obj_id

    # ── battery of edge cases ───────────────────────────────────────────
    def edge_cases(self, paths):
        for p in paths:
            # unknown id
            self.req('GET', f'{p}999999999/', expected=(404, 400), name=f'404 {p}unknown-id')
            # bad pagination
            self.req('GET', f'{p}?page=0', expected=(200, 400, 404), name=f'page0 {p}')
            self.req('GET', f'{p}?page=-1', expected=(200, 400, 404), name=f'pageneg {p}')
            self.req('GET', f'{p}?page=99999999', expected=(200, 404), name=f'pagehuge {p}')
            self.req('GET', f'{p}?page_size=100000', expected=(200, 400), name=f'pagesize-huge {p}')
            self.req('GET', f"{p}?search=%27%20OR%201%3D1--", expected=(200, 400), name=f'injection {p}')
            # bad date filters
            self.req('GET', f'{p}?start_date=not-a-date', expected=(200, 400), name=f'baddate {p}')
        # malformed JSON
        self.req('POST', '/billing/invoices/', expected=(400, 415),
                 data='{broken json', name='malformed JSON invoice',
                 headers_extra={'Content-Type': 'application/json'})

    def req(self, method, path, expected=(200, 201, 204), name=None,
            json_body=None, data=None, files=None, timeout=60, auth_required=True,
            headers_extra=None):
        name = name or f'{method} {path}'
        kwargs = {'timeout': timeout}
        if json_body is not None:
            kwargs['json'] = json_body
        if data is not None:
            kwargs['data'] = data
        if files is not None:
            kwargs['files'] = files
        if headers_extra:
            kwargs['headers'] = headers_extra
        t0 = time.time()
        try:
            r = self.s.request(method, self.base + path, **kwargs)
        except Exception as e:
            record(name, False, 'EXC', f'{type(e).__name__}: {e}')
            return None, None
        elapsed = time.time() - t0
        try:
            body = r.json()
        except Exception:
            body = r.text[:200]
        ok = r.status_code in expected
        record(name, ok, r.status_code,
               f'{elapsed*1000:.0f}ms' + ('' if ok else f' body={str(body)[:160]}'))
        return r.status_code, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8000')
    ap.add_argument('--fast', action='store_true', help='skip slow edge battery')
    args = ap.parse_args()

    t = ApiTester(args.base)

    print('== login ==')
    st, body = t.login('admin@chilli.potato', 'admin1234')
    ok = st == 200 and 'token' in (body or {})
    record('login admin', ok, st, str(body)[:100] if not ok else '')
    if not ok:
        print('FATAL: could not log in — is the server running and seeded?')
        sys.exit(2)
    t.auth(body['token'])

    # ── salon_admin ─────────────────────────────────────────────────────
    print('== salon_admin ==')
    center_id = t.crud('centers', '/salon_admin/api/centers/',
                       {'center_name': 'Smoke Test Center', 'phone': '98' + PH + '00',
                        'address': '1 Smoke St', 'region': 'Test'},
                       patch_payload={'display_name': 'Smoke Center Renamed'}, delete=False)
    t.crud('roles', '/salon_admin/api/roles/',
           {'name': 'SmokeRole', 'permissions': {'all_centers': False}},
           patch_payload={'description': 'smoke role'})

    for ep in ['summary', 'revenues', 'clients', 'finance', 'staff', 'services_products', '']:
        t.req('GET', f'/salon_admin/api/dashboard/{ep}', expected=(200,), name=f'dashboard/{ep or "index"}')
    t.req('GET', '/salon_admin/api/dashboard/revenues/?start_date=2026-01-01&end_date=2026-12-31',
          expected=(200,), name='dashboard/revenues dated')
    t.req('GET', '/salon_admin/api/dashboard/revenues/?start_date=garbage&end_date=garbage',
          expected=(200,), name='dashboard/revenues garbage dates')
    t.req('POST', '/salon_admin/api/centers/bulk-import/',
          files={'file': ('centers.csv', f'center_name,phone\nX,99{PH}777'.encode(), 'text/csv')},
          expected=(200, 201, 400), name='centers bulk-import csv')
    t.req('GET', '/salon_admin/api/centers/bulk-import-template/', expected=(200,), name='centers bulk template')

    # ── accounts ────────────────────────────────────────────────────────
    print('== accounts ==')
    t.req('GET', '/accounts/api/users/', expected=(200,), name='users list')
    t.req('GET', '/accounts/api/chat/users/', expected=(200,), name='chat users')
    t.req('GET', '/accounts/api/chat/unread/', expected=(200,), name='chat unread')
    t.req('GET', '/accounts/api/chat/messages/', expected=(200,), name='chat messages')
    t.req('GET', '/accounts/api/chat/reactions/', expected=(200,), name='chat reactions')
    st, body = t.req('POST', '/accounts/api/users/',
                     json_body={'email': 'smoketeam@test.com', 'full_name': 'Smoke Team',
                                'password': 'pass12345', 'phone': '98' + PH + '01'},
                     expected=(200, 201), name='create user')
    new_user_id = (body or {}).get('id')
    if new_user_id:
        t.req('PATCH', f'/accounts/api/users/{new_user_id}/', json_body={'phone': '98' + PH + '02'},
              expected=(200,), name='update user')
        t.req('DELETE', f'/accounts/api/users/{new_user_id}/', expected=(204, 200), name='delete user')
    t.req('POST', '/accounts/api/login/', json_body={'username': 'nobody@nowhere.com', 'password': 'x'},
          expected=(400,), name='login bad creds')

    # ── staff ───────────────────────────────────────────────────────────
    print('== staff ==')
    t.req('GET', '/staff/api/designations/', expected=(200,), name='designations list')
    t.req('GET', '/staff/api/members/', expected=(200,), name='members list')
    t.req('GET', '/staff/api/members/?center=1', expected=(200,), name='members by center')
    t.req('GET', '/staff/api/members/activity_feed/', expected=(200,), name='members activity feed')
    t.req('GET', '/staff/api/members/commission_report/?start_date=2026-01-01&end_date=2026-12-31', expected=(200, 400), name='commission report')
    t.req('GET', '/staff/api/members/incentive_report/?start_date=2026-01-01&end_date=2026-12-31', expected=(200, 400), name='incentive report')
    t.req('POST', '/staff/api/members/sync_transfers/', json_body={}, expected=(200, 201, 400), name='sync transfers')
    t.req('GET', '/staff/api/members/bulk_upload_template/', expected=(200,), name='members template')
    t.req('GET', '/staff/api/logs/', expected=(200,), name='service logs')
    t.req('GET', '/staff/api/consumptions/', expected=(200,), name='consumptions')
    t.req('GET', '/staff/api/reports/revenue/', expected=(200,), name='staff revenue report')
    t.req('GET', '/staff/api/reports/usage/', expected=(200,), name='staff usage report')
    t.req('GET', '/staff/api/reports/consumption/', expected=(200,), name='staff consumption report')
    staff_id = t.crud('staff', '/staff/api/members/',
                      {'first_name': 'SmokeStaff', 'designation': 'Manager',
                       'phone': '98' + PH + '03', 'center': center_id or 1,
                       'app_password': '1234'},
                      patch_payload={'last_name': 'Updated'}, delete=False)

    # staff mobile app
    t.req('POST', '/staff/api/app/login/',
          json_body={'phone': '98' + PH + '03', 'password': '1234'}, expected=(200, 400), name='staff app login')
    t.req('GET', '/staff/api/app/logs/', expected=(200, 400, 401), name='staff app logs')
    t.req('GET', '/staff/api/app/appointments/', expected=(200, 400, 401), name='staff app appointments')
    t.req('GET', '/staff/api/app/tools/', expected=(200, 400, 401), name='staff app tools')
    t.req('GET', '/staff/api/app/transfers/', expected=(200, 400, 401), name='staff app transfers')
    t.req('POST', '/staff/api/app/update_profile/', json_body={'first_name': 'Smoke'}, expected=(200, 400, 401),
          name='staff app update_profile')

    # ── clients ─────────────────────────────────────────────────────────
    print('== clients ==')
    client_id = t.crud('clients', '/clients/api/clients/',
                       {'first_name': 'Smoke', 'phone': '98' + PH + '04', 'gender': 'female',
                       'app_pin': '1234'},
                       patch_payload={'last_name': 'Client'}, delete=False)
    t.req('GET', '/clients/api/clients/?search=Smoke', expected=(200,), name='clients search')
    t.req('POST', '/clients/api/clients/bulk_upload/',
          files={'file': ('clients.csv', f'first_name,last_name,phone,gender\nBulk,One,98{PH}11,female'.encode(), 'text/csv')},
          expected=(200, 201, 400), name='clients bulk upload POST')
    st, body = t.req('POST', '/clients/api/app/login/',
                     json_body={'phone': '98' + PH + '04', 'pin': '1234'},
                     expected=(200, 400), name='client app login')
    if st == 200 and isinstance(body, dict) and body.get('auth_token'):
        t.s.headers['X-Client-Token'] = body['auth_token']
        t.req('GET', '/clients/api/app/data/', expected=(200,), name='client app data')
        t.req('POST', '/clients/api/app/update_profile/', json_body={'first_name': 'Smoke2'},
              expected=(200,), name='client app update_profile')
        t.req('POST', '/clients/api/app/contact/', json_body={'message': 'hello'},
              expected=(200, 201, 400), name='client app contact')
        t.s.headers.pop('X-Client-Token', None)

    # ── services ────────────────────────────────────────────────────────
    print('== services ==')
    svc_id = t.crud('service-master', '/services/api/master/',
                    {'name': 'Smoke Service', 'category': 'Hair', 'default_price': 999,
                     'duration_mins': 30, 'tax_percentage': 18},
                    patch_payload={'default_price': 1099}, delete=False)
    t.req('POST', '/services/api/master/bulk_upload/',
          files={'file': ('services.csv', b'name,category,default_price,duration_mins\nBulkSvc,Hair,500,30')},
          expected=(200, 201, 400), name='service bulk upload')
    t.req('GET', '/services/api/center/', expected=(200,), name='center services')
    t.req('POST', '/services/api/center/override/', json_body={'center': center_id or 1, 'service': svc_id or 1, 'price': 800}, expected=(200, 201, 400), name='center service override')

    # ── appointments ────────────────────────────────────────────────────
    print('== appointments ==')
    appt_id = t.crud('appointments', '/appointments/api/appointments/',
                     {'client_phone': '9800000005', 'client_name': 'Smoke Appt',
                      'date': '2026-08-20', 'start_time': '11:00', 'status': 'Scheduled',
                      'center': center_id or 1},
                     patch_payload={'status': 'Completed'}, delete=True)

    # ── inventory ───────────────────────────────────────────────────────
    print('== inventory ==')
    t.crud('vendors', '/inventory/api/vendors/',
           {'name': 'Smoke Vendor', 'phone': '98' + PH + '06', 'center': center_id or 1},
           delete=False)
    prod_id = t.crud('products', '/inventory/api/products/',
                     {'name': 'Smoke Product', 'category': 'Test', 'price': 100,
                      'current_stock': 10, 'center': center_id or 1},
                     patch_payload={'current_stock': 20}, delete=False)
    t.crud('lots', '/inventory/api/lots/',
           {'lot_number': 'SMK-1', 'net_price': 50, 'mrp': 100,
            'product': prod_id or 1}, delete=True)
    t.req('GET', '/inventory/api/low_stock/', expected=(200,), name='low stock')
    t.req('POST', '/inventory/api/products/audit/', json_body={'items': [{'product_id': prod_id or 1, 'quantity': 5}], 'center_id': center_id or 1}, expected=(200, 201, 400), name='product audit')
    t.req('GET', '/inventory/api/products/stock_history/?date=2026-08-18', expected=(200, 400), name='stock history')
    t.req('POST', '/inventory/api/products/checkout/', json_body={'items': [{'product_id': prod_id or 1, 'quantity': 2}], 'center_id': center_id or 1},
          expected=(200, 201, 400), name='product checkout')
    t.req('GET', '/inventory/api/products/bulk_upload_template/', expected=(200,), name='product template')
    t.req('GET', '/inventory/api/vendors/bulk_upload_template/', expected=(200,), name='vendor template')
    t.req('GET', '/inventory/api/purchase-orders/', expected=(200,), name='purchase orders')
    t.req('GET', '/inventory/api/stock-transactions/', expected=(200,), name='stock transactions')

    # ── marketing ───────────────────────────────────────────────────────
    print('== marketing ==')
    t.crud('promotions', '/marketing/api/promotions/',
           {'name': 'Smoke Promo', 'start_date': '2026-09-01', 'end_date': '2026-12-31',
            'discount_type': 'Percentage', 'discount_value': 10},
           patch_payload={'discount_value': 15}, delete=False)
    t.req('GET', '/marketing/api/promotions/usage_report/', expected=(200,), name='promo usage')
    t.req('GET', '/marketing/api/cards/', expected=(200,), name='value cards')
    t.req('GET', '/marketing/api/memberships/', expected=(200,), name='memberships')
    t.req('GET', '/marketing/api/packages/', expected=(200,), name='packages')
    t.req('GET', '/marketing/api/whatsapp/', expected=(200,), name='whatsapp list')
    t.req('POST', '/marketing/api/whatsapp/send_campaign/', json_body={'message': 'hi', 'clients': []},
          expected=(200, 201, 400), name='whatsapp campaign')

    # ── billing ─────────────────────────────────────────────────────────
    print('== billing ==')
    items = [{'description': 'Haircut', 'unit_price': 350, 'quantity': 1,
              'tax_percentage': 18, 'total_price': 350}]
    invoice_id = t.crud('invoices', '/billing/invoices/',
                        {'client': client_id or 1, 'center': center_id or 1,
                         'subtotal': 350, 'total_amount': 350, 'status': 'draft',
                         'items': items},
                        patch_payload={'notes': 'smoke note'}, delete=False)
    if invoice_id:
        t.req('POST', f'/billing/invoices/{invoice_id}/pay/',
              json_body={'payments': [{'amount': 350, 'payment_method': 'Cash'}]},
              expected=(200, 400), name='invoice pay')
    t.req('GET', '/billing/invoices/?status=paid', expected=(200,), name='invoices by status')
    t.req('GET', '/billing/invoices/?center=1&page=1', expected=(200,), name='invoices paged')
    t.crud('advances', '/billing/advances/',
           {'client': client_id or 1, 'amount': 100}, delete=False)
    t.req('GET', '/billing/change-logs/', expected=(200,), name='bill change logs')

    # ── finance ─────────────────────────────────────────────────────────
    print('== finance ==')
    t.crud('petty-cash', '/finance/api/petty-cash/',
           {'description': 'Smoke expense', 'amount': 50, 'center': center_id or 1},
           patch_payload={'amount': 60}, delete=True)
    t.req('GET', '/finance/api/daily-closing/', expected=(200,), name='daily closing')
    t.req('GET', '/finance/api/daily-closing/opening_balance/', expected=(200,), name='opening balance')
    t.req('GET', '/finance/api/shifts/', expected=(200,), name='shifts')
    t.req('GET', '/finance/api/rules/', expected=(200,), name='incentive rules')
    t.req('GET', '/finance/api/incentives/', expected=(200,), name='incentive configs')
    for ep in ['register_summary', 'monthly_sales', 'detailed_revenues', 'refunds',
               'procurement', 'export', 'export_multi_salon']:
        t.req('GET', f'/finance/api/{ep}/', expected=(200,), name=f'finance {ep}')
    for ep in ['tax', 'services', 'staff-performance', 'discounts', 'incentive-calculation',
               'multi_salon/balances', 'multi_salon/sales_export', 'multi_salon/categories',
               'multi_salon/drilldown/services', 'multi_salon/drilldown/products',
               'multi_salon/clients', 'multi_salon/staff']:
        t.req('GET', f'/finance/api/reports/{ep}/', expected=(200,), name=f'finance report {ep}')

    # ── audit logs ──────────────────────────────────────────────────────
    print('== audit logs ==')
    t.req('GET', '/audit_logs/logs/', expected=(200,), name='audit logs')

    # ── unauthenticated access ──────────────────────────────────────────
    print('== auth checks ==')
    old_headers = dict(t.s.headers)
    t.s.headers.pop('Authorization', None)
    for p in ['/billing/invoices/', '/staff/api/members/', '/accounts/api/users/',
              '/finance/api/daily-closing/']:
        st, _ = t.req('GET', p, expected=(401, 403), name=f'unauth {p}')
    t.s.headers.update(old_headers)

    # ── edge cases ──────────────────────────────────────────────────────
    if not args.fast:
        print('== edge cases ==')
        t.edge_cases(['/billing/invoices/', '/staff/api/members/', '/clients/api/clients/',
                      '/inventory/api/products/', '/appointments/api/appointments/'])

    # ── summary ─────────────────────────────────────────────────────────
    fails = [r for r in results if r[1] == FAIL]
    warns = [r for r in results if r[1] == WARN]
    print()
    print('=' * 78)
    print(f'TOTAL CHECKS: {len(results)}   FAILS: {len(fails)}   WARNS: {len(warns)}')
    print('=' * 78)
    if fails:
        print('FAILURES (real bugs / 5xx):')
        for name, _, status, extra in fails:
            print(f'  ✗ {name}  ->  HTTP {status}  {extra}')
    print('Slowest responses (>1500ms):')
    slow = sorted(results, key=lambda r: _ms(r[3]), reverse=True)[:10]
    for name, _, status, extra in slow:
        ms = _ms(extra)
        if ms > 1500:
            print(f'  🐢 {name}: {ms}ms (HTTP {status})')
    sys.exit(1 if fails else 0)


def _ms(extra):
    try:
        return int(extra.split('ms')[0])
    except Exception:
        return 0


if __name__ == '__main__':
    main()
