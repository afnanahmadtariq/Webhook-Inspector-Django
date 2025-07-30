from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from hooks.models import WebhookEndpoint, WebhookRequest


class AnalyticsSummary(models.Model):
    """Daily analytics summary for system-wide metrics"""
    
    date = models.DateField(unique=True)
    
    # Webhook metrics
    total_webhooks_created = models.PositiveIntegerField(default=0)
    total_active_webhooks = models.PositiveIntegerField(default=0)
    total_expired_webhooks = models.PositiveIntegerField(default=0)
    
    # Request metrics
    total_requests_received = models.PositiveIntegerField(default=0)
    total_bytes_received = models.PositiveBigIntegerField(default=0)
    average_request_size = models.FloatField(default=0.0)
    
    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    average_response_time_ms = models.FloatField(default=0.0)
    error_rate_percentage = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"Analytics for {self.date}"


class WebhookAnalyticsSnapshot(models.Model):
    """Hourly snapshots of webhook analytics"""
    
    webhook = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='analytics_snapshots')
    timestamp = models.DateTimeField()
    
    # Request metrics for this hour
    requests_count = models.PositiveIntegerField(default=0)
    bytes_received = models.PositiveBigIntegerField(default=0)
    unique_ips = models.PositiveIntegerField(default=0)
    
    # Method distribution
    get_count = models.PositiveIntegerField(default=0)
    post_count = models.PositiveIntegerField(default=0)
    put_count = models.PositiveIntegerField(default=0)
    patch_count = models.PositiveIntegerField(default=0)
    delete_count = models.PositiveIntegerField(default=0)
    other_count = models.PositiveIntegerField(default=0)
    
    # Response metrics
    average_response_time_ms = models.FloatField(default=0.0)
    error_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['webhook', 'timestamp']
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['webhook', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"Snapshot for {self.webhook.uuid} at {self.timestamp}"


class SystemMetrics(models.Model):
    """System-wide performance and health metrics"""
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # System performance
    cpu_usage_percentage = models.FloatField(default=0.0)
    memory_usage_percentage = models.FloatField(default=0.0)
    disk_usage_percentage = models.FloatField(default=0.0)
    
    # Database metrics
    database_connections = models.PositiveIntegerField(default=0)
    database_size_mb = models.FloatField(default=0.0)
    
    # Application metrics
    active_webhooks = models.PositiveIntegerField(default=0)
    requests_per_minute = models.FloatField(default=0.0)
    error_rate = models.FloatField(default=0.0)
    
    # Cache metrics (if using Redis)
    cache_hit_rate = models.FloatField(default=0.0)
    cache_memory_usage_mb = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"System metrics at {self.timestamp}"


class GeolocationData(models.Model):
    """Geolocation data for IP addresses"""
    
    ip_address = models.GenericIPAddressField(unique=True)
    country = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timezone = models.CharField(max_length=50, blank=True)
    isp = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['country_code']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} - {self.city}, {self.country}"


class AlertRule(models.Model):
    """Alert rules for monitoring webhook activity"""
    
    ALERT_TYPES = [
        ('high_volume', 'High Volume'),
        ('error_rate', 'High Error Rate'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('webhook_down', 'Webhook Down'),
        ('storage_limit', 'Storage Limit'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='medium')
    
    # Rule conditions
    threshold_value = models.FloatField()
    time_window_minutes = models.PositiveIntegerField(default=60)
    
    # Targeting
    webhook = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Configuration
    is_active = models.BooleanField(default=True)
    send_email = models.BooleanField(default=True)
    send_webhook = models.BooleanField(default=False)
    webhook_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Alert: {self.name} ({self.alert_type})"


class Alert(models.Model):
    """Generated alerts based on alert rules"""
    
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='alerts')
    webhook = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=AlertRule.SEVERITY_LEVELS)
    
    # Alert data
    triggered_value = models.FloatField()
    threshold_value = models.FloatField()
    
    # Status
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    
    # Notifications
    email_sent = models.BooleanField(default=False)
    webhook_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rule', '-created_at']),
            models.Index(fields=['webhook', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_resolved']),
        ]
    
    def __str__(self):
        return f"Alert: {self.title} ({self.severity})"
    
    def resolve(self, resolved_by=None):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.save()


class ExportJob(models.Model):
    """Track data export jobs"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('xml', 'XML'),
        ('pdf', 'PDF'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_jobs')
    webhook = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, null=True, blank=True)
    
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Export parameters
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    include_body = models.BooleanField(default=True)
    
    # Results
    file_path = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    records_exported = models.PositiveIntegerField(default=0)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Export job {self.id} - {self.format} ({self.status})"
