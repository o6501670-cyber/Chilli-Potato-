"""Regression tests for the login throttle configuration.

LoginRateThrottle used a hardcoded `rate = '5/minute'` class attribute that
ignored REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] — deployments could not tune
it (and it throttled an entire NAT'd salon at 5 logins/minute). It now reads
its rate from the 'login' scope in settings.
"""
from django.test import TestCase
from rest_framework.settings import api_settings

from pos_backend.throttles import LoginRateThrottle


class LoginThrottleTests(TestCase):
    def test_uses_settings_scope_not_hardcoded_rate(self):
        # The bug fix: no more hardcoded `rate = '5/minute'` class override;
        # the rate must come from DEFAULT_THROTTLE_RATES['login'] via `scope`.
        self.assertEqual(LoginRateThrottle.scope, 'login')
        throttle = LoginRateThrottle()
        self.assertEqual(
            throttle.get_rate(),
            api_settings.DEFAULT_THROTTLE_RATES.get('login'),
        )
