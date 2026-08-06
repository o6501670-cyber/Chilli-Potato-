from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClientViewSet
from .app_views import client_app_login, client_app_data, client_app_update_profile, client_app_contact

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='clients')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/app/login/', client_app_login, name='client_app_login'),
    path('api/app/data/', client_app_data, name='client_app_data'),
    path('api/app/update_profile/', client_app_update_profile, name='client_app_update_profile'),
    path('api/app/contact/', client_app_contact, name='client_app_contact'),
]
