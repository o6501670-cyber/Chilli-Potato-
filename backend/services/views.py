from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from django.db.models import Q
from .models import ServiceMaster, CenterService
from .serializers import ServiceMasterSerializer, CenterServiceSerializer
from pos_backend.permissions import IsOwner


def _has_all_center_access(user):
    permissions = getattr(getattr(user, 'role', None), 'permissions', {}) or {}
    return IsOwner.check_is_owner(user) or permissions.get('all_centers', False)


def _accessible_center(user, center_id):
    from salon_admin.models import Center
    try:
        center = Center.objects.get(pk=int(center_id), is_active=True)
    except (Center.DoesNotExist, TypeError, ValueError) as exc:
        raise ValidationError({'center_id': 'Select a valid active center.'}) from exc
    if _has_all_center_access(user):
        return center
    if user.centers.filter(pk=center.pk).exists() or user.center_id == center.pk:
        return center
    raise PermissionDenied("You are not assigned to this center.")


class ServiceMasterViewSet(viewsets.ModelViewSet):
    queryset = ServiceMaster.objects.all().prefetch_related('center_overrides', 'centers')
    serializer_class = ServiceMasterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        is_owner = IsOwner.check_is_owner(user)
        perms = getattr(user.role, 'permissions', {}) or {}
        is_all_centers = is_owner or perms.get('all_centers', False)
        
        if is_all_centers:
            center_id = self.request.query_params.get('center_id')
            if center_id:
                return queryset.filter(Q(centers__id=center_id) | Q(level='Organisation')).distinct()
            return queryset
            
        if user.centers.exists():
            return queryset.filter(Q(centers__in=user.centers.all()) | Q(level='Organisation')).distinct()
        elif getattr(user, 'center', None):
            return queryset.filter(Q(centers__id=user.center.id) | Q(level='Organisation')).distinct()
            
        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user
        has_global_access = _has_all_center_access(user)
        level = serializer.validated_data.get('level', 'Organisation')
        centers = serializer.validated_data.get('centers', [])

        if level == 'Organisation':
            if not has_global_access:
                raise PermissionDenied("Only owners or all-center users can create organisation services.")
            serializer.save()
            return

        if not centers:
            center_id = self.request.query_params.get('center_id') or self.request.data.get('center_id')
            if not center_id:
                raise ValidationError({'centers': 'At least one center is required.'})
            centers = [_accessible_center(user, center_id)]
        elif not has_global_access:
            for center in centers:
                _accessible_center(user, center.pk)
        serializer.save(level='Center', centers=centers)

    def perform_update(self, serializer):
        center_id = self.request.query_params.get('center_id')
        if center_id:
            center = _accessible_center(self.request.user, center_id)
            from .models import CenterService
            # When editing with a center_id, route center-specific fields to CenterService override
            # instead of mutating the global ServiceMaster record.
            center_override_fields = {}

            if 'default_price' in serializer.validated_data:
                center_override_fields['price'] = serializer.validated_data.pop('default_price')

            if 'incentive' in serializer.validated_data:
                # Incentive is per-center — store on CenterService, not globally
                center_override_fields['incentive'] = serializer.validated_data.pop('incentive')

            instance = serializer.save()

            if center_override_fields:
                CenterService.objects.update_or_create(
                    center_id=center.id,
                    service_id=instance.id,
                    defaults=center_override_fields
                )
        else:
            if not _has_all_center_access(self.request.user):
                raise PermissionDenied("A center_id is required when editing a center service.")
            serializer.save()

    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """Bulk upload/update services from Excel or CSV.
        Supported columns: S.No, Brand, Category, Sub Category, Service Name, Price, HSN Code, Tax
        If a service with the same name already exists it is updated; otherwise a new one is created.
        """
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file uploaded'}, status=400)
        if file_obj.size > 10 * 1024 * 1024:
            return Response({'error': 'Files cannot exceed 10 MB.'}, status=400)
        try:
            import pandas as pd
            if file_obj.name.endswith('.csv'):
                df = pd.read_csv(file_obj)
            elif file_obj.name.endswith('.xlsx') or file_obj.name.endswith('.xls'):
                df = pd.read_excel(file_obj)
            else:
                return Response({'error': 'Unsupported file format. Please upload a .csv or .xlsx file.'}, status=400)

            df = df.fillna('')
            # Strip whitespace from column names for robust matching
            df.columns = [str(c).strip() for c in df.columns]
            records = df.to_dict('records')

            user = request.user

            # Resolve the center to assign services to
            center = None
            center_id_param = request.data.get('center_id') or request.query_params.get('center_id')
            if center_id_param:
                center = _accessible_center(user, center_id_param)
            elif not _has_all_center_access(user):
                assigned = user.centers.filter(is_active=True)
                if user.center_id:
                    center = _accessible_center(user, user.center_id)
                elif assigned.count() == 1:
                    center = assigned.first()
                else:
                    raise ValidationError({'center_id': 'Center is required when multiple centers are assigned.'})

            def safe_float(val, default=0.0):
                try:
                    v = str(val).strip()
                    return float(v) if v not in ('', 'nan', 'None') else default
                except (ValueError, TypeError):
                    return default

            def safe_int(val, default=0):
                try:
                    v = str(val).strip()
                    return int(float(v)) if v not in ('', 'nan', 'None') else default
                except (ValueError, TypeError):
                    return default

            created_count = 0
            updated_count = 0
            skipped_count = 0
            errors = []

            from django.db import transaction as db_transaction
            with db_transaction.atomic():
                for idx, row in enumerate(records, start=2):
                    # Service Name (required) — supports both "Service Name" and "name"
                    name = str(row.get('Service Name', row.get('name', ''))).strip()
                    if not name or name in ('nan', 'None'):
                        errors.append(f'Row {idx}: Skipped - Service Name is empty.')
                        skipped_count += 1
                        continue

                    # Category
                    category = str(row.get('Category', row.get('category', ''))).strip()
                    if category in ('nan', 'None'):
                        category = ''

                    # Sub Category (informational, not a separate model field)
                    sub_category = str(row.get('Sub Category', row.get('sub_category', ''))).strip()
                    if sub_category in ('nan', 'None'):
                        sub_category = ''

                    # Brand (informational)
                    brand = str(row.get('Brand', row.get('brand', ''))).strip()
                    if brand in ('nan', 'None'):
                        brand = ''

                    # S.No -> service_code
                    service_code = str(row.get('S.No', row.get('service_code', ''))).strip()
                    if service_code in ('nan', 'None'):
                        service_code = ''

                    # Price
                    price = safe_float(row.get('Price', row.get('price', row.get('default_price', 0))))

                    # Tax
                    tax_str = str(row.get('Tax', row.get('tax_percentage', '5'))).strip().replace('%', '')
                    tax_percentage = safe_float(tax_str, 5.00)

                    # HSN Code / SAC Code
                    hsn_code = str(row.get('HSN Code', row.get('hsn_code', row.get('HSN', '')))).strip()
                    if hsn_code in ('nan', 'None', '0'):
                        hsn_code = ''
                    sac_code = str(row.get('SAC Code', row.get('sac_code', ''))).strip()
                    if sac_code in ('nan', 'None', '0'):
                        sac_code = ''

                    # Duration (optional column)
                    duration = safe_int(row.get('duration', row.get('duration_mins', 0)))

                    # Upsert: update if name matches, else create
                    existing_qs = ServiceMaster.objects.filter(name=name)
                    if existing_qs.exists():
                        existing = existing_qs.first()
                        existing.service_code = service_code or existing.service_code
                        existing.brand = brand or existing.brand
                        existing.sub_category = sub_category or existing.sub_category
                        existing.category = category or existing.category
                        existing.tax_percentage = tax_percentage
                        existing.sac_code = sac_code or existing.sac_code
                        existing.hsn_code = hsn_code or existing.hsn_code
                        if duration:
                            existing.duration_mins = duration
                        
                        if center:
                            existing.centers.add(center)
                            existing.save()
                            from .models import CenterService
                            # Always write the price to CenterService — never overwrite
                            # ServiceMaster.default_price from a center-specific upload.
                            # This ensures Centre B's upload cannot change Centre A's global price.
                            CenterService.objects.update_or_create(
                                center_id=center.id,
                                service_id=existing.id,
                                defaults={'price': price if price else existing.default_price}
                            )
                        else:
                            # No center context — update global price only when uploading org-level
                            existing.default_price = price if price else existing.default_price
                            existing.save()

                        updated_count += 1
                    else:
                        sm = ServiceMaster.objects.create(
                            service_code=service_code,
                            name=name,
                            brand=brand,
                            category=category,
                            sub_category=sub_category,
                            default_price=price,
                            tax_percentage=tax_percentage,
                            duration_mins=duration,
                            sac_code=sac_code,
                            hsn_code=hsn_code,
                            level='Organisation'
                        )
                        if center:
                            sm.centers.add(center)
                            from .models import CenterService
                            CenterService.objects.update_or_create(
                                center_id=center.id,
                                service_id=sm.id,
                                defaults={'price': price}
                            )
                        created_count += 1

            msg = f'Upload complete: {created_count} created, {updated_count} updated, {skipped_count} skipped.'
            result = {'message': msg, 'created': created_count, 'updated': updated_count, 'skipped': skipped_count}
            if errors:
                result['warnings'] = errors[:20]
            return Response(result)

        except APIException:
            raise
        except Exception:
            return Response({'error': 'The uploaded file could not be processed. Check its format and values.'}, status=400)


class CenterServiceViewSet(viewsets.ModelViewSet):
    serializer_class = CenterServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = CenterService.objects.all()
        
        is_owner = IsOwner.check_is_owner(user)
        perms = getattr(user.role, 'permissions', {}) or {}
        is_all_centers = is_owner or perms.get('all_centers', False)
        
        if is_all_centers:
            center_id = self.request.query_params.get('center_id')
            if center_id:
                return queryset.filter(center_id=center_id)
            return queryset
            
        if user.centers.exists():
            return queryset.filter(center__in=user.centers.all())
        elif getattr(user, 'center', None):
            return queryset.filter(center=user.center)
            
        return queryset.none()

    def perform_create(self, serializer):
        center = serializer.validated_data.get('center')
        _accessible_center(self.request.user, center.pk)
        serializer.save()

    def perform_update(self, serializer):
        center = serializer.validated_data.get('center', serializer.instance.center)
        _accessible_center(self.request.user, center.pk)
        serializer.save()
    
    @action(detail=False, methods=['post'])
    def override(self, request):
        user = request.user
        center_id = request.data.get('center_id')

        service_id = request.data.get('service_id')
        price = request.data.get('price')
        is_active = request.data.get('is_active', True)
        
        if not center_id or not service_id:
            return Response({"error": "Missing center_id or service_id"}, status=status.HTTP_400_BAD_REQUEST)
        center = _accessible_center(user, center_id)
            
        is_owner = IsOwner.check_is_owner(user)
        perms = getattr(user.role, 'permissions', {}) or {}
        is_all_centers = is_owner or perms.get('all_centers', False)
        
        if not is_all_centers:
            try:
                center_id_int = int(center_id)
                if user.centers.exists():
                    if not user.centers.filter(id=center_id_int).exists():
                        raise PermissionDenied("You do not have permission to override prices at this center.")
                elif getattr(user, 'center', None):
                    if user.center.id != center_id_int:
                        raise PermissionDenied("You do not have permission to override prices at this center.")
                else:
                    raise PermissionDenied("You are not assigned to any center.")
            except ValueError:
                return Response({"error": "Invalid center_id"}, status=status.HTTP_400_BAD_REQUEST)
            
        obj, created = CenterService.objects.update_or_create(
            center_id=center.id,
            service_id=service_id,
            defaults={'price': price, 'is_active': is_active}
        )
        return Response(CenterServiceSerializer(obj).data)
