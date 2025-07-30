from rest_framework import serializers
from .models import WebhookEndpoint, WebhookRequest, WebhookAnalytics, WebhookSchema


class WebhookEndpointSerializer(serializers.ModelSerializer):
    """Serializer for WebhookEndpoint model"""
    
    url = serializers.SerializerMethodField()
    inspect_url = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    should_auto_delete = serializers.ReadOnlyField()
    requests_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = WebhookEndpoint
        fields = [
            'uuid', 'name', 'description', 'owner', 'created_at', 'expires_at',
            'max_requests', 'current_request_count', 'status', 'is_public',
            'auto_delete_after_days', 'url', 'inspect_url', 'is_expired',
            'should_auto_delete', 'requests_remaining'
        ]
        read_only_fields = ['uuid', 'created_at', 'current_request_count', 'owner']
    
    def get_url(self, obj):
        """Get the webhook URL"""
        return f"/hooks/{obj.uuid}/"
    
    def get_inspect_url(self, obj):
        """Get the inspect URL"""
        return f"/hooks/{obj.uuid}/inspect/"
    
    def get_requests_remaining(self, obj):
        """Get remaining requests count"""
        return max(0, obj.max_requests - obj.current_request_count)


class WebhookEndpointCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating WebhookEndpoint"""
    
    class Meta:
        model = WebhookEndpoint
        fields = [
            'name', 'description', 'max_requests', 'auto_delete_after_days', 'is_public'
        ]
    
    def validate_max_requests(self, value):
        """Validate max_requests field"""
        if value < 1:
            raise serializers.ValidationError("Max requests must be at least 1")
        if value > 10000:
            raise serializers.ValidationError("Max requests cannot exceed 10,000")
        return value
    
    def validate_auto_delete_after_days(self, value):
        """Validate auto_delete_after_days field"""
        if value < 1:
            raise serializers.ValidationError("Auto delete days must be at least 1")
        if value > 365:
            raise serializers.ValidationError("Auto delete days cannot exceed 365")
        return value


class WebhookRequestSerializer(serializers.ModelSerializer):
    """Serializer for WebhookRequest model"""
    
    parsed_body = serializers.ReadOnlyField()
    size_in_bytes = serializers.ReadOnlyField()
    webhook_uuid = serializers.SerializerMethodField()
    
    class Meta:
        model = WebhookRequest
        fields = [
            'id', 'webhook_uuid', 'method', 'path', 'query_string', 'headers',
            'body', 'parsed_body', 'content_type', 'content_length', 'received_at',
            'ip_address', 'user_agent', 'referer', 'processed', 'processed_at',
            'size_in_bytes'
        ]
        read_only_fields = ['id', 'received_at', 'processed', 'processed_at']
    
    def get_webhook_uuid(self, obj):
        """Get the webhook UUID"""
        return str(obj.webhook.uuid)


class WebhookRequestSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for webhook request summaries"""
    
    webhook_uuid = serializers.SerializerMethodField()
    
    class Meta:
        model = WebhookRequest
        fields = [
            'id', 'webhook_uuid', 'method', 'content_type', 'content_length',
            'received_at', 'ip_address', 'processed'
        ]
    
    def get_webhook_uuid(self, obj):
        """Get the webhook UUID"""
        return str(obj.webhook.uuid)


class WebhookAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for WebhookAnalytics model"""
    
    webhook_uuid = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    most_common_method = serializers.SerializerMethodField()
    most_common_content_type = serializers.SerializerMethodField()
    
    class Meta:
        model = WebhookAnalytics
        fields = [
            'webhook_uuid', 'total_requests', 'successful_requests', 'failed_requests',
            'total_bytes_received', 'average_request_size', 'get_requests',
            'post_requests', 'put_requests', 'patch_requests', 'delete_requests',
            'other_requests', 'json_requests', 'xml_requests', 'form_requests',
            'text_requests', 'other_content_requests', 'last_request_at',
            'updated_at', 'success_rate', 'most_common_method', 'most_common_content_type'
        ]
        read_only_fields = ['updated_at']
    
    def get_webhook_uuid(self, obj):
        """Get the webhook UUID"""
        return str(obj.webhook.uuid)
    
    def get_success_rate(self, obj):
        """Calculate success rate percentage"""
        if obj.total_requests == 0:
            return 0.0
        return round((obj.successful_requests / obj.total_requests) * 100, 2)
    
    def get_most_common_method(self, obj):
        """Get the most common HTTP method"""
        methods = {
            'GET': obj.get_requests,
            'POST': obj.post_requests,
            'PUT': obj.put_requests,
            'PATCH': obj.patch_requests,
            'DELETE': obj.delete_requests,
            'OTHER': obj.other_requests
        }
        return max(methods, key=methods.get) if max(methods.values()) > 0 else None
    
    def get_most_common_content_type(self, obj):
        """Get the most common content type"""
        content_types = {
            'JSON': obj.json_requests,
            'XML': obj.xml_requests,
            'FORM': obj.form_requests,
            'TEXT': obj.text_requests,
            'OTHER': obj.other_content_requests
        }
        return max(content_types, key=content_types.get) if max(content_types.values()) > 0 else None


class WebhookSchemaSerializer(serializers.ModelSerializer):
    """Serializer for WebhookSchema model"""
    
    webhook_uuid = serializers.SerializerMethodField()
    
    class Meta:
        model = WebhookSchema
        fields = [
            'id', 'webhook_uuid', 'name', 'schema', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_webhook_uuid(self, obj):
        """Get the webhook UUID"""
        return str(obj.webhook.uuid)
    
    def validate_schema(self, value):
        """Validate that the schema is valid JSON Schema"""
        try:
            # Basic validation - check if it's a valid dict
            if not isinstance(value, dict):
                raise serializers.ValidationError("Schema must be a valid JSON object")
            
            # Check for required JSON Schema fields
            if 'type' not in value:
                raise serializers.ValidationError("Schema must have a 'type' field")
            
            return value
        except Exception as e:
            raise serializers.ValidationError(f"Invalid schema: {str(e)}")


class WebhookStatsSerializer(serializers.Serializer):
    """Serializer for webhook statistics"""
    
    total_requests = serializers.IntegerField()
    unique_ips = serializers.IntegerField()
    methods = serializers.DictField()
    content_types = serializers.DictField()
    hourly_distribution = serializers.DictField()
    daily_distribution = serializers.DictField()
    average_request_size = serializers.FloatField()
    largest_request = serializers.IntegerField()
    first_request = serializers.DateTimeField(allow_null=True)
    last_request = serializers.DateTimeField(allow_null=True)


class WebhookHealthSerializer(serializers.Serializer):
    """Serializer for webhook health check"""
    
    uuid = serializers.UUIDField()
    status = serializers.CharField()
    is_expired = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(allow_null=True)
    current_requests = serializers.IntegerField()
    max_requests = serializers.IntegerField()
    requests_remaining = serializers.IntegerField()
    last_request = serializers.DictField(allow_null=True)


class WebhookValidationSerializer(serializers.Serializer):
    """Serializer for schema validation results"""
    
    is_valid = serializers.BooleanField()
    error_message = serializers.CharField(allow_null=True)
    schema_name = serializers.CharField()


class BulkWebhookRequestSerializer(serializers.Serializer):
    """Serializer for bulk webhook request operations"""
    
    action = serializers.ChoiceField(choices=['delete', 'export', 'mark_processed'])
    request_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    
    def validate_request_ids(self, value):
        """Validate that all request IDs exist"""
        if len(value) > 1000:
            raise serializers.ValidationError("Cannot process more than 1000 requests at once")
        return value


class WebhookExportSerializer(serializers.Serializer):
    """Serializer for webhook data export"""
    
    format = serializers.ChoiceField(choices=['json', 'csv', 'xml'], default='json')
    include_body = serializers.BooleanField(default=True)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    method_filter = serializers.MultipleChoiceField(
        choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), 
                ('PATCH', 'PATCH'), ('DELETE', 'DELETE')],
        required=False
    )
    
    def validate(self, data):
        """Validate date range"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Start date must be before end date")
        
        return data
