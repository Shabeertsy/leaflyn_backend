from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification
from .utils import send_notification

@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance, created, **kwargs):
    if created:
        send_notification(
            user_id=instance.user.id,
            message={
                "id": instance.id,
                "title": instance.title,
                "message": instance.message,
                "type": instance.notification_type,
                "priority": instance.priority,
                "created_at": str(instance.created_at)
            }
        )
