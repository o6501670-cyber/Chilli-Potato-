from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SystemLogViewSet

router = DefaultRouter()
router.register(r'logs', SystemLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
