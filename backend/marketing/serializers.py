from rest_framework import serializers
from .models import WhatsAppMessage, Promotion, ValueCard, Membership, Package

class WhatsAppMessageSerializer(serializers.ModelSerializer):
    center_name = serializers.CharField(source='center.display_name', read_only=True)
    class Meta:
        model = WhatsAppMessage
        fields = '__all__'

class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = '__all__'

    def validate(self, attrs):
        from django.utils import timezone
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'End date cannot be before start date.'})
        if not self.instance and start and start < timezone.now().date():
            raise serializers.ValidationError({'start_date': 'Start date cannot be in the past.'})
        if attrs.get('discount_value') is not None and attrs['discount_value'] < 0:
            raise serializers.ValidationError({'discount_value': 'Discount value cannot be negative.'})
        max_usage = attrs.get('max_usage_per_client')
        if max_usage is not None and max_usage <= 0:
            raise serializers.ValidationError({'max_usage_per_client': 'Usage limit must be greater than zero.'})
        return super().validate(attrs)

class ValueCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValueCard
        fields = '__all__'

class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = '__all__'

class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = '__all__'
