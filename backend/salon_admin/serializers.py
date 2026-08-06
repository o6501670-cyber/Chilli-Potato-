from rest_framework import serializers
from .models import Center, Role

class CenterSerializer(serializers.ModelSerializer):
    mtd_revenue = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True, required=False)
    class Meta:
        model = Center
        fields = '__all__'

class RoleSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'users_count']
