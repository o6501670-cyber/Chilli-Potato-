from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from salon_admin.models import Center


class RegisterFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            email='register@example.com', password='StrongPass123!', full_name='Register Owner'
        )
        self.center = Center.objects.create(center_name='Register Center')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_shift_can_open_and_close_with_numeric_cash_values(self):
        opened = self.client.post(
            '/finance/api/shifts/',
            {'center': self.center.id, 'starting_float': 100},
            format='json',
        )
        self.assertEqual(opened.status_code, 201, opened.data)
        closed = self.client.post(
            f"/finance/api/shifts/{opened.data['id']}/close_shift/",
            {'actual_cash': 100, 'expected_cash': 100},
            format='json',
        )
        self.assertEqual(closed.status_code, 200, closed.data)
        self.assertEqual(closed.data['status'], 'Closed')
        self.assertEqual(closed.data['variance'], '0.00')
