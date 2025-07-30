import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webhook_inspector.settings')

app = Celery('webhook_inspector')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'cleanup-expired-webhooks': {
        'task': 'hooks.tasks.cleanup_expired_webhooks',
        'schedule': 3600.0,  # Run every hour
    },
    'generate-daily-analytics': {
        'task': 'analytics.tasks.generate_daily_analytics',
        'schedule': 86400.0,  # Run daily
    },
    'system-health-check': {
        'task': 'analytics.tasks.system_health_check',
        'schedule': 300.0,  # Run every 5 minutes
    },
    'check-alert-rules': {
        'task': 'analytics.tasks.check_alert_rules',
        'schedule': 60.0,  # Run every minute
    },
}

app.conf.timezone = 'UTC'


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
