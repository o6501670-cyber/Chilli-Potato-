from rest_framework import serializers
from .models import StaffMember, ServiceLog, StaffConsumptionLog, StaffTransfer, StaffToolTracker, PayrollRecord, Designation

class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = '__all__'

class StaffMemberSerializer(serializers.ModelSerializer):
    center_name = serializers.SerializerMethodField()
    has_overdue_tools = serializers.SerializerMethodField()
    
    class Meta:
        model = StaffMember
        fields = '__all__'

    def get_center_name(self, obj):
        if not obj.center:
            return ''
        return obj.center.display_name or obj.center.center_name or ''

    def get_has_overdue_tools(self, obj):
        if hasattr(obj, 'has_overdue_tools_annotated'):
            return obj.has_overdue_tools_annotated
        
        from datetime import date
        return obj.tool_trackers.filter(
            status='Taken', 
            expected_return_date__lt=date.today()
        ).exists()

class ServiceLogSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    center_name = serializers.SerializerMethodField()

    class Meta:
        model = ServiceLog
        fields = '__all__'

    def get_center_name(self, obj):
        if not obj.center:
            return ''
        return obj.center.display_name or obj.center.center_name or ''

    def get_staff_name(self, obj):
        name = obj.staff.first_name
        if obj.staff.last_name:
            name += f" {obj.staff.last_name}"
        return name

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.invoice and instance.invoice.client:
            data['client_name'] = f"{instance.invoice.client.first_name} {instance.invoice.client.last_name or ''}".strip()
        return data

class StaffConsumptionLogSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    center_name = serializers.SerializerMethodField()

    class Meta:
        model = StaffConsumptionLog
        fields = '__all__'

    def get_center_name(self, obj):
        if not obj.center:
            return ''
        return obj.center.display_name or obj.center.center_name or ''

    def get_staff_name(self, obj):
        name = obj.staff.first_name
        if obj.staff.last_name:
            name += f" {obj.staff.last_name}"
        return name

class StaffTransferSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    from_center_name = serializers.CharField(source='from_center.center_name', read_only=True)
    to_center_name = serializers.CharField(source='to_center.center_name', read_only=True)

    class Meta:
        model = StaffTransfer
        fields = '__all__'

    def get_staff_name(self, obj):
        name = obj.staff.first_name
        if obj.staff.last_name:
            name += f" {obj.staff.last_name}"
        return name

class StaffToolTrackerSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    staff_center_name = serializers.CharField(source='staff.center.center_name', read_only=True)

    class Meta:
        model = StaffToolTracker
        fields = '__all__'

    def get_staff_name(self, obj):
        name = obj.staff.first_name
        if obj.staff.last_name:
            name += f" {obj.staff.last_name}"
        return name

class PayrollRecordSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    center_name = serializers.CharField(source='center.display_name', read_only=True)

    class Meta:
        model = PayrollRecord
        fields = '__all__'

    def get_staff_name(self, obj):
        name = obj.staff.first_name
        if obj.staff.last_name:
            name += f" {obj.staff.last_name}"
        return name
