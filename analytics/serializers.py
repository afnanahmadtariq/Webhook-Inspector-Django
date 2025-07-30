from rest_framework import serializers
from .models import (
    AnalyticsSummary, WebhookAnalyticsSnapshot, SystemMetrics,
    GeolocationData, AlertRule, Alert, ExportJob
)


class AnalyticsSummarySerializer(serializers.ModelSerializer):
    """Serializer for analytics summary"""
    
    class Meta:
        model = AnalyticsSummary
        fields = [
            'date', 'total_webhooks_created', 'total_active_webhooks',
            'total_expired_webhooks', 'total_requests_received',
            'total_bytes_received', 'average_request_size', 'total_users',
            'active_users', 'new_users', 'average_response_time_ms',
            'error_rate_percentage', 'created_at', 'updated_at'
        ]


class WebhookAnalyticsSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for webhook analytics snapshots"""
    
    webhook_uuid = serializers.SerializerMethodField()
    
    class Meta:
        model = WebhookAnalyticsSnapshot
        fields = [
            'webhook_uuid', 'timestamp', 'requests_count', 'bytes_received',
            'unique_ips', 'get_count', 'post_count', 'put_count', 'patch_count',
            'delete_count', 'other_count', 'average_response_time_ms',
            'error_count', 'created_at'
        ]
    
    def get_webhook_uuid(self, obj):
        return str(obj.webhook.uuid)


class SystemMetricsSerializer(serializers.ModelSerializer):
    """Serializer for system metrics"""
    
    class Meta:
        model = SystemMetrics
        fields = [
            'timestamp', 'cpu_usage_percentage', 'memory_usage_percentage',
            'disk_usage_percentage', 'database_connections', 'database_size_mb',
            'active_webhooks', 'requests_per_minute', 'error_rate',
            'cache_hit_rate', 'cache_memory_usage_mb'
        ]


class GeolocationDataSerializer(serializers.ModelSerializer):
    """Serializer for geolocation data"""
    
    class Meta:
        model = GeolocationData
        fields = [
            'ip_address', 'country', 'country_code', 'region', 'city',
            'latitude', 'longitude', 'timezone', 'isp', 'created_at', 'updated_at'
        ]


class AlertRuleSerializer(serializers.ModelSerializer):
    """Serializer for alert rules"""
    
    webhook_uuid = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    
    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'alert_type', 'severity',
            'threshold_value', 'time_window_minutes', 'webhook_uuid',
            'username', 'is_active', 'send_email', 'send_webhook',
            'webhook_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_webhook_uuid(self, obj):
        return str(obj.webhook.uuid) if obj.webhook else None
    
    def get_username(self, obj):
        return obj.user.username if obj.user else None


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for alerts"""
    
    rule_name = serializers.SerializerMethodField()
    webhook_uuid = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    resolved_by_username = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'rule_name', 'webhook_uuid', 'username', 'title', 'message',
            'severity', 'triggered_value', 'threshold_value', 'is_resolved',
            'resolved_at', 'resolved_by_username', 'email_sent', 'webhook_sent',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_rule_name(self, obj):
        return obj.rule.name
    
    def get_webhook_uuid(self, obj):
        return str(obj.webhook.uuid) if obj.webhook else None
    
    def get_username(self, obj):
        return obj.user.username if obj.user else None
    
    def get_resolved_by_username(self, obj):
        return obj.resolved_by.username if obj.resolved_by else None


class ExportJobSerializer(serializers.ModelSerializer):
    """Serializer for export jobs"""
    
    username = serializers.SerializerMethodField()
    webhook_uuid = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = ExportJob
        fields = [
            'id', 'username', 'webhook_uuid', 'format', 'status',
            'start_date', 'end_date', 'include_body', 'file_path',
            'file_size_bytes', 'file_size_mb', 'records_exported',
            'created_at', 'started_at', 'completed_at', 'duration_seconds',
            'error_message'
        ]
        read_only_fields = [
            'id', 'status', 'file_path', 'file_size_bytes', 'records_exported',
            'created_at', 'started_at', 'completed_at', 'error_message'
        ]
    
    def get_username(self, obj):
        return obj.user.username
    
    def get_webhook_uuid(self, obj):
        return str(obj.webhook.uuid) if obj.webhook else None
    
    def get_file_size_mb(self, obj):
        if obj.file_size_bytes:
            return round(obj.file_size_bytes / (1024 * 1024), 2)
        return 0
    
    def get_duration_seconds(self, obj):
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    
    total_webhooks = serializers.IntegerField()
    active_webhooks = serializers.IntegerField()
    requests_today = serializers.IntegerField()
    bytes_today = serializers.IntegerField()
    unique_ips_today = serializers.IntegerField()
    top_countries = serializers.ListField()
    hourly_requests = serializers.DictField()
    alert_counts = serializers.DictField()


class SystemHealthSerializer(serializers.Serializer):
    """Serializer for system health status"""
    
    status = serializers.ChoiceField(choices=['healthy', 'warning', 'critical'])
    timestamp = serializers.DateTimeField()
    metrics = serializers.DictField()
    warnings = serializers.ListField()
    active_alerts = serializers.IntegerField()


class GeolocationStatsSerializer(serializers.Serializer):
    """Serializer for geolocation statistics"""
    
    countries = serializers.ListField()
    cities = serializers.ListField()
    total_locations = serializers.IntegerField()


class AlertCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating alerts"""
    
    class Meta:
        model = AlertRule
        fields = [
            'name', 'description', 'alert_type', 'severity',
            'threshold_value', 'time_window_minutes', 'webhook',
            'send_email', 'send_webhook', 'webhook_url'
        ]
    
    def validate(self, data):
        """Validate alert rule data"""
        if data.get('send_webhook') and not data.get('webhook_url'):
            raise serializers.ValidationError(
                "Webhook URL is required when webhook notifications are enabled"
            )
        
        if data['threshold_value'] <= 0:
            raise serializers.ValidationError(
                "Threshold value must be greater than 0"
            )
        
        if data['time_window_minutes'] <= 0:
            raise serializers.ValidationError(
                "Time window must be greater than 0 minutes"
            )
        
        return data


class ReportSerializer(serializers.Serializer):
    """Serializer for analytics reports"""
    
    period = serializers.DictField()
    totals = serializers.DictField()
    breakdown = serializers.ListField(required=False)
    daily_breakdown = serializers.ListField(required=False)
    weekly_breakdown = serializers.ListField(required=False)
