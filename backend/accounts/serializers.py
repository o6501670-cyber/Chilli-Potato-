from rest_framework import serializers
from .models import CustomUser, Message

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'full_name', 'phone', 'designation', 'role', 'center', 'centers', 'password')
        extra_kwargs = {'password': {'write_only': True, 'required': False}}
        
    def create(self, validated_data):
        centers = validated_data.pop('centers', [])
        try:
            user = CustomUser.objects.create_user(**validated_data)
            if centers:
                user.centers.set(centers)
            return user
        except Exception as e:
            raise serializers.ValidationError(str(e))

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        centers = validated_data.pop('centers', None)
        
        user = super().update(instance, validated_data)
        
        if password:
            user.set_password(password)
            user.save()
            
        if centers is not None:
            user.centers.set(centers)
            
        return user

class UserChatSerializer(serializers.ModelSerializer):
    center_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'full_name', 'email', 'center_name')

    def get_center_name(self, obj):
        if obj.center:
            return obj.center.display_name or obj.center.center_name
        elif obj.centers.exists():
            c = obj.centers.first()
            return c.display_name or c.center_name
        return "No Center"

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    receiver_name = serializers.CharField(source='receiver.full_name', read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'sender', 'sender_name', 'receiver', 'receiver_name', 'content', 'image', 'timestamp', 'is_read')
