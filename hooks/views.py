import json
import logging
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q, Count, Avg, Max
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator

from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import WebhookEndpoint, WebhookRequest, WebhookAnalytics, WebhookSchema
from .serializers import (
    WebhookEndpointSerializer, WebhookRequestSerializer, 
    WebhookAnalyticsSerializer, WebhookSchemaSerializer,
    WebhookEndpointCreateSerializer
)
from .filters import WebhookRequestFilter
try:
    from .tasks import generate_analytics_report, export_webhook_data
except ImportError:
    # Fallback when Celery is not available
    generate_analytics_report = None
    export_webhook_data = None

logger = logging.getLogger(__name__)


@csrf_exempt
def create_webhook(request):
    """Create a new webhook endpoint"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            webhook = WebhookEndpoint.objects.create(
                name=data.get('name', ''),
                description=data.get('description', ''),
                owner=request.user if request.user.is_authenticated else None,
                max_requests=data.get('max_requests', 100),
                auto_delete_after_days=data.get('auto_delete_after_days', 7)
            )
            return JsonResponse({
                'uuid': str(webhook.uuid),
                'url': f'/webhooks/{webhook.uuid}/',
                'inspect_url': f'/webhooks/{webhook.uuid}/inspect/',
                'created_at': webhook.created_at.isoformat(),
                'expires_at': webhook.expires_at.isoformat() if webhook.expires_at else None
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
def receive_webhook(request, hook_uuid):
    """Receive and process webhook requests"""
    try:
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        
        # Store webhook UUID for middleware processing
        request.webhook_uuid = hook_uuid
        
        # Check if webhook is expired
        if webhook.is_expired:
            webhook.status = 'expired'
            webhook.save()
            return HttpResponse("Webhook endpoint has expired.", status=410)
        
        # The actual request logging is handled by middleware
        # This view just returns a success response
        
        return JsonResponse({
            'status': 'received',
            'timestamp': timezone.now().isoformat(),
            'webhook_uuid': str(webhook.uuid),
            'method': request.method,
            'request_count': webhook.current_request_count + 1
        })
        
    except Exception as e:
        logger.error(f"Error processing webhook {hook_uuid}: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def inspect_webhook(request, hook_uuid):
    """Inspect webhook requests"""
    webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
    requests_list = WebhookRequest.objects.filter(webhook=webhook).order_by('-received_at')

    # Pagination
    paginator = Paginator(requests_list, 20)
    page_number = request.GET.get('page')
    requests = paginator.get_page(page_number)

    # Serialize requests
    requests_data = []
    for req in requests:
        requests_data.append({
            'id': req.id,
            'method': req.method,
            'body': req.body,
            'received_at': req.received_at.isoformat(),
            'ip_address': req.ip_address,
            'user_agent': req.user_agent,
            'content_type': req.content_type,
            'content_length': req.content_length,
            'processed': req.processed,
        })

    response_data = {
        'webhook': {
            'uuid': str(webhook.uuid),
            'name': webhook.name,
            'description': webhook.description,
            'created_at': webhook.created_at.isoformat(),
            'status': webhook.status,
        },
        'requests': requests_data,
        'total_requests': requests_list.count(),
        'page': requests.number,
        'num_pages': paginator.num_pages,
        'has_next': requests.has_next(),
        'has_previous': requests.has_previous(),
    }

    return JsonResponse(response_data)


# REST API Views

class WebhookEndpointListCreateView(generics.ListCreateAPIView):
    """API view for listing and creating webhook endpoints"""
    queryset = WebhookEndpoint.objects.all()
    serializer_class = WebhookEndpointSerializer
    permission_classes = [AllowAny]  # Change to [IsAuthenticated] for production
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_public']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'expires_at', 'current_request_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return WebhookEndpointCreateSerializer
        return WebhookEndpointSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user if self.request.user.is_authenticated else None)
    
    def create(self, request, *args, **kwargs):
        """Override create to return full object data"""
        create_serializer = self.get_serializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        instance = create_serializer.save(owner=request.user if request.user.is_authenticated else None)
        
        # Return the full object using the read serializer
        read_serializer = WebhookEndpointSerializer(instance, context={'request': request})
        headers = self.get_success_headers(read_serializer.data)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class WebhookEndpointDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating, and deleting webhook endpoints"""
    queryset = WebhookEndpoint.objects.all()
    serializer_class = WebhookEndpointSerializer
    lookup_field = 'uuid'
    permission_classes = [AllowAny]


class WebhookRequestListView(generics.ListAPIView):
    """API view for listing webhook requests"""
    serializer_class = WebhookRequestSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = WebhookRequestFilter
    search_fields = ['body', 'user_agent', 'ip_address']
    ordering_fields = ['received_at', 'method', 'content_length']
    ordering = ['-received_at']
    
    def get_queryset(self):
        hook_uuid = self.kwargs.get('hook_uuid')
        if hook_uuid:
            webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
            return WebhookRequest.objects.filter(webhook=webhook)
        return WebhookRequest.objects.all()


class WebhookRequestDetailView(generics.RetrieveAPIView):
    """API view for retrieving individual webhook requests"""
    serializer_class = WebhookRequestSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        hook_uuid = self.kwargs.get('hook_uuid')
        request_id = self.kwargs.get('request_id')
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        return get_object_or_404(WebhookRequest, webhook=webhook, id=request_id)


class WebhookAnalyticsView(APIView):
    """API view for webhook analytics"""
    permission_classes = [AllowAny]
    
    def get(self, request, hook_uuid=None):
        # If hook_uuid is provided in URL, use it; otherwise, check query params
        if not hook_uuid:
            hook_uuid = request.query_params.get('endpoint_uuid')
        
        if not hook_uuid:
            return Response({
                'error': 'endpoint_uuid parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        
        try:
            analytics = WebhookAnalytics.objects.get(webhook=webhook)
            serializer = WebhookAnalyticsSerializer(analytics)
            return Response(serializer.data)
        except WebhookAnalytics.DoesNotExist:
            # Create analytics if they don't exist
            analytics = WebhookAnalytics.objects.create(webhook=webhook)
            serializer = WebhookAnalyticsSerializer(analytics)
            return Response(serializer.data)


class WebhookStatsView(APIView):
    """Advanced analytics and statistics"""
    permission_classes = [AllowAny]
    
    def get(self, request, hook_uuid):
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        requests = webhook.requests.all()
        
        # Date range filter
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                requests = requests.filter(received_at__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                requests = requests.filter(received_at__lte=end_date)
            except ValueError:
                pass
        
        # Calculate statistics
        stats = {
            'total_requests': requests.count(),
            'unique_ips': requests.values('ip_address').distinct().count(),
            'methods': dict(requests.values('method').annotate(count=Count('method')).values_list('method', 'count')),
            'content_types': dict(requests.exclude(content_type='').values('content_type').annotate(count=Count('content_type')).values_list('content_type', 'count')),
            'hourly_distribution': self._get_hourly_distribution(requests),
            'daily_distribution': self._get_daily_distribution(requests),
            'average_request_size': requests.aggregate(avg_size=Avg('content_length'))['avg_size'] or 0,
            'largest_request': requests.aggregate(max_size=Max('content_length'))['max_size'] or 0,
            'first_request': requests.order_by('received_at').first().received_at.isoformat() if requests.exists() else None,
            'last_request': requests.order_by('-received_at').first().received_at.isoformat() if requests.exists() else None,
        }
        
        return Response(stats)
    
    def _get_hourly_distribution(self, requests):
        """Get request distribution by hour"""
        hourly = {}
        for i in range(24):
            hourly[f"{i:02d}"] = 0
        
        for request in requests:
            hour = request.received_at.strftime('%H')
            hourly[hour] += 1
        
        return hourly
    
    def _get_daily_distribution(self, requests):
        """Get request distribution by day (last 30 days)"""
        daily = {}
        end_date = timezone.now().date()
        
        for i in range(30):
            date = end_date - timedelta(days=i)
            daily[date.isoformat()] = 0
        
        for request in requests:
            date_key = request.received_at.date().isoformat()
            if date_key in daily:
                daily[date_key] += 1
        
        return daily


class WebhookExportView(APIView):
    """Export webhook data in various formats"""
    permission_classes = [AllowAny]
    
    def get(self, request, hook_uuid=None):
        # Debug logging
        print(f"🔍 WebhookExportView called with hook_uuid={hook_uuid}")
        print(f"🔍 Query params: {dict(request.query_params)}")
        print(f"🔍 Format requested: {request.query_params.get('format', 'none')}")
        
        # If hook_uuid is provided in URL, use it; otherwise, check query params
        if not hook_uuid:
            hook_uuid = request.query_params.get('endpoint_uuid')
        
        if not hook_uuid:
            return Response({
                'error': 'endpoint_uuid parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        format_type = request.query_params.get('format') or request.query_params.get('export_format') or request.query_params.get('type', 'json')
        format_type = format_type.lower()
        
        if format_type not in ['json', 'csv', 'xml']:
            return Response({'error': 'Invalid format. Supported: json, csv, xml'}, status=400)
        
        # Check if async processing is requested
        async_processing = request.query_params.get('async', 'false').lower() == 'true'
        
        # Try to use Celery for async processing if available and requested
        try:
            from .tasks import export_webhook_data_async, CELERY_AVAILABLE
            
            if CELERY_AVAILABLE and async_processing:
                # Start async task
                user_id = request.user.id if hasattr(request.user, 'id') else None
                task = export_webhook_data_async.delay(str(hook_uuid), format_type, user_id)
                
                return Response({
                    'status': 'processing',
                    'task_id': task.id,
                    'webhook_uuid': str(hook_uuid),
                    'format': format_type,
                    'message': 'Export started. Use task_id to check status.',
                    'check_status_url': f'/api/v1/webhooks/export-status/{task.id}/'
                }, status=202)  # 202 Accepted
                
        except ImportError:
            # Celery not available, fall back to synchronous processing
            pass
        
        # Synchronous export (fallback or when async not requested)
        requests = webhook.requests.all().order_by('-received_at')
        
        if format_type == 'json':
            # JSON export
            data = []
            for req in requests:
                data.append({
                    'id': req.id,
                    'method': req.method,
                    'path': req.path,
                    'query_string': req.query_string,
                    'headers': req.headers,
                    'body': req.body,
                    'content_type': req.content_type,
                    'content_length': req.content_length,
                    'ip_address': req.ip_address,
                    'user_agent': req.user_agent,
                    'received_at': req.received_at.isoformat(),
                    'processed': req.processed,
                })
            
            response_data = {
                'webhook': {
                    'uuid': str(webhook.uuid),
                    'name': webhook.name,
                    'description': webhook.description,
                    'created_at': webhook.created_at.isoformat(),
                    'status': webhook.status,
                },
                'requests': data,
                'export_metadata': {
                    'exported_at': timezone.now().isoformat(),
                    'total_requests': len(data),
                    'format': 'json',
                    'processing_mode': 'synchronous'
                }
            }
            return Response(response_data)
            
        elif format_type == 'csv':
            # Simple CSV export  
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['ID', 'Method', 'Body', 'Received At', 'IP Address'])
            
            # Write data
            for req in requests:
                writer.writerow([
                    req.id,
                    req.method,
                    req.body[:100] if req.body else '',  # Truncate body
                    req.received_at.isoformat(),
                    req.ip_address,
                ])
            
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="webhook_{webhook.uuid}.csv"'
            return response
            
        else:
            return Response({'error': 'Unsupported format'}, status=400)


class WebhookExportStatusView(APIView):
    """Check the status of an async export task"""
    permission_classes = [AllowAny]
    
    def get(self, request, task_id):
        try:
            from celery.result import AsyncResult
            from .tasks import CELERY_AVAILABLE
            
            if not CELERY_AVAILABLE:
                return Response({
                    'error': 'Celery not available'
                }, status=503)
            
            # Get task result
            task_result = AsyncResult(task_id)
            
            response_data = {
                'task_id': task_id,
                'status': task_result.status,
                'ready': task_result.ready(),
            }
            
            if task_result.ready():
                if task_result.successful():
                    result = task_result.result
                    response_data.update({
                        'completed': True,
                        'result': result
                    })
                else:
                    response_data.update({
                        'completed': True,
                        'error': str(task_result.result)
                    })
            else:
                response_data.update({
                    'completed': False,
                    'message': 'Task is still processing'
                })
            
            return Response(response_data)
            
        except ImportError:
            return Response({
                'error': 'Celery not available'
            }, status=503)
        except Exception as e:
            return Response({
                'error': f'Failed to check task status: {str(e)}'
            }, status=500)


class WebhookSchemaListCreateView(generics.ListCreateAPIView):
    """API view for managing webhook schemas"""
    serializer_class = WebhookSchemaSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        hook_uuid = self.kwargs.get('hook_uuid')
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        return WebhookSchema.objects.filter(webhook=webhook)
    
    def perform_create(self, serializer):
        hook_uuid = self.kwargs.get('hook_uuid')
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        serializer.save(webhook=webhook)


class WebhookSchemaDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for individual webhook schemas"""
    serializer_class = WebhookSchemaSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        hook_uuid = self.kwargs.get('hook_uuid')
        schema_id = self.kwargs.get('schema_id')
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        return get_object_or_404(WebhookSchema, webhook=webhook, id=schema_id)


@api_view(['GET'])
@permission_classes([AllowAny])
def webhook_health_check(request, hook_uuid):
    """Health check endpoint for a webhook"""
    try:
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        
        health_data = {
            'uuid': str(webhook.uuid),
            'status': webhook.status,
            'is_expired': webhook.is_expired,
            'created_at': webhook.created_at.isoformat(),
            'expires_at': webhook.expires_at.isoformat() if webhook.expires_at else None,
            'current_requests': webhook.current_request_count,
            'max_requests': webhook.max_requests,
            'requests_remaining': max(0, webhook.max_requests - webhook.current_request_count),
            'last_request': None
        }
        
        # Get last request info
        last_request = webhook.requests.order_by('-received_at').first()
        if last_request:
            health_data['last_request'] = {
                'timestamp': last_request.received_at.isoformat(),
                'method': last_request.method,
                'ip_address': last_request.ip_address
            }
        
        return Response(health_data)
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_webhook_schema(request, hook_uuid, schema_id):
    """Validate request body against a specific schema"""
    try:
        webhook = get_object_or_404(WebhookEndpoint, uuid=hook_uuid)
        schema = get_object_or_404(WebhookSchema, webhook=webhook, id=schema_id)
        
        body = request.data.get('body', '')
        is_valid, error_message = schema.validate_request_body(body)
        
        return Response({
            'is_valid': is_valid,
            'error_message': error_message,
            'schema_name': schema.name
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# Error handlers
def custom_404(request, exception):
    """Custom 404 error handler"""
    return JsonResponse({
        'error': 'Not found',
        'message': 'The requested resource was not found',
        'status_code': 404
    }, status=404)


def custom_500(request):
    """Custom 500 error handler"""
    return JsonResponse({
        'error': 'Internal server error',
        'message': 'An internal server error occurred',
        'status_code': 500
    }, status=500)
