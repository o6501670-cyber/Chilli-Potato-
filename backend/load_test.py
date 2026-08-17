#!/usr/bin/env python3
"""Deterministic HTTP load runner for the POS API.

It sends an exact request count across representative read endpoints and reports
latency percentiles/status counts. Remote targets require --allow-remote so this
cannot accidentally stress production.
"""

import argparse
import collections
import concurrent.futures
import json
import math
import os
import statistics
import threading
import time
from urllib.parse import urlparse

import requests

DEFAULT_ENDPOINTS = [
    '/salon_admin/api/centers/',
    '/staff/api/members/',
    '/inventory/api/products/',
    '/billing/invoices/',
    '/appointments/api/appointments/',
    '/clients/api/clients/?page=1&page_size=50',
    '/services/api/master/',
    '/marketing/api/promotions/',
    '/finance/api/register_summary/?start_date=2026-08-01&end_date=2026-08-31',
]

_thread_local = threading.local()


def percentile(values, percentage):
    if not values:
        return 0.0
    index = max(0, math.ceil((percentage / 100) * len(values)) - 1)
    return sorted(values)[index]


def get_session():
    if not hasattr(_thread_local, 'session'):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=0)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        _thread_local.session = session
    return _thread_local.session


def request_once(base_url, endpoint, token, timeout):
    headers = {'Authorization': f'Token {token}'} if token else {}
    started = time.perf_counter()
    try:
        response = get_session().get(base_url + endpoint, headers=headers, timeout=timeout)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return endpoint, response.status_code, elapsed_ms, None
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return endpoint, 0, elapsed_ms, type(exc).__name__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--requests', type=int, default=15000)
    parser.add_argument('--concurrency', type=int, default=300)
    parser.add_argument('--timeout', type=float, default=15)
    parser.add_argument('--token', action='append', default=[])
    parser.add_argument('--endpoint', action='append', default=[])
    parser.add_argument('--allow-remote', action='store_true')
    parser.add_argument('--json-output')
    args = parser.parse_args()

    if args.requests < 1 or args.concurrency < 1:
        parser.error('--requests and --concurrency must be positive')
    args.concurrency = min(args.concurrency, args.requests)
    parsed = urlparse(args.url)
    if parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} and not args.allow_remote:
        parser.error('Remote targets require --allow-remote')

    tokens = args.token or [token for token in os.environ.get('LOAD_TEST_TOKENS', '').split(',') if token]
    endpoints = args.endpoint or DEFAULT_ENDPOINTS
    base_url = args.url.rstrip('/')

    started = time.perf_counter()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = (
            executor.submit(
                request_once,
                base_url,
                endpoints[index % len(endpoints)],
                tokens[index % len(tokens)] if tokens else '',
                args.timeout,
            )
            for index in range(args.requests)
        )
        for future in concurrent.futures.as_completed(list(futures)):
            results.append(future.result())
    duration = time.perf_counter() - started

    status_counts = collections.Counter(result[1] for result in results)
    error_counts = collections.Counter(result[3] for result in results if result[3])
    endpoint_results = {}
    for endpoint in endpoints:
        subset = [result for result in results if result[0] == endpoint]
        endpoint_results[endpoint] = {
            'requests': len(subset),
            'failures': sum(1 for result in subset if not 200 <= result[1] < 400),
            'p95_ms': round(percentile([result[2] for result in subset], 95), 2),
        }

    latencies = [result[2] for result in results]
    failures = sum(count for code, count in status_counts.items() if not 200 <= code < 400)
    report = {
        'target': base_url,
        'requests': len(results),
        'concurrency': args.concurrency,
        'duration_seconds': round(duration, 3),
        'requests_per_second': round(len(results) / duration, 2),
        'failures': failures,
        'status_counts': dict(sorted(status_counts.items())),
        'network_errors': dict(error_counts),
        'latency_ms': {
            'mean': round(statistics.fmean(latencies), 2),
            'p50': round(percentile(latencies, 50), 2),
            'p95': round(percentile(latencies, 95), 2),
            'p99': round(percentile(latencies, 99), 2),
            'max': round(max(latencies), 2),
        },
        'endpoints': endpoint_results,
    }
    output = json.dumps(report, indent=2)
    print(output)
    if args.json_output:
        with open(args.json_output, 'w', encoding='utf-8') as handle:
            handle.write(output + '\n')
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
