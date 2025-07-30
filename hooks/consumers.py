import json
import logging
from typing import Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import WebhookEndpoint, WebhookRequest

logger = logging.getLogger(__name__)


class WebhookConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time webhook updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.webhook_uuid = self.scope['url_route']['kwargs']['webhook_uuid']
        self.room_group_name = f'webhook_{self.webhook_uuid}'
        
        # Check if webhook exists
        webhook_exists = await self.check_webhook_exists(self.webhook_uuid)
        if not webhook_exists:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial webhook info
        webhook_info = await self.get_webhook_info(self.webhook_uuid)
        await self.send(text_data=json.dumps({
            'type': 'webhook_info',
            'data': webhook_info
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'get_recent_requests':
                # Send recent requests
                recent_requests = await self.get_recent_requests(self.webhook_uuid)
                await self.send(text_data=json.dumps({
                    'type': 'recent_requests',
                    'data': recent_requests
                }))
            
            elif message_type == 'get_analytics':
                # Send analytics data
                analytics = await self.get_webhook_analytics(self.webhook_uuid)
                await self.send(text_data=json.dumps({
                    'type': 'analytics',
                    'data': analytics
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    # Receive message from room group
    async def webhook_request(self, event):
        """Send webhook request to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_request',
            'data': event['data']
        }))
    
    async def webhook_analytics_update(self, event):
        """Send analytics update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'analytics_update',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def check_webhook_exists(self, webhook_uuid):
        """Check if webhook exists"""
        try:
            WebhookEndpoint.objects.get(uuid=webhook_uuid)
            return True
        except WebhookEndpoint.DoesNotExist:
            return False
    
    @database_sync_to_async
    def get_webhook_info(self, webhook_uuid):
        """Get webhook information"""
        try:
            webhook = WebhookEndpoint.objects.get(uuid=webhook_uuid)
            return {
                'uuid': str(webhook.uuid),
                'name': webhook.name,
                'status': webhook.status,
                'created_at': webhook.created_at.isoformat(),
                'expires_at': webhook.expires_at.isoformat() if webhook.expires_at else None,
                'current_requests': webhook.current_request_count,
                'max_requests': webhook.max_requests,
                'is_expired': webhook.is_expired
            }
        except WebhookEndpoint.DoesNotExist:
            return None
    
    @database_sync_to_async
    def get_recent_requests(self, webhook_uuid, limit=20):
        """Get recent requests for webhook"""
        try:
            webhook = WebhookEndpoint.objects.get(uuid=webhook_uuid)
            requests = webhook.requests.order_by('-received_at')[:limit]
            
            return [{
                'id': req.id,
                'method': req.method,
                'path': req.path,
                'content_type': req.content_type,
                'content_length': req.content_length,
                'ip_address': req.ip_address,
                'received_at': req.received_at.isoformat(),
                'headers': req.headers,
                'body': req.body[:500] + '...' if len(req.body) > 500 else req.body
            } for req in requests]
        except WebhookEndpoint.DoesNotExist:
            return []
    
    @database_sync_to_async
    def get_webhook_analytics(self, webhook_uuid):
        """Get webhook analytics"""
        try:
            webhook = WebhookEndpoint.objects.get(uuid=webhook_uuid)
            
            # Get analytics if exists
            try:
                analytics = webhook.analytics
                return {
                    'total_requests': analytics.total_requests,
                    'successful_requests': analytics.successful_requests,
                    'failed_requests': analytics.failed_requests,
                    'total_bytes_received': analytics.total_bytes_received,
                    'average_request_size': analytics.average_request_size,
                    'last_request_at': analytics.last_request_at.isoformat() if analytics.last_request_at else None
                }
            except:
                return {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'total_bytes_received': 0,
                    'average_request_size': 0,
                    'last_request_at': None
                }
        except WebhookEndpoint.DoesNotExist:
            return None


class DashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for dashboard real-time updates"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.room_group_name = 'dashboard'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial dashboard data
        dashboard_data = await self.get_dashboard_data()
        await self.send(text_data=json.dumps({
            'type': 'dashboard_data',
            'data': dashboard_data
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'get_system_stats':
                stats = await self.get_system_stats()
                await self.send(text_data=json.dumps({
                    'type': 'system_stats',
                    'data': stats
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    # Receive message from room group
    async def dashboard_update(self, event):
        """Send dashboard update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': event['data']
        }))
    
    async def system_alert(self, event):
        """Send system alert to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'system_alert',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_dashboard_data(self):
        """Get dashboard overview data"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get counts
        total_webhooks = WebhookEndpoint.objects.count()
        active_webhooks = WebhookEndpoint.objects.filter(status='active').count()
        total_requests_today = WebhookRequest.objects.filter(received_at__gte=today).count()
        
        # Get recent requests
        recent_requests = WebhookRequest.objects.order_by('-received_at')[:10]
        
        return {
            'total_webhooks': total_webhooks,
            'active_webhooks': active_webhooks,
            'expired_webhooks': total_webhooks - active_webhooks,
            'requests_today': total_requests_today,
            'recent_requests': [{
                'id': req.id,
                'webhook_uuid': str(req.webhook.uuid),
                'method': req.method,
                'ip_address': req.ip_address,
                'received_at': req.received_at.isoformat()
            } for req in recent_requests]
        }
    
    @database_sync_to_async
    def get_system_stats(self):
        """Get system performance stats"""
        # This would typically gather system metrics
        # For now, return placeholder data
        return {
            'cpu_usage': 45.2,
            'memory_usage': 62.8,
            'disk_usage': 34.1,
            'active_connections': 23,
            'requests_per_minute': 145
        }


class UserConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for user-specific notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        if self.user == AnonymousUser():
            await self.close()
            return
        
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        
        # Check if user can access this channel
        if str(self.user.id) != self.user_id:
            await self.close()
            return
        
        self.room_group_name = f'user_{self.user_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'mark_notification_read':
                notification_id = text_data_json.get('notification_id')
                await self.mark_notification_read(notification_id)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    # Receive message from room group
    async def user_notification(self, event):
        """Send notification to user"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))
    
    async def webhook_alert(self, event):
        """Send webhook alert to user"""
        await self.send(text_data=json.dumps({
            'type': 'webhook_alert',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read"""
        # Implementation would depend on notification model
        pass


# Utility functions for sending WebSocket messages
async def send_webhook_update(webhook_uuid: str, data: Dict[str, Any]):
    """Send webhook update to all connected clients"""
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    if channel_layer:
        await channel_layer.group_send(
            f'webhook_{webhook_uuid}',
            {
                'type': 'webhook_request',
                'data': data
            }
        )


async def send_dashboard_update(data: Dict[str, Any]):
    """Send dashboard update to all connected clients"""
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    if channel_layer:
        await channel_layer.group_send(
            'dashboard',
            {
                'type': 'dashboard_update',
                'data': data
            }
        )


async def send_user_notification(user_id: int, data: Dict[str, Any]):
    """Send notification to specific user"""
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    if channel_layer:
        await channel_layer.group_send(
            f'user_{user_id}',
            {
                'type': 'user_notification',
                'data': data
            }
        )
