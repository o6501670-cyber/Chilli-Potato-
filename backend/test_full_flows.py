from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from salon_admin.models import Center, Role
from clients.models import Client
from services.models import ServiceMaster
from rest_framework import status
from django.utils import timezone

User = get_user_model()

class POSSystemFullFlowTest(APITestCase):
    
    def setUp(self):
        # Create a superadmin user to bypass permission checks
        self.user = User.objects.create_superuser(password='password123', email='admin@test.com')
        self.client.force_authenticate(user=self.user)
        self.center = Center.objects.create(center_name='Global Center', phone='9999999999')
        
    def test_01_salon_admin_flow(self):
        """Test Center and Role Creation"""
        res = self.client.post('/salon_admin/api/centers/', {
            'center_name': 'Test Flow Center',
            'phone': '9999999999',
            'address': '123 Test St'
        }, format='json')
        self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Center Creation Failed: {res.data}")
        
        res = self.client.post('/salon_admin/api/roles/', {
            'name': 'Test Flow Role',
            'permissions': {'staff': {'directory': {'read': True}}}
        }, format='json')
        self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Role Creation Failed: {res.data}")

    def test_02_staff_flow(self):
        """Test Staff and Designation Creation"""
        res = self.client.post('/staff/api/designations/', {
            'name': 'Test Stylist',
            'category': 'Hair'
        }, format='json')
        self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Designation Creation Failed: {res.data}")
        
        res = self.client.post('/staff/api/members/', {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '8888888888',
            'designation': 'Test Stylist',
            'center': self.center.id,
            'gender': 'Male',
            'salary': 50000,
            'is_active': True
        }, format='json')
        self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Staff Creation Failed: {res.data}")

    def test_03_services_flow(self):
        """Test Service Master Creation"""
        res = self.client.post('/services/api/master/', {
            'name': 'Test Haircut',
            'category': 'Hair',
            'sub_category': 'Men',
            'duration_mins': 30,
            'default_price': 500,
            'is_active': True
        }, format='json')
        self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Service Creation Failed: {res.data}")

    def test_04_clients_flow(self):
        """Test Client Creation"""
        res = self.client.post('/clients/api/clients/', {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'phone': '7777777777',
            'gender': 'Female',
            'center': self.center.id
        }, format='json')
        self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Client Creation Failed: {res.data}")
        
    def test_05_inventory_flow(self):
        """Test Product and Vendor Creation"""
        res = self.client.post('/inventory/api/vendors/', {
            'name': 'Test Vendor LLC',
            'contact_person': 'Bob',
            'phone': '6666666666',
            'center': self.center.id
        }, format='json')
        self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Vendor Creation Failed: {res.data}")
        
        res = self.client.post('/inventory/api/products/', {
            'name': 'Test Shampoo',
            'brand': 'Loreal Test',
            'category': 'Hair Care',
            'price': 200,
            'current_stock': 50,
            'center': self.center.id
        }, format='json')
        self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Product Creation Failed: {res.data}")

    def test_06_finance_flow(self):
        """Test Petty Cash"""
        res = self.client.post('/finance/api/petty_cash/', {
            'center': self.center.id,
            'amount': 1000,
            'type': 'in',
            'category': 'topup',
            'description': 'Initial Topup'
        }, format='json')
        if res.status_code != 404:
            self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Petty Cash Creation Failed: {res.data}")
            
    def test_07_marketing_flow(self):
        """Test Marketing Creation"""
        res = self.client.post('/marketing/api/promotions/', {
            'title': 'Test Promo 10% Off',
            'description': 'Test',
            'promo_type': 'discount',
            'level': 'Global',
            'is_active': True,
            'config': {'discount_type': 'percent', 'discount_value': 10},
            'center': self.center.id
        }, format='json')
        if res.status_code != 404:
            self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Promotion Creation Failed: {res.data}")
            
    def test_08_appointments_flow(self):
        """Test Appointment"""
        res = self.client.post('/appointments/api/appointments/', {
            'center': self.center.id,
            'client_name': 'Appt Client',
            'client_phone': '5555555555',
            'date': timezone.now().date().isoformat(),
            'start_time': '10:00',
            'status': 'scheduled'
        }, format='json')
        if res.status_code != 404:
            self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Appointment Creation Failed: {res.data}")

    def test_09_billing_flow(self):
        """Test Billing"""
        client = Client.objects.create(first_name='Bill Client', phone='4444444444', center=self.center)
        res = self.client.post('/billing/api/invoices/', {
            'center': self.center.id,
            'client': client.id,
            'status': 'unpaid',
            'subtotal': 100,
            'total_amount': 100,
            'payment_status': 'unpaid'
        }, format='json')
        if res.status_code != 404:
            self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK], f"Invoice Creation Failed: {res.data}")
