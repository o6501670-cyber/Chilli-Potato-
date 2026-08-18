from rest_framework import serializers

from .models import Membership, Package, Promotion, ValueCard, WhatsAppMessage


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
        # If this is a creation (no instance) or start_date is being changed
        if not self.instance and 'start_date' in attrs:
            if attrs['start_date'] < timezone.now().date():
                raise serializers.ValidationError({"start_date": "Start date cannot be in the past."})
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
