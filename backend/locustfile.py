"""Authenticated, non-destructive Locust profile for sustained POS API load.

Set LOAD_TEST_TOKENS to a comma-separated list of dedicated test-user tokens.
Example:
  LOAD_TEST_TOKENS=abc,def locust --headless -u 300 -r 50 -t 2m --host http://127.0.0.1:8000
"""

import itertools
import os
import threading

from locust import HttpUser, between, task

TOKENS = [token.strip() for token in os.environ.get('LOAD_TEST_TOKENS', '').split(',') if token.strip()]
_token_cycle = itertools.cycle(TOKENS)
_token_lock = threading.Lock()


class POSReadUser(HttpUser):
    wait_time = between(0.05, 0.25)

    def on_start(self):
        if not TOKENS:
            raise RuntimeError('LOAD_TEST_TOKENS must contain dedicated test-user tokens')
        with _token_lock:
            token = next(_token_cycle)
        self.client.headers.update({'Authorization': f'Token {token}'})

    @task(4)
    def dashboard(self):
        self.client.get(
            '/finance/api/register_summary/?start_date=2026-08-01&end_date=2026-08-31',
            name='/finance/api/register_summary/',
        )

    @task(3)
    def operational_lists(self):
        self.client.get('/appointments/api/appointments/')
        self.client.get('/billing/invoices/')
        self.client.get('/clients/api/clients/?page=1&page_size=50', name='/clients/api/clients/')

    @task(2)
    def inventory_and_services(self):
        self.client.get('/inventory/api/products/')
        self.client.get('/services/api/master/')
        self.client.get('/staff/api/members/')

    @task(1)
    def administration(self):
        self.client.get('/salon_admin/api/centers/')
        self.client.get('/marketing/api/promotions/')
