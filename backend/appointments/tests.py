from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CustomUser
from clients.models import Client
from salon_admin.models import Center, Role
from staff.models import StaffMember
from .models import Appointment


@override_settings(AUDIT_LOG_ENABLED=False)
class AppointmentIntegrityTests(APITestCase):
    def setUp(self):
        self.center = Center.objects.create(center_name='Main')
        self.other_center = Center.objects.create(center_name='Other')
        role = Role.objects.create(name='Receptionist')
        self.user = CustomUser.objects.create_user(
            email='reception@example.com', full_name='Reception', password='Strong-Test-Pass-847!',
            role=role, center=self.center,
        )
        self.staff = StaffMember.objects.create(
            center=self.center, first_name='Stylist', designation='Senior Stylist',
        )
        self.client.force_authenticate(self.user)

    def _appointment_payload(self, start='10:00', duration=60):
        return {
            'center': self.center.id,
            'client_name': 'Client',
            'client_phone': '9999999999',
            'date': '2026-08-20',
            'start_time': start,
            'status': 'Scheduled',
            'services': [{
                'service_name': 'Haircut',
                'time': start,
                'duration': duration,
                'staff': self.staff.id,
                'price': '500.00',
            }],
        }

    def test_validated_time_data_prevents_overlapping_staff_booking(self):
        first = self.client.post(
            '/appointments/api/appointments/', self._appointment_payload(), format='json'
        )
        overlapping = self.client.post(
            '/appointments/api/appointments/', self._appointment_payload(start='10:30'), format='json'
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(overlapping.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_update_cannot_move_appointment_to_unauthorised_center(self):
        appointment = Appointment.objects.create(
            center=self.center, client_name='Client', client_phone='9999999999',
            date='2026-08-20', start_time='10:00',
        )
        response = self.client.patch(
            f'/appointments/api/appointments/{appointment.id}/',
            {'center': self.other_center.id}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        appointment.refresh_from_db()
        self.assertEqual(appointment.center, self.center)

    def test_client_linking_is_scoped_to_appointment_center(self):
        Client.objects.create(center=self.other_center, first_name='Wrong', phone='9999999999')
        expected = Client.objects.create(center=self.center, first_name='Correct', phone='9999999999')

        response = self.client.post(
            '/appointments/api/appointments/', self._appointment_payload(), format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        appointment = Appointment.objects.get(pk=response.data['id'])
        self.assertEqual(appointment.client, expected)
