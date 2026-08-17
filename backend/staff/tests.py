from django.contrib.auth.hashers import check_password
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from salon_admin.models import Center
from .models import StaffMember
from .serializers import StaffMemberSerializer
from .views import _generate_staff_token


class StaffPasswordSerializerTests(TestCase):
    def test_app_password_is_hashed_and_never_serialized(self):
        center = Center.objects.create(center_name='Main')
        serializer = StaffMemberSerializer(data={
            'center': center.id,
            'first_name': 'Stylist',
            'designation': 'Stylist',
            'app_password': '1234',
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        staff = serializer.save()

        self.assertTrue(check_password('1234', staff.app_password))
        self.assertGreater(len(staff.app_password), 50)
        self.assertNotIn('app_password', StaffMemberSerializer(staff).data)


@override_settings(AUDIT_LOG_ENABLED=False)
class StaffAppSecurityTests(APITestCase):
    def test_query_string_token_is_rejected(self):
        center = Center.objects.create(center_name='Main')
        serializer = StaffMemberSerializer(data={
            'center': center.id,
            'first_name': 'Stylist',
            'designation': 'Stylist',
            'app_password': '1234',
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        staff = serializer.save()
        token = _generate_staff_token(staff)

        response = self.client.get(f'/staff/api/app/logs/?_token={token}')

        self.assertEqual(response.status_code, 401)
