from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django.db.models import Q
import json

from .models import CustomUser, Message
from .serializers import UserSerializer, MessageSerializer, UserChatSerializer


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

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Rotate the token at login. Returning an existing expired token made a
        # successful login unusable and keeping the same token indefinitely
        # increased the impact of a leaked credential.
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
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
        
        # Fetch rooms and participants in two queries rather than one query per
        # room during serializer display-name generation.
        rooms = request.user.chat_rooms.prefetch_related('participants').all()
        
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

class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        room_id = self.request.query_params.get('user_id') # Note: frontend sends user_id, but it's actually room_id now
        
        if room_id:
            return Message.objects.filter(room_id=room_id, room__participants=user).order_by('timestamp')

        return Message.objects.none()

    def _get_member_room(self, room_id):
        from .models import ChatRoom
        try:
            return ChatRoom.objects.get(id=room_id, participants=self.request.user)
        except (ChatRoom.DoesNotExist, TypeError, ValueError):
            raise PermissionDenied("You are not a participant in this chat room.")

    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        room_id = request.data.get('room_id')
        if not room_id:
            return Response({'error': 'room_id required'}, status=400)
        room = self._get_member_room(room_id)
        Message.objects.filter(
            room=room, is_read=False
        ).exclude(sender=request.user).update(is_read=True)
        return Response({'status': 'ok'})

    @transaction.atomic
    def perform_create(self, serializer):
        room_id = (
            self.request.data.get('room_id')
            or self.request.query_params.get('user_id')  # legacy frontend name
        )
        if not room_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'room_id': 'A chat room is required.'})

        room = self._get_member_room(room_id)
        serializer.save(sender=self.request.user, room=room, receiver=None)

        # Mentions can add valid users to the current room, but malformed input
        # must fail the request instead of being silently ignored.
        mentions_data = self.request.data.get('mentions')
        if mentions_data:
            from rest_framework.exceptions import ValidationError
            try:
                mention_ids = json.loads(mentions_data) if isinstance(mentions_data, str) else mentions_data
                if not isinstance(mention_ids, list):
                    raise ValueError
                mention_ids = {int(mid) for mid in mention_ids}
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValidationError({'mentions': 'Expected a JSON list of user IDs.'}) from exc

            valid_ids = set(CustomUser.objects.filter(id__in=mention_ids, is_active=True).values_list('id', flat=True))
            if valid_ids != mention_ids:
                raise ValidationError({'mentions': 'One or more mentioned users do not exist or are inactive.'})
            room.participants.add(*valid_ids)
            if room.participants.count() > 2 and not room.is_group:
                room.is_group = True
                room.save(update_fields=['is_group', 'updated_at'])
