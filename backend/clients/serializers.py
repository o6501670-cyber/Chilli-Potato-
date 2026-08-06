from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Client, ClientMembership, ClientPackage, ClientValueCard
from salon_admin.models import Center
from marketing.serializers import MembershipSerializer, PackageSerializer, ValueCardSerializer
from django.db.models import Sum


class ClientMembershipSerializer(serializers.ModelSerializer):
    membership_detail = MembershipSerializer(source='membership', read_only=True)

    class Meta:
        model = ClientMembership
        fields = '__all__'


class ClientPackageSerializer(serializers.ModelSerializer):
    package_detail = PackageSerializer(source='package', read_only=True)

    class Meta:
        model = ClientPackage
        fields = '__all__'


class ClientValueCardSerializer(serializers.ModelSerializer):
    value_card_detail = ValueCardSerializer(source='value_card', read_only=True)

    class Meta:
        model = ClientValueCard
        fields = '__all__'


class ClientSerializer(serializers.ModelSerializer):
    center = serializers.PrimaryKeyRelatedField(queryset=Center.objects.all(), allow_null=True, required=False)
    app_pin = serializers.CharField(write_only=True, required=False, allow_blank=True)
    center_detail = serializers.SerializerMethodField()
    active_memberships = serializers.SerializerMethodField()
    active_packages = serializers.SerializerMethodField()
    active_value_cards = serializers.SerializerMethodField()
    # List views annotate these balances in one query. The model-property
    # fallback keeps detail serialization compatible with older callers.
    advance_balance = serializers.SerializerMethodField()
    cashback_balance = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = '__all__'

    def create(self, validated_data):
        pin = validated_data.get('app_pin')
        if pin:
            validated_data['app_pin'] = make_password(str(pin))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        pin = validated_data.get('app_pin')
        if pin:
            validated_data['app_pin'] = make_password(str(pin))
        elif pin == '':
            validated_data.pop('app_pin', None)
        return super().update(instance, validated_data)

    def to_internal_value(self, data):
        # Convert frontend empty strings to Python None to prevent DRF validation crashes
        data = data.copy() if hasattr(data, 'copy') else data
        for field in ['birthday', 'email', 'gst_number', 'app_pin', 'notes', 'blacklist_reason']:
            if field in data and data[field] == '':
                data[field] = None
        return super().to_internal_value(data)

    def get_advance_balance(self, obj):
        value = getattr(obj, 'advance_balance_annotated', None)
        return float(value if value is not None else obj.advance_balance)

    def get_cashback_balance(self, obj):
        value = getattr(obj, 'cashback_balance_annotated', None)
        return float(value if value is not None else obj.cashback_balance)

    def get_center_detail(self, obj):
        if obj.center:
            return {
                'id': obj.center.id,
                'display_name': obj.center.display_name,
                'center_name': obj.center.display_name or obj.center.center_name,
                'address': obj.center.address,
            }
        return None

    def get_active_memberships(self, obj):
        from datetime import date
        today = date.today()
        active = [m for m in obj.memberships.all() if m.is_active and m.expiry_date >= today]
        return ClientMembershipSerializer(active, many=True).data

    def get_active_packages(self, obj):
        from datetime import date
        today = date.today()
        active = [p for p in obj.packages.all() if p.is_active and p.expiry_date >= today]
        return ClientPackageSerializer(active, many=True).data

    def get_active_value_cards(self, obj):
        from datetime import date
        today = date.today()
        active = [c for c in obj.value_cards.all() if c.is_active and c.expiry_date >= today and c.balance > 0]
        return ClientValueCardSerializer(active, many=True).data
