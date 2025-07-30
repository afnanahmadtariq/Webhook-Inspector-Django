from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """Extended user profile for additional webhook-related settings"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Webhook limits
    max_webhooks = models.PositiveIntegerField(default=10)
    max_requests_per_webhook = models.PositiveIntegerField(default=1000)
    
    # API settings
    api_key = models.CharField(max_length=255, blank=True, null=True, unique=True)
    api_key_created_at = models.DateTimeField(null=True, blank=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    webhook_retention_days = models.PositiveIntegerField(default=30)
    
    # Usage tracking
    total_webhooks_created = models.PositiveIntegerField(default=0)
    total_requests_received = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def generate_api_key(self):
        """Generate a new API key for the user"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits
        api_key = ''.join(secrets.choice(alphabet) for _ in range(40))
        
        self.api_key = f"whi_{api_key}"
        self.api_key_created_at = timezone.now()
        self.save()
        
        return self.api_key
    
    def can_create_webhook(self):
        """Check if user can create more webhooks"""
        current_webhooks = self.user.webhookendpoint_set.filter(
            status='active'
        ).count()
        return current_webhooks < self.max_webhooks


class APIUsage(models.Model):
    """Track API usage for rate limiting and analytics"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_usage')
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    response_status = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['endpoint']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.method} {self.endpoint} at {self.timestamp}"


class UserSession(models.Model):
    """Track user sessions for security"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions_tracked')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"Session for {self.user.username} from {self.ip_address}"
