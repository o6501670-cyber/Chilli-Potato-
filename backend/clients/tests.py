"""Regression tests: PIN/password fields must never leak through the API."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from clients.models import Client
from clients.serializers import ClientSerializer
from salon_admin.models import Center
from staff.models import Designation, StaffMember
from staff.serializers import StaffMemberSerializer


class SensitiveFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            email='sec@test.com', password='pass1234', full_name='Sec Tester')
        cls.center = Center.objects.create(center_name='Sec Center')

    def setUp(self):
        self.c = APIClient()
        self.c.force_authenticate(self.user)

    def test_client_app_pin_write_only(self):
        client = Client.objects.create(first_name='A', phone='9600000001',
                                       app_pin='1234', center=self.center)
        data = ClientSerializer(client).data
        self.assertNotIn('app_pin', data)
        r = self.c.get(f'/clients/api/clients/{client.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('app_pin', r.json())

    def test_staff_app_password_write_only(self):
        desg = Designation.objects.create(name='Stylist')
        staff = StaffMember.objects.create(first_name='S', designation='Stylist',
                                           designation_fk=desg, app_password='abcd',
                                           center=self.center)
        data = StaffMemberSerializer(staff).data
        self.assertNotIn('app_password', data)
        r = self.c.get(f'/staff/api/members/{staff.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('app_password', r.json())
