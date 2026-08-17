from decimal import Decimal
from rest_framework.test import APIRequestFactory
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from accounts.models import CustomUser
from salon_admin.models import Center, Role
from .models import CenterService, ServiceMaster
from .serializers import ServiceMasterSerializer


class ServiceMasterSerializerTests(TestCase):
    def setUp(self):
        self.center = Center.objects.create(center_name='Test Center', display_name='Test Center')
        self.service = ServiceMaster.objects.create(
            name='Haircut',
            category='Cuts',
            default_price=Decimal('120.00'),
            level='Organisation',
        )

    def test_price_field_uses_center_override_when_available(self):
        CenterService.objects.create(center=self.center, service=self.service, price=Decimal('150.00'), is_active=True)
        request = APIRequestFactory().get('/services/api/master/', {'center_id': str(self.center.id)})
        serializer = ServiceMasterSerializer(self.service, context={'request': request})
        self.assertEqual(serializer.data['price'], Decimal('150.00'))

    def test_price_field_falls_back_to_default_price(self):
        request = APIRequestFactory().get('/services/api/master/', {'center_id': str(self.center.id)})
        serializer = ServiceMasterSerializer(self.service, context={'request': request})
        self.assertEqual(serializer.data['price'], Decimal('120.00'))


@override_settings(AUDIT_LOG_ENABLED=False)
class ServiceCenterSecurityTests(APITestCase):
    def setUp(self):
        self.center = Center.objects.create(center_name='Assigned')
        self.other = Center.objects.create(center_name='Other')
        role = Role.objects.create(name='Staff')
        self.user = CustomUser.objects.create_user(
            email='services@example.com', full_name='Services User',
            password='Strong-Test-Pass-847!', role=role, center=self.center,
        )
        self.service = ServiceMaster.objects.create(
            name='Haircut', category='Cuts', default_price='100.00'
        )
        self.client.force_authenticate(self.user)

    def test_default_organisation_service_creation_is_denied(self):
        response = self.client.post('/services/api/master/', {
            'name': 'Injected Global Service', 'category': 'Cuts', 'default_price': '1.00'
        }, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ServiceMaster.objects.filter(name='Injected Global Service').exists())

    def test_cross_center_override_is_denied(self):
        response = self.client.post('/services/api/center/override/', {
            'center_id': self.other.id,
            'service_id': self.service.id,
            'price': '1.00',
        }, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CenterService.objects.filter(center=self.other, service=self.service).exists())

    def test_assigned_center_override_succeeds(self):
        response = self.client.post('/services/api/center/override/', {
            'center_id': self.center.id,
            'service_id': self.service.id,
            'price': '125.00',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            CenterService.objects.get(center=self.center, service=self.service).price,
            Decimal('125.00'),
        )
