from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Throttles login attempts per client IP.

    The rate comes from settings: REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login']
    (override with the LOGIN_THROTTLE_RATE env var), so it can be tuned per
    deployment instead of being hardcoded.
    """
    scope = 'login'
