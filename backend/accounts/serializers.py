from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import CustomUser, Message

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'full_name', 'phone', 'designation', 'role', 'center', 'centers', 'password')
        extra_kwargs = {'password': {'write_only': True, 'required': False, 'allow_blank': False}}

    def validate(self, attrs):
        password = attrs.get('password')
        if self.instance is None and not password:
            raise serializers.ValidationError({'password': 'A password is required when creating a user.'})
        if password:
            candidate = self.instance or CustomUser(
                email=attrs.get('email', ''),
                full_name=attrs.get('full_name', ''),
            )
            try:
                validate_password(password, user=candidate)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'password': list(exc.messages)}) from exc
        return attrs
        
    def create(self, validated_data):
        centers = validated_data.pop('centers', [])
        user = CustomUser.objects.create_user(**validated_data)
        if centers:
            user.centers.set(centers)
        return user

    def update(self, instance, validated_data):
        # Passwords should be changed via a dedicated endpoint, not general update
        validated_data.pop('password', None)
        centers = validated_data.pop('centers', None)
        
        user = super().update(instance, validated_data)
            
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

from .models import CustomUser, Message, ChatRoom

class ChatRoomSerializer(serializers.ModelSerializer):
    participants = UserChatSerializer(many=True, read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ('id', 'name', 'display_name', 'is_group', 'participants')

    def get_display_name(self, obj):
        if obj.name:
            return obj.name
        request = self.context.get('request')
        if request and request.user:
            others = obj.participants.exclude(id=request.user.id)
            if others.exists():
                return ", ".join([o.full_name or o.email for o in others])
        return "Chat Room"

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    receiver_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'sender', 'sender_name', 'receiver', 'receiver_name', 'room', 'content', 'image', 'timestamp', 'is_read')
        read_only_fields = ('room', 'is_read')

    def validate(self, attrs):
        content = (attrs.get('content') or '').strip()
        image = attrs.get('image')
        if not content and not image:
            raise serializers.ValidationError('A message must contain text or an image.')
        if len(content) > 5000:
            raise serializers.ValidationError({'content': 'Messages cannot exceed 5,000 characters.'})
        if image and image.size > 5 * 1024 * 1024:
            raise serializers.ValidationError({'image': 'Images cannot exceed 5 MB.'})
        attrs['content'] = content or None
        return attrs

    def get_receiver_name(self, obj):
        if obj.receiver:
            return obj.receiver.full_name
        return None
