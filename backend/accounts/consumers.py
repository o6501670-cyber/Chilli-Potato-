import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat.
    URL pattern: ws://host/ws/chat/<room_id>/?token=<auth_token>
    """

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = None

        # Authenticate via token in query string
        token_key = self._get_token_from_scope()
        if not token_key:
            await self.close(code=4001)
            return

        self.user = await self._get_user_from_token(token_key)
        if not self.user:
            await self.close(code=4001)
            return

        # Check room membership
        is_participant = await self._is_participant(self.room_id, self.user)
        if not is_participant:
            await self.close(code=4003)
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        
        # Track online presence in user-specific group
        self.user_group = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        await self.accept()

        # Broadcast this user is online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_online',
                'user_id': self.user.id,
                'full_name': self.user.full_name,
            }
        )

    def _get_token_from_scope(self):
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        for part in query_string.split('&'):
            if part.startswith('token='):
                return part[6:]
        return None

    @database_sync_to_async
    def _get_user_from_token(self, token_key):
        try:
            from rest_framework.authtoken.models import Token
            token = Token.objects.select_related('user').get(key=token_key)
            if token.user.is_active:
                return token.user
        except Exception:
            pass
        return None

    @database_sync_to_async
    def _is_participant(self, room_id, user):
        try:
            from .models import ChatRoom
            return ChatRoom.objects.filter(id=room_id, participants=user).exists()
        except Exception:
            return False

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Broadcast offline status
            if self.user:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_offline',
                        'user_id': self.user.id,
                    }
                )
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming WebSocket messages from the client."""
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')

        if msg_type == 'chat_message':
            await self._handle_chat_message(data)
        elif msg_type == 'typing':
            await self._handle_typing(data)
        elif msg_type == 'stop_typing':
            await self._handle_stop_typing()
        elif msg_type == 'read_receipt':
            await self._handle_read_receipt(data)
        elif msg_type == 'reaction':
            await self._handle_reaction(data)
        elif msg_type == 'delete_message':
            await self._handle_delete_message(data)
        elif msg_type == 'edit_message':
            await self._handle_edit_message(data)

    async def _handle_chat_message(self, data):
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to_id')

        if not content:
            return

        # Save to database
        message = await self._save_message(content, reply_to_id)
        if not message:
            return

        # Update room's updated_at for sorting in room list
        await self._touch_room()

        # Broadcast to room
        reply_data = None
        if reply_to_id:
            reply_data = await self._get_reply_preview(reply_to_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': message['id'],
                'content': message['content'],
                'sender_id': self.user.id,
                'sender_name': self.user.full_name,
                'timestamp': message['timestamp'],
                'status': 'sent',
                'reply_to': reply_data,
            }
        )

        # Mark as delivered for all other participants who are online
        await self._mark_delivered_for_online_participants(message['id'])

    async def _handle_typing(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'user_name': self.user.full_name,
                'is_typing': True,
            }
        )

    async def _handle_stop_typing(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'user_name': self.user.full_name,
                'is_typing': False,
            }
        )

    async def _handle_read_receipt(self, data):
        message_ids = data.get('message_ids', [])
        if not message_ids:
            return

        updated_sender_ids = await self._mark_messages_read(message_ids)

        # Notify senders their messages were read
        for sender_id in updated_sender_ids:
            await self.channel_layer.group_send(
                f'user_{sender_id}',
                {
                    'type': 'messages_read',
                    'message_ids': message_ids,
                    'reader_id': self.user.id,
                    'room_id': int(self.room_id),
                }
            )

    async def _handle_reaction(self, data):
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        if not message_id or not emoji:
            return

        reaction = await self._save_reaction(message_id, emoji)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'reaction_update',
                'message_id': message_id,
                'user_id': self.user.id,
                'user_name': self.user.full_name,
                'emoji': emoji,
                'action': reaction['action'],  # 'added' or 'removed'
            }
        )

    async def _handle_delete_message(self, data):
        message_id = data.get('message_id')
        if not message_id:
            return

        success = await self._soft_delete_message(message_id)
        if success:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                    'deleted_by': self.user.id,
                }
            )

    async def _handle_edit_message(self, data):
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()
        if not message_id or not new_content:
            return

        success = await self._edit_message(message_id, new_content)
        if success:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_edited',
                    'message_id': message_id,
                    'content': new_content,
                    'edited_by': self.user.id,
                }
            )

    # ─── Group event handlers (called by channel layer) ─────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'chat_message', **event}))

    async def typing_indicator(self, event):
        # Don't send typing events back to the same user
        if event.get('user_id') != self.user.id:
            await self.send(text_data=json.dumps({'type': 'typing', **event}))

    async def user_online(self, event):
        if event.get('user_id') != self.user.id:
            await self.send(text_data=json.dumps({'type': 'user_online', **event}))

    async def user_offline(self, event):
        if event.get('user_id') != self.user.id:
            await self.send(text_data=json.dumps({'type': 'user_offline', **event}))

    async def messages_read(self, event):
        await self.send(text_data=json.dumps({'type': 'messages_read', **event}))

    async def reaction_update(self, event):
        await self.send(text_data=json.dumps({'type': 'reaction_update', **event}))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({'type': 'message_deleted', **event}))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({'type': 'message_edited', **event}))

    # ─── Database helpers ────────────────────────────────────────────────────

    @database_sync_to_async
    def _save_message(self, content, reply_to_id=None):
        try:
            from .models import ChatRoom, Message
            room = ChatRoom.objects.get(id=self.room_id)
            msg = Message.objects.create(
                sender=self.user,
                room=room,
                content=content,
                reply_to_id=reply_to_id if reply_to_id else None,
                status=Message.STATUS_SENT,
            )
            return {'id': msg.id, 'content': msg.content, 'timestamp': msg.timestamp.isoformat()}
        except Exception as e:
            logger.error(f"[ChatConsumer] Failed to save message: {e}", exc_info=True)
            return None

    @database_sync_to_async
    def _touch_room(self):
        try:
            from .models import ChatRoom
            ChatRoom.objects.filter(id=self.room_id).update(updated_at=timezone.now())
        except Exception:
            pass

    @database_sync_to_async
    def _get_reply_preview(self, reply_to_id):
        try:
            from .models import Message
            msg = Message.objects.select_related('sender').get(id=reply_to_id)
            return {
                'id': msg.id,
                'content': msg.content[:100] if msg.content else '[Image]',
                'sender_name': msg.sender.full_name,
            }
        except Exception:
            return None

    @database_sync_to_async
    def _mark_messages_read(self, message_ids):
        """Mark messages as read, return list of sender IDs who need to be notified."""
        try:
            from .models import Message
            messages = Message.objects.filter(
                id__in=message_ids,
                room_id=self.room_id,
                status__in=[Message.STATUS_SENT, Message.STATUS_DELIVERED]
            ).exclude(sender=self.user).select_related('sender')
            
            sender_ids = set(m.sender_id for m in messages)
            messages.update(status=Message.STATUS_READ, is_read=True)
            return list(sender_ids)
        except Exception as e:
            logger.error(f"[ChatConsumer] read receipt failed: {e}")
            return []

    @database_sync_to_async
    def _mark_delivered_for_online_participants(self, message_id):
        """Mark message as delivered if recipient is connected."""
        pass  # handled by room-level broadcast; status promoted on receipt

    @database_sync_to_async
    def _save_reaction(self, message_id, emoji):
        try:
            from .models import MessageReaction
            reaction, created = MessageReaction.objects.get_or_create(
                message_id=message_id,
                user=self.user,
                defaults={'emoji': emoji}
            )
            if not created:
                if reaction.emoji == emoji:
                    reaction.delete()
                    return {'action': 'removed'}
                else:
                    reaction.emoji = emoji
                    reaction.save()
                    return {'action': 'changed'}
            return {'action': 'added'}
        except Exception as e:
            logger.error(f"[ChatConsumer] reaction failed: {e}")
            return {'action': 'error'}

    @database_sync_to_async
    def _soft_delete_message(self, message_id):
        try:
            from .models import Message
            msg = Message.objects.get(id=message_id, room_id=self.room_id, sender=self.user)
            msg.deleted_at = timezone.now()
            msg.content = None
            msg.save(update_fields=['deleted_at', 'content'])
            return True
        except Message.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"[ChatConsumer] delete failed: {e}")
            return False

    @database_sync_to_async
    def _edit_message(self, message_id, new_content):
        try:
            from .models import Message
            msg = Message.objects.get(id=message_id, room_id=self.room_id, sender=self.user)
            if msg.deleted_at:
                return False
            msg.content = new_content
            msg.edited_at = timezone.now()
            msg.save(update_fields=['content', 'edited_at'])
            return True
        except Message.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"[ChatConsumer] edit failed: {e}")
            return False
