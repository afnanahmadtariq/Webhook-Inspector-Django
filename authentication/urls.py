from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication endpoints
    path('register/', views.UserRegistrationView.as_view(), name='user_register'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Profile management
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('profile/api-key/', views.GenerateAPIKeyView.as_view(), name='generate_api_key'),
    path('profile/stats/', views.UserStatsView.as_view(), name='user_stats'),
    
    # API usage tracking
    path('usage/', views.APIUsageListView.as_view(), name='api_usage'),
]
