from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from billing.models import InvoiceItem
from pos_backend.permissions import IsOwner
from salon_admin.models import Center

from .models import (
    Membership,
    Package,
    Promotion,
    PromotionUsage,
    ValueCard,
    WhatsAppMessage,
)
from .serializers import (
    MembershipSerializer,
    PackageSerializer,
    PromotionSerializer,
    ValueCardSerializer,
    WhatsAppMessageSerializer,
)


class MarketingBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        is_owner = IsOwner.check_is_owner(user)
        perms = getattr(user.role, 'permissions', {}) or {}
        is_all_centers = is_owner or perms.get('all_centers', False)

        # Only owners/all-center users can view inactive items — restrict the flag for others
        show_inactive = self.request.query_params.get('show_inactive', 'false').lower() == 'true'
        if not show_inactive or not is_all_centers:
            if hasattr(self.serializer_class.Meta.model, 'is_active'):
                queryset = queryset.filter(is_active=True)
        
        if is_all_centers:
            center_id = self.request.query_params.get('center_id')
            if center_id and center_id.lower() != 'null':
                # If they explicitly filter by center, we show center specific ones AND org level ones
                # Except for WhatsApp messages which don't have a 'level' field
                if hasattr(self.serializer_class.Meta.model, 'level'):
                    return queryset.filter(Q(center_id=center_id) | Q(level='Organisation'))
                else:
                    return queryset.filter(center_id=center_id)
            return queryset
            
        # Regular users can only see their own center's items (and org level items)
        if user.centers.exists():
            if hasattr(self.serializer_class.Meta.model, 'level'):
                return queryset.filter(Q(center__in=user.centers.all()) | Q(level='Organisation'))
            else:
                return queryset.filter(center__in=user.centers.all())
        elif hasattr(user, 'center') and user.center:
            if hasattr(self.serializer_class.Meta.model, 'level'):
                return queryset.filter(Q(center_id=user.center.id) | Q(level='Organisation'))
            else:
                return queryset.filter(center_id=user.center.id)
                
        # If user has no center and isn't owner, they see nothing
        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = IsOwner.check_is_owner(user)
        is_all_centers = is_owner or perms.get('all_centers', False)
        
        # Check if creating an org level item
        if 'level' in self.request.data and self.request.data['level'] == 'Organisation':
            if not is_all_centers:
                raise PermissionDenied("Only owners or users with all-center access can create organisation level items.")
            serializer.save(center=None)
            return
            
        # Creating center specific item
        if is_all_centers:
            serializer.save()
        else:
            # Regular user is forced to their own center
            kwargs = {}
            if user.centers.exists():
                kwargs['center'] = user.centers.first()
            elif getattr(user, 'center', None):
                kwargs['center'] = user.center
            else:
                raise PermissionDenied("User is not assigned to any center.")
                
            if hasattr(self.serializer_class.Meta.model, 'level'):
                kwargs['level'] = 'Center'
                
            serializer.save(**kwargs)

    def get_object(self):
        """
        Override to use the unfiltered base queryset when performing update/delete actions.
        This prevents 404 when trying to activate an item that is currently inactive
        (since inactive items are filtered out of the default queryset).
        """
        if self.action in ('update', 'partial_update', 'destroy', 'toggle_status'):
            # Use the raw model queryset, bypassing is_active / expired filters
            queryset = self.get_serializer_class().Meta.model.objects.all()
            obj = get_object_or_404(queryset, pk=self.kwargs['pk'])
            self.check_object_permissions(self.request, obj)
            return obj
        return super().get_object()

    def perform_update(self, serializer):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = IsOwner.check_is_owner(user)
        is_all_centers = is_owner or perms.get('all_centers', False)

        instance = serializer.instance
        if hasattr(instance, 'level') and instance.level == 'Organisation':
            if not is_all_centers:
                raise PermissionDenied("Only owners or users with all-center access can modify organisation level items.")

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = IsOwner.check_is_owner(user)
        is_all_centers = is_owner or perms.get('all_centers', False)

        if hasattr(instance, 'level') and instance.level == 'Organisation':
            if not is_all_centers:
                raise PermissionDenied("Only owners or users with all-center access can delete organisation level items.")

        instance.delete()

    @action(detail=True, methods=['patch'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        """Dedicated endpoint to toggle is_active. Always fetches by PK, bypassing active/expired filters."""
        obj = self.get_object()  # uses our overridden get_object which bypasses filters
        obj.is_active = not obj.is_active
        obj.save(update_fields=['is_active'])
        return Response({'id': obj.id, 'is_active': obj.is_active})


class WhatsAppMessageViewSet(MarketingBaseViewSet):
    queryset = WhatsAppMessage.objects.all().select_related('center').order_by('-created_at')
    serializer_class = WhatsAppMessageSerializer

    @action(detail=False, methods=['post'])
    def send_campaign(self, request):
        role_name = getattr(request.user.role, 'name', '').lower() if getattr(request.user, 'role', None) else ''
        if not request.user.is_superuser and role_name not in ['owner', 'marketing']:
            return Response({'error': 'Permission denied. Only owners and marketing staff can send campaigns.'}, status=status.HTTP_403_FORBIDDEN)

        center_id = request.data.get('center_id')
        message = request.data.get('message')

        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)


        from django.utils import timezone

        from clients.models import Client

        # Use .only() to avoid loading ALL client fields into RAM
        # Exclude DND clients
        base_qs = Client.objects.exclude(dnd_status__iexact='ON DND')
        if center_id and str(center_id).lower() != 'all':
            clients = base_qs.filter(
                center_id=center_id
            ).only('id', 'phone', 'first_name', 'last_name', 'center_id').select_related('center')
        else:
            clients = base_qs.only('id', 'phone', 'first_name', 'last_name', 'center_id').select_related('center')

        if not clients.exists():
            return Response({'error': 'No eligible clients found in the selected center (or all are on DND)'}, status=status.HTTP_404_NOT_FOUND)
            
        total_clients = clients.count()

        messages_created = []
        now = timezone.now()
        date_today = now.date()
        time_now = now.time()
        default_center = None  # cache to avoid repeated DB hit

        for client in clients.iterator(chunk_size=500):  # stream in chunks — never loads all into RAM
            if not client.phone:
                continue
            client_center = client.center
            if not client_center:
                if default_center is None:
                    default_center = Center.objects.first()
                client_center = default_center
            messages_created.append(WhatsAppMessage(
                center=client_center,
                date=date_today,
                time=time_now,
                client_name=client.full_name,
                client_phone=client.phone,
                message=message,
                status='Sent (Mock)'
            ))
            # Bulk-create every 1000 to avoid holding massive lists in memory
            if len(messages_created) >= 1000:
                WhatsAppMessage.objects.bulk_create(messages_created)
                messages_created = []

        if messages_created:
            WhatsAppMessage.objects.bulk_create(messages_created)

        return Response({
            'message': f'Campaign sent to {total_clients} clients',
            'count': total_clients
        })

class PromotionViewSet(MarketingBaseViewSet):
    queryset = Promotion.objects.all().select_related('center').order_by('-created_at')
    serializer_class = PromotionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        import datetime

        today = datetime.date.today()
        show_expired = self.request.query_params.get('show_expired', 'false').lower() == 'true'
        
        if not show_expired:
            qs = qs.filter(end_date__gte=today)
        return qs.order_by('-created_at')

    @action(detail=False, methods=['get'])
    def usage_report(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Get promotions visible to this user
        promotions = self.get_queryset()
        
        usage_qs = PromotionUsage.objects.filter(promotion__in=promotions)
        if start_date:
            usage_qs = usage_qs.filter(date__gte=start_date)
        if end_date:
            usage_qs = usage_qs.filter(date__lte=end_date)
            
        # Aggregate by promotion and center
        report = usage_qs.values('promotion', 'center__center_name', 'center__display_name').annotate(
            usage_count=Count('id'),
            total_revenue=Sum('revenue_generated')
        )
        
        # Build response with promotion details
        promo_dict = {p.id: p for p in promotions}
        data_map = {}
        for p in promotions:
            key = f"promo_{p.id}"
            data_map[key] = {
                'id': key,
                'name': p.name,
                'type': 'Promotion',
                'start_date': p.start_date,
                'end_date': p.end_date,
                'level': p.level,
                'status': 'Active' if p.is_active else 'Inactive',
                'count': 0,
                'revenue': 0,
                'center_breakdown': []
            }

        for row in report:
            promo = promo_dict.get(row['promotion'])
            if promo:
                key = f"promo_{promo.id}"
                cname = row.get('center__display_name') or row.get('center__center_name') or 'Organisation / All Centers'
                data_map[key]['count'] += row['usage_count']
                data_map[key]['revenue'] += (row['total_revenue'] or 0)
                data_map[key]['center_breakdown'].append({
                    'center_name': cname,
                    'count': row['usage_count'],
                    'revenue': (row['total_revenue'] or 0)
                })
        
        # Now fetch Memberships, Packages, Value Cards
        user = request.user
        center_id = request.headers.get('Center-Id')
        
        memberships = Membership.objects.all().select_related('center')
        packages = Package.objects.all().select_related('center')
        cards = ValueCard.objects.all().select_related('center')
        
        if (not user.role or user.role.name.lower() != 'owner') and not user.is_superuser:
            memberships = memberships.filter(Q(level='Organisation') | Q(center=user.center))
            packages = packages.filter(Q(level='Organisation') | Q(center=user.center))
            cards = cards.filter(Q(level='Organisation') | Q(center=user.center))
        else:
            if center_id and center_id != 'null':
                memberships = memberships.filter(Q(level='Organisation') | Q(center_id=center_id))
                packages = packages.filter(Q(level='Organisation') | Q(center_id=center_id))
                cards = cards.filter(Q(level='Organisation') | Q(center_id=center_id))
                
        mem_ct = ContentType.objects.get_for_model(Membership)
        pkg_ct = ContentType.objects.get_for_model(Package)
        card_ct = ContentType.objects.get_for_model(ValueCard)
        
        for m in memberships:
            key = f"membership_{m.id}"
            data_map[key] = {
                'id': key,
                'name': m.name,
                'type': 'Membership',
                'start_date': m.created_at.date() if hasattr(m, 'created_at') else None,
                'end_date': None,
                'level': m.level,
                'status': 'Active' if m.is_active else 'Inactive',
                'count': 0,
                'revenue': 0,
                'center_breakdown': []
            }

        for p in packages:
            key = f"package_{p.id}"
            data_map[key] = {
                'id': key,
                'name': p.name,
                'type': 'Package',
                'start_date': p.created_at.date() if hasattr(p, 'created_at') else None,
                'end_date': None,
                'level': p.level,
                'status': 'Active' if p.is_active else 'Inactive',
                'count': 0,
                'revenue': 0,
                'center_breakdown': []
            }

        for c in cards:
            key = f"value card_{c.id}"
            data_map[key] = {
                'id': key,
                'name': c.title,
                'type': 'Value Card',
                'start_date': c.created_at.date() if hasattr(c, 'created_at') else None,
                'end_date': None,
                'level': c.level,
                'status': 'Active' if c.is_active else 'Inactive',
                'count': 0,
                'revenue': 0,
                'center_breakdown': []
            }

        items = InvoiceItem.objects.filter(
            invoice__status__in=['paid', 'partial', 'Paid', 'Partial', 'completed', 'Completed', 'draft', 'Draft'],
            content_type__in=[mem_ct, pkg_ct, card_ct]
        )
        
        if start_date:
            items = items.filter(invoice__created_at__date__gte=start_date)
        if end_date:
            items = items.filter(invoice__created_at__date__lte=end_date)
            
        items_agg = items.values('content_type', 'object_id', 'invoice__center__center_name', 'invoice__center__display_name').annotate(
            usage_count=Count('id'),
            total_revenue=Sum('total_price')
        )
        
        mem_dict = {m.id: m for m in memberships}
        pkg_dict = {p.id: p for p in packages}
        card_dict = {c.id: c for c in cards}
        
        for row in items_agg:
            ct_id = row['content_type']
            obj_id = row['object_id']
            
            obj = None
            type_str = ''
            if ct_id == mem_ct.id:
                obj = mem_dict.get(obj_id)
                type_str = 'Membership'
            elif ct_id == pkg_ct.id:
                obj = pkg_dict.get(obj_id)
                type_str = 'Package'
            elif ct_id == card_ct.id:
                obj = card_dict.get(obj_id)
                type_str = 'Value Card'
                
            if obj:
                key = f"{type_str.lower()}_{obj.id}"
                if key not in data_map:
                    data_map[key] = {
                        'id': key,
                        'name': obj.name if hasattr(obj, 'name') else obj.title,
                        'type': type_str,
                        'start_date': obj.created_at.date() if hasattr(obj, 'created_at') else None,
                        'end_date': None,
                        'level': obj.level,
                        'status': 'Active' if (hasattr(obj, 'is_active') and obj.is_active) or (not hasattr(obj, 'is_active')) else 'Inactive',
                        'count': 0,
                        'revenue': 0,
                        'center_breakdown': []
                    }
                cname = row.get('invoice__center__display_name') or row.get('invoice__center__center_name') or 'Organisation / All Centers'
                data_map[key]['count'] += row['usage_count']
                data_map[key]['revenue'] += (row['total_revenue'] or 0)
                data_map[key]['center_breakdown'].append({
                    'center_name': cname,
                    'count': row['usage_count'],
                    'revenue': (row['total_revenue'] or 0)
                })
                
        return Response(list(data_map.values()))

class ValueCardViewSet(MarketingBaseViewSet):
    queryset = ValueCard.objects.all().select_related('center').order_by('-created_at')
    serializer_class = ValueCardSerializer

class MembershipViewSet(MarketingBaseViewSet):
    queryset = Membership.objects.all().select_related('center').order_by('-created_at')
    serializer_class = MembershipSerializer

class PackageViewSet(MarketingBaseViewSet):
    queryset = Package.objects.all().select_related('center').order_by('-created_at')
    serializer_class = PackageSerializer
