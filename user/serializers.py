from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserProfile, APIUsage


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        UserProfile.objects.create(user=user)
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    can_create_webhook = serializers.ReadOnlyField()
    
    class Meta:
        model = UserProfile
        fields = [
            'username', 'email',
            'max_webhooks', 'max_requests_per_webhook', 'email_notifications',
            'webhook_retention_days', 'total_webhooks_created', 'total_requests_received',
            'api_key_created_at', 'can_create_webhook', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'total_webhooks_created', 'total_requests_received', 
            'api_key_created_at', 'created_at', 'updated_at'
        ]


class APIKeySerializer(serializers.Serializer):
    """Serializer for API key generation"""
    
    api_key = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user info"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        
        # Add profile info if available
        try:
            profile = user.profile
            token['max_webhooks'] = profile.max_webhooks
            token['api_key_exists'] = bool(profile.api_key)
        except UserProfile.DoesNotExist:
            pass
        
        return token


class APIUsageSerializer(serializers.ModelSerializer):
    """Serializer for API usage tracking"""
    
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = APIUsage
        fields = [
            'id', 'username', 'endpoint', 'method', 'timestamp',
            'ip_address', 'user_agent', 'response_status'
        ]
        read_only_fields = ['id', 'timestamp']


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics"""
    
    total_webhooks = serializers.IntegerField()
    active_webhooks = serializers.IntegerField()
    total_requests_received = serializers.IntegerField()
    requests_this_month = serializers.IntegerField()
    api_calls_today = serializers.IntegerField()
    storage_used_mb = serializers.FloatField()
    webhook_retention_days = serializers.IntegerField()
    max_webhooks = serializers.IntegerField()
    webhooks_remaining = serializers.IntegerField()
