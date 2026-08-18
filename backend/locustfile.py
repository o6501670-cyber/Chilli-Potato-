"""
Load test for the Chilli Potato POS backend.

Simulates many concurrent users hitting the ENTIRE API surface at once:
dashboards, lists, reports, billing writes, appointment writes, etc.

Usage (15,000-request soak — every user runs 100 tasks):
    locust -f locustfile.py --headless \
        -u 150 -r 50 --iterations 100 \
        -H http://127.0.0.1:8000 \
        --csv=loadtest_results --csv-full-history

Login credentials are read from env (defaults match the QA seed data):
    LOCUST_USERNAME / LOCUST_PASSWORD
"""
import os
import random
import threading

from locust import HttpUser, between, task

USERNAME = os.environ.get('LOCUST_USERNAME', 'admin@chilli.potato')
PASSWORD = os.environ.get('LOCUST_PASSWORD', 'admin1234')

# Read-only resource IDs are discovered once at startup so GETs hit real rows.
STATE = {'center_ids': [], 'client_ids': [], 'invoice_ids': []}
_DISCOVERY_LOCK = threading.Lock()
_DISCOVERY_DONE = threading.Event()


class POSUser(HttpUser):
    wait_time = between(0.05, 0.4)   # aggressive: most users act almost immediately
    token = None

    def on_start(self):
        with self.client.post('/accounts/api/login/',
                              json={'username': USERNAME, 'password': PASSWORD},
                              name='POST /accounts/api/login/', catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f'login failed: {r.status_code} {r.text[:200]}')
                return
            data = r.json()
            self.token = data.get('token')
            self.client.headers['Authorization'] = f'Token {self.token}'

        # Discover IDs once per user (cheap; also warms the caches).
        # Note: page/page_size params return a paginated dict {results: [...]};
        # without them the API returns a raw array. Handle both shapes.
        def _ids(resp, name):
            data = resp.json() or []
            if isinstance(data, dict):
                data = data.get('results', [])
            ids = [x['id'] for x in data if isinstance(x, dict) and 'id' in x]
            resp.success() if ids else resp.failure(f'{name} returned no ids')
            return ids

        # First user populates the shared state; everyone else waits for it.
        _DISCOVERY_DONE.wait(timeout=10)
        if not STATE['center_ids'] and _DISCOVERY_LOCK.acquire(blocking=False):
            try:
                with self.client.get('/salon_admin/api/centers/', name='discover centers', catch_response=True) as c:
                    STATE['center_ids'] = _ids(c, 'centers')
                with self.client.get('/clients/api/clients/?page=1&page_size=50', name='discover clients', catch_response=True) as cl:
                    STATE['client_ids'] = _ids(cl, 'clients')
                with self.client.get('/billing/invoices/?page=1&page_size=50', name='discover invoices', catch_response=True) as inv:
                    STATE['invoice_ids'] = _ids(inv, 'invoices')
            except Exception:
                pass
            finally:
                # Always signal: a failed discovery must not hang other users
                _DISCOVERY_DONE.set()
                _DISCOVERY_LOCK.release()

    def _center(self):
        return random.choice(STATE['center_ids'] or [1])

    # ─── read-heavy: dashboards & lists (the bulk of real usage) ──────────────
    @task(7)
    def dashboard_summary(self):
        self.client.get(f"/salon_admin/api/dashboard/summary/?center_id={self._center()}",
                        name='GET dashboard/summary')

    @task(7)
    def invoices_list(self):
        self.client.get(f'/billing/invoices/?center={self._center()}&page=1&page_size=20',
                        name='GET invoices list')

    @task(6)
    def appointments_list(self):
        self.client.get(f'/appointments/api/appointments/?center={self._center()}&page=1&page_size=20',
                        name='GET appointments list')

    @task(5)
    def clients_list(self):
        self.client.get('/clients/api/clients/?page=1&page_size=20', name='GET clients list')

    @task(5)
    def staff_list(self):
        self.client.get(f'/staff/api/members/?center={self._center()}&page=1&page_size=20',
                        name='GET staff members')

    @task(4)
    def products_list(self):
        self.client.get(f'/inventory/api/products/?center={self._center()}&page=1&page_size=20',
                        name='GET products')

    @task(4)
    def register_summary(self):
        self.client.get(f'/finance/api/register_summary/?center_id={self._center()}',
                        name='GET register_summary')

    @task(4)
    def services_list(self):
        self.client.get('/services/api/master/', name='GET services master')

    @task(3)
    def dashboard_revenues(self):
        self.client.get(f"/salon_admin/api/dashboard/revenues/?center_id={self._center()}",
                        name='GET dashboard/revenues')

    @task(3)
    def finance_tax_report(self):
        self.client.get(f'/finance/api/reports/tax/?center_id={self._center()}',
                        name='GET finance tax report')

    @task(2)
    def low_stock(self):
        self.client.get(f'/inventory/api/low_stock/?center={self._center()}', name='GET low stock')

    @task(2)
    def chat_users(self):
        self.client.get('/accounts/api/chat/users/', name='GET chat users')

    @task(2)
    def audit_logs(self):
        self.client.get('/audit_logs/logs/?page=1&page_size=20', name='GET audit logs')

    @task(2)
    def invoice_detail(self):
        iid = random.choice(STATE['invoice_ids'] or [1])
        self.client.get(f'/billing/invoices/{iid}/', name='GET invoice detail')

    @task(2)
    def client_detail(self):
        cid = random.choice(STATE['client_ids'] or [1])
        self.client.get(f'/clients/api/clients/{cid}/', name='GET client detail')

    # ─── write flows (everything at once, including checkout & billing) ───────
    @task(3)
    def create_invoice(self):
        cid = random.choice(STATE['client_ids'] or [1])
        price = random.randint(200, 4000)
        payload = {
            'client': cid,
            'center': self._center(),
            'subtotal': price,
            'total_amount': price,
            'status': 'draft',
            'items': [{'description': 'Load Test Service', 'unit_price': price,
                       'quantity': 1, 'tax_percentage': 18, 'total_price': price}],
        }
        self.client.post('/billing/invoices/', json=payload, name='POST create invoice')

    @task(2)
    def create_appointment(self):
        payload = {
            'center': self._center(),
            'client_phone': f'99{random.randint(10000000, 99999999)}',
            'client_name': f'Load {random.randint(1000, 9999)}',
            'date': '2026-08-25',
            'start_time': f'{random.randint(9, 19)}:00',
            'status': 'Scheduled',
        }
        self.client.post('/appointments/api/appointments/', json=payload,
                         name='POST create appointment')

    @task(2)
    def create_client(self):
        payload = {
            'first_name': 'Load',
            'last_name': f'{random.randint(1000, 999999)}',
            'phone': f'97{random.randint(10000000, 99999999)}',
            'gender': random.choice(['female', 'male']),
            'center': self._center(),
        }
        self.client.post('/clients/api/clients/', json=payload, name='POST create client')

    @task(1)
    def create_petty_cash(self):
        payload = {
            'center': self._center(),
            'description': f'Load expense {random.randint(1000, 999999)}',
            'amount': random.randint(10, 500),
        }
        self.client.post('/finance/api/petty-cash/', json=payload, name='POST petty cash')

    @task(1)
    def pay_invoice(self):
        """Pay an existing draft invoice — exercises the heaviest write path."""
        try:
            drafts = self.client.get('/billing/invoices/?status=draft&page=1&page_size=5',
                                     name='GET draft invoices').json() or []
            iid = drafts[0]['id']
        except Exception:
            return
        payload = {'payments': [{'amount': 100, 'payment_method': 'Cash'}]}
        self.client.post(f'/billing/invoices/{iid}/pay/', json=payload,
                         name='POST pay invoice')
