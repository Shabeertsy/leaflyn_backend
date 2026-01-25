from django.db.models.signals import post_save
from django.dispatch import receiver
from notifications.utils import send_notification, send_push_notification
from django.contrib.auth import get_user_model
from .models import CompanyTransaction, ServiceTransaction



User = get_user_model()

@receiver(post_save, sender=CompanyTransaction)
def notify_company_transaction_creation_or_update(sender, instance, created, **kwargs):
    verb = "New" if created else "Updated"
    person_name = str(instance.person) if instance.person else "Unknown"
    message = f"{verb} Company Transaction: {instance.get_transaction_type_display()} of {instance.amount} by {person_name}. Status: {instance.admin_status}"
    
    recipients = User.objects.filter(user_type__in=['partner', 'admin'], is_active=True)
    for user in recipients:
        # 1. WebSocket Notification
        send_notification(user.id, message)
        
    # 2. FCM Push Notification
    send_push_notification(
        users=recipients,
        title=f"{verb} Company Transaction",
        body=message,
        data={"transaction_id": str(instance.id), "type": "company_transaction"}
    )



@receiver(post_save, sender=ServiceTransaction)
def notify_service_transaction_creation_or_update(sender, instance, created, **kwargs):
    verb = "New" if created else "Updated"
    service_name = str(instance.service) if instance.service else "Unknown"
    message = f"{verb} Service Transaction: {instance.get_transaction_type_display()} of {instance.amount} for {service_name}. Status: {instance.status}"
    recipients = User.objects.filter(user_type__in=['partner', 'admin'], is_active=True)
    for user in recipients:
        # 1. WebSocket Notification
        send_notification(user.id, message)
        
    # 2. FCM Push Notification
    send_push_notification(
        users=recipients,
        title=f"{verb} Service Transaction",
        body=message,
        data={"transaction_id": str(instance.id), "type": "service_transaction"}
    )