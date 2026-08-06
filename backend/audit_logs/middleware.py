import json
import re
import logging
import threading
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from django.utils.deprecation import MiddlewareMixin
from django.db import OperationalError
from .models import SystemLog

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='audit_log')

SENSITIVE_KEYS = {
    'password', 'pin', 'token', 'auth_token',
    'new_password', 'confirm_password', 'secret',
    'app_password', 'app_pin', 'aadhar_number', 'card_number',
}

EXCLUDED_PREFIXES = (
    '/audit_logs/',
    '/admin/',
    '/static/',
    '/media/',
)

MODULE_RULES = [
    (r'/accounts/api/login',                'USERS',        'Session'),
    (r'/accounts/api/logout',               'USERS',        'Session'),
    (r'/accounts/api/users',                'USERS',        'User'),
    (r'/salon_admin/api/centers',           'CENTRES',      'Centre'),
    (r'/salon_admin/api/roles',             'ROLES',        'Role'),
    (r'/salon_admin/api/dashboard',         'DASHBOARD',    'Dashboard'),
    (r'/staff/api/members',                 'STAFF',        'Staff Member'),
    (r'/staff/api/logs',                    'STAFF',        'Service Log'),
    (r'/staff/api/consumptions',            'STAFF',        'Consumption'),
    (r'/staff/api/payrolls',                'STAFF',        'Payroll'),
    (r'/staff/api/transfers',               'STAFF',        'Transfer'),
    (r'/staff/api/tools',                   'STAFF',        'Tool'),
    (r'/staff/api/designations',            'STAFF',        'Designation'),
    (r'/staff/api/reports',                 'STAFF',        'Staff Report'),
    (r'/clients/api/app/login',             'CLIENTS',      'Client Session'),
    (r'/clients/api/clients',               'CLIENTS',      'Client'),
    (r'/services/api/master',               'SERVICES',     'Service'),
    (r'/services/api/center',               'SERVICES',     'Centre Service Override'),
    (r'/inventory/api/products/checkout',   'INVENTORY',    'Stock Checkout'),
    (r'/inventory/api/products/audit',      'INVENTORY',    'Stock Audit'),
    (r'/inventory/api/products',            'INVENTORY',    'Product'),
    (r'/inventory/api/vendors',             'INVENTORY',    'Vendor'),
    (r'/inventory/api/purchase-orders',     'INVENTORY',    'Purchase Order'),
    (r'/inventory/api/lots',                'INVENTORY',    'Product Lot'),
    (r'/inventory/api/stock-transactions',  'INVENTORY',    'Stock Transaction'),
    (r'/billing/invoices',                  'BILLING',      'Invoice'),
    (r'/billing/advances',                  'BILLING',      'Advance'),
    (r'/appointments/api/appointments',     'APPOINTMENTS', 'Appointment'),
    (r'/marketing/api/promotions',          'MARKETING',    'Promotion'),
    (r'/marketing/api/cards',               'MARKETING',    'Value Card'),
    (r'/marketing/api/memberships',         'MARKETING',    'Membership'),
    (r'/marketing/api/packages',            'MARKETING',    'Package'),
    (r'/marketing/api/whatsapp',            'MARKETING',    'WhatsApp Campaign'),
    (r'/finance/api/daily-closing',         'FINANCE',      'Daily Closing'),
    (r'/finance/api/petty-cash',            'FINANCE',      'Petty Cash'),
    (r'/finance/api/shifts',                'FINANCE',      'Shift'),
    (r'/finance/api/incentives',            'FINANCE',      'Incentive'),
    (r'/finance/api/refunds',               'FINANCE',      'Refund'),
]


# ─── Device & Browser parsing (using user-agents library) ─────────────────────
def _parse_ua(ua_string: str) -> dict:
    """Returns dict with device_type, browser, os_info."""
    if not ua_string:
        return {'device_type': 'Unknown', 'browser': 'Unknown', 'os_info': 'Unknown'}
    try:
        import user_agents
        ua = user_agents.parse(ua_string)

        # Device type
        if ua.is_mobile:
            dtype = 'Mobile'
        elif ua.is_tablet:
            dtype = 'Tablet'
        elif ua.is_pc:
            dtype = 'Desktop / Laptop'
        elif ua.is_bot:
            dtype = 'Bot'
        else:
            dtype = 'Unknown'

        # Browser: name + major version
        browser_name = ua.browser.family or ''
        browser_ver  = str(ua.browser.version[0]) if ua.browser.version and ua.browser.version[0] else ''
        browser = f'{browser_name} {browser_ver}'.strip() if browser_name else 'Unknown'

        # OS: e.g. "Windows 10", "macOS 14", "iOS 17", "Android 14"
        os_family  = ua.os.family or ''
        os_ver     = ua.os.version_string or ''
        os_info    = f'{os_family} {os_ver}'.strip() if os_family else 'Unknown'

        return {'device_type': dtype, 'browser': browser, 'os_info': os_info}
    except Exception:
        return {'device_type': 'Unknown', 'browser': 'Unknown', 'os_info': 'Unknown'}


def _is_private_ip(ip: str) -> bool:
    """Check if an IP is private/loopback (no geo lookup possible)."""
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return True


@lru_cache(maxsize=512)
def _cached_geo(ip: str) -> dict:
    """Lookup city/country from IP using freeipapi.com (free, HTTPS)."""
    if not ip or _is_private_ip(ip):
        return {'city': 'Local Network', 'region': '', 'country': 'Local', 'country_code': ''}
    try:
        import requests as req
        resp = req.get(
            f'https://freeipapi.com/api/json/{ip}',
            timeout=3
        )
        data = resp.json()
        if data.get('cityName') or data.get('countryName'):
            return {
                'city':         data.get('cityName', ''),
                'region':       data.get('regionName', ''),
                'country':      data.get('countryName', ''),
                'country_code': data.get('countryCode', ''),
            }
    except Exception:
        pass
    return {'city': '', 'region': '', 'country': '', 'country_code': ''}


# ─── Token & Centre lookups (LRU-cached) ──────────────────────────────────────
@lru_cache(maxsize=256)
def _cached_user_from_token(token_key: str):
    """Returns tuple of user info or None. Cached per token key."""
    try:
        from rest_framework.authtoken.models import Token
        t = Token.objects.select_related('user', 'user__role', 'user__center').get(key=token_key)
        u = t.user
        role_str = ''
        try:
            role_str = str(u.role) if u.role else ('Super Admin' if u.is_superuser else '')
        except Exception:
            role_str = 'Super Admin' if u.is_superuser else ''
        c_id   = u.center_id if hasattr(u, 'center_id') else None
        c_name = u.center.center_name if (hasattr(u, 'center') and u.center) else ''
        return (u.pk, getattr(u, 'full_name', '') or '', u.email or '',
                role_str, c_id, c_name)
    except Exception as e:
        logger.error(f"Error resolving user from token: {e}")
        return None


@lru_cache(maxsize=64)
def _cached_centre_name(center_id: int) -> str:
    try:
        from salon_admin.models import Center
        c = Center.objects.filter(pk=center_id).values('center_name').first()
        return c['center_name'] if c else ''
    except Exception:
        return ''


def _get_action(method: str, path: str) -> str:
    p = path.lower()
    if 'login'          in p: return 'LOGIN'
    if 'logout'         in p: return 'LOGOUT'
    if 'refund'         in p: return 'REFUND'
    if 'cancel'         in p: return 'CANCEL'
    if 'close_shift'    in p: return 'CLOSE_SHIFT'
    if 'lock'           in p: return 'LOCK'
    if 'mark_paid'      in p: return 'MARK_PAID'
    if '/pay/'          in p: return 'PAYMENT'
    if 'override'       in p: return 'OVERRIDE'
    if 'carry-over'     in p: return 'CARRY_OVER'
    if 'checkout'       in p: return 'CHECKOUT'
    if 'audit'          in p: return 'AUDIT'
    if 'send_campaign'  in p: return 'CAMPAIGN'
    if method == 'POST':      return 'CREATE'
    if method in ('PUT', 'PATCH'): return 'UPDATE'
    if method == 'DELETE':    return 'DELETE'
    return method


def _get_module_entity(path: str):
    for pattern, module, entity in MODULE_RULES:
        if re.search(pattern, path):
            return module, entity
    return 'SYSTEM', 'Request'


def _extract_entity_id(path: str) -> str:
    for part in reversed(path.rstrip('/').split('/')):
        if part.isdigit():
            return part
    return ''


def _sanitise(body_bytes: bytes) -> dict:
    """Redact sensitive keys recursively before persisting request bodies."""
    if not body_bytes:
        return {}

    def redact(value):
        if isinstance(value, dict):
            return {
                key: ('***' if str(key).lower() in SENSITIVE_KEYS else redact(item))
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [redact(item) for item in value]
        return value

    try:
        data = json.loads(body_bytes)
        return redact(data) if isinstance(data, dict) else {}
    except Exception:
        return {}


def _human_description(action, entity, entity_id, who, body, centre_name):
    verb = {
        'LOGIN':       'logged in',
        'LOGOUT':      'logged out',
        'CREATE':      f'created a new {entity}',
        'UPDATE':      f'updated {entity}',
        'DELETE':      f'deleted {entity}',
        'CANCEL':      f'cancelled {entity}',
        'REFUND':      f'processed a Refund on {entity}',
        'CLOSE_SHIFT': 'closed a Shift',
        'LOCK':        f'locked {entity}',
        'MARK_PAID':   f'marked {entity} as Paid',
        'PAYMENT':     f'recorded a Payment on {entity}',
        'OVERRIDE':    f'overrode price for {entity}',
        'CARRY_OVER':  'carried over client perks',
        'CHECKOUT':    'performed Stock Checkout',
        'AUDIT':       'performed Stock Audit',
        'CAMPAIGN':    'sent a WhatsApp Campaign',
    }.get(action, f'performed {action} on {entity}')

    name_hints = ['name', 'full_name', 'first_name', 'phone', 'email', 'title', 'code']
    hint = ''
    for h in name_hints:
        v = body.get(h, '')
        if v and str(v) not in ('***', '', 'None'):
            hint = f'"{v}"'
            break
    if not hint and entity_id:
        hint = f'(ID {entity_id})'

    loc = f' at {centre_name}' if centre_name else ''
    if action in ('LOGIN', 'LOGOUT', 'CAMPAIGN', 'CHECKOUT', 'AUDIT', 'CARRY_OVER'):
        return f'{who} {verb}{loc}.'
    return (f'{who} {verb} {hint}{loc}.' if hint else f'{who} {verb}{loc}.').strip()


# ─── Background log writer ────────────────────────────────────────────────────
def _write_log(token_key, session_user_pk, path, method, body_bytes, ip, ua_string, staff_token=None, client_token=None):
    try:
        # ── User resolution ───────────────────────────────────────────────────
        user_obj = user_pk = user_name = user_email = user_role = None
        center_id = center_name = ''

        if token_key:
            cached = _cached_user_from_token(token_key)
            if cached:
                user_pk, user_name, user_email, user_role, center_id, center_name = cached
                # Get a fresh DB ref for the FK (never store ORM objects in lru_cache)
                try:
                    from django.contrib.auth import get_user_model
                    user_obj = get_user_model().objects.get(pk=user_pk)
                except Exception:
                    user_obj = None
        elif staff_token:
            try:
                from staff.views import _verify_staff_token
                staff = _verify_staff_token(staff_token)
                if staff:
                    user_pk = staff.id
                    user_name = f"{staff.first_name} {staff.last_name or ''}".strip()
                    user_email = staff.phone or ''
                    user_role = 'Staff'
                    center_id = staff.center_id
                    center_name = staff.center.center_name if staff.center else ''
            except Exception:
                pass
        elif client_token:
            try:
                from clients.app_views import _verify_client_token
                client = _verify_client_token(client_token)
                if client:
                    user_pk = client.id
                    user_name = client.full_name or ''
                    user_email = client.phone or ''
                    user_role = 'Client'
            except Exception:
                pass
        elif session_user_pk:
            try:
                from django.contrib.auth import get_user_model
                u = get_user_model().objects.select_related('role', 'center').get(pk=session_user_pk)
                user_obj   = u
                user_pk    = u.pk
                user_name  = getattr(u, 'full_name', '') or ''
                user_email = u.email or ''
                user_role  = str(u.role) if (hasattr(u, 'role') and u.role) else (
                    'Super Admin' if u.is_superuser else '')
                center_id   = u.center_id if hasattr(u, 'center_id') else None
                center_name = getattr(u.center, 'center_name', '') if (hasattr(u, 'center') and u.center) else ''
            except Exception:
                pass

        # ── Body & action ─────────────────────────────────────────────────────
        body       = _sanitise(body_bytes)
        action     = _get_action(method, path)
        module, entity = _get_module_entity(path)
        entity_id  = _extract_entity_id(path)

        # Centre from body if not already known
        if not center_id:
            bc = body.get('center_id') or body.get('center')
            if bc:
                try:
                    center_id   = int(bc)
                    center_name = _cached_centre_name(center_id)
                except (TypeError, ValueError):
                    pass

        # If it's a login, we can also extract the user email from the body as a fallback
        if action == 'LOGIN' and not user_email:
            user_email = body.get('username') or body.get('email') or ''

        who   = user_name or user_email or 'System'
        human = _human_description(action, entity, entity_id, who, body, center_name)

        # ── Device info ───────────────────────────────────────────────────────
        device_info = _parse_ua(ua_string)

        # ── Geolocation from IP ───────────────────────────────────────────────
        geo = _cached_geo(ip) if ip else {}

        # ── Save to DB ────────────────────────────────────────────────────────
        SystemLog.objects.create(
            user=user_obj,
            user_name=user_name or '',
            user_email=user_email or '',
            user_role=user_role or '',
            user_id_snapshot=user_pk,
            center_id=center_id or None,
            center_name=center_name or '',
            action=action,
            module=module,
            entity_type=entity,
            entity_id=entity_id,
            human_description=human,
            path=path,
            description=json.dumps(body) if body else '',
            ip_address=ip or None,
            device_info=ua_string,
            device_type=device_info.get('device_type', ''),
            browser=device_info.get('browser', ''),
            os_info=device_info.get('os_info', ''),
            geo_city=geo.get('city', ''),
            geo_region=geo.get('region', ''),
            geo_country=geo.get('country', ''),
            geo_country_code=geo.get('country_code', ''),
        )
    except OperationalError as e:
        # SQLite serialises writes and can briefly be locked by Django's test
        # transaction. Audit failure must never turn into noisy application
        # errors or affect the request that already completed.
        logger.debug('audit log write skipped: %s', e)
    except Exception as e:
        logger.error(f'audit_log _write_log error: {e}', exc_info=True)


class AuditLogMiddleware(MiddlewareMixin):
    """Zero-latency audit middleware — DB work runs in background thread."""

    def process_request(self, request):
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            try:
                _ = request.body
            except Exception:
                pass

    def process_response(self, request, response):
        method = request.method
        if method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return response

        path = getattr(request, 'path', '')
        if any(path.startswith(p) for p in EXCLUDED_PREFIXES):
            return response

        try:
            # Try to get token from Authorization header
            token_key = ''
            auth = request.META.get('HTTP_AUTHORIZATION', '')
            if auth.startswith('Token '):
                token_key = auth[6:].strip()

            # If it's a login, the token is returned in the response
            if not token_key and hasattr(response, 'data') and isinstance(response.data, dict):
                token_key = response.data.get('token', '')

            # Check for Staff and Client app tokens
            staff_token = request.headers.get('X-Staff-Token') or request.META.get('HTTP_X_STAFF_TOKEN', '')
            client_token = request.headers.get('X-Client-Token') or request.META.get('HTTP_X_CLIENT_TOKEN', '')

            # If it's a login response that returned auth_token for apps
            if hasattr(response, 'data') and isinstance(response.data, dict) and 'auth_token' in response.data:
                if 'staff' in path.lower():
                    staff_token = response.data.get('auth_token', '')
                elif 'client' in path.lower():
                    client_token = response.data.get('auth_token', '')
                
            session_user_pk = None
            if not token_key and not staff_token and not client_token and hasattr(request, 'user') and request.user and request.user.is_authenticated:
                session_user_pk = request.user.pk

            body_bytes = bytes(getattr(request, '_body', None) or b'')

            xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
            ip  = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')
            ua  = request.META.get('HTTP_USER_AGENT', '')[:600]

            # Fire and forget — response returns IMMEDIATELY, logging happens in background
            _executor.submit(_write_log, token_key, session_user_pk,
                             path, method, body_bytes, ip, ua, staff_token, client_token)

        except Exception as e:
            logger.error(f'AuditLogMiddleware submit error: {e}')

        return response
