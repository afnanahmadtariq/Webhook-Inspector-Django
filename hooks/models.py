import uuid
from django.db import models

class Webhook(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class WebhookRequest(models.Model):
    webhook = models.ForeignKey(Webhook, on_delete=models.CASCADE)
    received_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=10)
    headers = models.TextField()
    body = models.TextField()
    ip_address = models.GenericIPAddressField()
