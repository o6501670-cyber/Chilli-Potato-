from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from django.conf import settings
import logging
import os

from .models import CustomUser, Message, ChatRoom, MessageReaction
from .serializers import UserSerializer, MessageSerializer, UserChatSerializer, MessageReactionSerializer

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = CustomUser.objects.all().select_related('role', 'center').prefetch_related('centers').order_by('full_name')
        
        role = getattr(user, 'role', None)
        is_owner = IsOwner.check_is_owner(user)
        perms = getattr(role, 'permissions', {}) or {}

        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                queryset = queryset.filter(
                    Q(center__in=user.centers.all()) | Q(centers__in=user.centers.all())
                ).distinct()
            elif hasattr(user, 'center') and user.center:
                queryset = queryset.filter(
                    Q(center=user.center) | Q(centers=user.center)
                ).distinct()
                
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        role = getattr(user, 'role', None)
        is_owner = IsOwner.check_is_owner(user)
        if not is_owner:
            raise PermissionDenied("Only owners can create users.")
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        role = getattr(user, 'role', None)
        is_owner = IsOwner.check_is_owner(user)
        if not is_owner:
            for f in ('role', 'center', 'centers'):
                serializer.validated_data.pop(f, None)
            if serializer.instance.pk != user.pk:
                raise PermissionDenied("You may only edit your own profile.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        role = getattr(user, 'role', None)
        is_owner = IsOwner.check_is_owner(user)
        if not is_owner:
            raise PermissionDenied("Only owners can delete users.")
        instance.delete()


from pos_backend.throttles import LoginRateThrottle
from pos_backend.permissions import IsOwner

class CustomAuthToken(ObtainAuthToken):
    throttle_classes = [LoginRateThrottle]
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'full_name': user.full_name,
            'is_superuser': user.is_superuser,
            'role': user.role.name if user.role else None,
            'permissions': user.role.permissions if user.role else {},
            'center_id': user.center.id if user.center else None,
            'centers': list(user.centers.values_list('id', flat=True)),
        })


class ChatUserListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import ChatRoom
        from .serializers import ChatRoomSerializer
        from django.db.models import Subquery, OuterRef
        
        # Now fetch all rooms for the user
        rooms = request.user.chat_rooms.all()
        
        last_message_subquery = Message.objects.filter(
            room_id=OuterRef('pk')
        ).order_by('-timestamp')
        
        rooms = rooms.annotate(
            last_message_content=Subquery(last_message_subquery.values('content')[:1]),
            last_message_time_annotated=Subquery(last_message_subquery.values('timestamp')[:1]),
            last_message_image=Subquery(last_message_subquery.values('image')[:1])
        )
        
        serializer = ChatRoomSerializer(rooms, many=True, context={'request': request})
        data = serializer.data
        
        import datetime
        epoch = datetime.datetime.min

        for i, room_model in enumerate(rooms):
            room_data = data[i]
            # Map room_data to what the frontend expects!
            room_data['full_name'] = room_data.get('display_name')
            room_data['email'] = '' # Just to avoid undefined
            room_data['center_name'] = 'Group' if room_data.get('is_group') else 'Private'
            
            if room_model.last_message_time_annotated:
                content = room_model.last_message_content
                image = room_model.last_message_image
                room_data['last_message'] = content if content else ('[Image]' if image else None)
                room_data['last_message_time'] = room_model.last_message_time_annotated
            else:
                room_data['last_message'] = None
                room_data['last_message_time'] = None

        data.sort(
            key=lambda x: x['last_message_time'] if x['last_message_time'] else epoch,
            reverse=True
        )
        
        return Response(data)

class UnreadMessageCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(room__participants=request.user, is_read=False).exclude(sender=request.user).count()
        return Response({'count': count})

from rest_framework.pagination import CursorPagination

class MessageCursorPagination(CursorPagination):
    ordering = '-timestamp'
    page_size = 50

class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = MessageCursorPagination

    def get_queryset(self):
        user = self.request.user
        room_id = self.request.query_params.get('room_id') or self.request.query_params.get('user_id')
        
        if room_id:
            return Message.objects.filter(room_id=room_id, room__participants=user)

        return Message.objects.none()

    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        user = self.request.user
        room_id = self.request.data.get('room_id')
        if room_id:
            Message.objects.filter(
                room_id=room_id, status__in=[Message.STATUS_SENT, Message.STATUS_DELIVERED]
            ).exclude(sender=user).update(status=Message.STATUS_READ, is_read=True)
            return Response({'status': 'ok'})
        return Response({'error': 'room_id required'}, status=400)

    def perform_create(self, serializer):
        room_id = self.request.data.get('room_id') or self.request.query_params.get('user_id') or self.request.data.get('receiver')
        
        if not room_id:
            raise PermissionDenied("room_id is required")
            
        room = ChatRoom.objects.filter(id=room_id, participants=self.request.user).first()
        if not room:
            raise PermissionDenied("You are not a participant of this room")
            
        serializer.save(sender=self.request.user, room=room, receiver=None, status=Message.STATUS_SENT)
        room.updated_at = __import__('django').utils.timezone.now()
        room.save(update_fields=['updated_at'])

class MessageReactionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageReactionSerializer

    def get_queryset(self):
        user = self.request.user
        return MessageReaction.objects.filter(message__room__participants=user)

    def perform_create(self, serializer):
        message = serializer.validated_data.get('message')
        if not ChatRoom.objects.filter(id=message.room_id, participants=self.request.user).exists():
            raise PermissionDenied("You are not a participant of this room")
        
        # Check if reaction already exists
        existing = MessageReaction.objects.filter(message=message, user=self.request.user).first()
        if existing:
            if existing.emoji == serializer.validated_data.get('emoji'):
                existing.delete()
                raise serializers.ValidationError({"status": "removed"})
            else:
                existing.emoji = serializer.validated_data.get('emoji')
                existing.save()
                raise serializers.ValidationError({"status": "updated", "emoji": existing.emoji})
        else:
            serializer.save(user=self.request.user)
