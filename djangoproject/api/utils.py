import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_task_notification(task):
    try:
        telegram_ids = []

        if task.mahallahs.exists():
            from api.models import User
            users = User.objects.filter(mahallah__in=task.mahallahs.all(), telegram_id__isnull=False)
            telegram_ids = list(users.values_list('telegram_id', flat=True))

        if not telegram_ids:
            logger.warning(f"No users found for task {task.id}")
            return

        payload = {
            'task_id': task.id,
            'title': task.title,
            'description': task.description,
            'deadline': task.deadline.strftime('%Y-%m-%d %H:%M') if task.deadline else 'Not specified',
            'telegram_ids': telegram_ids
        }

        webhook_url = getattr(settings, 'TELEGRAM_BOT_WEBHOOK_URL', 'http://localhost:8080')

        response = requests.post(
            f"{webhook_url}/webhook/task-notification",
            json=payload,
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"Failed to send task notification: {response.text}")
        else:
            logger.info(f"Task notification sent successfully for task {task.id}")

    except Exception as e:
        logger.exception(f"Error sending task notification: {e}")

