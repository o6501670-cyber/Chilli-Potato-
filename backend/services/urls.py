from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CenterServiceViewSet, ServiceMasterViewSet

router = DefaultRouter()
router.register(r'master', ServiceMasterViewSet, basename='servicemaster')
router.register(r'center', CenterServiceViewSet, basename='centerservice')

urlpatterns = [
    path('api/', include(router.urls)),
]
