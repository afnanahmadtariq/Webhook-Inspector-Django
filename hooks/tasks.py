import json
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import models
try:
    from celery import shared_task
except ImportError:
    # Fallback for when Celery is not available
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from .models import WebhookEndpoint, WebhookRequest, WebhookSchema

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_webhook_request_async(self, request_id):
    """
    Asynchronously process a webhook request.
    This includes validation, schema checking, and additional processing.
    """
    try:
        webhook_request = WebhookRequest.objects.get(id=request_id)
        
        # Mark as being processed
        webhook_request.processed = True
        webhook_request.processed_at = timezone.now()
        webhook_request.save()
        
        # Validate against schemas if any exist
        schemas = WebhookSchema.objects.filter(
            webhook=webhook_request.webhook,
            is_active=True
        )
        
        for schema in schemas:
            is_valid, error_message = schema.validate_request_body(webhook_request.body)
            if not is_valid:
                logger.warning(
                    f"Schema validation failed for request {request_id}: {error_message}"
                )
        
        # Additional processing can be added here
        # - Send notifications
        # - Forward to other services
        # - Store in external systems
        
        logger.info(f"Successfully processed webhook request {request_id}")
        
    except WebhookRequest.DoesNotExist:
        logger.error(f"Webhook request {request_id} not found")
    except Exception as exc:
        logger.error(f"Error processing webhook request {request_id}: {exc}")
        # Retry the task
        raise self.retry(exc=exc, countdown=60)


@shared_task
def cleanup_expired_webhooks():
    """
    Cleanup task to remove expired webhooks and old requests.
    Should be run periodically (e.g., every hour).
    """
    try:
        # Mark expired webhooks
        expired_webhooks = WebhookEndpoint.objects.filter(
            status='active',
            expires_at__lt=timezone.now()
        )
        expired_count = expired_webhooks.update(status='expired')
        
        # Mark webhooks that exceeded request limits
        over_limit_webhooks = WebhookEndpoint.objects.filter(
            status='active'
        ).extra(
            where=["current_request_count >= max_requests"]
        )
        over_limit_count = over_limit_webhooks.update(status='expired')
        
        # Delete old webhooks that should be auto-deleted
        cutoff_date = timezone.now() - timedelta(days=7)  # Default, can be configurable
        webhooks_to_delete = WebhookEndpoint.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['expired', 'disabled']
        )
        
        deleted_webhooks = 0
        deleted_requests = 0
        
        for webhook in webhooks_to_delete:
            if webhook.should_auto_delete:
                # Count related requests before deletion
                deleted_requests += webhook.requests.count()
                webhook.delete()
                deleted_webhooks += 1
        
        logger.info(
            f"Cleanup completed: {expired_count} expired by time, "
            f"{over_limit_count} expired by request limit, "
            f"{deleted_webhooks} webhooks deleted, "
            f"{deleted_requests} requests deleted"
        )
        
        return {
            'expired_by_time': expired_count,
            'expired_by_limit': over_limit_count,
            'deleted_webhooks': deleted_webhooks,
            'deleted_requests': deleted_requests
        }
        
    except Exception as exc:
        logger.error(f"Error during cleanup: {exc}")
        raise


@shared_task
def generate_analytics_report(webhook_uuid):
    """
    Generate detailed analytics report for a webhook.
    """
    try:
        webhook = WebhookEndpoint.objects.get(uuid=webhook_uuid)
        requests = webhook.requests.all()
        
        # Generate comprehensive analytics
        analytics = {
            'webhook_uuid': str(webhook.uuid),
            'total_requests': requests.count(),
            'date_range': {
                'start': webhook.created_at.isoformat(),
                'end': timezone.now().isoformat()
            },
            'methods': {},
            'content_types': {},
            'hourly_distribution': {},
            'daily_distribution': {},
            'response_times': [],
            'request_sizes': [],
            'top_ips': {},
            'top_user_agents': {}
        }
        
        # Method distribution
        method_counts = requests.values('method').annotate(
            count=models.Count('method')
        ).order_by('-count')
        for item in method_counts:
            analytics['methods'][item['method']] = item['count']
        
        # Content type distribution
        content_type_counts = requests.exclude(
            content_type=''
        ).values('content_type').annotate(
            count=models.Count('content_type')
        ).order_by('-count')
        for item in content_type_counts:
            analytics['content_types'][item['content_type']] = item['count']
        
        # IP address distribution
        ip_counts = requests.values('ip_address').annotate(
            count=models.Count('ip_address')
        ).order_by('-count')[:10]  # Top 10 IPs
        for item in ip_counts:
            analytics['top_ips'][item['ip_address']] = item['count']
        
        # User agent distribution
        ua_counts = requests.exclude(
            user_agent=''
        ).values('user_agent').annotate(
            count=models.Count('user_agent')
        ).order_by('-count')[:10]  # Top 10 User Agents
        for item in ua_counts:
            analytics['top_user_agents'][item['user_agent']] = item['count']
        
        # Time-based distributions
        for request in requests:
            hour_key = request.received_at.strftime('%H')
            day_key = request.received_at.strftime('%Y-%m-%d')
            
            analytics['hourly_distribution'][hour_key] = analytics['hourly_distribution'].get(hour_key, 0) + 1
            analytics['daily_distribution'][day_key] = analytics['daily_distribution'].get(day_key, 0) + 1
            analytics['request_sizes'].append(request.size_in_bytes)
        
        logger.info(f"Generated analytics report for webhook {webhook_uuid}")
        return analytics
        
    except WebhookEndpoint.DoesNotExist:
        logger.error(f"Webhook {webhook_uuid} not found for analytics")
        return None
    except Exception as exc:
        logger.error(f"Error generating analytics for webhook {webhook_uuid}: {exc}")
        raise


@shared_task
def export_webhook_data(webhook_uuid, format='json'):
    """
    Export webhook data in various formats (JSON, CSV, XML).
    """
    try:
        webhook = WebhookEndpoint.objects.get(uuid=webhook_uuid)
        requests = webhook.requests.all().order_by('-received_at')
        
        if format.lower() == 'json':
            return export_as_json(webhook, requests)
        elif format.lower() == 'csv':
            return export_as_csv(webhook, requests)
        elif format.lower() == 'xml':
            return export_as_xml(webhook, requests)
        else:
            raise ValueError(f"Unsupported export format: {format}")
            
    except WebhookEndpoint.DoesNotExist:
        logger.error(f"Webhook {webhook_uuid} not found for export")
        return None
    except Exception as exc:
        logger.error(f"Error exporting webhook {webhook_uuid}: {exc}")
        raise


def export_as_json(webhook, requests):
    """Export webhook data as JSON"""
    data = {
        'webhook': {
            'uuid': str(webhook.uuid),
            'name': webhook.name,
            'created_at': webhook.created_at.isoformat(),
            'status': webhook.status,
            'total_requests': requests.count()
        },
        'requests': []
    }
    
    for request in requests:
        data['requests'].append({
            'id': request.id,
            'method': request.method,
            'path': request.path,
            'query_string': request.query_string,
            'headers': request.headers,
            'body': request.body,
            'content_type': request.content_type,
            'content_length': request.content_length,
            'ip_address': request.ip_address,
            'user_agent': request.user_agent,
            'received_at': request.received_at.isoformat()
        })
    
    return json.dumps(data, indent=2)


def export_as_csv(webhook, requests):
    """Export webhook data as CSV"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'ID', 'Method', 'Path', 'Query String', 'Content Type',
        'Content Length', 'IP Address', 'User Agent', 'Received At', 'Body'
    ])
    
    # Write data
    for request in requests:
        writer.writerow([
            request.id,
            request.method,
            request.path,
            request.query_string,
            request.content_type,
            request.content_length,
            request.ip_address,
            request.user_agent,
            request.received_at.isoformat(),
            request.body[:1000] + '...' if len(request.body) > 1000 else request.body
        ])
    
    return output.getvalue()


def export_as_xml(webhook, requests):
    """Export webhook data as XML"""
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom
    
    root = Element('webhook_data')
    
    # Webhook info
    webhook_elem = SubElement(root, 'webhook')
    SubElement(webhook_elem, 'uuid').text = str(webhook.uuid)
    SubElement(webhook_elem, 'name').text = webhook.name or ''
    SubElement(webhook_elem, 'created_at').text = webhook.created_at.isoformat()
    SubElement(webhook_elem, 'status').text = webhook.status
    
    # Requests
    requests_elem = SubElement(root, 'requests')
    for request in requests:
        request_elem = SubElement(requests_elem, 'request')
        SubElement(request_elem, 'id').text = str(request.id)
        SubElement(request_elem, 'method').text = request.method
        SubElement(request_elem, 'path').text = request.path
        SubElement(request_elem, 'query_string').text = request.query_string
        SubElement(request_elem, 'content_type').text = request.content_type
        SubElement(request_elem, 'content_length').text = str(request.content_length)
        SubElement(request_elem, 'ip_address').text = request.ip_address
        SubElement(request_elem, 'user_agent').text = request.user_agent
        SubElement(request_elem, 'received_at').text = request.received_at.isoformat()
        SubElement(request_elem, 'body').text = request.body
    
    # Pretty print
    rough_string = tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")
