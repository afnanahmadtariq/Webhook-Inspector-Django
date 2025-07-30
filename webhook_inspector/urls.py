"""
URL configuration for webhook_inspector project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# API version prefix
API_VERSION = 'v1'

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Main webhook endpoints
    path('', include('hooks.urls')),
    
    # Authentication endpoints
    path('auth/', include('authentication.urls')),
    
    # API endpoints with versioning
    path(f'api/{API_VERSION}/', include([
        path('', include('hooks.urls')),
        path('auth/', include('authentication.urls')),
        path('analytics/', include('analytics.urls')),
    ])),
]

# Development static files serving
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler404 = 'hooks.views.custom_404'
handler500 = 'hooks.views.custom_500'