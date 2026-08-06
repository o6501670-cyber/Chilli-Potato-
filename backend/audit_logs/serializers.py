from rest_framework import serializers
from .models import SystemLog


class SystemLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemLog
        fields = [
            'id', 'timestamp',
            # Who
            'user_id_snapshot', 'user_name', 'user_email', 'user_role',
            # Where
            'center_id', 'center_name',
            # What
            'action', 'module', 'entity_type', 'entity_id', 'human_description',
            # Device
            'device_type', 'browser', 'os_info',
            # Geo
            'ip_address', 'geo_city', 'geo_region', 'geo_country', 'geo_country_code',
            # Technical
            'path', 'description', 'device_info',
        ]
