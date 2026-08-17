import io
from decimal import Decimal

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CustomUser
from salon_admin.models import Center, Role
from .models import Product, ProductLot, StockTransaction, Vendor


@override_settings(AUDIT_LOG_ENABLED=False)
class InventoryIntegrityTests(APITestCase):
    def setUp(self):
        self.center = Center.objects.create(center_name='Allowed')
        self.other_center = Center.objects.create(center_name='Forbidden')
        self.staff_role = Role.objects.create(name='Cashier')
        self.user = CustomUser.objects.create_user(
            email='cashier@example.com', full_name='Cashier', password='Strong-Test-Pass-847!',
            role=self.staff_role, center=self.center,
        )
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(
            center=self.center, name='Shampoo', current_stock=10, price=100,
        )
        self.second_product = Product.objects.create(
            center=self.center, name='Conditioner', current_stock=1, price=80,
        )
        self.foreign_product = Product.objects.create(
            center=self.other_center, name='Foreign', current_stock=10, price=50,
        )

    def test_checkout_rejects_negative_and_duplicate_quantities(self):
        negative = self.client.post('/inventory/api/products/checkout/', {
            'center_id': self.center.id,
            'items': [{'product_id': self.product.id, 'quantity': -1}],
        }, format='json')
        duplicate = self.client.post('/inventory/api/products/checkout/', {
            'center_id': self.center.id,
            'items': [
                {'product_id': self.product.id, 'quantity': 1},
                {'product_id': self.product.id, 'quantity': 1},
            ],
        }, format='json')

        self.assertEqual(negative.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 10)

    def test_failed_batch_checkout_is_all_or_nothing(self):
        response = self.client.post('/inventory/api/products/checkout/', {
            'center_id': self.center.id,
            'items': [
                {'product_id': self.product.id, 'quantity': 2},
                {'product_id': self.second_product.id, 'quantity': 2},
            ],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.second_product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 10)
        self.assertEqual(self.second_product.current_stock, 1)
        self.assertEqual(StockTransaction.objects.count(), 0)

    def test_valid_checkout_updates_stock_and_history(self):
        response = self.client.post('/inventory/api/products/checkout/', {
            'center_id': self.center.id,
            'items': [{'product_id': self.product.id, 'quantity': 3}],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 7)
        transaction = StockTransaction.objects.get(product=self.product)
        self.assertEqual(transaction.quantity_change, -3)
        self.assertEqual(transaction.created_by, self.user)

    def test_stock_operations_cannot_cross_centers(self):
        checkout = self.client.post('/inventory/api/products/checkout/', {
            'center_id': self.center.id,
            'items': [{'product_id': self.foreign_product.id, 'quantity': 1}],
        }, format='json')
        audit = self.client.post('/inventory/api/products/audit/', {
            'center_id': self.other_center.id,
            'items': [{'product_id': self.foreign_product.id, 'quantity': 1}],
        }, format='json')

        self.assertEqual(checkout.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(audit.status_code, status.HTTP_403_FORBIDDEN)
        self.foreign_product.refresh_from_db()
        self.assertEqual(self.foreign_product.current_stock, 10)

    def test_audit_rejects_negative_stock(self):
        response = self.client.post('/inventory/api/products/audit/', {
            'center_id': self.center.id,
            'items': [{'product_id': self.product.id, 'quantity': -1}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 10)

    def test_product_lots_are_scoped_through_product_center(self):
        ProductLot.objects.create(product=self.product, lot_number='A', net_price=50, mrp=100)
        ProductLot.objects.create(product=self.foreign_product, lot_number='B', net_price=20, mrp=50)

        response = self.client.get('/inventory/api/lots/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([lot['lot_number'] for lot in response.data], ['A'])

    def test_non_owner_cannot_move_product_or_create_across_all_centers(self):
        moved = self.client.patch(
            f'/inventory/api/products/{self.product.id}/',
            {'center': self.other_center.id}, format='json',
        )
        create_all = self.client.post('/inventory/api/products/', {
            'name': 'Global product', 'center': self.center.id,
            'create_all_centers': True,
        }, format='json')

        self.assertEqual(moved.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(create_all.status_code, status.HTTP_403_FORBIDDEN)
        self.product.refresh_from_db()
        self.assertEqual(self.product.center, self.center)
        self.assertFalse(Product.objects.filter(name='Global product').exists())

    def test_invalid_bulk_center_never_falls_back_to_all_centers(self):
        upload = io.BytesIO(b'vendorName,phone\nInjected Vendor,9999999999\n')
        upload.name = 'vendors.csv'
        response = self.client.post(
            '/inventory/api/vendors/bulk_upload/?center_id=999999',
            {'file': upload}, format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Vendor.objects.filter(name='Injected Vendor').exists())


@override_settings(AUDIT_LOG_ENABLED=False)
class PurchaseOrderCalculationTests(APITestCase):
    def setUp(self):
        self.center = Center.objects.create(center_name='Main')
        self.other_center = Center.objects.create(center_name='Other')
        owner_role = Role.objects.create(name='Owner')
        self.owner = CustomUser.objects.create_user(
            email='owner-inventory@example.com', full_name='Owner', password='Strong-Test-Pass-847!',
            role=owner_role,
        )
        self.client.force_authenticate(self.owner)
        self.vendor = Vendor.objects.create(center=self.center, name='Vendor')
        self.foreign_vendor = Vendor.objects.create(center=self.other_center, name='Foreign Vendor')
        self.product = Product.objects.create(center=self.center, name='Product', current_stock=0)

    def test_purchase_order_tax_is_calculated_after_discount(self):
        response = self.client.post('/inventory/api/purchase-orders/', {
            'center': self.center.id,
            'vendor': self.vendor.id,
            'items': [{
                'product': self.product.id,
                'quantity': 2,
                'rate': '100.00',
                'discount_percent': '10.00',
                'tax_percent': '10.00',
                'total_price': '0.00',
            }],
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Decimal(response.data['total_amount']), Decimal('198.00'))

    def test_purchase_order_rejects_vendor_from_another_center(self):
        response = self.client.post('/inventory/api/purchase-orders/', {
            'center': self.center.id,
            'vendor': self.foreign_vendor.id,
            'items': [],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('vendor', response.data)
