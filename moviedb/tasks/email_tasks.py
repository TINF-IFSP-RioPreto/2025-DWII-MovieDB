from celery import shared_task
from flask import current_app


@shared_task(bind=True, max_retries=3)
def send_email_task(self, to, subject, text_body=None, html_body=None, from_email=None,
                    from_name=None, **kwargs):
    """Send email asynchronously."""
    try:
        with current_app.app_context():
            email_service = current_app.extensions.get('email_service')
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

            current_app.logger.info(f"Email sent to {to}: {subject}")
            return {'status': 'sent', 'message_id': result.message_id, 'to': to}

    except Exception as exc:
        current_app.logger.error(f"Error sending email to {to}: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
