from django.urls import path
from . import views

# Traditional Django URLs
urlpatterns = [
    # Traditional views
    path('create/', views.create_webhook, name='create_webhook'),
    path('<uuid:hook_uuid>/', views.receive_webhook, name='receive_webhook'),
    path('<uuid:hook_uuid>/inspect/', views.inspect_webhook, name='inspect_webhook'),
    
    # # DRF API endpoints for webhook management
    path('endpoints/', views.WebhookEndpointListCreateView.as_view(), name='webhook_endpoints'),
    # path('endpoints/<uuid:uuid>/', views.WebhookEndpointDetailView.as_view(), name='webhook_endpoint_detail'),
    # path('capture/<uuid:hook_uuid>/', views.receive_webhook, name='webhook_capture'),
    
    # # Request management endpoints
    path('requests/', views.WebhookRequestListView.as_view(), name='webhook_requests'),
    # path('requests/<int:request_id>/', views.WebhookRequestDetailView.as_view(), name='webhook_request_detail'),
    # path('requests/export/', views.WebhookExportView.as_view(), name='webhook_export'),
    # path('export-status/<str:task_id>/', views.WebhookExportStatusView.as_view(), name='webhook_export_status'),
    
    # # Analytics endpoints
    # path('analytics/', views.WebhookAnalyticsView.as_view(), name='webhook_analytics_all'),
    # path('<uuid:hook_uuid>/analytics/', views.WebhookAnalyticsView.as_view(), name='webhook_analytics'),
    # path('<uuid:hook_uuid>/stats/', views.WebhookStatsView.as_view(), name='webhook_stats'),
    
    # # Health check
    # path('health/', views.webhook_health_check, name='webhook_health'),
    
    # # Schema management
    # path('schemas/', views.WebhookSchemaListCreateView.as_view(), name='webhook_schemas'),
    # path('schemas/<int:schema_id>/', views.WebhookSchemaDetailView.as_view(), name='webhook_schema_detail'),
    # path('schemas/<int:schema_id>/validate/', views.validate_webhook_schema, name='validate_schema'),
    
    # # Legacy API endpoints (for backward compatibility)
    # path('api/webhooks/', views.WebhookEndpointListCreateView.as_view(), name='api_webhook_list'),
    # path('api/webhooks/<uuid:uuid>/', views.WebhookEndpointDetailView.as_view(), name='api_webhook_detail'),
    # path('api/webhooks/<uuid:hook_uuid>/requests/', views.WebhookRequestListView.as_view(), name='api_webhook_requests'),
    # path('api/webhooks/<uuid:hook_uuid>/requests/<int:request_id>/', views.WebhookRequestDetailView.as_view(), name='api_webhook_request_detail'),
    # path('api/webhooks/<uuid:hook_uuid>/analytics/', views.WebhookAnalyticsView.as_view(), name='api_webhook_analytics'),
    # path('api/webhooks/<uuid:hook_uuid>/stats/', views.WebhookStatsView.as_view(), name='api_webhook_stats'),
    # path('api/webhooks/<uuid:hook_uuid>/export/', views.WebhookExportView.as_view(), name='api_webhook_export'),
    # path('api/webhooks/<uuid:hook_uuid>/health/', views.webhook_health_check, name='api_webhook_health'),
    # path('api/webhooks/<uuid:hook_uuid>/schemas/', views.WebhookSchemaListCreateView.as_view(), name='api_webhook_schemas'),
    # path('api/webhooks/<uuid:hook_uuid>/schemas/<int:schema_id>/', views.WebhookSchemaDetailView.as_view(), name='api_webhook_schema_detail'),
    # path('api/webhooks/<uuid:hook_uuid>/schemas/<int:schema_id>/validate/', views.validate_webhook_schema, name='api_validate_schema'),
    # path('api/requests/', views.WebhookRequestListView.as_view(), name='api_all_requests'),
]
