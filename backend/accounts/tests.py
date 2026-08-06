from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from salon_admin.models import Center, Role


class RolePermissionRegressionTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.center = Center.objects.create(center_name='Scoped Center')
        self.role = Role.objects.create(
            name='Operator',
            permissions={
                'staff': {
                    'directory': {'read': True, 'create': False, 'update': False, 'delete': False}
                }
            },
        )
        self.user = User.objects.create_user(
            email='operator@example.com', password='StrongPass123!',
            full_name='Operator', role=self.role, center=self.center
        )
        self.client.force_authenticate(self.user)

    def test_read_is_allowed_but_write_requires_explicit_action(self):
        read = self.client.get('/staff/api/members/')
        self.assertEqual(read.status_code, 200, read.data)
        create = self.client.post('/staff/api/members/', {
            'first_name': 'Not Allowed',
            'designation': 'Stylist',
            'center': self.center.id,
        }, format='json')
        self.assertEqual(create.status_code, 403, create.data)

    def test_unknown_module_is_denied_even_when_authenticated(self):
        response = self.client.get('/finance/api/register_summary/')
        self.assertEqual(response.status_code, 403, response.data)
