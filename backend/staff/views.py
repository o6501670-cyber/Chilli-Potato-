from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
import openpyxl
from datetime import datetime
from decimal import Decimal
import hashlib
import logging
from django.contrib.auth.hashers import check_password, make_password
from django.utils.crypto import constant_time_compare
from salon_admin.models import Center
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import api_view, permission_classes, throttle_classes, action
from accounts.throttles import AppLoginRateThrottle
from django.db import transaction
from django.db.models import Sum, Count, Q
from .models import StaffMember, ServiceLog, StaffConsumptionLog, StaffTransfer, StaffToolTracker, PayrollRecord, Designation
from .serializers import (
    StaffMemberSerializer, StaffAppSerializer, ServiceLogSerializer, StaffConsumptionLogSerializer,
    StaffTransferSerializer, StaffToolTrackerSerializer, PayrollRecordSerializer, DesignationSerializer
)
import datetime
from .utils import sync_staff_transfers_and_tools
from accounts.access import can_access_center, has_global_access
from accounts.permissions import RoleActionPermission

logger = logging.getLogger(__name__)


def _read_bulk_rows(uploaded_file):
    """Read an XLSX/CSV upload into normalized dictionaries."""
    if uploaded_file.name.lower().endswith('.csv'):
        import csv
        from io import TextIOWrapper
        rows = list(csv.DictReader(TextIOWrapper(uploaded_file.file, encoding='utf-8')))
        return [
            {str(key).strip().lower().replace(' ', '_'): value for key, value in row.items()}
            for row in rows
        ]
    workbook = openpyxl.load_workbook(uploaded_file, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(value or '').strip().lower().replace(' ', '_') for value in rows[0]]
    return [dict(zip(headers, row)) for row in rows[1:] if any(value not in (None, '') for value in row)]


def _bulk_value(row, *names, default=None):
    for name in names:
        value = row.get(name)
        if value not in (None, ''):
            return value
    return default


def _bulk_date(value):
    if value in (None, ''):
        return None
    if hasattr(value, 'date'):
        return value.date()
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%d %b %Y'):
        try:
            return datetime.datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f'Invalid date: {value}')


def _bulk_time(value):
    if value in (None, ''):
        return None
    if hasattr(value, 'strftime'):
        return value
    for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p'):
        try:
            return datetime.datetime.strptime(str(value).strip(), fmt).time()
        except ValueError:
            continue
    raise ValueError(f'Invalid time: {value}')


def _bulk_center(value):
    if value in (None, ''):
        return None
    try:
        return Center.objects.get(pk=int(value))
    except (TypeError, ValueError, Center.DoesNotExist):
        return Center.objects.filter(center_name__iexact=str(value).strip()).first()


def _bulk_staff(value):
    if value in (None, ''):
        return None
    try:
        return StaffMember.objects.get(pk=int(value))
    except (TypeError, ValueError, StaffMember.DoesNotExist):
        return StaffMember.objects.filter(staff_code__iexact=str(value).strip()).first()


class DesignationViewSet(viewsets.ModelViewSet):
    queryset = Designation.objects.all().order_by('name')
    serializer_class = DesignationSerializer
    permission_classes = [RoleActionPermission]

class StaffMemberViewSet(viewsets.ModelViewSet):
    serializer_class = StaffMemberSerializer
    permission_classes = [RoleActionPermission]

    def get_queryset(self):
        user = self.request.user
        from django.db.models import Exists, OuterRef
        from .models import StaffToolTracker
        from datetime import date
        
        # Optimize N+1 queries by selecting related center and annotating overdue tools
        overdue_tools = StaffToolTracker.objects.filter(
            staff=OuterRef('pk'),
            status='Taken',
            expected_return_date__lt=date.today()
        )
        queryset = StaffMember.objects.all().select_related('center').annotate(
            has_overdue_tools_annotated=Exists(overdue_tools)
        ).order_by('first_name')
        role = getattr(user, 'role', None)
        is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
        perms = getattr(role, 'permissions', {}) or {}

        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                queryset = queryset.filter(center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                queryset = queryset.filter(center=user.center)
            else:
                queryset = queryset.none()

        center_id = self.request.query_params.get('center_id')
        if center_id:
            queryset = queryset.filter(center_id=center_id)

        include_inactive = self.request.query_params.get('include_inactive', 'false')
        if self.action == 'list' and include_inactive != 'true':
            queryset = queryset.filter(is_active=True)

        return queryset

    def destroy(self, request, *args, **kwargs):
        """Deactivate staff instead of cascading payroll/service history."""
        staff = self.get_object()
        staff.is_active = False
        staff.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def sync_transfers(self, request):
        """Manually trigger transfer/tool expiry sync. Call from a scheduled task or management command."""
        from .utils import sync_staff_transfers_and_tools
        try:
            sync_staff_transfers_and_tools()
            return Response({'status': 'sync complete'})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


    @action(detail=False, methods=['get'])
    def bulk_upload_template(self, request):
        import io
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            return Response({'error': 'openpyxl not installed.'}, status=400)
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Staff Import"
        
        headers = [
            'staffCode', 'firstName', 'lastName', 'gender', 'designation', 'center',
            'salary', 'joiningDate', 'phone', 'email', 'address', 'city', 'state', 'pinCode'
        ]
        ws.append(headers)
        
        header_fill = PatternFill(start_color="16A34A", end_color="16A34A", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        
        for col_num, cell in enumerate(ws[1], 1):
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 20
            
        help_text = [
            'Optional (for update)', 'Required', 'Optional', 'Male/Female', 'Optional', 'Required',
            'Optional', 'YYYY-MM-DD', 'Optional', 'Optional', 'Optional', 'Optional', 'Optional', 'Optional'
        ]
        ws.append(help_text)
        
        help_fill = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid")
        help_font = Font(color="15803D", italic=True)
        for cell in ws[2]:
            cell.fill = help_fill
            cell.font = help_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
        example_row = [
            'STF-001', 'John', 'Doe', 'Male', 'Senior Stylist', 'Main Center',
            '25000', '2023-01-15', '9876543210', 'john@example.com', '123 Main St', 'Mumbai', 'Maharashtra', '400001'
        ]
        ws.append(example_row)
            
        response_io = io.BytesIO()
        wb.save(response_io)
        response_io.seek(0)
        
        from django.http import HttpResponse
        response = HttpResponse(response_io.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="staff_import_template.xlsx"'
        return response

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_upload(self, request):
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided'}, status=400)
            
        excel_file = request.FILES['file']
        
        filename = excel_file.name.lower()
        rows = []
        if filename.endswith('.csv'):
            import csv
            from io import StringIO
            try:
                decoded_file = excel_file.read().decode('utf-8')
                io_string = StringIO(decoded_file)
                reader = csv.reader(io_string)
                rows = list(reader)
            except Exception as e:
                return Response({'detail': f'Error reading CSV file: {str(e)}'}, status=400)
        else:
            try:
                wb = openpyxl.load_workbook(excel_file, data_only=True)
                sheet = wb.active
                rows = list(sheet.iter_rows(values_only=True))
            except Exception as e:
                return Response({'detail': f'Error reading Excel file: {str(e)}'}, status=400)

        header_idx = 0
        for idx, row in enumerate(rows):
            if any(str(cell).strip() for cell in row if cell is not None):
                header_idx = idx
                break
                
        if len(rows) <= header_idx + 1:
            return Response({'detail': 'File is empty or missing headers'}, status=400)
            
        header = [str(h).strip().lower().replace(' ', '_') if h else '' for h in rows[header_idx]]
        
        user = request.user
        center_id_param = request.data.get('center_id') or request.query_params.get('center_id')
        allowed_ids = None if has_global_access(user) else {
            int(value) for value in (
                list(user.centers.values_list('id', flat=True)) +
                ([user.center_id] if getattr(user, 'center_id', None) else [])
            )
        }
        if center_id_param and str(center_id_param).lower() != 'null':
            try:
                requested_id = int(center_id_param)
            except (TypeError, ValueError):
                return Response({'detail': 'Invalid center_id'}, status=400)
            if allowed_ids is not None and requested_id not in allowed_ids:
                raise PermissionDenied('You do not have access to this center.')
            try:
                all_centers = [Center.objects.get(id=requested_id)]
            except Center.DoesNotExist:
                return Response({'detail': 'Center not found'}, status=404)
        else:
            all_centers = (
                list(Center.objects.all()) if allowed_ids is None
                else list(Center.objects.filter(id__in=allowed_ids))
            )

        if not all_centers:
            return Response({'detail': 'User is not assigned to a center.'}, status=403)

        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        from django.db import transaction as db_transaction
        with db_transaction.atomic():
            for i, row in enumerate(rows[header_idx+1:], start=header_idx+2):
                if not any(row):
                    continue
                
                row_data = dict(zip(header, row))
                
                first_name = str(row_data.get('firstname', row_data.get('first_name', ''))).strip()
                last_name = str(row_data.get('lastname', row_data.get('last_name', ''))).strip()
                
                if not first_name:
                    raw_name = str(row_data.get('name') or row_data.get('full_name') or row_data.get('staff_name') or '').strip()
                    if raw_name:
                        parts = raw_name.split(' ', 1)
                        first_name = parts[0]
                        last_name = parts[1] if len(parts) > 1 else ''
                
                if not first_name or first_name in ('nan', 'None'):
                    errors.append(f"Row {i}: Skipped – First Name is empty.")
                    skipped_count += 1
                    continue
                    
                staff_code = str(row_data.get('staffcode', row_data.get('staff_code', ''))).strip()
                if staff_code in ('nan', 'None', '0'): staff_code = ''
                
                phone = str(row_data.get('phone', row_data.get('phone_number', row_data.get('mobile', '')))).strip()
                if phone.endswith('.0'): phone = phone[:-2]
                if phone in ('nan', 'None'): phone = ''
                
                email = str(row_data.get('email', '')).strip()
                if email in ('nan', 'None'): email = ''
                
                address = str(row_data.get('address', '')).strip()
                city = str(row_data.get('city', '')).strip()
                state = str(row_data.get('state', '')).strip()
                pin_code = str(row_data.get('pincode', row_data.get('pin', ''))).strip()
                if pin_code in ('nan', 'None', '0'): pin_code = ''
                
                loc_name = str(row_data.get('center') or row_data.get('location_name') or row_data.get('location') or '').strip()
                center = None
                if loc_name and loc_name not in ('nan', 'None'):
                    center = Center.objects.filter(center_name__icontains=loc_name).first()
                if not center:
                    center = all_centers[0]
                if not has_global_access(user) and not can_access_center(user, center):
                    errors.append(f'Row {i}: Center is outside the user scope.')
                    skipped_count += 1
                    continue
                    
                designation = str(row_data.get('designation', '')).strip()
                if designation in ('nan', 'None'): designation = ''
                
                gender = str(row_data.get('gender', '')).strip().capitalize()
                if gender not in ['Male', 'Female', 'Other']:
                    gender = 'Female'
                    
                raw_salary = row_data.get('salary', row_data.get('monthly_gross', 0))
                try:
                    salary = Decimal(str(raw_salary))
                except Exception:
                    salary = Decimal('0.0')
                    
                comm_perc = row_data.get('commission_percentage', row_data.get('comm._%', row_data.get('comm_%', 0)))
                try:
                    comm_perc = Decimal(str(comm_perc))
                except Exception:
                    comm_perc = Decimal('0.0')

                prod_comm = row_data.get('product_commission_percentage', row_data.get('prod._comm._%', row_data.get('prod_comm_%', 0)))
                try:
                    prod_comm = Decimal(str(prod_comm))
                except Exception:
                    prod_comm = Decimal('0.0')
                    
                raw_date = row_data.get('joindate', row_data.get('joiningdate', row_data.get('joining_date', '')))
                joining_date = None
                if raw_date and str(raw_date) not in ('nan', 'None', ''):
                    if hasattr(raw_date, 'date'):
                        joining_date = raw_date.date()
                    else:
                        try:
                            import datetime
                            joining_date = datetime.datetime.strptime(str(raw_date).strip(), '%d %b %Y').date()
                        except ValueError:
                            try:
                                joining_date = datetime.datetime.strptime(str(raw_date).strip(), '%Y-%m-%d').date()
                            except ValueError:
                                pass
                                
                existing = None
                if staff_code:
                    existing = StaffMember.objects.filter(staff_code__iexact=staff_code, center=center).first()
                if not existing and phone:
                    existing = StaffMember.objects.filter(phone=phone, center=center).first()
                if not existing:
                    existing = StaffMember.objects.filter(first_name__iexact=first_name, last_name__iexact=last_name, center=center).first()

                try:
                    if existing:
                        existing.first_name = first_name
                        if last_name and last_name not in ('nan', 'None'): existing.last_name = last_name
                        if staff_code: existing.staff_code = staff_code
                        if phone: existing.phone = phone
                        if email: existing.email = email
                        if address and address not in ('nan', 'None'): existing.address = address
                        if city and city not in ('nan', 'None'): existing.city = city
                        if state and state not in ('nan', 'None'): existing.state = state
                        if pin_code: existing.pin_code = pin_code
                        if designation: existing.designation = designation
                        existing.gender = gender
                        if salary: existing.salary = salary
                        if comm_perc: existing.commission_percentage = comm_perc
                        if prod_comm: existing.product_commission_percentage = prod_comm
                        if joining_date: existing.joining_date = joining_date
                        existing.save()
                        updated_count += 1
                    else:
                        StaffMember.objects.create(
                            center=center,
                            first_name=first_name,
                            last_name=last_name,
                            staff_code=staff_code,
                            phone=phone,
                            email=email,
                            address=address,
                            city=city,
                            state=state,
                            pin_code=pin_code,
                            designation=designation,
                            gender=gender,
                            salary=salary,
                            commission_percentage=comm_perc,
                            product_commission_percentage=prod_comm,
                            joining_date=joining_date,
                            is_active=True
                        )
                        created_count += 1
                except Exception as e:
                    errors.append(f"Row {i}: Error saving '{first_name}' - {str(e)}")
                    skipped_count += 1
                    
        result = {
            'message': f'Upload complete: {created_count} created, {updated_count} updated, {skipped_count} skipped.',
            'created': created_count, 'updated': updated_count, 'skipped': skipped_count
        }
        if errors:
            result['warnings'] = errors[:20]
        return Response(result)

    def perform_create(self, serializer):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        
        if not is_owner and not perms.get('all_centers', False):
            center = serializer.validated_data.get('center')
            if center:
                if user.centers.exists() and center not in user.centers.all():
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create staff for this center.")
                elif not user.centers.exists() and hasattr(user, 'center') and center != user.center:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create staff for this center.")
        serializer.save()

    @action(detail=False, methods=['get'])
    def activity_feed(self, request):
        from django.utils import timezone
        import datetime
        feed = []
        
        center_id = request.query_params.get('center_id')
        role = getattr(request.user, 'role', None)
        is_owner = getattr(request.user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
        perms = getattr(role, 'permissions', {}) or {}
        
        services_qs = ServiceLog.objects.exclude(
            invoice__status__in=['cancelled', 'refunded']
        ).select_related('staff', 'invoice__client').order_by('-date', '-time')
        consumptions_qs = StaffConsumptionLog.objects.select_related('staff').order_by('-date', '-time')
        tools_qs = StaffToolTracker.objects.select_related('staff').order_by('-created_at')
        transfers_qs = StaffTransfer.objects.select_related('staff', 'to_center', 'from_center').order_by('-created_at')

        is_global = is_owner or perms.get('all_centers', False)
        if not is_global:
            if user.centers.exists():
                scope = user.centers.all()
                services_qs = services_qs.filter(staff__center__in=scope)
                consumptions_qs = consumptions_qs.filter(staff__center__in=scope)
                tools_qs = tools_qs.filter(staff__center__in=scope)
                transfers_qs = transfers_qs.filter(Q(from_center__in=scope) | Q(to_center__in=scope))
            elif getattr(user, 'center', None):
                services_qs = services_qs.filter(staff__center=user.center)
                consumptions_qs = consumptions_qs.filter(staff__center=user.center)
                tools_qs = tools_qs.filter(staff__center=user.center)
                transfers_qs = transfers_qs.filter(Q(from_center=user.center) | Q(to_center=user.center))
            else:
                return Response([])

        if center_id:
            try:
                center_id = int(center_id)
            except (TypeError, ValueError):
                return Response({'error': 'Invalid center_id'}, status=400)
            if not is_global:
                allowed = set(user.centers.values_list('id', flat=True))
                if getattr(user, 'center_id', None):
                    allowed.add(user.center_id)
                if center_id not in allowed:
                    return Response({'error': 'You do not have access to this center.'}, status=403)
            services_qs = services_qs.filter(staff__center_id=center_id)
            consumptions_qs = consumptions_qs.filter(staff__center_id=center_id)
            tools_qs = tools_qs.filter(staff__center_id=center_id)
            transfers_qs = transfers_qs.filter(Q(from_center_id=center_id) | Q(to_center_id=center_id))
        
        # Limit each source to 20 to reduce data load — final sort will pick top 50 overall
        services = services_qs[:20]
        for s in services:
            dt = datetime.datetime.combine(s.date, s.time if s.time else datetime.time())
            client_display = s.client_name
            if s.invoice and s.invoice.client:
                client_display = f"{s.invoice.client.first_name} {s.invoice.client.last_name or ''}".strip()

            feed.append({
                'id': f"srv_{s.id}",
                'type': 'service',
                'staff_name': f"{s.staff.first_name} {s.staff.last_name or ''}".strip(),
                'title': 'Logged a Service',
                'description': '',
                'details': {
                    'Client': client_display,
                    'Item': s.service_name,
                    'Type': s.service_type,
                    'Price': f"₹{s.price}"
                },
                'timestamp': dt.isoformat()
            })
            
        consumptions = consumptions_qs[:20]
        for c in consumptions:
            dt = datetime.datetime.combine(c.date, c.time if c.time else datetime.time())
            feed.append({
                'id': f"cons_{c.id}",
                'type': 'consumption',
                'staff_name': f"{c.staff.first_name} {c.staff.last_name or ''}".strip(),
                'title': 'Consumed a Perk',
                'description': '',
                'details': {
                    'Item': c.service_name,
                    'Payment': c.payment_method,
                    'Cost': f"₹{c.amount}"
                },
                'timestamp': dt.isoformat()
            })
            
        tools = tools_qs[:20]
        for t in tools:
            feed.append({
                'id': f"tool_{t.id}",
                'type': 'tool',
                'staff_name': f"{t.staff.first_name} {t.staff.last_name or ''}".strip(),
                'title': 'Tool Assigned' if t.status == 'Taken' else 'Tool Returned',
                'description': '',
                'details': {
                    'Tool': t.tool_name,
                    'Qty': t.amount,
                    'Status': t.status,
                    'Return By': t.expected_return_date.strftime('%d %b %Y') if t.expected_return_date else 'N/A'
                },
                'timestamp': t.created_at.isoformat()
            })
            
        transfers = transfers_qs[:20]
        for tr in transfers:
            feed.append({
                'id': f"trans_{tr.id}",
                'type': 'transfer',
                'staff_name': f"{tr.staff.first_name} {tr.staff.last_name or ''}".strip(),
                'title': 'Staff Transfer',
                'description': '',
                'details': {
                    'Type': tr.transfer_type,
                    'From': (tr.from_center.display_name or tr.from_center.center_name) if tr.from_center else 'Unknown',
                    'To': (tr.to_center.display_name or tr.to_center.center_name) if tr.to_center else 'Unknown',
                    'Duration': f"{tr.start_date.strftime('%d %b %Y')} to {tr.end_date.strftime('%d %b %Y') if tr.end_date else 'Permanent'}"
                },
                'timestamp': tr.created_at.isoformat()
            })
            
        feed.sort(key=lambda x: x['timestamp'], reverse=True)
        return Response(feed[:50])

    @action(detail=False, methods=['get'])
    def commission_report(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date are required'}, status=400)

        center_id = request.query_params.get('center_id')
        staff_qs = self.get_queryset()
        if center_id:
            staff_qs = staff_qs.filter(center_id=center_id)

        logs = (
            ServiceLog.objects
            .filter(
                staff__in=staff_qs,
                date__gte=start_date,
                date__lte=end_date,
                invoice__status__in=['paid', 'partial'],
            )
            .values('staff_id', 'staff__first_name', 'staff__last_name',
                    'staff__commission_percentage', 'staff__product_commission_percentage',
                    'staff__salary', 'staff__center__display_name')
            .annotate(
                service_revenue=Sum('price', filter=Q(service_type__in=['Service', 'Membership', 'Package'])),
                product_revenue=Sum('price', filter=Q(service_type='Product')),
            )
        )

        report = []
        for row in logs:
            svc_rev = float(row['service_revenue'] or 0)
            prod_rev = float(row['product_revenue'] or 0)
            svc_comm = svc_rev * float(row['staff__commission_percentage'] or 0) / 100
            prod_comm = prod_rev * float(row['staff__product_commission_percentage'] or 0) / 100
            name = row['staff__first_name']
            if row['staff__last_name']:
                name += f" {row['staff__last_name']}"
            report.append({
                'staff_id': row['staff_id'],
                'staff_name': name,
                'center_name': row['staff__center__display_name'] or 'N/A',
                'salary': float(row['staff__salary'] or 0),
                'service_revenue': svc_rev,
                'product_revenue': prod_rev,
                'total_revenue': svc_rev + prod_rev,
                'service_commission': round(svc_comm, 2),
                'product_commission': round(prod_comm, 2),
                'total_commission': round(svc_comm + prod_comm, 2),
            })
        return Response(report)

    @action(detail=False, methods=['get'])
    def incentive_report(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date are required'}, status=400)

        staff_qs = self.get_queryset().select_related('center')

        logs = (
            ServiceLog.objects
            .filter(
                staff__in=staff_qs,
                date__gte=start_date,
                date__lte=end_date,
                invoice__status__in=['paid', 'partial']
            )
            .values(
                'staff_id',
                'staff__first_name',
                'staff__last_name',
                'staff__salary',
                'staff__center__display_name',
            )
            .annotate(total_sales=Sum('price'))
        )

        sales_by_staff = {row['staff_id']: row for row in logs}

        report = []
        
        # Check for dynamic overrides from the frontend
        override_multiplier = request.query_params.get('target_multiplier')
        override_percent = request.query_params.get('incentive_percent')
        
        if override_multiplier and override_percent:
            try:
                tiers = [(float(override_multiplier), float(override_percent))]
            except ValueError:
                tiers = []
        else:
            # Load IncentiveConfig tiers from DB (ordered by custom_percent descending = highest first)
            # IncentiveConfig.category = 'multiplier_tier' entries represent threshold tiers.
            # Each entry's use_multiple=True means "multiplier >= X", custom_percent = the incentive %.
            # The 'name' field stores the multiplier threshold (as a float string, e.g. '7', '6', '5').
            from finance.models import IncentiveConfig
            center_id_filter = request.query_params.get('center_id')
            incentive_configs = IncentiveConfig.objects.filter(
                category='multiplier_tier',
            ).order_by('-custom_percent')
            # Also try center-specific ones first if we have a center filter
            if center_id_filter:
                center_configs = incentive_configs.filter(center_id=center_id_filter)
                if center_configs.exists():
                    incentive_configs = center_configs
                else:
                    incentive_configs = incentive_configs.filter(center__isnull=True)

            # Build sorted (threshold, percent) pairs. Fall back to hardcoded defaults.
            tiers = [(float(cfg.name), float(cfg.custom_percent)) for cfg in incentive_configs if _is_float(cfg.name)]
            if not tiers:
                # Default tiers: multiplier >= 7 → 5%, >= 6 → 4%, >= 5 → 3%
                tiers = [(7.0, 5.0), (6.0, 4.0), (5.0, 3.0)]
            # Sort highest threshold first
            tiers.sort(key=lambda t: t[0], reverse=True)

        for member in staff_qs:
            row = sales_by_staff.get(member.id, {})
            total_sales = float(row.get('total_sales') or 0)
            salary = float(member.salary or 0)
            multiplier = total_sales / salary if salary > 0 else 0

            incentive_percentage = 0
            for threshold, pct in tiers:
                if multiplier >= threshold:
                    incentive_percentage = pct
                    break

            incentive_amount = total_sales * (incentive_percentage / 100.0)

            report.append({
                'staff_id': member.id,
                'staff_name': str(member),
                'center_name': member.center.display_name if member.center else 'N/A',
                'salary': salary,
                'total_sales': round(total_sales, 2),
                'multiplier': round(multiplier, 2),
                'incentive_percentage': incentive_percentage,
                'incentive_amount': round(incentive_amount, 2),
            })

        return Response(report)

def _is_float(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


class ServiceLogViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'head', 'options']
    serializer_class = ServiceLogSerializer
    permission_classes = [RoleActionPermission]

    def get_queryset(self):
        user = self.request.user
        queryset = ServiceLog.objects.exclude(invoice__status__in=['cancelled', 'refunded']).select_related('staff', 'invoice', 'invoice__client').order_by('-date', '-time')
        role = getattr(user, 'role', None)
        is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
        perms = getattr(role, 'permissions', {}) or {}

        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                queryset = queryset.filter(center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                queryset = queryset.filter(center=user.center)
            else:
                queryset = queryset.none()

        staff_id = self.request.query_params.get('staff_id')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)

        client_name = self.request.query_params.get('client_name')
        if client_name:
            queryset = queryset.filter(client_name__icontains=client_name)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])

        return queryset


    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_upload(self, request):
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided'}, status=400)
        try:
            rows = _read_bulk_rows(request.FILES['file'])
        except Exception as exc:
            return Response({'detail': f'Error reading file: {exc}'}, status=400)
        created, errors = 0, []
        with transaction.atomic():
            for row_number, row in enumerate(rows, start=2):
                try:
                    staff = _bulk_staff(_bulk_value(row, 'staff_id', 'staff', 'staff_code'))
                    center = _bulk_center(_bulk_value(row, 'center', 'center_id')) or (staff.center if staff else None)
                    if not staff or not center or staff.center_id != center.id:
                        raise ValueError('staff and a matching center are required')
                    if not can_access_center(request.user, center):
                        raise PermissionDenied('center is outside your scope')
                    payload = {
                        'staff': staff.id,
                        'center': center.id,
                        'client_name': str(_bulk_value(row, 'client_name', 'client', default='')).strip(),
                        'service_name': str(_bulk_value(row, 'service_name', 'service', 'name', default='')).strip(),
                        'service_type': _bulk_value(row, 'service_type', default='Service'),
                        'price': _bulk_value(row, 'price', 'amount', default=0),
                        'date': _bulk_date(_bulk_value(row, 'date')) or datetime.date.today(),
                        'time': _bulk_time(_bulk_value(row, 'time')) or datetime.datetime.now().time(),
                    }
                    serializer = self.get_serializer(data=payload, context={'request': request})
                    serializer.is_valid(raise_exception=True)
                    self.perform_create(serializer)
                    created += 1
                except Exception as exc:
                    errors.append(f'Row {row_number}: {exc}')
        return Response({'created': created, 'errors': errors}, status=201 if created else 400)

    def perform_create(self, serializer):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        
        if not is_owner and not perms.get('all_centers', False):
            center = serializer.validated_data.get('center')
            if center:
                if user.centers.exists() and center not in user.centers.all():
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create logs for this center.")
                elif not user.centers.exists() and hasattr(user, 'center') and center != user.center:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create logs for this center.")
        serializer.save()

@api_view(['GET'])
@permission_classes([RoleActionPermission])
def revenue_report(request):
    user = request.user
    queryset = ServiceLog.objects.all()
    role = getattr(user, 'role', None)
    is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
    perms = getattr(role, 'permissions', {}) or {}
    if not is_owner and not perms.get('all_centers', False):
        if user.centers.exists():
            queryset = queryset.filter(center__in=user.centers.all())
        elif hasattr(user, 'center') and user.center:
            queryset = queryset.filter(center=user.center)
        else:
            queryset = queryset.none()
            
    center_id = request.query_params.get('center_id')
    if center_id:
        queryset = queryset.filter(center_id=center_id)

    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    if start_date and end_date:
        queryset = queryset.filter(date__range=[start_date, end_date])

    queryset = queryset.filter(Q(invoice__isnull=True) | Q(invoice__status__in=['paid', 'partial']))

    total_revenue = queryset.aggregate(total=Sum('price'))['total'] or 0
    total_services = queryset.count()
    total_staff = queryset.values('staff').distinct().count()

    staff_breakdown = queryset.values('staff__first_name', 'staff__last_name', 'center__display_name').annotate(
        services=Count('id'),
        revenue=Sum('price')
    ).order_by('-revenue')

    breakdown = []
    for item in staff_breakdown:
        name = item['staff__first_name']
        if item['staff__last_name']:
            name += f" {item['staff__last_name']}"
        breakdown.append({
            'staff_name': name,
            'location': item['center__display_name'],
            'services': item['services'],
            'revenue': item['revenue']
        })

    feed = []
    for log in queryset.select_related('staff').order_by('-date', '-time')[:50]:
        staff_name = log.staff.first_name
        if log.staff.last_name:
            staff_name += f" {log.staff.last_name}"
        feed.append({
            'staff_name': staff_name,
            'client_name': log.client_name,
            'service_name': log.service_name,
            'service_type': log.service_type,
            'time': log.time.strftime('%I:%M %p') if log.time else '',
            'price': float(log.price)
        })

    return Response({
        'total_revenue': total_revenue,
        'total_services': total_services,
        'total_staff': total_staff,
        'breakdown': breakdown,
        'activity_feed': feed
    })

@api_view(['GET'])
@permission_classes([RoleActionPermission])
def usage_report(request):
    user = request.user
    queryset = ServiceLog.objects.all()
    role = getattr(user, 'role', None)
    is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
    perms = getattr(role, 'permissions', {}) or {}
    if not is_owner and not perms.get('all_centers', False):
        if user.centers.exists():
            queryset = queryset.filter(center__in=user.centers.all())
        elif hasattr(user, 'center') and user.center:
            queryset = queryset.filter(center=user.center)
        else:
            queryset = queryset.none()

    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    if start_date and end_date:
        queryset = queryset.filter(date__range=[start_date, end_date])

    queryset = queryset.filter(Q(invoice__isnull=True) | Q(invoice__status__in=['paid', 'partial']))

    services_count = queryset.filter(service_type='Service').count()
    products_count = queryset.filter(service_type='Product').count()
    memberships_count = queryset.filter(service_type='Membership').count()
    packages_count = queryset.filter(service_type='Package').count()

    item_breakdown = queryset.values('service_name', 'service_type').annotate(
        times_used=Count('id'),
        revenue=Sum('price')
    ).order_by('-times_used')

    return Response({
        'services_count': services_count,
        'products_count': products_count,
        'memberships_count': memberships_count,
        'packages_count': packages_count,
        'breakdown': list(item_breakdown)
    })

class StaffConsumptionLogViewSet(viewsets.ModelViewSet):
    serializer_class = StaffConsumptionLogSerializer
    permission_classes = [RoleActionPermission]

    def get_queryset(self):
        user = self.request.user
        queryset = StaffConsumptionLog.objects.all().order_by('-date', '-time')
        role = getattr(user, 'role', None)
        is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
        perms = getattr(role, 'permissions', {}) or {}

        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                queryset = queryset.filter(center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                queryset = queryset.filter(center=user.center)
            else:
                queryset = queryset.none()

        staff_id = self.request.query_params.get('staff_id')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)

        center_id = self.request.query_params.get('center_id')
        if center_id:
            queryset = queryset.filter(center_id=center_id)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])

        return queryset


    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_upload(self, request):
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided'}, status=400)
        try:
            rows = _read_bulk_rows(request.FILES['file'])
        except Exception as exc:
            return Response({'detail': f'Error reading file: {exc}'}, status=400)
        created, errors = 0, []
        with transaction.atomic():
            for row_number, row in enumerate(rows, start=2):
                try:
                    staff = _bulk_staff(_bulk_value(row, 'staff_id', 'staff', 'staff_code'))
                    center = _bulk_center(_bulk_value(row, 'center', 'center_id')) or (staff.center if staff else None)
                    if not staff or not center or staff.center_id != center.id:
                        raise ValueError('staff and a matching center are required')
                    if not can_access_center(request.user, center):
                        raise PermissionDenied('center is outside your scope')
                    payload = {
                        'staff': staff.id,
                        'center': center.id,
                        'service_name': str(_bulk_value(row, 'service_name', 'service', 'name', default='')).strip(),
                        'date': _bulk_date(_bulk_value(row, 'date')) or datetime.date.today(),
                        'time': _bulk_time(_bulk_value(row, 'time')) or datetime.datetime.now().time(),
                        'payment_method': _bulk_value(row, 'payment_method', default='Points'),
                        'amount': _bulk_value(row, 'amount', default=0),
                    }
                    serializer = self.get_serializer(data=payload, context={'request': request})
                    serializer.is_valid(raise_exception=True)
                    self.perform_create(serializer)
                    created += 1
                except Exception as exc:
                    errors.append(f'Row {row_number}: {exc}')
        return Response({'created': created, 'errors': errors}, status=201 if created else 400)

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        
        if not is_owner and not perms.get('all_centers', False):
            center = serializer.validated_data.get('center')
            if center:
                if user.centers.exists() and center not in user.centers.all():
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create logs for this center.")
                elif not user.centers.exists() and hasattr(user, 'center') and center != user.center:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create logs for this center.")

        payment_method = serializer.validated_data.get('payment_method', 'Points')
        amount = serializer.validated_data.get('amount', 0)
        staff = serializer.validated_data.get('staff')
        center = serializer.validated_data.get('center')
        if amount <= 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'amount': 'Consumption amount must be greater than zero.'})
        if staff and center and staff.center_id != center.id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'staff': 'Staff member does not belong to the selected center.'})
        service_name = serializer.validated_data.get('service_name')
        
        remaining_money_amount = 0

        if payment_method == 'Points':
            if staff.allocated_points < amount:
                if staff.allocated_points <= 0:
                    serializer.validated_data['payment_method'] = 'Money'
                    payment_method = 'Money'
                else:
                    points_to_deduct = staff.allocated_points
                    remaining_money_amount = amount - points_to_deduct
                    
                    serializer.validated_data['amount'] = points_to_deduct
                    staff.allocated_points = 0
                    staff.save()
            else:
                staff.allocated_points -= amount
                staff.save()

        from inventory.models import Product
        from rest_framework.exceptions import ValidationError
        product = Product.objects.filter(name__iexact=service_name, center=staff.center).first()
        if product:
            if product.current_stock <= 0:
                raise ValidationError({'service_name': f'No stock available for {product.name}.'})
            product.current_stock -= 1
            product.save(update_fields=['current_stock'])

        serializer.save()

        if remaining_money_amount > 0:
            StaffConsumptionLog.objects.create(
                staff=staff,
                center=serializer.validated_data.get('center'),
                service_name=service_name,
                date=serializer.validated_data.get('date'),
                time=serializer.validated_data.get('time'),
                payment_method='Money',
                amount=remaining_money_amount
            )

@api_view(['GET'])
@permission_classes([RoleActionPermission])
def consumption_report(request):
    user = request.user
    queryset = StaffConsumptionLog.objects.all()
    role = getattr(user, 'role', None)
    is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
    perms = getattr(role, 'permissions', {}) or {}
    
    if not is_owner and not perms.get('all_centers', False):
        if user.centers.exists():
            queryset = queryset.filter(center__in=user.centers.all())
        elif hasattr(user, 'center') and user.center:
            queryset = queryset.filter(center=user.center)
        else:
            queryset = queryset.none()
            
    center_id = request.query_params.get('center_id')
    if center_id:
        queryset = queryset.filter(center_id=center_id)

    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    if start_date and end_date:
        queryset = queryset.filter(date__range=[start_date, end_date])

    report = queryset.values('staff__first_name', 'staff__last_name', 'service_name', 'payment_method', 'center__display_name').annotate(
        total_amount=Sum('amount'),
        times_used=Count('id')
    ).order_by('-total_amount')

    formatted_report = []
    for item in report:
        name = item['staff__first_name']
        if item['staff__last_name']:
            name += f" {item['staff__last_name']}"
            
        formatted_report.append({
            'staff_name': name,
            'service_name': item['service_name'],
            'payment_method': item['payment_method'],
            'center_name': item['center__display_name'],
            'times_used': item['times_used'],
            'total_amount': item['total_amount']
        })

    return Response(formatted_report)

class StaffTransferViewSet(viewsets.ModelViewSet):
    serializer_class = StaffTransferSerializer
    permission_classes = [RoleActionPermission]

    def get_queryset(self):
        user = self.request.user
        queryset = StaffTransfer.objects.all().order_by('-created_at')
        role = getattr(user, 'role', None)
        is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
        perms = getattr(role, 'permissions', {}) or {}

        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                queryset = queryset.filter(to_center__in=user.centers.all()) | queryset.filter(from_center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                queryset = queryset.filter(to_center=user.center) | queryset.filter(from_center=user.center)
            else:
                queryset = queryset.none()

        staff_id = self.request.query_params.get('staff_id')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)

        return queryset.distinct()


    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_upload(self, request):
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided'}, status=400)
        try:
            rows = _read_bulk_rows(request.FILES['file'])
        except Exception as exc:
            return Response({'detail': f'Error reading file: {exc}'}, status=400)
        created, errors = 0, []
        with transaction.atomic():
            for row_number, row in enumerate(rows, start=2):
                try:
                    staff = _bulk_staff(_bulk_value(row, 'staff_id', 'staff', 'staff_code'))
                    from_center = _bulk_center(_bulk_value(row, 'from_center', 'from_center_id', 'from'))
                    to_center = _bulk_center(_bulk_value(row, 'to_center', 'to_center_id', 'to'))
                    if not staff or not from_center or not to_center:
                        raise ValueError('staff_id, from_center and to_center are required')
                    if staff.center_id != from_center.id:
                        raise ValueError('staff is not assigned to from_center')
                    if not has_global_access(request.user) and (not can_access_center(request.user, from_center) or not can_access_center(request.user, to_center)):
                        raise PermissionDenied('center is outside your scope')
                    transfer = StaffTransfer.objects.create(
                        staff=staff,
                        from_center=from_center,
                        to_center=to_center,
                        transfer_type=_bulk_value(row, 'transfer_type', default='Permanent'),
                        start_date=_bulk_date(_bulk_value(row, 'start_date')) or datetime.date.today(),
                        end_date=_bulk_date(_bulk_value(row, 'end_date')),
                        status=_bulk_value(row, 'status', default='Active'),
                        reason=_bulk_value(row, 'reason', default='') or '',
                    )
                    staff.center = transfer.to_center
                    staff.save(update_fields=['center'])
                    created += 1
                except Exception as exc:
                    errors.append(f'Row {row_number}: {exc}')
        return Response({'created': created, 'errors': errors}, status=201 if created else 400)

    def perform_create(self, serializer):
        user = self.request.user
        from rest_framework.exceptions import PermissionDenied, ValidationError
        from_center = serializer.validated_data.get('from_center')
        to_center = serializer.validated_data.get('to_center')
        staff = serializer.validated_data.get('staff')
        if not from_center or not to_center or not staff:
            raise ValidationError('staff, from_center and to_center are required.')
        if staff.center_id != from_center.id:
            raise ValidationError({'staff': 'Staff member is not currently assigned to from_center.'})
        if not has_global_access(user) and (
            not can_access_center(user, from_center) or not can_access_center(user, to_center)
        ):
            raise PermissionDenied('You cannot transfer staff through an inaccessible center.')
        if from_center.id == to_center.id:
            raise ValidationError('from_center and to_center must be different.')

        transfer = serializer.save()
        staff.center = transfer.to_center
        staff.save(update_fields=['center'])

    def perform_update(self, serializer):
        immutable = {'staff', 'from_center', 'to_center'}
        if immutable.intersection(serializer.validated_data.keys()):
            raise ValidationError('Staff transfer origin, destination and staff cannot be changed after creation.')
        serializer.save()

    def perform_destroy(self, instance):
        raise PermissionDenied('Staff transfers are audit records and cannot be deleted.')

class StaffToolTrackerViewSet(viewsets.ModelViewSet):
    queryset = StaffToolTracker.objects.all().order_by('-created_at')
    serializer_class = StaffToolTrackerSerializer
    permission_classes = [RoleActionPermission]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if hasattr(user, 'role') and user.role and user.role.name.lower() == 'owner':
            pass
        elif hasattr(user, 'is_superuser') and user.is_superuser:
            pass
        elif user.centers.exists():
            queryset = queryset.filter(staff__center__in=user.centers.all())
        elif hasattr(user, 'center') and user.center:
            queryset = queryset.filter(staff__center=user.center)
        else:
            queryset = queryset.none()

        staff_id = self.request.query_params.get('staff_id')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)

        return queryset


    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_upload(self, request):
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided'}, status=400)
        try:
            rows = _read_bulk_rows(request.FILES['file'])
        except Exception as exc:
            return Response({'detail': f'Error reading file: {exc}'}, status=400)
        created, errors = 0, []
        with transaction.atomic():
            for row_number, row in enumerate(rows, start=2):
                try:
                    staff = _bulk_staff(_bulk_value(row, 'staff_id', 'staff', 'staff_code'))
                    if not staff or not can_access_center(request.user, staff.center):
                        raise PermissionDenied('staff member is outside your scope')
                    tool_name = str(_bulk_value(row, 'tool_name', 'name', default='')).strip()
                    amount = int(_bulk_value(row, 'amount', 'quantity', default=1))
                    if not tool_name or amount <= 0:
                        raise ValueError('tool_name and a positive amount are required')
                    StaffToolTracker.objects.create(
                        staff=staff,
                        tool_name=tool_name,
                        details=_bulk_value(row, 'details'),
                        amount=amount,
                        date_taken=_bulk_date(_bulk_value(row, 'date_taken')) or datetime.date.today(),
                        expected_return_date=_bulk_date(_bulk_value(row, 'expected_return_date')),
                        actual_return_date=_bulk_date(_bulk_value(row, 'actual_return_date')),
                        status=_bulk_value(row, 'status', default='Taken'),
                    )
                    created += 1
                except Exception as exc:
                    errors.append(f'Row {row_number}: {exc}')
        return Response({'created': created, 'errors': errors}, status=201 if created else 400)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied, ValidationError
        staff = serializer.validated_data.get('staff')
        if not staff:
            raise ValidationError({'staff': 'Staff member is required.'})
        if not can_access_center(self.request.user, staff.center):
            raise PermissionDenied('You cannot assign tools at this center.')
        serializer.save()

    def perform_update(self, serializer):
        if 'staff' in serializer.validated_data:
            raise ValidationError('Tool ownership cannot be changed after assignment.')
        serializer.save()

    def perform_destroy(self, instance):
        raise PermissionDenied('Tool assignments are audit records and cannot be deleted.')

class PayrollRecordViewSet(viewsets.ModelViewSet):
    queryset = PayrollRecord.objects.all().order_by('-created_at')
    serializer_class = PayrollRecordSerializer
    permission_classes = [RoleActionPermission]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        role = getattr(user, 'role', None)
        is_owner = getattr(user, 'is_superuser', False) or (role and role.name.lower() == 'owner')
        perms = getattr(role, 'permissions', {}) or {}
        
        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                queryset = queryset.filter(center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                queryset = queryset.filter(center=user.center)
            else:
                queryset = queryset.none()
                
        staff_id = self.request.query_params.get('staff_id')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
            
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        if month:
            queryset = queryset.filter(month=month)
        if year:
            queryset = queryset.filter(year=year)
            
        return queryset


    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def bulk_upload(self, request):
        if 'file' not in request.FILES:
            return Response({'detail': 'No file provided'}, status=400)
        try:
            rows = _read_bulk_rows(request.FILES['file'])
        except Exception as exc:
            return Response({'detail': f'Error reading file: {exc}'}, status=400)
        created, errors = 0, []
        with transaction.atomic():
            for row_number, row in enumerate(rows, start=2):
                try:
                    staff = _bulk_staff(_bulk_value(row, 'staff_id', 'staff', 'staff_code'))
                    center = _bulk_center(_bulk_value(row, 'center', 'center_id')) or (staff.center if staff else None)
                    if not staff or not center or not can_access_center(request.user, center):
                        raise PermissionDenied('staff or center is outside your scope')
                    month = int(_bulk_value(row, 'month'))
                    year = int(_bulk_value(row, 'year'))
                    base = Decimal(str(_bulk_value(row, 'base_salary', default=staff.salary or 0)))
                    service_commission = Decimal(str(_bulk_value(row, 'service_commission', default=0)))
                    product_commission = Decimal(str(_bulk_value(row, 'product_commission', default=0)))
                    deductions = Decimal(str(_bulk_value(row, 'deductions', default=0)))
                    net_pay = base + service_commission + product_commission - deductions
                    PayrollRecord.objects.update_or_create(
                        staff=staff, month=month, year=year,
                        defaults={
                            'center': center,
                            'base_salary': base,
                            'service_commission': service_commission,
                            'product_commission': product_commission,
                            'deductions': deductions,
                            'net_pay': net_pay,
                            'status': _bulk_value(row, 'status', default='Draft'),
                        },
                    )
                    created += 1
                except Exception as exc:
                    errors.append(f'Row {row_number}: {exc}')
        return Response({'created': created, 'errors': errors}, status=201 if created else 400)

    def perform_create(self, serializer):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        if not is_owner and not perms.get('all_centers', False):
            center = serializer.validated_data.get('center')
            if center:
                if user.centers.exists() and center not in user.centers.all():
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create payrolls for this center.")
                elif not user.centers.exists() and hasattr(user, 'center') and center != user.center:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create payrolls for this center.")
        serializer.save()

    def perform_update(self, serializer):
        payroll = serializer.instance
        if payroll.status != 'Draft':
            raise ValidationError('Only draft payroll records can be edited.')
        values = {**{
            'base_salary': payroll.base_salary,
            'service_commission': payroll.service_commission,
            'product_commission': payroll.product_commission,
            'deductions': payroll.deductions,
        }, **serializer.validated_data}
        values['net_pay'] = (
            Decimal(str(values.get('base_salary', 0))) +
            Decimal(str(values.get('service_commission', 0))) +
            Decimal(str(values.get('product_commission', 0))) -
            Decimal(str(values.get('deductions', 0)))
        )
        serializer.save(net_pay=values['net_pay'])

    def perform_destroy(self, instance):
        if instance.status != 'Draft':
            raise PermissionDenied('Locked or paid payroll records cannot be deleted.')
        instance.delete()

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def mark_paid(self, request, pk=None):
        payroll = PayrollRecord.objects.select_for_update().get(pk=self.get_object().pk)
        if payroll.status != 'Locked':
            return Response({'detail': 'Payroll must be locked before it can be paid.'}, status=400)
        payroll.status = 'Paid'
        payroll.save(update_fields=['status', 'updated_at'])
        return Response(PayrollRecordSerializer(payroll).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def lock(self, request, pk=None):
        payroll = PayrollRecord.objects.select_for_update().get(pk=self.get_object().pk)
        if payroll.status != 'Draft':
            return Response({'detail': 'Only draft payroll can be locked.'}, status=400)
        payroll.status = 'Locked'
        payroll.save(update_fields=['status', 'updated_at'])
        return Response(PayrollRecordSerializer(payroll).data)

# ─────────────────────────────────────────────────────────────────────────────
# Staff App Endpoints — Token-Secured (replaces insecure AllowAny pattern)
# ─────────────────────────────────────────────────────────────────────────────

from django.core import signing as _signing

def _pin_digest(value):
    return hashlib.sha256((value or '').encode('utf-8')).hexdigest()


def _staff_pin_matches(staff, pin):
    stored = staff.app_password or ''
    if stored.startswith(('pbkdf2_', 'argon2', 'bcrypt', 'scrypt')):
        return check_password(pin, stored)
    return constant_time_compare(stored, str(pin or ''))


def _generate_staff_token(staff):
    """Generate a signed, password-bound token valid for 30 days."""
    return _signing.dumps(
        {'staff_id': staff.id, 'pin_digest': _pin_digest(staff.app_password)},
        salt='staff-app-token'
    )


def _verify_staff_token(token):
    """Verify a staff app token and invalidate it when the PIN changes."""
    try:
        data = _signing.loads(token, salt='staff-app-token', max_age=86400 * 30)
        staff = StaffMember.objects.select_related('center').get(
            id=data['staff_id'],
            is_active=True,
        )
        if not constant_time_compare(data.get('pin_digest', ''), _pin_digest(staff.app_password)):
            return None
        return staff
    except Exception:
        return None

def _get_authenticated_staff(request):
    """Extract and validate X-Staff-Token from request headers. Returns staff or None."""
    token = request.headers.get('X-Staff-Token') or request.query_params.get('_token')
    if not token:
        return None
    return _verify_staff_token(token)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@throttle_classes([AppLoginRateThrottle])
def staff_app_login(request):
    """Staff app login. Returns staff data + auth_token for subsequent requests."""
    identifier = request.data.get('identifier') or request.data.get('phone')
    pin = request.data.get('pin')

    if not identifier:
        return Response({'error': 'Phone or ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not pin:
        return Response({'error': 'PIN is required'}, status=status.HTTP_400_BAD_REQUEST)

    staff = None
    try:
        staff = StaffMember.objects.get(phone=identifier, is_active=True)
    except StaffMember.DoesNotExist:
        try:
            staff = StaffMember.objects.get(id=int(identifier), is_active=True)
        except (StaffMember.DoesNotExist, ValueError):
            pass

    if staff and _staff_pin_matches(staff, pin):
        # Migrate legacy plaintext PINs at first successful login.
        if staff.app_password and not staff.app_password.startswith(('pbkdf2_', 'argon2', 'bcrypt', 'scrypt')):
            staff.app_password = make_password(str(pin))
            staff.save(update_fields=['app_password'])
        data = StaffAppSerializer(staff).data
        data['auth_token'] = _generate_staff_token(staff)
        return Response(data)

    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def staff_app_logs(request):
    """Return service logs for the authenticated staff member on a given date."""
    staff = _get_authenticated_staff(request)
    if not staff:
        return Response({'error': 'Unauthorized. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)

    target_date_str = request.query_params.get('date')
    from datetime import date, datetime
    if target_date_str:
        try:
            target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    logs = ServiceLog.objects.filter(staff=staff, date=target_date).exclude(invoice__status__in=['cancelled', 'refunded']).order_by('-created_at')
    return Response(ServiceLogSerializer(logs, many=True).data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def staff_app_appointments(request):
    """Return appointments for the authenticated staff member on a given date."""
    staff = _get_authenticated_staff(request)
    if not staff:
        return Response({'error': 'Unauthorized. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        from appointments.models import Appointment
        from appointments.serializers import AppointmentSerializer
        from datetime import date, datetime

        target_date_str = request.query_params.get('date')
        if target_date_str:
            try:
                target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()

        appointments = (
            Appointment.objects
            .filter(services__staff=staff, date=target_date)
            .distinct()
            .order_by('date', 'start_time')
        )
        return Response(AppointmentSerializer(appointments, many=True).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def staff_app_tools(request):
    """Return tools assigned to the authenticated staff member."""
    staff = _get_authenticated_staff(request)
    if not staff:
        return Response({'error': 'Unauthorized. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)

    tools = StaffToolTracker.objects.filter(staff=staff).order_by('-created_at')
    return Response(StaffToolTrackerSerializer(tools, many=True).data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def staff_app_transfers(request):
    """Return transfers for the authenticated staff member."""
    staff = _get_authenticated_staff(request)
    if not staff:
        return Response({'error': 'Unauthorized. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)

    transfers = StaffTransfer.objects.filter(staff=staff).order_by('-created_at')
    return Response(StaffTransferSerializer(transfers, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def staff_app_update_profile(request):
    """Allow staff to update their own Aadhaar number."""
    staff = _get_authenticated_staff(request)
    if not staff:
        return Response({'error': 'Unauthorized. Please log in again.'}, status=status.HTTP_401_UNAUTHORIZED)

    aadhar = request.data.get('aadhar_number')
    if aadhar is not None:
        staff.aadhar_number = aadhar
        staff.save(update_fields=['aadhar_number'])

    return Response({'success': True, 'message': 'Profile updated.'})


