import uuid
import json
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class WebhookEndpoint(models.Model):
    """Model representing a unique webhook endpoint"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('disabled', 'Disabled'),
    ]
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Expiration settings
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    max_requests = models.PositiveIntegerField(default=100)
    current_request_count = models.PositiveIntegerField(default=0)
    
    # Status and settings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_public = models.BooleanField(default=True)
    
    # Auto-deletion
    auto_delete_after_days = models.PositiveIntegerField(default=7)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Webhook {self.uuid} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.expires_at and self.pk is None:
            # Set default expiration to 1 hour from creation
            from django.conf import settings
            expiry_minutes = getattr(settings, 'WEBHOOK_EXPIRY_MINUTES', 60)
            self.expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if webhook has expired"""
        if self.status != 'active':
            return True
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        if self.current_request_count >= self.max_requests:
            return True
        return False
    
    @property
    def should_auto_delete(self):
        """Check if webhook should be auto-deleted"""
        cutoff_date = timezone.now() - timedelta(days=self.auto_delete_after_days)
        return self.created_at < cutoff_date
    
    def increment_request_count(self):
        """Increment the request count and update status if needed"""
        self.current_request_count += 1
        if self.current_request_count >= self.max_requests:
            self.status = 'expired'
        self.save(update_fields=['current_request_count', 'status'])
    
    def get_absolute_url(self):
        return f"/hooks/{self.uuid}/"


class WebhookRequest(models.Model):
    """Model representing an individual webhook request"""
    
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
        ('HEAD', 'HEAD'),
        ('OPTIONS', 'OPTIONS'),
    ]
    
    webhook = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='requests')
    
    # Request details
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    path = models.CharField(max_length=500, default='/')
    query_string = models.TextField(blank=True)
    
    # Headers and body
    headers = models.JSONField(default=dict)
    body = models.TextField(blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    content_length = models.PositiveIntegerField(default=0)
    
    # Request metadata
    received_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True, null=True)
    
    # Processing status
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['webhook', '-received_at']),
            models.Index(fields=['method']),
            models.Index(fields=['content_type']),
            models.Index(fields=['processed']),
        ]
    
    def __str__(self):
        return f"{self.method} request to {self.webhook.uuid} at {self.received_at}"
    
    @property
    def parsed_body(self):
        """Try to parse body as JSON, fallback to raw text"""
        if not self.body:
            return None
        
        if self.content_type and 'application/json' in self.content_type:
            try:
                return json.loads(self.body)
            except json.JSONDecodeError:
                pass
        
        return self.body
    
    @property
    def size_in_bytes(self):
        """Calculate total request size"""
        headers_size = len(str(self.headers).encode('utf-8'))
        body_size = len(self.body.encode('utf-8'))
        return headers_size + body_size


class WebhookAnalytics(models.Model):
    """Model for storing webhook analytics data"""
    
    webhook = models.OneToOneField(WebhookEndpoint, on_delete=models.CASCADE, related_name='analytics')
    
    # Request statistics
    total_requests = models.PositiveIntegerField(default=0)
    successful_requests = models.PositiveIntegerField(default=0)
    failed_requests = models.PositiveIntegerField(default=0)
    
    # Data statistics
    total_bytes_received = models.PositiveBigIntegerField(default=0)
    average_request_size = models.FloatField(default=0.0)
    
    # Method distribution
    get_requests = models.PositiveIntegerField(default=0)
    post_requests = models.PositiveIntegerField(default=0)
    put_requests = models.PositiveIntegerField(default=0)
    patch_requests = models.PositiveIntegerField(default=0)
    delete_requests = models.PositiveIntegerField(default=0)
    other_requests = models.PositiveIntegerField(default=0)
    
    # Content type distribution
    json_requests = models.PositiveIntegerField(default=0)
    xml_requests = models.PositiveIntegerField(default=0)
    form_requests = models.PositiveIntegerField(default=0)
    text_requests = models.PositiveIntegerField(default=0)
    other_content_requests = models.PositiveIntegerField(default=0)
    
    # Timestamps
    last_request_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.webhook.uuid}"
    
    def update_stats(self, request_obj):
        """Update analytics based on a new request"""
        self.total_requests += 1
        self.successful_requests += 1  # Assume successful for now
        self.total_bytes_received += request_obj.size_in_bytes
        self.last_request_at = request_obj.received_at
        
        # Update average request size
        if self.total_requests > 0:
            self.average_request_size = self.total_bytes_received / self.total_requests
        
        # Update method counts
        method_field = f"{request_obj.method.lower()}_requests"
        if hasattr(self, method_field):
            setattr(self, method_field, getattr(self, method_field) + 1)
        else:
            self.other_requests += 1
        
        # Update content type counts
        if request_obj.content_type:
            if 'json' in request_obj.content_type.lower():
                self.json_requests += 1
            elif 'xml' in request_obj.content_type.lower():
                self.xml_requests += 1
            elif 'form' in request_obj.content_type.lower():
                self.form_requests += 1
            elif 'text' in request_obj.content_type.lower():
                self.text_requests += 1
            else:
                self.other_content_requests += 1
        else:
            self.other_content_requests += 1
        
        self.save()


class WebhookSchema(models.Model):
    """Model for storing JSON schema validation rules"""
    
    webhook = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='schemas')
    name = models.CharField(max_length=255)
    schema = models.JSONField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Schema {self.name} for {self.webhook.uuid}"
    
    def validate_request_body(self, body):
        """Validate request body against this schema"""
        try:
            import jsonschema
            parsed_body = json.loads(body) if isinstance(body, str) else body
            jsonschema.validate(instance=parsed_body, schema=self.schema)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
        except jsonschema.ValidationError as e:
            return False, f"Schema validation failed: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
