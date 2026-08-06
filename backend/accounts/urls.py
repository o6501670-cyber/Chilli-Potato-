from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomAuthToken, UserViewSet, MessageViewSet, ChatUserListView, UnreadMessageCountView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'chat/messages', MessageViewSet, basename='chat-messages')

urlpatterns = [
    path('api/login/', CustomAuthToken.as_view(), name='api_login'),
    path('api/chat/users/', ChatUserListView.as_view(), name='chat-users'),
    path('api/chat/unread/', UnreadMessageCountView.as_view(), name='chat-unread'),
    path('api/', include(router.urls)),
]
