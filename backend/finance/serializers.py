from rest_framework import serializers
from .models import PettyCashEntry, DailyClosing, IncentiveConfig, IncentiveTier, Shift, IncentiveRule

class PettyCashEntrySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Petty cash amount cannot be negative.')
        return value

    class Meta:
        model = PettyCashEntry
        fields = '__all__'

class DailyClosingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    def validate(self, attrs):
        for field, value in attrs.items():
            if field not in {'user', 'center', 'date'} and value is not None and value < 0:
                raise serializers.ValidationError({field: 'Closing values cannot be negative.'})
        return attrs

    class Meta:
        model = DailyClosing
        fields = '__all__'


class IncentiveTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncentiveTier
        fields = ('id', 'min_multiple', 'incentive_percent')


class IncentiveConfigSerializer(serializers.ModelSerializer):
    tiers = IncentiveTierSerializer(many=True, required=False)

    class Meta:
        model = IncentiveConfig
        fields = ('id', 'center', 'name', 'category', 'use_multiple', 'use_custom_percent', 'custom_percent', 'tiers')

    def create(self, validated_data):
        tiers_data = validated_data.pop('tiers', [])
        config = IncentiveConfig.objects.create(**validated_data)
        for tier in tiers_data:
            IncentiveTier.objects.create(config=config, **tier)
        return config

    def update(self, instance, validated_data):
        tiers_data = validated_data.pop('tiers', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tiers_data is not None:
            instance.tiers.all().delete()
            for tier in tiers_data:
                IncentiveTier.objects.create(config=instance, **tier)
        return instance

class ShiftSerializer(serializers.ModelSerializer):
    opened_by_name = serializers.CharField(source='opened_by.get_full_name', read_only=True)
    closed_by_name = serializers.CharField(source='closed_by.get_full_name', read_only=True)

    class Meta:
        model = Shift
        fields = '__all__'
        read_only_fields = ('opened_at',)


class IncentiveRuleSerializer(serializers.ModelSerializer):
    center_name = serializers.SerializerMethodField()
    slabs = serializers.JSONField(required=False, write_only=False)

    class Meta:
        model = IncentiveRule
        fields = '__all__'

    def get_center_name(self, obj):
        if obj.center:
            return obj.center.display_name or obj.center.center_name
        return 'All Centers (Organization-wide)'

    def to_internal_value(self, data):
        data = data.copy()
        rule_type = data.get('rule_type', '')
        # Normalize rule_type to model choices
        if rule_type in ['slabs', 'slab']:
            data['rule_type'] = 'slab'
            if 'slabs' in data and data['slabs']:
                data['tiers'] = data['slabs']
        elif rule_type in ['multiple', 'multipliers']:
            data['rule_type'] = 'multiple'
        elif rule_type in ['flat_percentage', 'percentage']:
            data['rule_type'] = 'percentage'
        elif rule_type in ['flat_amount', 'flat']:
            data['rule_type'] = 'flat'
        return super().to_internal_value(data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.rule_type in ['slab', 'slabs']:
            ret['slabs'] = instance.tiers or []
        else:
            ret['slabs'] = []
        return ret

    def create(self, validated_data):
        validated_data.pop('slabs', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('slabs', None)
        return super().update(instance, validated_data)


