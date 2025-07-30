import json
import logging
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve, Resolver404
from .models import WebhookEndpoint, WebhookRequest, WebhookAnalytics
from .tasks import process_webhook_request_async

logger = logging.getLogger(__name__)


class RawRequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to capture and log raw webhook requests.
    Only processes requests to webhook endpoints.
    """
    
    def process_request(self, request):
        """Capture raw request data for webhook endpoints"""
        try:
            # Check if this is a webhook endpoint request
            resolved = resolve(request.path_info)
            if resolved.url_name == 'receive_webhook':
                # Store raw request data for processing
                request._webhook_data = {
                    'method': request.method,
                    'path': request.path_info,
                    'query_string': request.META.get('QUERY_STRING', ''),
                    'headers': self._extract_headers(request),
                    'body': self._get_request_body(request),
                    'content_type': request.content_type,
                    'content_length': int(request.META.get('CONTENT_LENGTH', 0)),
                    'ip_address': self._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'referer': request.META.get('HTTP_REFERER', ''),
                }
        except (Resolver404, AttributeError):
            # Not a webhook endpoint, skip
            pass
        
        return None
    
    def process_response(self, request, response):
        """Process the response and log webhook data if applicable"""
        if hasattr(request, '_webhook_data') and hasattr(request, 'webhook_uuid'):
            try:
                # Get the webhook endpoint
                webhook = WebhookEndpoint.objects.get(uuid=request.webhook_uuid)
                
                # Check if webhook is still active
                if webhook.is_expired:
                    webhook.status = 'expired'
                    webhook.save()
                    return HttpResponse("Webhook endpoint has expired.", status=410)
                
                # Create webhook request record
                webhook_request = WebhookRequest.objects.create(
                    webhook=webhook,
                    method=request._webhook_data['method'],
                    path=request._webhook_data['path'],
                    query_string=request._webhook_data['query_string'],
                    headers=request._webhook_data['headers'],
                    body=request._webhook_data['body'],
                    content_type=request._webhook_data['content_type'],
                    content_length=request._webhook_data['content_length'],
                    ip_address=request._webhook_data['ip_address'],
                    user_agent=request._webhook_data['user_agent'],
                    referer=request._webhook_data['referer'],
                )
                
                # Increment request count
                webhook.increment_request_count()
                
                # Update or create analytics
                analytics, created = WebhookAnalytics.objects.get_or_create(
                    webhook=webhook,
                    defaults={}
                )
                analytics.update_stats(webhook_request)
                
                # Process request asynchronously (if Celery is available)
                try:
                    process_webhook_request_async.delay(webhook_request.id)
                except Exception as e:
                    logger.warning(f"Failed to queue async processing: {e}")
                
                logger.info(f"Webhook request logged: {webhook.uuid} - {request.method}")
                
            except WebhookEndpoint.DoesNotExist:
                logger.warning(f"Webhook endpoint not found: {getattr(request, 'webhook_uuid', 'unknown')}")
            except Exception as e:
                logger.error(f"Error processing webhook request: {e}")
        
        return response
    
    def _extract_headers(self, request):
        """Extract HTTP headers from request"""
        headers = {}
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                # Convert HTTP_HEADER_NAME to Header-Name
                header_name = key[5:].replace('_', '-').title()
                headers[header_name] = value
            elif key in ['CONTENT_TYPE', 'CONTENT_LENGTH']:
                # Include content headers
                header_name = key.replace('_', '-').title()
                headers[header_name] = value
        return headers
    
    def _get_request_body(self, request):
        """Safely extract request body"""
        try:
            if hasattr(request, 'body'):
                return request.body.decode('utf-8')
            return ''
        except UnicodeDecodeError:
            # Handle binary data
            return f"[Binary data: {len(request.body)} bytes]"
        except Exception:
            return '[Unable to decode body]'
    
    def _get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip


class CORSMiddleware(MiddlewareMixin):
    """
    Custom CORS middleware for webhook endpoints
    """
    
    def process_response(self, request, response):
        """Add CORS headers to webhook responses"""
        try:
            resolved = resolve(request.path_info)
            if resolved.url_name == 'receive_webhook':
                response['Access-Control-Allow-Origin'] = '*'
                response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS'
                response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                response['Access-Control-Max-Age'] = '3600'
        except (Resolver404, AttributeError):
            pass
        
        return response
    
    def process_request(self, request):
        """Handle preflight OPTIONS requests"""
        if request.method == 'OPTIONS':
            try:
                resolved = resolve(request.path_info)
                if resolved.url_name == 'receive_webhook':
                    response = HttpResponse()
                    response['Access-Control-Allow-Origin'] = '*'
                    response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS'
                    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                    response['Access-Control-Max-Age'] = '3600'
                    return response
            except (Resolver404, AttributeError):
                pass
        
        return None
