from rest_framework import viewsets, permissions
from django.db import transaction
from .models import Appointment, AppointmentService
from .serializers import AppointmentSerializer
import datetime
from pos_backend.permissions import IsOwner

class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related(
            'client', 'center'
        ).prefetch_related(
            'services', 'services__staff'
        ).order_by('-date', '-start_time')
        role = getattr(user, 'role', None)
        is_owner = IsOwner.check_is_owner(user)
        perms = getattr(role, 'permissions', {}) or {}

        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                queryset = queryset.filter(center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                queryset = queryset.filter(center=user.center)

        center_id = self.request.query_params.get('center_id')
        if center_id:
            queryset = queryset.filter(center_id=center_id)

        date_str = self.request.query_params.get('date')
        if date_str:
            queryset = queryset.filter(date=date_str)

        client_phone = self.request.query_params.get('client_phone')
        if client_phone:
            queryset = queryset.filter(client_phone=client_phone)

        return queryset

    def _check_double_booking(self, services_data, appt_date, exclude_appt_id=None):
        """
        Check if any staff member is double-booked on the given date.
        Compares new service time slots against existing scheduled appointments.
        Returns (is_conflict, error_message).
        """
        if not services_data:
            return False, None

        def _get_staff_id(svc):
            s = svc.get('staff')
            try:
                return s.id if hasattr(s, 'id') else int(s)
            except (ValueError, TypeError):
                return 0
                
        sorted_services = sorted(services_data, key=_get_staff_id)

        for svc in sorted_services:
            staff = svc.get('staff')
            if not staff:
                continue

            staff_id = staff.id if hasattr(staff, 'id') else int(staff)
            svc_time = svc.get('time')
            duration = int(svc.get('duration') or 30)

            # Guard: after DRF validation this should be datetime.time, but be defensive
            if not svc_time or not hasattr(svc_time, 'hour'):
                continue

            # Lock the staff member to serialize appointment creation for them
            from staff.models import StaffMember
            try:
                staff_obj = StaffMember.objects.select_for_update().get(id=staff_id)
                staff_name = f"{staff_obj.first_name} {staff_obj.last_name or ''}".strip()
            except StaffMember.DoesNotExist:
                staff_name = f"Staff #{staff_id}"

            # Find all other active appointments for this staff member on the same date
            existing_services = AppointmentService.objects.filter(
                staff_id=staff_id,
                appointment__date=appt_date,
                appointment__status='Scheduled'
            ).select_related('appointment')

            if exclude_appt_id:
                existing_services = existing_services.exclude(appointment_id=exclude_appt_id)

            for existing_svc in existing_services:
                existing_time = existing_svc.time
                existing_duration = int(existing_svc.duration or 30)

                # Convert to minutes for overlap comparison
                new_start = svc_time.hour * 60 + svc_time.minute
                new_end = new_start + max(duration, 1)

                existing_start = existing_time.hour * 60 + existing_time.minute
                existing_end = existing_start + max(existing_duration, 1)

                # True overlap: new starts before existing ends AND new ends after existing starts
                if new_start < existing_end and new_end > existing_start:
                    return True, (
                        f"{staff_name} already has an appointment at "
                        f"{existing_time.strftime('%I:%M %p')} on {appt_date}. "
                        f"Please choose a different time slot."
                    )

        return False, None

    def _validate_center_access(self, center):
        user = self.request.user
        perms = getattr(getattr(user, 'role', None), 'permissions', {}) or {}
        if IsOwner.check_is_owner(user) or perms.get('all_centers', False):
            return
        if user.centers.exists():
            allowed = user.centers.filter(pk=center.pk).exists()
        else:
            allowed = bool(user.center_id and user.center_id == center.pk)
        if not allowed:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot manage appointments for this center.")

    @transaction.atomic
    def perform_create(self, serializer):
        center = serializer.validated_data.get('center')
        self._validate_center_access(center)

        client_phone = serializer.validated_data.get('client_phone')
        if client_phone:
            from clients.models import Client
            client = Client.objects.filter(phone=client_phone, center=center).first()
            if client and client.is_blacklisted:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Client is blacklisted and cannot book appointments.")

        # Use DRF-validated nested data so times are datetime.time objects and
        # staff values are StaffMember objects. Raw JSON strings silently
        # bypassed conflict detection.
        services_data = serializer.validated_data.get('services', [])
        appt_date = serializer.validated_data.get('date')
        if services_data and appt_date:
            is_conflict, error_msg = self._check_double_booking(services_data, appt_date)
            if is_conflict:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(error_msg)

        appt = serializer.save()
        self._link_client(appt)

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.instance
        center = serializer.validated_data.get('center', instance.center)
        self._validate_center_access(center)
        services_data = serializer.validated_data.get('services')
        appt_date = serializer.validated_data.get('date', instance.date)

        if services_data is not None and appt_date:
            is_conflict, error_msg = self._check_double_booking(
                services_data, appt_date, exclude_appt_id=instance.id
            )
            if is_conflict:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(error_msg)

        appt = serializer.save()
        self._link_client(appt)

    def _link_client(self, appt):
        if not appt.client and appt.client_phone:
            from clients.models import Client
            client = Client.objects.filter(phone=appt.client_phone, center=appt.center).first()
            if client:
                appt.client = client
                appt.save(update_fields=['client'])
