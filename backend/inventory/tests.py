"""Regression tests for inventory checkout/audit robustness.

The checkout/audit actions used item['product_id'] directly, so a malformed
payload produced a 500 KeyError instead of a clean 4xx response.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from inventory.models import Product
from salon_admin.models import Center


class CheckoutRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            email='inv@test.com', password='pass1234', full_name='Inventory Tester')
        cls.center = Center.objects.create(center_name='Inv Center')
        cls.product = Product.objects.create(name='Shampoo', price=100,
                                             current_stock=10, center=cls.center)

    def setUp(self):
        self.c = APIClient()
        self.c.force_authenticate(self.user)
        self.c.force_authenticate(self.user)

    def test_checkout_missing_product_id_returns_400(self):
        """Was: 500 KeyError 'product_id'."""
        r = self.c.post('/inventory/api/products/checkout/',
                        {'items': [{'quantity': 1}], 'center_id': self.center.id},
                        format='json')
        self.assertEqual(r.status_code, 400)

    def test_checkout_unknown_product_returns_404(self):
        """Was: 500 Product.DoesNotExist."""
        r = self.c.post('/inventory/api/products/checkout/',
                        {'items': [{'product_id': 999999, 'quantity': 1}],
                         'center_id': self.center.id}, format='json')
        self.assertEqual(r.status_code, 404)

    def test_checkout_happy_path(self):
        r = self.c.post('/inventory/api/products/checkout/',
                        {'items': [{'product_id': self.product.id, 'quantity': 2}],
                         'center_id': self.center.id}, format='json')
        self.assertEqual(r.status_code, 200, r.content[:200])
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 8)

    def test_audit_missing_product_id_returns_400(self):
        r = self.c.post('/inventory/api/products/audit/',
                        {'items': [{'quantity': 5}], 'center_id': self.center.id},
                        format='json')
        self.assertEqual(r.status_code, 400)
