"""Authentication with bounded token lifetime for staff/admin sessions."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ExpiringTokenAuthentication(TokenAuthentication):
    """Reject DRF tokens older than the configured session lifetime."""

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        max_age_days = int(getattr(settings, 'API_TOKEN_MAX_AGE_DAYS', 30))
        created = token.created
        if timezone.now() - created > timedelta(days=max_age_days):
            token.delete()
            raise AuthenticationFailed('Authentication token has expired.')
        if not user.is_active:
            raise AuthenticationFailed('User account is inactive.')
        return user, token
