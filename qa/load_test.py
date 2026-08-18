#!/usr/bin/env python
"""Precise 15,000-request concurrent load test against the POS backend.

150 concurrent workers, every endpoint family hit simultaneously (dashboards,
lists, reports, billing writes, appointment writes, checkout, chat, audit).
Exactly TOTAL_REQUESTS requests are issued (default 15,000). Login requests are
counted separately.

Usage:
    python qa/load_test.py --base http://127.0.0.1:8000 \
        --total 15000 --workers 150 --out qa/load_test_report.json
"""
import argparse
import json
import random
import statistics
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests

# ── weighted task mix: (weight, method, path_builder, payload_builder) ────────
# path_builder(ctx) -> str, payload_builder(ctx) -> dict|None
def _center(ctx):
    return random.choice(ctx['center_ids'])

def _client(ctx):
    return random.choice(ctx['client_ids'])

def _invoice(ctx):
    return random.choice(ctx['invoice_ids'])

TASKS = [
    # read-heavy
    (7, 'GET', lambda c: f"/salon_admin/api/dashboard/summary/?center_id={_center(c)}", None),
    (7, 'GET', lambda c: f'/billing/invoices/?center={_center(c)}&page=1&page_size=20', None),
    (6, 'GET', lambda c: f'/appointments/api/appointments/?center={_center(c)}&page=1&page_size=20', None),
    (5, 'GET', lambda c: '/clients/api/clients/?page=1&page_size=20', None),
    (5, 'GET', lambda c: f'/staff/api/members/?center={_center(c)}&page=1&page_size=20', None),
    (4, 'GET', lambda c: f'/inventory/api/products/?center={_center(c)}&page=1&page_size=20', None),
    (4, 'GET', lambda c: f'/finance/api/register_summary/?center_id={_center(c)}', None),
    (4, 'GET', lambda c: '/services/api/master/', None),
    (3, 'GET', lambda c: f"/salon_admin/api/dashboard/revenues/?center_id={_center(c)}", None),
    (3, 'GET', lambda c: f'/finance/api/reports/tax/?center_id={_center(c)}', None),
    (3, 'GET', lambda c: f'/finance/api/reports/staff-performance/?center_id={_center(c)}', None),
    (2, 'GET', lambda c: f'/inventory/api/low_stock/?center={_center(c)}', None),
    (2, 'GET', lambda c: '/accounts/api/chat/users/', None),
    (2, 'GET', lambda c: '/audit_logs/logs/?page=1&page_size=20', None),
    (2, 'GET', lambda c: f'/billing/invoices/{_invoice(c)}/', None),
    (2, 'GET', lambda c: f'/clients/api/clients/{_client(c)}/', None),
    (2, 'GET', lambda c: '/marketing/api/promotions/', None),
    (1, 'GET', lambda c: '/finance/api/daily-closing/', None),
    (1, 'GET', lambda c: f'/finance/api/detailed_revenues/?center_id={_center(c)}', None),
    (1, 'GET', lambda c: f'/finance/api/reports/multi_salon/balances/?center_id={_center(c)}', None),
    (1, 'GET', lambda c: f'/salon_admin/api/dashboard/clients/?center_id={_center(c)}', None),
    (1, 'GET', lambda c: f'/salon_admin/api/dashboard/finance/?center_id={_center(c)}', None),
    (1, 'GET', lambda c: f'/salon_admin/api/dashboard/staff/?center_id={_center(c)}', None),
    (1, 'GET', lambda c: f'/salon_admin/api/dashboard/services_products/?center_id={_center(c)}', None),
    # writes
    (3, 'POST', lambda c: '/billing/invoices/', lambda c: {
        'client': _client(c), 'center': _center(c),
        'subtotal': 350, 'total_amount': 350, 'status': 'draft',
        'items': [{'description': 'Load Service', 'unit_price': 350,
                   'quantity': 1, 'tax_percentage': 18, 'total_price': 350}],
    }),
    (2, 'POST', lambda c: '/appointments/api/appointments/', lambda c: {
        'center': _center(c),
        'client_phone': f'99{random.randint(10000000, 99999999)}',
        'client_name': f'Load {random.randint(1000, 9999)}',
        'date': '2026-08-25',
        'start_time': f'{random.randint(9, 19)}:00',
        'status': 'Scheduled',
    }),
    (2, 'POST', lambda c: '/clients/api/clients/', lambda c: {
        'first_name': 'Load', 'last_name': f'{random.randint(1000, 999999)}',
        'phone': f'97{random.randint(10000000, 99999999)}',
        'gender': random.choice(['female', 'male']), 'center': _center(c),
    }),
    (1, 'POST', lambda c: '/finance/api/petty-cash/', lambda c: {
        'center': _center(c), 'description': f'Load expense {random.randint(1000, 999999)}',
        'amount': random.randint(10, 500),
    }),
    (1, 'POST', lambda c: '/inventory/api/products/checkout/', lambda c: {
        'items': [{'product_id': random.choice(c['product_ids']), 'quantity': 1}],
        'center_id': _center(c),
    }),
    (1, 'PATCH', lambda c: f"/billing/invoices/{_invoice(c)}/", lambda c: {
        'notes': f'load note {random.randint(1000, 999999)}'}),
    (1, 'POST', lambda c: '/staff/api/designations/', lambda c: {
        'name': f'Load Desg {random.randint(1000, 999999)}'}),
]

WEIGHTS = [t[0] for t in TASKS]


def pick_task():
    return random.choices(TASKS, weights=WEIGHTS, k=1)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:8000')
    ap.add_argument('--total', type=int, default=15000)
    ap.add_argument('--workers', type=int, default=150)
    ap.add_argument('--out', default='qa/load_test_report.json')
    args = ap.parse_args()

    base = args.base.rstrip('/')

    # ── shared state ─────────────────────────────────────────────────────────
    state = {'center_ids': [], 'client_ids': [], 'invoice_ids': [], 'product_ids': []}
    counter_lock = threading.Lock()
    issued = [0]
    stats_lock = threading.Lock()
    stats = {'requests': 0, 'errors': 0, 'status_counts': {}, 'latencies': [],
             'errors_by_url': {}}
    t0 = time.time()

    _discover_lock = threading.Lock()
    _discover_done = threading.Event()

    def discover(session):
        if not _discover_done.wait(timeout=30):
            raise RuntimeError('timed out waiting for ID discovery')
        if not state['invoice_ids']:
            raise RuntimeError('ID discovery produced no data')

    def run_discovery(session):
        if not _discover_lock.acquire(blocking=False):
            return
        try:
            def ids_of(resp):
                data = resp.json()
                if isinstance(data, dict):
                    data = data.get('results', [])
                return [x['id'] for x in data if isinstance(x, dict)] or [1]
            r = session.get(f'{base}/salon_admin/api/centers/', timeout=30)
            state['center_ids'] = ids_of(r)
            r = session.get(f'{base}/clients/api/clients/?page=1&page_size=50', timeout=30)
            state['client_ids'] = ids_of(r)
            r = session.get(f'{base}/billing/invoices/?page=1&page_size=50', timeout=30)
            state['invoice_ids'] = ids_of(r)
            r = session.get(f'{base}/inventory/api/products/?page=1&page_size=50', timeout=30)
            state['product_ids'] = ids_of(r)
            _discover_done.set()
        finally:
            _discover_lock.release()

    def worker(wid):
        s = requests.Session()
        tok = None
        for attempt in range(5):
            try:
                r = s.post(f'{base}/accounts/api/login/',
                           json={'username': 'admin@chilli.potato', 'password': 'admin1234'},
                           timeout=30)
                if r.status_code == 200:
                    tok = (r.json() or {}).get('token')
                    if tok:
                        break
                time.sleep(0.5 * (attempt + 1))
            except Exception:
                time.sleep(0.5 * (attempt + 1))
        if not tok:
            with stats_lock:
                stats['errors'] += 1
                stats['errors_by_url']['LOGIN'] = stats['errors_by_url'].get('LOGIN', 0) + 1
            return
        s.headers['Authorization'] = f'Token {tok}'

        try:
            run_discovery(s)
            discover(s)
        except Exception as e:
            with stats_lock:
                stats['errors'] += 1
                stats['errors_by_url'][f'DISCOVER {e}'] = stats['errors_by_url'].get(f'DISCOVER {e}', 0) + 1
            return

        while True:
            with counter_lock:
                if issued[0] >= args.total:
                    return
                issued[0] += 1
            _, method, path_fn, payload_fn = pick_task()
            path = path_fn(state)
            payload = payload_fn(state) if payload_fn else None
            t_start = time.time()
            try:
                if method == 'GET':
                    r = s.get(base + path, timeout=60)
                elif method == 'PATCH':
                    r = s.patch(base + path, json=payload, timeout=60)
                else:
                    r = s.post(base + path, json=payload, timeout=60)
                ok = r.status_code < 500
            except Exception as e:
                ok = False
                r = None
                err = f'{type(e).__name__}: {e}'[:120]
            lat = (time.time() - t_start) * 1000
            with stats_lock:
                stats['requests'] += 1
                stats['latencies'].append(lat)
                if not ok:
                    stats['errors'] += 1
                    key = f'{method} {path.split("?")[0]}'
                    stats['errors_by_url'][key] = stats['errors_by_url'].get(key, 0) + 1
                else:
                    sc = r.status_code
                    stats['status_counts'][sc] = stats['status_counts'].get(sc, 0) + 1
            if not ok:
                pass

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(worker, range(args.workers)))

    elapsed = time.time() - t0
    lats = sorted(stats['latencies'])
    p = lambda q: lats[int(len(lats) * q)] if lats else 0
    report = {
        'total_requests': stats['requests'],
        'errors': stats['errors'],
        'error_rate_pct': round(100 * stats['errors'] / max(stats['requests'], 1), 2),
        'duration_s': round(elapsed, 2),
        'rps': round(stats['requests'] / max(elapsed, 0.001), 1),
        'concurrent_workers': args.workers,
        'latency_ms': {
            'min': round(min(lats), 1) if lats else 0,
            'p50': round(p(0.50), 1), 'p75': round(p(0.75), 1),
            'p90': round(p(0.90), 1), 'p95': round(p(0.95), 1),
            'p99': round(p(0.99), 1), 'max': round(max(lats), 1) if lats else 0,
        },
        'status_counts': stats['status_counts'],
        'errors_by_url': stats['errors_by_url'],
    }
    with open(args.out, 'w') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    ok = report['errors'] == 0
    print('LOAD TEST:', 'PASS — zero errors' if ok else f'FAIL — {report["errors"]} errors')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
