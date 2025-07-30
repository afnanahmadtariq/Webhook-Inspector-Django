import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from django.contrib.auth.models import User

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from hooks.models import WebhookEndpoint, WebhookRequest
from .models import (
    AnalyticsSummary, WebhookAnalyticsSnapshot, SystemMetrics,
    GeolocationData, AlertRule, Alert, ExportJob
)

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_analytics():
    """Generate daily analytics summary"""
    try:
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Check if analytics already exist for yesterday
        summary, created = AnalyticsSummary.objects.get_or_create(
            date=yesterday,
            defaults={}
        )
        
        if not created and summary.updated_at.date() == timezone.now().date():
            logger.info(f"Analytics for {yesterday} already up to date")
            return
        
        # Calculate webhook metrics
        webhooks_created = WebhookEndpoint.objects.filter(
            created_at__date=yesterday
        ).count()
        
        active_webhooks = WebhookEndpoint.objects.filter(
            status='active'
        ).count()
        
        expired_webhooks = WebhookEndpoint.objects.filter(
            status__in=['expired', 'disabled']
        ).count()
        
        # Calculate request metrics
        yesterday_start = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        yesterday_end = yesterday_start + timedelta(days=1)
        
        requests_yesterday = WebhookRequest.objects.filter(
            received_at__gte=yesterday_start,
            received_at__lt=yesterday_end
        )
        
        total_requests = requests_yesterday.count()
        total_bytes = requests_yesterday.aggregate(
            total=Sum('content_length')
        )['total'] or 0
        
        avg_request_size = requests_yesterday.aggregate(
            avg=Avg('content_length')
        )['avg'] or 0
        
        # Calculate user metrics
        total_users = User.objects.count()
        
        # Users who had webhook activity yesterday
        active_users = User.objects.filter(
            webhookendpoint__requests__received_at__gte=yesterday_start,
            webhookendpoint__requests__received_at__lt=yesterday_end
        ).distinct().count()
        
        new_users = User.objects.filter(
            date_joined__date=yesterday
        ).count()
        
        # Update summary
        summary.total_webhooks_created = webhooks_created
        summary.total_active_webhooks = active_webhooks
        summary.total_expired_webhooks = expired_webhooks
        summary.total_requests_received = total_requests
        summary.total_bytes_received = total_bytes
        summary.average_request_size = avg_request_size
        summary.total_users = total_users
        summary.active_users = active_users
        summary.new_users = new_users
        summary.save()
        
        logger.info(f"Generated daily analytics for {yesterday}")
        return summary.id
        
    except Exception as exc:
        logger.error(f"Error generating daily analytics: {exc}")
        raise


@shared_task
def generate_hourly_snapshots():
    """Generate hourly analytics snapshots for active webhooks"""
    try:
        current_hour = timezone.now().replace(minute=0, second=0, microsecond=0)
        hour_start = current_hour - timedelta(hours=1)
        
        active_webhooks = WebhookEndpoint.objects.filter(status='active')
        
        for webhook in active_webhooks:
            # Get requests for the past hour
            hour_requests = webhook.requests.filter(
                received_at__gte=hour_start,
                received_at__lt=current_hour
            )
            
            if hour_requests.exists():
                # Calculate metrics
                requests_count = hour_requests.count()
                bytes_received = hour_requests.aggregate(
                    total=Sum('content_length')
                )['total'] or 0
                
                unique_ips = hour_requests.values('ip_address').distinct().count()
                
                # Method counts
                method_counts = hour_requests.values('method').annotate(
                    count=Count('method')
                )
                
                method_data = {
                    'get_count': 0,
                    'post_count': 0,
                    'put_count': 0,
                    'patch_count': 0,
                    'delete_count': 0,
                    'other_count': 0
                }
                
                for item in method_counts:
                    method = item['method'].lower()
                    count = item['count']
                    
                    if method in method_data:
                        method_data[f'{method}_count'] = count
                    else:
                        method_data['other_count'] += count
                
                # Create or update snapshot
                snapshot, created = WebhookAnalyticsSnapshot.objects.get_or_create(
                    webhook=webhook,
                    timestamp=hour_start,
                    defaults={
                        'requests_count': requests_count,
                        'bytes_received': bytes_received,
                        'unique_ips': unique_ips,
                        **method_data
                    }
                )
                
                if not created:
                    # Update existing snapshot
                    snapshot.requests_count = requests_count
                    snapshot.bytes_received = bytes_received
                    snapshot.unique_ips = unique_ips
                    for key, value in method_data.items():
                        setattr(snapshot, key, value)
                    snapshot.save()
        
        logger.info(f"Generated hourly snapshots for {current_hour}")
        
    except Exception as exc:
        logger.error(f"Error generating hourly snapshots: {exc}")
        raise


@shared_task
def system_health_check():
    """Perform system health check and collect metrics"""
    try:
        import psutil
        
        # Get system metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database metrics (simplified)
        active_webhooks = WebhookEndpoint.objects.filter(status='active').count()
        
        # Calculate requests per minute
        one_minute_ago = timezone.now() - timedelta(minutes=1)
        recent_requests = WebhookRequest.objects.filter(
            received_at__gte=one_minute_ago
        ).count()
        
        # Create system metrics record
        SystemMetrics.objects.create(
            cpu_usage_percentage=cpu_usage,
            memory_usage_percentage=memory.percent,
            disk_usage_percentage=disk.percent,
            active_webhooks=active_webhooks,
            requests_per_minute=recent_requests
        )
        
        # Clean up old metrics (keep last 24 hours)
        cutoff_time = timezone.now() - timedelta(hours=24)
        SystemMetrics.objects.filter(timestamp__lt=cutoff_time).delete()
        
        logger.info("System health check completed")
        
    except ImportError:
        logger.warning("psutil not available, skipping system metrics")
    except Exception as exc:
        logger.error(f"Error in system health check: {exc}")
        raise


@shared_task
def check_alert_rules():
    """Check alert rules and trigger alerts if necessary"""
    try:
        active_rules = AlertRule.objects.filter(is_active=True)
        
        for rule in active_rules:
            try:
                should_alert = False
                triggered_value = 0
                
                # Calculate time window
                window_start = timezone.now() - timedelta(minutes=rule.time_window_minutes)
                
                if rule.alert_type == 'high_volume':
                    # Check for high request volume
                    if rule.webhook:
                        request_count = rule.webhook.requests.filter(
                            received_at__gte=window_start
                        ).count()
                    else:
                        request_count = WebhookRequest.objects.filter(
                            received_at__gte=window_start
                        ).count()
                    
                    triggered_value = request_count
                    should_alert = request_count > rule.threshold_value
                
                elif rule.alert_type == 'error_rate':
                    # Check for high error rate
                    if rule.webhook:
                        total_requests = rule.webhook.requests.filter(
                            received_at__gte=window_start
                        ).count()
                        # For now, assume all requests are successful
                        error_rate = 0
                    else:
                        total_requests = WebhookRequest.objects.filter(
                            received_at__gte=window_start
                        ).count()
                        error_rate = 0
                    
                    triggered_value = error_rate
                    should_alert = error_rate > rule.threshold_value
                
                elif rule.alert_type == 'suspicious_activity':
                    # Check for suspicious patterns
                    suspicious_ips = WebhookRequest.objects.filter(
                        received_at__gte=window_start
                    ).values('ip_address').annotate(
                        request_count=Count('id')
                    ).filter(request_count__gt=rule.threshold_value).count()
                    
                    triggered_value = suspicious_ips
                    should_alert = suspicious_ips > 0
                
                elif rule.alert_type == 'webhook_down':
                    # Check if webhook hasn't received requests
                    if rule.webhook:
                        last_request = rule.webhook.requests.order_by('-received_at').first()
                        if last_request:
                            minutes_since_last = (timezone.now() - last_request.received_at).total_seconds() / 60
                            triggered_value = minutes_since_last
                            should_alert = minutes_since_last > rule.threshold_value
                
                # Create alert if conditions are met
                if should_alert:
                    # Check if similar alert already exists (prevent spam)
                    recent_alert = Alert.objects.filter(
                        rule=rule,
                        webhook=rule.webhook,
                        created_at__gte=window_start,
                        is_resolved=False
                    ).first()
                    
                    if not recent_alert:
                        alert = Alert.objects.create(
                            rule=rule,
                            webhook=rule.webhook,
                            user=rule.user,
                            title=f"{rule.name} - {rule.alert_type}",
                            message=f"Alert triggered: {rule.description}",
                            severity=rule.severity,
                            triggered_value=triggered_value,
                            threshold_value=rule.threshold_value
                        )
                        
                        # Send notifications
                        if rule.send_email:
                            send_alert_email.delay(alert.id)
                        
                        if rule.send_webhook and rule.webhook_url:
                            send_alert_webhook.delay(alert.id)
                        
                        logger.info(f"Alert created: {alert.title}")
                
            except Exception as e:
                logger.error(f"Error checking alert rule {rule.id}: {e}")
        
    except Exception as exc:
        logger.error(f"Error checking alert rules: {exc}")
        raise


@shared_task
def send_alert_email(alert_id):
    """Send email notification for alert"""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        alert = Alert.objects.get(id=alert_id)
        
        subject = f"Webhook Inspector Alert: {alert.title}"
        message = f"""
        Alert Details:
        - Title: {alert.title}
        - Severity: {alert.severity}
        - Message: {alert.message}
        - Triggered Value: {alert.triggered_value}
        - Threshold: {alert.threshold_value}
        - Time: {alert.created_at}
        
        Webhook: {alert.webhook.uuid if alert.webhook else 'System-wide'}
        """
        
        recipient_email = None
        if alert.user:
            recipient_email = alert.user.email
        elif alert.webhook and alert.webhook.owner:
            recipient_email = alert.webhook.owner.email
        
        if recipient_email:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient_email],
                fail_silently=False,
            )
            
            alert.email_sent = True
            alert.save()
            
            logger.info(f"Alert email sent for alert {alert_id}")
        
    except Alert.DoesNotExist:
        logger.error(f"Alert {alert_id} not found")
    except Exception as exc:
        logger.error(f"Error sending alert email for {alert_id}: {exc}")


@shared_task
def send_alert_webhook(alert_id):
    """Send webhook notification for alert"""
    try:
        import requests
        
        alert = Alert.objects.get(id=alert_id)
        
        if not alert.rule.webhook_url:
            logger.warning(f"No webhook URL configured for alert {alert_id}")
            return
        
        payload = {
            'alert_id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity,
            'triggered_value': alert.triggered_value,
            'threshold_value': alert.threshold_value,
            'timestamp': alert.created_at.isoformat(),
            'webhook_uuid': str(alert.webhook.uuid) if alert.webhook else None
        }
        
        response = requests.post(
            alert.rule.webhook_url,
            json=payload,
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        response.raise_for_status()
        
        alert.webhook_sent = True
        alert.save()
        
        logger.info(f"Alert webhook sent for alert {alert_id}")
        
    except Alert.DoesNotExist:
        logger.error(f"Alert {alert_id} not found")
    except Exception as exc:
        logger.error(f"Error sending alert webhook for {alert_id}: {exc}")


@shared_task
def geocode_ip_addresses():
    """Geocode IP addresses for analytics"""
    try:
        # Get unique IP addresses that haven't been geocoded
        uncoded_ips = WebhookRequest.objects.exclude(
            ip_address__in=GeolocationData.objects.values_list('ip_address', flat=True)
        ).values_list('ip_address', flat=True).distinct()[:100]  # Limit to 100 per run
        
        for ip_address in uncoded_ips:
            try:
                # You would integrate with a geolocation service here
                # For example: ipapi, ipinfo, maxmind, etc.
                # This is a placeholder implementation
                
                geolocation_data = get_ip_geolocation(ip_address)
                
                if geolocation_data:
                    GeolocationData.objects.get_or_create(
                        ip_address=ip_address,
                        defaults=geolocation_data
                    )
                
            except Exception as e:
                logger.warning(f"Failed to geocode IP {ip_address}: {e}")
        
        logger.info(f"Geocoded {len(uncoded_ips)} IP addresses")
        
    except Exception as exc:
        logger.error(f"Error in geocoding task: {exc}")


def get_ip_geolocation(ip_address):
    """Get geolocation data for an IP address"""
    # Placeholder implementation
    # In production, you would use a real geolocation service
    
    # Example with ipapi.co (free tier)
    try:
        import requests
        
        response = requests.get(
            f'https://ipapi.co/{ip_address}/json/',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            return {
                'country': data.get('country_name', ''),
                'country_code': data.get('country_code', ''),
                'region': data.get('region', ''),
                'city': data.get('city', ''),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'timezone': data.get('timezone', ''),
                'isp': data.get('org', '')
            }
    
    except Exception as e:
        logger.warning(f"Geolocation API error for {ip_address}: {e}")
    
    return None


@shared_task
def cleanup_old_analytics():
    """Clean up old analytics data"""
    try:
        # Keep analytics summaries for 1 year
        cutoff_date = timezone.now().date() - timedelta(days=365)
        deleted_summaries = AnalyticsSummary.objects.filter(
            date__lt=cutoff_date
        ).delete()[0]
        
        # Keep hourly snapshots for 30 days
        cutoff_time = timezone.now() - timedelta(days=30)
        deleted_snapshots = WebhookAnalyticsSnapshot.objects.filter(
            timestamp__lt=cutoff_time
        ).delete()[0]
        
        # Keep system metrics for 7 days
        cutoff_time = timezone.now() - timedelta(days=7)
        deleted_metrics = SystemMetrics.objects.filter(
            timestamp__lt=cutoff_time
        ).delete()[0]
        
        # Clean up resolved alerts older than 30 days
        cutoff_time = timezone.now() - timedelta(days=30)
        deleted_alerts = Alert.objects.filter(
            is_resolved=True,
            resolved_at__lt=cutoff_time
        ).delete()[0]
        
        logger.info(
            f"Cleanup completed: {deleted_summaries} summaries, "
            f"{deleted_snapshots} snapshots, {deleted_metrics} metrics, "
            f"{deleted_alerts} alerts deleted"
        )
        
    except Exception as exc:
        logger.error(f"Error in cleanup task: {exc}")
        raise
