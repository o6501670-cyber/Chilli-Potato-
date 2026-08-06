from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.db.models import OuterRef, Subquery, Sum, DecimalField, Value
from django.db.models.functions import Coalesce
from .models import Client, ClientMembership, ClientPackage, ClientValueCard
from .serializers import ClientSerializer
from staff.models import ServiceLog
from accounts.access import has_global_access, can_access_center
from accounts.permissions import RoleActionPermission

class ClientViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleActionPermission]
    queryset = Client.objects.all().select_related('center').prefetch_related(
        'memberships__membership',
        'packages__package',
        'value_cards__value_card'
    )
    serializer_class = ClientSerializer
    
    def get_queryset(self):
        user = self.request.user
        from billing.models import AdvancePayment, CashbackTransaction
        advance_total = (
            AdvancePayment.objects.filter(client_id=OuterRef('pk'))
            .values('client_id').annotate(total=Sum('amount')).values('total')[:1]
        )
        cashback_total = (
            CashbackTransaction.objects.filter(client_id=OuterRef('pk'))
            .values('client_id').annotate(total=Sum('amount')).values('total')[:1]
        )
        balance_field = DecimalField(max_digits=12, decimal_places=2)
        qs = super().get_queryset().filter(is_active=True).annotate(
            advance_balance_annotated=Coalesce(
                Subquery(advance_total, output_field=balance_field),
                Value(0), output_field=balance_field,
            ),
            cashback_balance_annotated=Coalesce(
                Subquery(cashback_total, output_field=balance_field),
                Value(0), output_field=balance_field,
            ),
        )
        
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                qs = qs.filter(center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                qs = qs.filter(center=user.center)
            else:
                return qs.none()
                
        q = self.request.query_params.get('q')
        phone = self.request.query_params.get('phone')
        center_id = self.request.query_params.get('center_id')
        if q:
            qs = qs.filter(models.Q(phone__icontains=q) | models.Q(first_name__icontains=q) | models.Q(last_name__icontains=q))
        elif phone:
            qs = qs.filter(phone__icontains=phone)
        if center_id:
            try:
                cid = int(center_id)
                qs = qs.filter(center_id=cid)
            except ValueError:
                pass
        return qs.order_by('-id')

    def perform_create(self, serializer):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        
        if not is_owner and not perms.get('all_centers', False):
            center = serializer.validated_data.get('center')
            if center:
                if user.centers.exists() and center not in user.centers.all():
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create clients for this center.")
                elif not user.centers.exists() and hasattr(user, 'center') and center != user.center:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create clients for this center.")
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        
        if not is_owner and not perms.get('all_centers', False):
            center = serializer.validated_data.get('center')
            if center:
                if user.centers.exists() and center not in user.centers.all():
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot move clients to this center.")
                elif not user.centers.exists() and hasattr(user, 'center') and center != user.center:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot move clients to this center.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        client = self.get_object()
        client.is_active = False
        client.save(update_fields=['is_active'])
        return Response(status=204)

    @action(detail=True, methods=['get'])
    def service_history(self, request, pk=None):
        client = self.get_object()
        logs = ServiceLog.objects.filter(invoice__client=client).exclude(invoice__status__in=['cancelled', 'refunded']).select_related('staff', 'center', 'invoice').order_by('-date', '-time')[:50]
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'date': log.date,
                'time': log.time,
                'service_name': log.service_name,
                'service_type': log.service_type,
                'price': log.price,
                'staff_name': (log.staff.first_name + ' ' + (log.staff.last_name or '')).strip() if log.staff else 'Unknown',
                'center_name': (log.center.display_name or log.center.center_name) if log.center else 'Unknown',
                'invoice_id': log.invoice.id if log.invoice else None
            })
        return Response(data)

    @action(detail=True, methods=['post'], url_path='carry-over')
    def carry_over(self, request, pk=None):
        client = self.get_object()
        data = request.data
        source_type = data.get('source_type')
        source_id = data.get('source_id')
        target_id = data.get('target_id')
        
        from django.db import transaction as db_transaction
        try:
            with db_transaction.atomic():
                if source_type == 'package':
                    source_pkg = ClientPackage.objects.select_for_update().get(id=source_id, client=client)
                    target_pkg = ClientPackage.objects.select_for_update().get(id=target_id, client=client)
                    
                    src_services = source_pkg.services_remaining or {}
                    tgt_services = target_pkg.services_remaining or {}
                    
                    for s_id, qty in src_services.items():
                        tgt_services[s_id] = tgt_services.get(s_id, 0) + qty
                    
                    target_pkg.services_remaining = tgt_services
                    target_pkg.save()
                    
                    source_pkg.is_active = False
                    source_pkg.services_remaining = {}
                    source_pkg.save()
                    
                elif source_type == 'value_card':
                    source_vc = ClientValueCard.objects.select_for_update().get(id=source_id, client=client)
                    target_vc = ClientValueCard.objects.select_for_update().get(id=target_id, client=client)
                    
                    target_vc.balance = float(target_vc.balance) + float(source_vc.balance)
                    target_vc.save()
                    
                    source_vc.is_active = False
                    source_vc.balance = 0
                    source_vc.save()
                    
                elif source_type == 'membership':
                    source_mem = ClientMembership.objects.get(id=source_id, client=client)
                    new_expiry = data.get('new_expiry')
                    if new_expiry:
                        source_mem.expiry_date = new_expiry
                        source_mem.save()
                else:
                    return Response({'error': 'Invalid source_type'}, status=400)
                    
            return Response({'status': 'success'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        client = self.get_object()
        from django.db.models import Sum, Max
        from billing.models import Invoice
        
        invoices = Invoice.objects.filter(client=client, status__in=['paid', 'partial'])
        ltv = invoices.aggregate(total=Sum('paid_amount'))['total'] or 0
        last_visit = invoices.aggregate(last=Max('created_at'))['last']

        return Response({
            'client_id': client.id,
            'name': client.full_name,   # FIXED: uses safe full_name property
            'phone': client.phone,
            'ltv': float(ltv),
            'last_visit': last_visit
        })

    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file uploaded'}, status=400)
        try:
            import pandas as pd
            if file_obj.name.endswith('.csv'):
                df = pd.read_csv(file_obj)
            elif file_obj.name.endswith('.xlsx'):
                df = pd.read_excel(file_obj)
            else:
                return Response({'error': 'Unsupported file format'}, status=400)
            df = df.fillna('')
            records = df.to_dict('records')
            created_count = 0
            user = request.user
            center = None
            if hasattr(user, 'center') and user.center:
                center = user.center
            elif user.centers.exists():
                center = user.centers.first()
            if not center and not has_global_access(user):
                return Response({'error': 'User is not assigned to a center.'}, status=403)
            
            # Load existing phones/emails into sets for O(1) duplicate checks
            # instead of per-row exists() queries (was N+1)
            existing_phones = set(Client.objects.values_list('phone', flat=True))
            existing_emails = set(Client.objects.exclude(email='').values_list('email', flat=True))
            
            to_create = []
            for row in records:
                phone = str(row.get('phone', '')).strip()
                if phone.endswith('.0'): phone = phone[:-2]
                if not phone or phone in existing_phones:
                    continue
                first_name = str(row.get('first_name', row.get('name', ''))).strip()
                last_name = str(row.get('last_name', '')).strip()
                if not last_name and ' ' in first_name:
                    parts = first_name.split(' ', 1)
                    first_name = parts[0]
                    last_name = parts[1]
                email = str(row.get('email', '')).strip()
                if email and email in existing_emails:
                    continue
                to_create.append(Client(
                    center=center,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    email=email,
                    gender=str(row.get('gender', '')).strip(),
                    notes=str(row.get('notes', '')).strip()
                ))
                existing_phones.add(phone)
                if email:
                    existing_emails.add(email)
            
            # Bulk create in chunks of 500 to keep memory bounded
            CHUNK = 500
            from django.db import transaction as db_tx
            with db_tx.atomic():
                for i in range(0, len(to_create), CHUNK):
                    chunk = to_create[i:i + CHUNK]
                    created = Client.objects.bulk_create(chunk, ignore_conflicts=True)
                    created_count += len(created)
            return Response({'message': f'Successfully imported {created_count} clients.'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)
