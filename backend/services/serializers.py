from rest_framework import serializers

from .models import CenterService, ServiceMaster


class CenterServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CenterService
        fields = '__all__'

class ServiceMasterSerializer(serializers.ModelSerializer):
    center_overrides = CenterServiceSerializer(many=True, read_only=True)
    center_override = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    center_incentive = serializers.SerializerMethodField()
    level = serializers.CharField(read_only=False, required=False)
    
    class Meta:
        model = ServiceMaster
        fields = (
            'id', 'service_code', 'name', 'brand', 'category', 'sub_category',
            'sac_code', 'hsn_code', 'default_price', 'tax_percentage', 'duration_mins',
            'level', 'centers', 'created_at', 'updated_at', 'center_overrides',
            'center_override', 'price', 'center_incentive', 'incentive'
        )

    def _get_center_id(self):
        request = self.context.get('request')
        if not request:
            return None
        center_id = getattr(request, 'query_params', request.GET).get('center_id')
        if not center_id:
            return None
        try:
            return int(center_id)
        except (TypeError, ValueError):
            return None

    def _get_center_override_obj(self, obj):
        """Return the CenterService override for the requested center, or None.
        Uses the prefetch cache (center_overrides is prefetched on the queryset),
        so this does NOT hit the DB — it filters Python-side from the cache."""
        cid = self._get_center_id()
        if cid is None:
            return None
        # Use prefetch cache via .all() — no extra DB query
        for o in obj.center_overrides.all():
            if o.center_id == cid:
                return o
        return None

    def get_center_override(self, obj):
        override = self._get_center_override_obj(obj)
        if override is None:
            return None
        return CenterServiceSerializer(override).data

    def get_price(self, obj):
        override = self._get_center_override_obj(obj)
        if override and override.price is not None:
            return override.price
        return obj.default_price

    def get_center_incentive(self, obj):
        """Return the per-center incentive % if set, else fallback to ServiceMaster.incentive."""
        override = self._get_center_override_obj(obj)
        if override and override.incentive is not None:
            return float(override.incentive)
        return float(obj.incentive or 0)


