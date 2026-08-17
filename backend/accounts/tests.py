import datetime

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from audit_logs.middleware import _sanitise
from salon_admin.models import Center, Role
from .models import ChatRoom, CustomUser, Message


@override_settings(AUDIT_LOG_ENABLED=False)
class AuthenticationAndChatSecurityTests(APITestCase):
    def setUp(self):
        self.center = Center.objects.create(center_name='Main')
        self.owner_role = Role.objects.create(name='Owner')
        self.owner = CustomUser.objects.create_user(
            email='owner@example.com', full_name='Owner', password='Strong-Test-Pass-847!',
            role=self.owner_role, center=self.center,
        )
        self.member = CustomUser.objects.create_user(
            email='member@example.com', full_name='Member', password='Strong-Test-Pass-847!',
            center=self.center,
        )
        self.outsider = CustomUser.objects.create_user(
            email='outsider@example.com', full_name='Outsider', password='Strong-Test-Pass-847!',
            center=self.center,
        )
        self.room = ChatRoom.objects.create(name='Private')
        self.room.participants.add(self.owner, self.member)

    def test_login_rotates_existing_token(self):
        old_token = Token.objects.create(user=self.owner)
        response = self.client.post('/accounts/api/login/', {
            'username': self.owner.email,
            'password': 'Strong-Test-Pass-847!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data['token'], old_token.key)
        self.assertFalse(Token.objects.filter(key=old_token.key).exists())

    @override_settings(API_TOKEN_MAX_AGE_DAYS=7)
    def test_expired_token_is_rejected(self):
        token = Token.objects.create(user=self.owner)
        Token.objects.filter(pk=token.pk).update(
            created=timezone.now() - datetime.timedelta(days=8)
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = self.client.get('/salon_admin/api/centers/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_outsider_cannot_read_send_or_mark_room_messages(self):
        Message.objects.create(sender=self.owner, room=self.room, content='secret')
        self.client.force_authenticate(self.outsider)

        read = self.client.get(f'/accounts/api/chat/messages/?user_id={self.room.id}')
        send = self.client.post('/accounts/api/chat/messages/', {
            'room_id': self.room.id, 'content': 'intrusion'
        }, format='json')
        mark = self.client.post('/accounts/api/chat/messages/mark_read/', {
            'room_id': self.room.id
        }, format='json')

        self.assertEqual(read.status_code, status.HTTP_200_OK)
        self.assertEqual(read.data, [])
        self.assertEqual(send.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(mark.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Message.objects.filter(room=self.room).count(), 1)

    def test_room_member_can_send_and_mark_messages_read(self):
        incoming = Message.objects.create(sender=self.owner, room=self.room, content='hello')
        self.client.force_authenticate(self.member)

        send = self.client.post('/accounts/api/chat/messages/', {
            'room_id': self.room.id, 'content': 'reply'
        }, format='json')
        mark = self.client.post('/accounts/api/chat/messages/mark_read/', {
            'room_id': self.room.id
        }, format='json')

        self.assertEqual(send.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mark.status_code, status.HTTP_200_OK)
        incoming.refresh_from_db()
        self.assertTrue(incoming.is_read)

    def test_owner_user_creation_requires_password(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post('/accounts/api/users/', {
            'email': 'no-password@example.com', 'full_name': 'No Password'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)


class AuditSanitisationTests(SimpleTestCase):
    def test_nested_secrets_are_redacted(self):
        body = b'{"profile":{"password":"secret","items":[{"token":"abc"}]},"name":"safe"}'
        result = _sanitise(body)
        self.assertEqual(result['profile']['password'], '***')
        self.assertEqual(result['profile']['items'][0]['token'], '***')
        self.assertEqual(result['name'], 'safe')

    def test_oversized_body_is_not_stored(self):
        result = _sanitise(b'x' * (1024 * 1024 + 1))
        self.assertIn('_audit_note', result)
