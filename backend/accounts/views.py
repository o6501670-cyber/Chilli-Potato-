from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from django.conf import settings
import logging
import os
from datetime import timedelta
from django.utils import timezone

from .models import CustomUser, Message
from .serializers import UserSerializer, MessageSerializer, UserChatSerializer
from .access import has_action_permission, can_access_center
from .permissions import RoleActionPermission
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleActionPermission]
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = CustomUser.objects.all().order_by('full_name')
        
        role = getattr(user, 'role', None)
        is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
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
            else:
                queryset = queryset.none()
                
        return queryset

    def _require_write(self, action):
        if not has_action_permission(self.request.user, 'admin', 'users', action):
            raise PermissionDenied('You do not have permission to modify users.')

    def _validate_centers(self, validated_data):
        for center in ([validated_data.get('center')] if validated_data.get('center') else []):
            if not can_access_center(self.request.user, center):
                raise PermissionDenied('You cannot assign users to another center.')
        for center in validated_data.get('centers', []) or []:
            if not can_access_center(self.request.user, center):
                raise PermissionDenied('You cannot assign users to another center.')

    def perform_create(self, serializer):
        self._require_write('create')
        self._validate_centers(serializer.validated_data)
        serializer.save()

    def perform_update(self, serializer):
        self._require_write('update')
        self._validate_centers(serializer.validated_data)
        serializer.save()

    def perform_destroy(self, instance):
        self._require_write('delete')
        instance.delete()


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        max_age_days = getattr(settings, 'API_TOKEN_MAX_AGE_DAYS', 30)
        if timezone.now() - token.created > timedelta(days=max_age_days):
            token.delete()
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
        from django.db.models import Subquery, OuterRef
        
        last_message_subquery = Message.objects.filter(
            Q(sender=request.user, receiver_id=OuterRef('pk')) |
            Q(sender_id=OuterRef('pk'), receiver=request.user)
        ).order_by('-timestamp')

        if request.user.is_superuser:
            users = CustomUser.objects.exclude(id=request.user.id)
        else:
            users = CustomUser.objects.filter(is_superuser=True)

        users = users.select_related('center').prefetch_related('centers').annotate(
            last_message_content=Subquery(last_message_subquery.values('content')[:1]),
            last_message_time_annotated=Subquery(last_message_subquery.values('timestamp')[:1]),
            last_message_image=Subquery(last_message_subquery.values('image')[:1])
        )

        serializer = UserChatSerializer(users, many=True)
        data = serializer.data

        import datetime
        epoch = datetime.datetime.min

        for i, user_model in enumerate(users):
            user_data = data[i]
            if user_model.last_message_time_annotated:
                content = user_model.last_message_content
                image = user_model.last_message_image
                user_data['last_message'] = content if content else ('[Image]' if image else None)
                user_data['last_message_time'] = user_model.last_message_time_annotated
            else:
                user_data['last_message'] = None
                user_data['last_message_time'] = None

        data.sort(
            key=lambda x: x['last_message_time'] if x['last_message_time'] else epoch,
            reverse=True
        )

        logger.info(f"Chat users returned: {len(data)}")

        return Response(data)


class UnreadMessageCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(receiver=request.user, is_read=False).count()
        return Response({'count': count})


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MessageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        other_user_id = self.request.query_params.get('user_id')

        if other_user_id:
            # Mark incoming messages as read
            Message.objects.filter(
                sender_id=other_user_id, receiver=user, is_read=False
            ).update(is_read=True)

            return Message.objects.filter(
                Q(sender=user, receiver_id=other_user_id) |
                Q(sender_id=other_user_id, receiver=user)
            ).order_by('timestamp')

        return Message.objects.none()

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
