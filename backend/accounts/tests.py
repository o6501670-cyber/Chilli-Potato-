"""Regression tests for accounts app bugs found in the full API audit.

- MessageReactionViewSet.perform_create raised `serializers.ValidationError`
  without importing `serializers` → NameError (500) when toggling a reaction.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import ChatRoom, Message, MessageReaction


class MessageReactionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u1 = get_user_model().objects.create_user(
            email='u1@test.com', password='pass1234', full_name='User One')
        cls.u2 = get_user_model().objects.create_user(
            email='u2@test.com', password='pass1234', full_name='User Two')
        cls.room = ChatRoom.objects.create(name='room')
        cls.room.participants.set([cls.u1, cls.u2])
        cls.msg = Message.objects.create(sender=cls.u1, room=cls.room, content='hi')

    def setUp(self):
        self.c = APIClient()
        self.c.force_authenticate(self.u1)

    def _create_reaction(self, emoji='👍'):
        return self.c.post('/accounts/api/chat/reactions/',
                           {'message': self.msg.id, 'emoji': emoji}, format='json')

    def test_create_reaction(self):
        """First reaction creates a row (was crashing with NameError)."""
        r = self._create_reaction()
        self.assertEqual(r.status_code, 201, r.content[:200])
        self.assertTrue(MessageReaction.objects.filter(message=self.msg, user=self.u1).exists())

    def test_toggle_same_reaction_removes(self):
        """Same emoji again → row deleted, 400 with {'status': 'removed'}."""
        self._create_reaction()
        r = self._create_reaction()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json().get('status'), 'removed')
        self.assertFalse(MessageReaction.objects.filter(message=self.msg, user=self.u1).exists())

    def test_toggle_different_reaction_updates(self):
        """Different emoji → row updated, 400 with {'status': 'updated'}."""
        self._create_reaction('👍')
        r = self._create_reaction('❤️')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json().get('status'), 'updated')
        self.assertEqual(MessageReaction.objects.get(message=self.msg, user=self.u1).emoji, '❤️')
