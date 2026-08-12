from django.contrib.auth.hashers import make_password, check_password
"""
Client App Views — Token-Secured API endpoints for the client mobile PWA.

Authentication flow:
  1. POST /clients/api/app/login/  → returns client data + auth_token
  2. All subsequent requests send: Header: X-Client-Token: <token>
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions, status
from rest_framework.response import Response
from django.core import signing as _signing
from .models import Client


# ─────────────────────────────────────────────────────────────────────────────
# Token Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_client_token(client):
    """Generate a signed 30-day token for the client app."""
    return _signing.dumps(
        {'client_id': client.id, 'pin_hash': str(client.app_pin)[-10:]},
        salt='client-app-token'
    )

def _verify_client_token(token):
    """Validate a client token. Returns Client or None."""
    try:
        data = _signing.loads(token, salt='client-app-token', max_age=86400 * 30)
        client = Client.objects.get(id=data['client_id'])
        if data.get('pin_hash') != str(client.app_pin)[-10:]:
            return None # Token invalid due to PIN change
        return client
    except Exception:
        return None

def _get_authenticated_client(request):
    """Extract and validate X-Client-Token header. Returns client or None."""
    token = request.headers.get('X-Client-Token') or request.query_params.get('_token')
    if not token:
        return None
    return _verify_client_token(token)


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────
from pos_backend.throttles import LoginRateThrottle
from rest_framework.decorators import throttle_classes

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@throttle_classes([LoginRateThrottle])
def client_app_login(request):
    """Client login. Returns client data + auth_token for subsequent requests."""
    phone = request.data.get('phone')
    pin = request.data.get('pin')

    if not phone:
        return Response({'error': 'Phone is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        client = Client.objects.get(phone=phone)
    except Client.DoesNotExist:
        return Response({'error': 'Invalid phone number or PIN'}, status=status.HTTP_401_UNAUTHORIZED)

    if not client.app_pin:
        return Response({'error': 'PIN has not been set yet. Please ask the front desk to set your PIN.'}, status=status.HTTP_400_BAD_REQUEST)
    elif client.app_pin == str(pin):
        from django.contrib.auth.hashers import make_password
        client.app_pin = make_password(str(pin))
        client.save(update_fields=['app_pin'])
    elif not check_password(str(pin), client.app_pin):
        return Response({'error': 'Invalid phone number or PIN'}, status=status.HTTP_401_UNAUTHORIZED)

    return Response({
        'id': client.id,
        'phone': client.phone,
        'first_name': client.first_name,
        'last_name': client.last_name,
        'full_name': client.full_name,
        'email': client.email,
        'gender': client.gender,
        'dnd_status': client.dnd_status,
        'auth_token': _generate_client_token(client),
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def client_app_data(request):
    """Return full client dashboard data. Requires X-Client-Token header."""
    client = _get_authenticated_client(request)
    if not client:
        return Response({'error': 'Unauthorized. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)

    # Balances — Memberships
    memberships = client.memberships.filter(is_active=True).select_related('membership')
    mem_data = [
        {'name': m.membership.name, 'expiry': m.expiry_date}
        for m in memberships
    ]

    # Value Cards
    value_cards = client.value_cards.filter(is_active=True).select_related('value_card')
    vc_data = [
        {'title': v.value_card.title, 'balance': float(v.balance), 'expiry': v.expiry_date}
        for v in value_cards
    ]

    # Advance balance
    advances = client.advance_balance

    # Packages — resolve service IDs to names
    from services.models import ServiceMaster
    packages = client.packages.filter(is_active=True).select_related('package')
    # Build a service id→name map
    service_id_set = set()
    for p in packages:
        if isinstance(p.services_remaining, dict):
            service_id_set.update(p.services_remaining.keys())
    service_names = {}
    if service_id_set:
        service_qs = ServiceMaster.objects.filter(id__in=[
            int(sid) for sid in service_id_set if str(sid).isdigit()
        ]).values('id', 'name')
        service_names = {str(s['id']): s['name'] for s in service_qs}

    pkg_data = []
    for p in packages:
        remaining_named = {}
        if isinstance(p.services_remaining, dict):
            for sid, qty in p.services_remaining.items():
                sname = service_names.get(str(sid), f'Service #{sid}')
                remaining_named[sname] = qty
        pkg_data.append({
            'name': p.package.name if p.package else 'Custom Package',
            'remaining': remaining_named,
            'expiry': p.expiry_date,
        })

    # Appointments
    from appointments.models import Appointment
    upcoming_appts = (
        Appointment.objects
        .filter(client=client, status='Scheduled')
        .order_by('date', 'start_time')
    )
    appt_data = [
        {
            'id': a.id,
            'date': a.date,
            'start_time': a.start_time,
            'center_name': a.center.display_name if a.center else '',
        }
        for a in upcoming_appts
    ]

    # Visit History
    from staff.models import ServiceLog
    history = (
        ServiceLog.objects
        .filter(invoice__client=client)
        .select_related('staff', 'center')
        .order_by('-date', '-time')[:100]  # cap at 100 most recent entries
    )
    hist_data = [
        {
            'date': log.date,
            'service_name': log.service_name,
            'staff_name': (
                (log.staff.first_name + ' ' + (log.staff.last_name or '')).strip()
                if log.staff else 'Unknown'
            ),
            'center_name': (log.center.display_name or log.center.center_name) if log.center else '',
            'price': float(log.price),
        }
        for log in history
    ]

    return Response({
        'balances': {
            'memberships': mem_data,
            'value_cards': vc_data,
            'advances': advances,
            'packages': pkg_data,
        },
        'appointments': appt_data,
        'history': hist_data,
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def client_app_update_profile(request):
    """Update email, DND status, or PIN. Requires X-Client-Token header."""
    client = _get_authenticated_client(request)
    if not client:
        return Response({'error': 'Unauthorized. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)

    updated_fields = []
    email = request.data.get('email')
    dnd_status = request.data.get('dnd_status')
    pin = request.data.get('pin')

    if email is not None:
        client.email = email
        updated_fields.append('email')
    if dnd_status is not None:
        client.dnd_status = dnd_status
        updated_fields.append('dnd_status')
    if pin is not None:
        client.app_pin = pin
        updated_fields.append('app_pin')

    if updated_fields:
        client.save(update_fields=updated_fields)

    return Response({'success': True})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def client_app_contact(request):
    """Contact form endpoint. Requires X-Client-Token header."""
    client = _get_authenticated_client(request)
    if not client:
        return Response({'error': 'Unauthorized. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({'success': True, 'message': 'Message sent successfully.'})
