"""
ASGI config for webhook_inspector project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# Import Django components and configure settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webhook_inspector.settings')
django_asgi_app = get_asgi_application()

# Import Channels components after Django setup
try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from hooks.routing import websocket_urlpatterns
    
    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        ),
    })
except ImportError:
    # Fallback to Django ASGI if Channels is not available
    application = django_asgi_app
