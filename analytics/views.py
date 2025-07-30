from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta, datetime

from .models import (
    AnalyticsSummary, WebhookAnalyticsSnapshot, SystemMetrics,
    GeolocationData, AlertRule, Alert, ExportJob
)
from .serializers import (
    AnalyticsSummarySerializer, SystemMetricsSerializer,
    GeolocationDataSerializer, AlertRuleSerializer, AlertSerializer,
    ExportJobSerializer
)


class AnalyticsDashboardView(APIView):
    """Main analytics dashboard data"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Get date range
            days = int(request.query_params.get('days', 30))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get summary data
            summaries = AnalyticsSummary.objects.filter(
                date__range=[start_date, end_date]
            ).order_by('date')
            
            # Calculate totals
            totals = summaries.aggregate(
                total_webhooks=Sum('total_webhooks_created'),
                total_requests=Sum('total_requests_received'),
                total_bytes=Sum('total_bytes_received'),
                total_users=Sum('new_users')
            )
            
            # Get recent system metrics
            recent_metrics = SystemMetrics.objects.order_by('-timestamp')[:24]
            
            # Get active alerts
            active_alerts = Alert.objects.filter(is_resolved=False).count()
            
            # Prepare time series data
            time_series = {
                'dates': [summary.date.isoformat() for summary in summaries],
                'webhooks_created': [summary.total_webhooks_created for summary in summaries],
                'requests_received': [summary.total_requests_received for summary in summaries],
                'new_users': [summary.new_users for summary in summaries],
            }
            
            dashboard_data = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'totals': {
                    'webhooks_created': totals['total_webhooks'] or 0,
                    'requests_received': totals['total_requests'] or 0,
                    'bytes_received': totals['total_bytes'] or 0,
                    'new_users': totals['total_users'] or 0,
                    'active_alerts': active_alerts
                },
                'time_series': time_series,
                'system_metrics': [
                    {
                        'timestamp': metric.timestamp.isoformat(),
                        'cpu_usage': metric.cpu_usage_percentage,
                        'memory_usage': metric.memory_usage_percentage,
                        'requests_per_minute': metric.requests_per_minute
                    } for metric in recent_metrics
                ]
            }
            
            return Response(dashboard_data)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class AnalyticsSummaryListView(generics.ListAPIView):
    """List analytics summaries"""
    serializer_class = AnalyticsSummarySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = AnalyticsSummary.objects.all().order_by('-date')
        
        # Date filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date).date()
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date).date()
                queryset = queryset.filter(date__lte=end_date)
            except ValueError:
                pass
        
        return queryset


class AnalyticsSummaryDetailView(generics.RetrieveAPIView):
    """Get analytics summary for specific date"""
    serializer_class = AnalyticsSummarySerializer
    permission_classes = [AllowAny]
    lookup_field = 'date'
    queryset = AnalyticsSummary.objects.all()


class SystemMetricsListView(generics.ListAPIView):
    """List system metrics"""
    serializer_class = SystemMetricsSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Default to last 24 hours
        hours = int(self.request.query_params.get('hours', 24))
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        return SystemMetrics.objects.filter(
            timestamp__gte=cutoff_time
        ).order_by('-timestamp')


@api_view(['GET'])
@permission_classes([AllowAny])
def system_health_status(request):
    """Get current system health status"""
    try:
        # Get latest metrics
        latest_metric = SystemMetrics.objects.order_by('-timestamp').first()
        
        if not latest_metric:
            return Response({'error': 'No metrics available'}, status=404)
        
        # Determine health status based on thresholds
        health_status = 'healthy'
        warnings = []
        
        if latest_metric.cpu_usage_percentage > 80:
            health_status = 'warning'
            warnings.append('High CPU usage')
        
        if latest_metric.memory_usage_percentage > 85:
            health_status = 'critical' if health_status != 'critical' else health_status
            warnings.append('High memory usage')
        
        if latest_metric.disk_usage_percentage > 90:
            health_status = 'critical'
            warnings.append('High disk usage')
        
        # Check for active alerts
        active_alerts = Alert.objects.filter(is_resolved=False).count()
        if active_alerts > 0:
            health_status = 'warning' if health_status == 'healthy' else health_status
            warnings.append(f'{active_alerts} active alerts')
        
        return Response({
            'status': health_status,
            'timestamp': latest_metric.timestamp.isoformat(),
            'metrics': {
                'cpu_usage': latest_metric.cpu_usage_percentage,
                'memory_usage': latest_metric.memory_usage_percentage,
                'disk_usage': latest_metric.disk_usage_percentage,
                'active_webhooks': latest_metric.active_webhooks,
                'requests_per_minute': latest_metric.requests_per_minute
            },
            'warnings': warnings,
            'active_alerts': active_alerts
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


class AlertListView(generics.ListAPIView):
    """List alerts"""
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Alert.objects.all().order_by('-created_at')
        
        # Filter by user's webhooks if not staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Filter parameters
        is_resolved = self.request.query_params.get('resolved')
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')
        
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        return queryset


class AlertDetailView(generics.RetrieveAPIView):
    """Get alert details"""
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'alert_id'
    
    def get_queryset(self):
        queryset = Alert.objects.all()
        
        # Filter by user's webhooks if not staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        return queryset


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_alert(request, alert_id):
    """Resolve an alert"""
    try:
        alert = Alert.objects.get(id=alert_id)
        
        # Check permissions
        if not request.user.is_staff and alert.user != request.user:
            return Response({'error': 'Permission denied'}, status=403)
        
        alert.resolve(resolved_by=request.user)
        
        return Response({'message': 'Alert resolved successfully'})
        
    except Alert.DoesNotExist:
        return Response({'error': 'Alert not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


class AlertRuleListCreateView(generics.ListCreateAPIView):
    """List and create alert rules"""
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = AlertRule.objects.all().order_by('-created_at')
        
        # Filter by user if not staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AlertRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Alert rule detail operations"""
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'rule_id'
    
    def get_queryset(self):
        queryset = AlertRule.objects.all()
        
        # Filter by user if not staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        return queryset


class GeolocationDataListView(generics.ListAPIView):
    """List geolocation data"""
    serializer_class = GeolocationDataSerializer
    permission_classes = [AllowAny]
    queryset = GeolocationData.objects.all().order_by('country', 'city')


@api_view(['GET'])
@permission_classes([AllowAny])
def geolocation_stats(request):
    """Get geolocation statistics"""
    try:
        # Country distribution
        country_stats = GeolocationData.objects.values('country').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # City distribution
        city_stats = GeolocationData.objects.exclude(
            city=''
        ).values('city', 'country').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return Response({
            'countries': [
                {'country': item['country'], 'count': item['count']}
                for item in country_stats
            ],
            'cities': [
                {'city': item['city'], 'country': item['country'], 'count': item['count']}
                for item in city_stats
            ],
            'total_locations': GeolocationData.objects.count()
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


class ExportJobListView(generics.ListAPIView):
    """List export jobs"""
    serializer_class = ExportJobSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ExportJob.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class ExportJobDetailView(generics.RetrieveAPIView):
    """Get export job details"""
    serializer_class = ExportJobSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'job_id'
    
    def get_queryset(self):
        return ExportJob.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_export_job(request):
    """Create a new export job"""
    try:
        from hooks.models import WebhookEndpoint
        
        webhook_uuid = request.data.get('webhook_uuid')
        format_type = request.data.get('format', 'json')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        include_body = request.data.get('include_body', True)
        
        webhook = None
        if webhook_uuid:
            try:
                webhook = WebhookEndpoint.objects.get(uuid=webhook_uuid)
                # Check permissions
                if webhook.owner and webhook.owner != request.user and not request.user.is_staff:
                    return Response({'error': 'Permission denied'}, status=403)
            except WebhookEndpoint.DoesNotExist:
                return Response({'error': 'Webhook not found'}, status=404)
        
        # Create export job
        export_job = ExportJob.objects.create(
            user=request.user,
            webhook=webhook,
            format=format_type,
            start_date=start_date,
            end_date=end_date,
            include_body=include_body
        )
        
        # Queue the export task
        try:
            from .tasks import process_export_job
            process_export_job.delay(export_job.id)
        except ImportError:
            # Handle synchronously if Celery not available
            pass
        
        serializer = ExportJobSerializer(export_job)
        return Response(serializer.data, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def daily_report(request):
    """Generate daily analytics report"""
    try:
        date_str = request.query_params.get('date')
        if date_str:
            try:
                report_date = datetime.fromisoformat(date_str).date()
            except ValueError:
                return Response({'error': 'Invalid date format'}, status=400)
        else:
            report_date = timezone.now().date() - timedelta(days=1)
        
        try:
            summary = AnalyticsSummary.objects.get(date=report_date)
            serializer = AnalyticsSummarySerializer(summary)
            return Response({
                'date': report_date.isoformat(),
                'summary': serializer.data
            })
        except AnalyticsSummary.DoesNotExist:
            return Response({'error': f'No data available for {report_date}'}, status=404)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def weekly_report(request):
    """Generate weekly analytics report"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
        
        summaries = AnalyticsSummary.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Calculate weekly totals
        totals = summaries.aggregate(
            total_webhooks=Sum('total_webhooks_created'),
            total_requests=Sum('total_requests_received'),
            total_bytes=Sum('total_bytes_received'),
            total_users=Sum('new_users'),
            avg_response_time=Avg('average_response_time_ms'),
            avg_error_rate=Avg('error_rate_percentage')
        )
        
        daily_data = AnalyticsSummarySerializer(summaries, many=True).data
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'type': 'weekly'
            },
            'totals': totals,
            'daily_breakdown': daily_data
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def monthly_report(request):
    """Generate monthly analytics report"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        summaries = AnalyticsSummary.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Calculate monthly totals
        totals = summaries.aggregate(
            total_webhooks=Sum('total_webhooks_created'),
            total_requests=Sum('total_requests_received'),
            total_bytes=Sum('total_bytes_received'),
            total_users=Sum('new_users'),
            avg_response_time=Avg('average_response_time_ms'),
            avg_error_rate=Avg('error_rate_percentage')
        )
        
        # Group by week for better visualization
        weekly_data = []
        current_week_start = start_date
        while current_week_start <= end_date:
            week_end = min(current_week_start + timedelta(days=6), end_date)
            week_summaries = summaries.filter(
                date__range=[current_week_start, week_end]
            )
            
            week_totals = week_summaries.aggregate(
                webhooks=Sum('total_webhooks_created'),
                requests=Sum('total_requests_received'),
                bytes=Sum('total_bytes_received'),
                users=Sum('new_users')
            )
            
            weekly_data.append({
                'week_start': current_week_start.isoformat(),
                'week_end': week_end.isoformat(),
                **week_totals
            })
            
            current_week_start = week_end + timedelta(days=1)
        
        return Response({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'type': 'monthly'
            },
            'totals': totals,
            'weekly_breakdown': weekly_data
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)
