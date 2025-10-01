from celery import shared_task
from flask import current_app


@shared_task(bind=True)
def remover_codigos_expirados_task(self):
    """Remove expired 2FA backup codes."""
    with current_app.app_context():
        from moviedb.services.user_2fa_service import Backup2FAService

        self.update_state(state='PROGRESS', meta={'status': 'Removing expired codes...'})
        current_app.logger.info("Starting task: remover_codigos_expirados_task")

        result = Backup2FAService.remover_codigos_expirados()

        current_app.logger.info(f"Task completed. Result: {result}")
        return {'status': 'completed', 'result': result}
