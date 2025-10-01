"""Celery application for background tasks."""
import json
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from celery import Celery
from celery.schedules import crontab

# Load config directly without creating Flask app
config_path = os.path.join(os.path.dirname(__file__), 'instance', 'config.dev.json')
with open(config_path) as f:
    config = json.load(f)

# Create Celery instance with Redis configuration
celery_app = Celery(
        'moviedb',
        broker=config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        backend=config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        include=['celery_app']  # Auto-discover tasks in this module
)

# Update Celery configuration
celery_app.conf.update(
        timezone=config.get('CELERY_TIMEZONE', 'America/Sao_Paulo'),
        enable_utc=True,
        task_track_started=True,
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        worker_send_task_events=False,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        broker_connection_retry_on_startup=True,
        beat_schedule={
            'remover-codigos-expirados-diariamente': {
                'task'    : 'celery_app.remover_codigos_expirados_task',
                'schedule': crontab(hour=3, minute=0),  # Midnight UTC-3 = 3 AM UTC
            },
        }
)

# Async email task
@celery_app.task(name='celery_app.send_email_task', bind=True, max_retries=3)
def send_email_task(self, to, subject, text_body=None, html_body=None, from_email=None, from_name=None, **kwargs):
    """Send email asynchronously."""
    from moviedb import create_app
    flask_app = create_app()

    try:
        with flask_app.app_context():
            email_service = flask_app.extensions.get('email_service')
            if not email_service:
                raise Exception("Email service not configured")

            result = email_service.send_email(
                to=to,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                from_email=from_email,
                from_name=from_name,
                **kwargs
            )

            flask_app.logger.info(f"Email sent to {to}: {subject}")
            return {'status': 'sent', 'message_id': result.message_id, 'to': to}

    except Exception as exc:
        flask_app.logger.error(f"Error sending email to {to}: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# Task with Flask context
@celery_app.task(name='celery_app.remover_codigos_expirados_task', bind=True)
def remover_codigos_expirados_task(self):
    """Remove expired 2FA backup codes."""
    from moviedb import create_app
    flask_app = create_app()

    with flask_app.app_context():
        from moviedb.services.user_2fa_service import Backup2FAService

        self.update_state(state='PROGRESS', meta={'status': 'Removing expired codes...'})
        flask_app.logger.info("Starting task: remover_codigos_expirados_task")

        result = Backup2FAService.remover_codigos_expirados()

        flask_app.logger.info(f"Task completed. Result: {result}")
        return {'status': 'completed', 'result': result}
