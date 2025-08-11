from django.core.mail import send_mail
from django.conf import settings

def send_webhook_alert(subject, message, recipient=None):
    """
    Send an email alert for webhook errors or security issues.
    Uses Django's email settings and can be called from Celery.
    """
    if recipient is None:
        recipient = getattr(settings, 'ALERT_EMAIL_RECIPIENT', settings.EMAIL_HOST_USER)
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [recipient],
        fail_silently=False,
    )
