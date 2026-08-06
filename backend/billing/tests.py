from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APITestCase

from clients.models import Client
from inventory.models import Product, StockTransaction
from marketing.models import Promotion, PromotionUsage
from salon_admin.models import Center

from .models import Invoice, InvoiceRefund


class BillingIntegrityTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            email='owner@example.com', password='StrongPass123!', full_name='Owner'
        )
        self.client.force_authenticate(self.user)
        self.center = Center.objects.create(center_name='Test Center')
        self.customer = Client.objects.create(
            first_name='Customer', phone='9000000001', center=self.center
        )
        self.product = Product.objects.create(
            name='Test Product', center=self.center, price=100,
            current_stock=1, gst_percent=0
        )

    def _invoice_payload(self, key='sale-1', promo_id=None):
        payload = {
            'idempotency_key': key,
            'client': self.customer.id,
            'center': self.center.id,
            'subtotal': 100,
            'discount': 0,
            'cgst': 0,
            'sgst': 0,
            'rounding': 0,
            'total_amount': 100,
            'status': 'paid',
            'payments': [{'amount': 100, 'payment_method': 'Cash'}],
            'items': [{
                'content_type': 'inventory.product',
                'object_id': self.product.id,
                'description': 'Test Product',
                'unit_price': 100,
                'discount': 0,
                'quantity': 1,
                'tax_percentage': 0,
            }],
        }
        if promo_id:
            payload['promo_id'] = promo_id
        return payload

    def test_create_is_idempotent_and_finalizes_once(self):
        first = self.client.post('/billing/invoices/', self._invoice_payload(), format='json')
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post('/billing/invoices/', self._invoice_payload(), format='json')
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data['id'], second.data['id'])
        invoice = Invoice.objects.get(pk=first.data['id'])
        self.assertIsNotNone(invoice.finalized_at)
        self.assertEqual(Product.objects.get(pk=self.product.id).current_stock, 0)
        self.assertEqual(StockTransaction.objects.filter(product=self.product, transaction_type='SALE').count(), 1)
        self.assertEqual(invoice.payments.count(), 1)

    def test_insufficient_stock_rolls_back_invoice(self):
        self.product.current_stock = 0
        self.product.save(update_fields=['current_stock'])
        response = self.client.post('/billing/invoices/', self._invoice_payload('no-stock'), format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Invoice.objects.filter(idempotency_key='no-stock').exists())
        self.assertEqual(StockTransaction.objects.filter(product=self.product).count(), 0)

    def test_full_refund_reverses_stock_and_cannot_repeat(self):
        response = self.client.post('/billing/invoices/', self._invoice_payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        invoice_id = response.data['id']
        refund = self.client.post(f'/billing/invoices/{invoice_id}/refund/', {}, format='json')
        self.assertEqual(refund.status_code, 200, refund.data)
        self.assertEqual(Invoice.objects.get(pk=invoice_id).status, 'refunded')
        self.assertEqual(InvoiceRefund.objects.filter(invoice_id=invoice_id).count(), 1)
        self.assertEqual(Product.objects.get(pk=self.product.id).current_stock, 1)
        again = self.client.post(f'/billing/invoices/{invoice_id}/refund/', {}, format='json')
        self.assertEqual(again.status_code, 400, again.data)

    def test_cashback_promotion_is_recorded_once(self):
        promotion = Promotion.objects.create(
            name='Cashback', promo_type='Cashback', level='Organisation',
            start_date=date.today(), end_date=date.today() + timedelta(days=5),
            config={'cashback_min_bill': 50, 'cashback_discount': 10},
        )
        # Use a second product so this test has stock independent of the first test.
        self.product.current_stock = 2
        self.product.save(update_fields=['current_stock'])
        response = self.client.post(
            '/billing/invoices/', self._invoice_payload('cashback-1', promotion.id), format='json'
        )
        self.assertEqual(response.status_code, 201, response.data)
        invoice = Invoice.objects.get(pk=response.data['id'])
        self.assertEqual(PromotionUsage.objects.filter(invoice=invoice).count(), 1)
        self.assertEqual(float(self.customer.cashback_balance), 10.0)
        self.client.post(f'/billing/invoices/{invoice.id}/refund/', {}, format='json')
        self.assertEqual(float(Client.objects.get(pk=self.customer.id).cashback_balance), 0.0)
        self.assertFalse(PromotionUsage.objects.filter(invoice=invoice).exists())
