from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models import Task
from api.utils import send_task_notification

@receiver(post_save, sender=Task)
def task_post_save(sender, instance, created, **kwargs):
    if created:
        send_task_notification(instance)

