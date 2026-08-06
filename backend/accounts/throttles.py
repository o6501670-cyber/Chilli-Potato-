from rest_framework.throttling import AnonRateThrottle


class AppLoginRateThrottle(AnonRateThrottle):
    scope = 'app_login'
