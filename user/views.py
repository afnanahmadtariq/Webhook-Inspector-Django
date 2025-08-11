from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

from .models import UserProfile, APIUsage
from .serializers import (
    UserRegistrationSerializer, UserProfileSerializer, 
    APIKeySerializer, CustomTokenObtainPairSerializer,
    APIUsageSerializer, UserStatsSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view with additional user info"""
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """Logout endpoint (for token blacklisting)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # If using token blacklisting
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile management"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class GenerateAPIKeyView(APIView):
    """Generate new API key for user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            api_key = profile.generate_api_key()
            
            serializer = APIKeySerializer({
                'api_key': api_key,
                'created_at': profile.api_key_created_at
            })
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserStatsView(APIView):
    """User statistics and usage overview"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get user profile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)
        
        # Calculate statistics
        from hooks.models import WebhookEndpoint, WebhookRequest
        
        total_webhooks = WebhookEndpoint.objects.filter(owner=user).count()
        active_webhooks = WebhookEndpoint.objects.filter(owner=user, status='active').count()
        
        # Requests this month
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        requests_this_month = WebhookRequest.objects.filter(
            webhook__owner=user,
            received_at__gte=month_start
        ).count()
        
        # API calls today
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        api_calls_today = APIUsage.objects.filter(
            user=user,
            timestamp__gte=today_start
        ).count()
        
        # Storage calculation (approximate)
        requests_today = WebhookRequest.objects.filter(
            webhook__owner=user,
            received_at__gte=today_start
        ).count()
        
        total_requests = WebhookRequest.objects.filter(webhook__owner=user)
        storage_bytes = total_requests.aggregate(
            total=Sum('content_length')
        )['total'] or 0
        storage_mb = storage_bytes / (1024 * 1024)
        
        stats = {
            'totalEndpoints': total_webhooks,
            'activeEndpoints': active_webhooks,
            'totalRequests': profile.total_requests_received,
            'requestsToday': requests_today,
            'requests_this_month': requests_this_month,
            'api_calls_today': api_calls_today,
            'storage_used_mb': round(storage_mb, 2),
            'webhook_retention_days': profile.webhook_retention_days,
            'max_webhooks': profile.max_webhooks,
            'webhooks_remaining': max(0, profile.max_webhooks - active_webhooks)
        }
        
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)


class APIUsageListView(generics.ListAPIView):
    """List API usage for the current user"""
    serializer_class = APIUsageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return APIUsage.objects.filter(user=self.request.user).order_by('-timestamp')


# API Key authentication middleware
class APIKeyAuthentication:
    """Custom API key authentication"""
    
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        try:
            profile = UserProfile.objects.get(api_key=api_key)
            return (profile.user, None)
        except UserProfile.DoesNotExist:
            return None
    
    def authenticate_header(self, request):
        return 'X-API-Key'


# Utility functions
def track_api_usage(user, endpoint, method, ip_address, user_agent, response_status):
    """Track API usage for a user"""
    try:
        APIUsage.objects.create(
            user=user,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent or '',
            response_status=response_status
        )
    except Exception:
        # Fail silently to not break the main request
        pass


def check_rate_limit(user, endpoint, limit=100, window_minutes=60):
    """Check if user has exceeded rate limit for an endpoint"""
    if not user or not user.is_authenticated:
        return True  # Allow anonymous requests for now
    
    window_start = timezone.now() - timedelta(minutes=window_minutes)
    recent_calls = APIUsage.objects.filter(
        user=user,
        endpoint=endpoint,
        timestamp__gte=window_start
    ).count()
    
    return recent_calls < limit
