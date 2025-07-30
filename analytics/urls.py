from django.urls import path
from . import views

urlpatterns = [
    # Analytics dashboard
    path('dashboard/', views.AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
    path('summary/', views.AnalyticsSummaryListView.as_view(), name='analytics_summary'),
    path('summary/<str:date>/', views.AnalyticsSummaryDetailView.as_view(), name='analytics_summary_detail'),
    
    # System metrics
    path('system/metrics/', views.SystemMetricsListView.as_view(), name='system_metrics'),
    path('system/health/', views.system_health_status, name='system_health'),
    
    # Alerts
    path('alerts/', views.AlertListView.as_view(), name='alert_list'),
    path('alerts/<int:alert_id>/', views.AlertDetailView.as_view(), name='alert_detail'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    path('alert-rules/', views.AlertRuleListCreateView.as_view(), name='alert_rule_list'),
    path('alert-rules/<int:rule_id>/', views.AlertRuleDetailView.as_view(), name='alert_rule_detail'),
    
    # Geolocation
    path('geolocation/', views.GeolocationDataListView.as_view(), name='geolocation_list'),
    path('geolocation/stats/', views.geolocation_stats, name='geolocation_stats'),
    
    # Export jobs
    path('exports/', views.ExportJobListView.as_view(), name='export_job_list'),
    path('exports/<int:job_id>/', views.ExportJobDetailView.as_view(), name='export_job_detail'),
    path('exports/create/', views.create_export_job, name='create_export_job'),
    
    # Reports
    path('reports/daily/', views.daily_report, name='daily_report'),
    path('reports/weekly/', views.weekly_report, name='weekly_report'),
    path('reports/monthly/', views.monthly_report, name='monthly_report'),
]
