try:
    import django_filters
except ImportError:
    django_filters = None

from django import forms
from django.db.models import Q, F, Count
from django.db import models
from .models import WebhookRequest, WebhookEndpoint, WebhookAnalytics


class WebhookRequestFilter(django_filters.FilterSet):
    """Advanced filtering for webhook requests"""
    
    # Date range filters
    start_date = django_filters.DateTimeFilter(
        field_name='received_at',
        lookup_expr='gte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    end_date = django_filters.DateTimeFilter(
        field_name='received_at',
        lookup_expr='lte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    # Method filter
    method = django_filters.MultipleChoiceFilter(
        choices=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('PATCH', 'PATCH'),
            ('DELETE', 'DELETE'),
            ('HEAD', 'HEAD'),
            ('OPTIONS', 'OPTIONS'),
        ],
        widget=forms.CheckboxSelectMultiple
    )
    
    # Content type filter
    content_type = django_filters.CharFilter(
        field_name='content_type',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., application/json'})
    )
    
    # IP address filter
    ip_address = django_filters.CharFilter(
        field_name='ip_address',
        lookup_expr='exact',
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 192.168.1.1'})
    )
    
    # User agent filter
    user_agent = django_filters.CharFilter(
        field_name='user_agent',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'Search user agent'})
    )
    
    # Body content search
    body_contains = django_filters.CharFilter(
        field_name='body',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'Search in body content'})
    )
    
    # Request size filters
    min_size = django_filters.NumberFilter(
        field_name='content_length',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={'placeholder': 'Min size (bytes)'})
    )
    max_size = django_filters.NumberFilter(
        field_name='content_length',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={'placeholder': 'Max size (bytes)'})
    )
    
    # Processing status
    processed = django_filters.BooleanFilter(
        field_name='processed',
        widget=forms.CheckboxInput()
    )
    
    # Header search (JSON field search)
    header_contains = django_filters.CharFilter(
        method='filter_header_contains',
        widget=forms.TextInput(attrs={'placeholder': 'Search in headers'})
    )
    
    # Path filter
    path = django_filters.CharFilter(
        field_name='path',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'Search in path'})
    )
    
    # Query string filter
    query_string = django_filters.CharFilter(
        field_name='query_string',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'Search in query string'})
    )
    
    class Meta:
        model = WebhookRequest
        fields = [
            'method', 'content_type', 'ip_address', 'processed',
            'start_date', 'end_date', 'body_contains', 'min_size', 'max_size',
            'user_agent', 'header_contains', 'path', 'query_string'
        ]
    
    def filter_header_contains(self, queryset, name, value):
        """Custom filter to search within JSON headers field"""
        if value:
            # Search for the value in the JSON headers field
            return queryset.extra(
                where=["LOWER(headers::text) LIKE LOWER(%s)"],
                params=[f'%{value}%']
            )
        return queryset


class WebhookEndpointFilter(django_filters.FilterSet):
    """Filtering for webhook endpoints"""
    
    # Date range filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    # Status filter
    status = django_filters.MultipleChoiceFilter(
        choices=[
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('disabled', 'Disabled'),
        ],
        widget=forms.CheckboxSelectMultiple
    )
    
    # Request count filters
    min_requests = django_filters.NumberFilter(
        field_name='current_request_count',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={'placeholder': 'Min requests'})
    )
    max_requests = django_filters.NumberFilter(
        field_name='current_request_count',
        lookup_expr='lte',
        widget=forms.NumberInput(attrs={'placeholder': 'Max requests'})
    )
    
    # Public/private filter
    is_public = django_filters.BooleanFilter(
        field_name='is_public',
        widget=forms.CheckboxInput()
    )
    
    # Name search
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'Search webhook name'})
    )
    
    # Description search
    description = django_filters.CharFilter(
        field_name='description',
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={'placeholder': 'Search description'})
    )
    
    # Expiration filters
    expires_soon = django_filters.BooleanFilter(
        method='filter_expires_soon',
        widget=forms.CheckboxInput(),
        label='Expires within 1 hour'
    )
    
    expired = django_filters.BooleanFilter(
        method='filter_expired',
        widget=forms.CheckboxInput(),
        label='Currently expired'
    )
    
    class Meta:
        model = WebhookEndpoint
        fields = [
            'status', 'is_public', 'name', 'description',
            'created_after', 'created_before', 'min_requests', 'max_requests',
            'expires_soon', 'expired'
        ]
    
    def filter_expires_soon(self, queryset, name, value):
        """Filter webhooks that expire within 1 hour"""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            soon = timezone.now() + timedelta(hours=1)
            return queryset.filter(
                expires_at__lte=soon,
                expires_at__gt=timezone.now(),
                status='active'
            )
        return queryset
    
    def filter_expired(self, queryset, name, value):
        """Filter currently expired webhooks"""
        if value:
            from django.utils import timezone
            return queryset.filter(
                Q(expires_at__lt=timezone.now()) |
                Q(status__in=['expired', 'disabled']) |
                Q(current_request_count__gte=F('max_requests'))
            )
        return queryset


class WebhookAnalyticsFilter(django_filters.FilterSet):
    """Filtering for webhook analytics"""
    
    # Request count filters
    min_total_requests = django_filters.NumberFilter(
        field_name='total_requests',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={'placeholder': 'Min total requests'})
    )
    
    # Data size filters
    min_bytes_received = django_filters.NumberFilter(
        field_name='total_bytes_received',
        lookup_expr='gte',
        widget=forms.NumberInput(attrs={'placeholder': 'Min bytes received'})
    )
    
    # Success rate filter
    min_success_rate = django_filters.NumberFilter(
        method='filter_min_success_rate',
        widget=forms.NumberInput(attrs={'placeholder': 'Min success rate (%)'})
    )
    
    # Last request filter
    last_request_after = django_filters.DateTimeFilter(
        field_name='last_request_at',
        lookup_expr='gte',
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    class Meta:
        model = WebhookAnalytics
        fields = [
            'min_total_requests', 'min_bytes_received',
            'min_success_rate', 'last_request_after'
        ]
    
    def filter_min_success_rate(self, queryset, name, value):
        """Filter by minimum success rate percentage"""
        if value is not None:
            # Calculate success rate and filter
            return queryset.extra(
                where=["CASE WHEN total_requests > 0 THEN (successful_requests::float / total_requests::float) * 100 ELSE 0 END >= %s"],
                params=[value]
            )
        return queryset


class DateRangeFilter(django_filters.Filter):
    """Custom date range filter"""
    
    def filter(self, qs, value):
        if value:
            # Expecting value in format: "2024-01-01,2024-01-31"
            try:
                start_date, end_date = value.split(',')
                start_date = django_filters.utils.parse_date(start_date)
                end_date = django_filters.utils.parse_date(end_date)
                
                if start_date and end_date:
                    return qs.filter(
                        **{f'{self.field_name}__date__gte': start_date},
                        **{f'{self.field_name}__date__lte': end_date}
                    )
            except ValueError:
                pass
        
        return qs


class AdvancedWebhookRequestFilter(WebhookRequestFilter):
    """Extended webhook request filter with advanced search capabilities"""
    
    # Custom date range filter
    date_range = DateRangeFilter(field_name='received_at')
    
    # JSON path search (for PostgreSQL)
    json_path = django_filters.CharFilter(
        method='filter_json_path',
        widget=forms.TextInput(attrs={'placeholder': 'JSON path query (e.g., $.user.id)'})
    )
    
    # Multiple IP filter
    ip_addresses = django_filters.CharFilter(
        method='filter_multiple_ips',
        widget=forms.TextInput(attrs={'placeholder': 'Comma-separated IPs'})
    )
    
    # Request frequency filter (requests from same IP within timeframe)
    suspicious_activity = django_filters.BooleanFilter(
        method='filter_suspicious_activity',
        widget=forms.CheckboxInput(),
        label='Suspicious activity (>10 requests/minute from same IP)'
    )
    
    def filter_json_path(self, queryset, name, value):
        """Filter by JSON path in request body (PostgreSQL only)"""
        if value:
            try:
                # This works with PostgreSQL JSON fields
                return queryset.extra(
                    where=["body::json #>> %s IS NOT NULL"],
                    params=[f'{{{value}}}']
                )
            except Exception:
                # Fallback for other databases
                return queryset.filter(body__icontains=value)
        return queryset
    
    def filter_multiple_ips(self, queryset, name, value):
        """Filter by multiple IP addresses"""
        if value:
            ips = [ip.strip() for ip in value.split(',') if ip.strip()]
            if ips:
                return queryset.filter(ip_address__in=ips)
        return queryset
    
    def filter_suspicious_activity(self, queryset, name, value):
        """Filter requests showing suspicious activity patterns"""
        if value:
            from django.utils import timezone
            from datetime import timedelta
            from django.db.models import Count
            
            # Find IPs with more than 10 requests in the last minute
            one_minute_ago = timezone.now() - timedelta(minutes=1)
            
            suspicious_ips = WebhookRequest.objects.filter(
                received_at__gte=one_minute_ago
            ).values('ip_address').annotate(
                request_count=Count('id')
            ).filter(request_count__gt=10).values_list('ip_address', flat=True)
            
            return queryset.filter(ip_address__in=suspicious_ips)
        
        return queryset
