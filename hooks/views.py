from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Webhook, WebhookRequest

def home(request):
    return render(request, 'hooks/home.html')

def create_webhook(request):
    hook = Webhook.objects.create()
    return render(request, 'hooks/webhook_created.html', {'hook': hook})

def receive_webhook(request, hook_uuid):
    webhook = get_object_or_404(Webhook, uuid=hook_uuid)
    WebhookRequest.objects.create(
        webhook=webhook,
        method=request.method,
        headers=str(request.headers),
        body=request.body.decode('utf-8'),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    return HttpResponse("Webhook received.")

def inspect_webhook(request, hook_uuid):
    webhook = get_object_or_404(Webhook, uuid=hook_uuid)
    requests = WebhookRequest.objects.filter(webhook=webhook).order_by('-received_at')
    return render(request, 'hooks/inspect.html', {'webhook': webhook, 'requests': requests})
