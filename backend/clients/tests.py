from django.contrib.auth.hashers import check_password, make_password
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase

from accounts.models import CustomUser
from salon_admin.models import Center, Role
from .app_views import _generate_client_token
from .models import Client
from .serializers import ClientSerializer


class ClientPinSerializerTests(TestCase):
    def test_pin_is_hashed_and_never_serialized(self):
        serializer = ClientSerializer(data={
            'first_name': 'Client', 'phone': '9000000001', 'app_pin': '1234'
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        client = serializer.save()

        self.assertTrue(check_password('1234', client.app_pin))
        self.assertNotIn('app_pin', ClientSerializer(client).data)


@override_settings(AUDIT_LOG_ENABLED=False)
class ClientAppSecurityTests(APITestCase):
    def setUp(self):
        self.center = Center.objects.create(center_name='Main')
        self.client_record = Client.objects.create(
            center=self.center, first_name='Client', phone='9000000001',
            app_pin=make_password('1234'),
        )
        self.token = _generate_client_token(self.client_record)

    def test_query_string_token_is_rejected(self):
        response = self.client.get(f'/clients/api/app/data/?_token={self.token}')
        self.assertEqual(response.status_code, 401)

    def test_profile_pin_update_hashes_new_pin(self):
        response = self.client.post(
            '/clients/api/app/update_profile/', {'pin': '5678'}, format='json',
            HTTP_X_CLIENT_TOKEN=self.token,
        )
        self.assertEqual(response.status_code, 200)
        self.client_record.refresh_from_db()
        self.assertTrue(check_password('5678', self.client_record.app_pin))
        self.assertNotEqual(self.client_record.app_pin, '5678')

    def test_duplicate_phone_login_requires_center(self):
        other = Center.objects.create(center_name='Other')
        Client.objects.create(
            center=other, first_name='Duplicate', phone='9000000001',
            app_pin=make_password('1234'),
        )
        response = self.client.post(
            '/clients/api/app/login/', {'phone': '9000000001', 'pin': '1234'}, format='json'
        )
        self.assertEqual(response.status_code, 409)


@override_settings(AUDIT_LOG_ENABLED=False)
class ClientListPerformanceTests(APITestCase):
    def test_query_count_does_not_scale_per_client(self):
        center = Center.objects.create(center_name='Main')
        owner = CustomUser.objects.create_user(
            email='client-list-owner@example.com', full_name='Owner',
            password='Strong-Test-Pass-847!', role=Role.objects.create(name='Owner'),
        )
        Client.objects.bulk_create([
            Client(center=center, first_name=f'Client {index}', phone=f'91111{index:05d}', app_pin='!')
            for index in range(30)
        ])
        self.client.force_authenticate(owner)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/clients/api/clients/?page=1&page_size=50')

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 12, [query['sql'] for query in queries])
