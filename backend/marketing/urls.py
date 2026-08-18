from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MembershipViewSet,
    PackageViewSet,
    PromotionViewSet,
    ValueCardViewSet,
    WhatsAppMessageViewSet,
)

router = DefaultRouter()
router.register(r'whatsapp', WhatsAppMessageViewSet, basename='whatsapp')
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'cards', ValueCardViewSet, basename='card')
router.register(r'memberships', MembershipViewSet, basename='membership')
router.register(r'packages', PackageViewSet, basename='package')

urlpatterns = [
    path('api/', include(router.urls)),
]
