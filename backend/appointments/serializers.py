from rest_framework import serializers
from django.db import transaction
from .models import Appointment, AppointmentService

class AppointmentServiceSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentService
        fields = '__all__'
        read_only_fields = ('appointment',)

    def get_staff_name(self, obj):
        if obj.staff:
            return f"{obj.staff.first_name} {obj.staff.last_name}".strip()
        return "Any Staff"

# Fields that should not be passed to AppointmentService.objects.create()
_SERVICE_READONLY_FIELDS = {'id', 'appointment', 'staff_name'}

def _extract_service_staff_id(staff_val):
    """Normalise the staff value coming from the frontend.
    The frontend can send either an integer ID or the full staff object dict."""
    if staff_val is None:
        return None
    if isinstance(staff_val, dict):
        return staff_val.get('id')
    try:
        return int(staff_val)
    except (TypeError, ValueError):
        return None

def _clean_service_data(service_data: dict) -> dict:
    """Return a copy of service_data with all read-only / extra keys removed."""
    return {k: v for k, v in service_data.items() if k not in _SERVICE_READONLY_FIELDS}

class AppointmentSerializer(serializers.ModelSerializer):
    services = AppointmentServiceSerializer(many=True, required=False)
    invoice_id = serializers.SerializerMethodField()
    invoice_status = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = '__all__'

    def get_invoice_id(self, obj):
        valid_invoices = [inv for inv in obj.invoices.all() if inv.status != 'cancelled']
        if valid_invoices:
            return valid_invoices[0].id
        return None

    def get_invoice_status(self, obj):
        valid_invoices = [inv for inv in obj.invoices.all() if inv.status != 'cancelled']
        if valid_invoices:
            return valid_invoices[0].status
        return None

    @transaction.atomic
    def create(self, validated_data):
        services_data = validated_data.pop('services', [])
        appointment = Appointment.objects.create(**validated_data)

        for service_data in services_data:
            service_data = _clean_service_data(dict(service_data))
            staff_member = service_data.get('staff')
            if staff_member and staff_member.center_id != appointment.center_id:
                raise serializers.ValidationError("Staff member does not belong to this center.")
            AppointmentService.objects.create(appointment=appointment, **service_data)
        return appointment

    @transaction.atomic
    def update(self, instance, validated_data):
        services_data = validated_data.pop('services', None)

        # Update Appointment fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update services if provided
        if services_data is not None:
            instance.services.all().delete()
            for service_data in services_data:
                service_data = _clean_service_data(dict(service_data))
                staff_member = service_data.get('staff')
                if staff_member and staff_member.center_id != instance.center_id:
                    raise serializers.ValidationError("Staff member does not belong to this center.")
                AppointmentService.objects.create(appointment=instance, **service_data)

        return instance

