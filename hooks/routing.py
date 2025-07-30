from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/webhook/(?P<webhook_uuid>[0-9a-f-]+)/$', consumers.WebhookConsumer.as_asgi()),
    re_path(r'ws/dashboard/$', consumers.DashboardConsumer.as_asgi()),
    re_path(r'ws/user/(?P<user_id>\d+)/$', consumers.UserConsumer.as_asgi()),
]
