"""Regression tests for finance report views.

These lock in the fixes for the crashes found during the full API audit:
- MultiSalonClientsView used phantom model attributes (vc.remaining_amount,
  pkg.service, pkg.remaining_quantity) → 500 AttributeError.
- MultiSalonSalesExportView crashed with a 500 when `item_type` was omitted.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import Invoice
from clients.models import Client, ClientPackage, ClientValueCard
from marketing.models import Package, ValueCard
from salon_admin.models import Center


class FinanceReportRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            email='fin@test.com', password='pass1234', full_name='Finance Tester')
        cls.center = Center.objects.create(center_name='Fin Center')
        cls.customer = Client.objects.create(first_name='Fin', phone='9700000000',
                                           center=cls.center)
        cls.vip = ValueCard.objects.create(title='VIP', value=5000,
                                           pre_tax_price=5000, post_tax_price=5900,
                                           expiry_days=180)
        cls.pkg = Package.objects.create(name='Glow', price=5000, validity_days=90)
        ClientValueCard.objects.create(client=cls.customer, value_card=cls.vip,
                                       balance=1200, expiry_date=date.today() + timedelta(days=30))
        ClientPackage.objects.create(client=cls.customer, package=cls.pkg,
                                     services_remaining={'1': 2},
                                     expiry_date=date.today() + timedelta(days=30))
        Invoice.objects.create(client=cls.customer, center=cls.center,
                               subtotal=100, total_amount=100, status='paid')

    def setUp(self):
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def test_multi_salon_clients_does_not_crash(self):
        """Was: AttributeError 'ClientValueCard' has no attribute 'remaining_amount'."""
        r = self.c.get('/finance/api/reports/multi_salon/clients/')
        self.assertEqual(r.status_code, 200, r.content[:300])
        rows = r.json()
        self.assertTrue(any(row['id'] == self.customer.id for row in rows))
        row = next(row for row in rows if row['id'] == self.customer.id)
        # Card balance comes from ClientValueCard.balance (1200)
        self.assertGreaterEqual(row.get('card_balance', 0), 1200)
        self.assertEqual(row['is_member'], 'No')

    def test_multi_salon_sales_export_without_item_type(self):
        """Was: AttributeError NoneType has no attribute 'capitalize' (500)."""
        r = self.c.get('/finance/api/reports/multi_salon/sales_export/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('application/vnd.openxmlformats', r['Content-Type'])

    def test_multi_salon_sales_export_advances(self):
        r = self.c.get('/finance/api/reports/multi_salon/sales_export/?item_type=advances')
        self.assertEqual(r.status_code, 200)
