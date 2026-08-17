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

from .models import CustomUser, Message, ChatRoom, MessageReaction

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

class MessageReactionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = MessageReaction
        fields = ('id', 'user', 'user_name', 'emoji', 'created_at')

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    receiver_name = serializers.SerializerMethodField()
    reactions_summary = serializers.SerializerMethodField()
    reply_to_preview = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            'id', 'sender', 'sender_name', 'receiver', 'receiver_name', 'room',
            'content', 'image', 'timestamp', 'is_read', 'status', 'reply_to',
            'reply_to_preview', 'deleted_at', 'edited_at', 'reactions_summary'
        )

    def get_receiver_name(self, obj):
        if obj.receiver:
            return obj.receiver.full_name
        return None

    def get_reactions_summary(self, obj):
        reactions = obj.reactions.all()
        summary = {}
        for r in reactions:
            if r.emoji not in summary:
                summary[r.emoji] = []
            summary[r.emoji].append({'user_id': r.user_id, 'user_name': r.user.full_name})
        return summary
        
    def get_reply_to_preview(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'sender_name': obj.reply_to.sender.full_name,
                'content': obj.reply_to.content[:100] if obj.reply_to.content else '[Image]'
            }
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data['content'] = None
            data['image'] = None
        return data
