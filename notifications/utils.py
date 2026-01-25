from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification


def send_notification(user_id, message):
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}"
    
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "send_notification",
            "message": message,
        }
    )

def send_push_notification(users, title, body, data=None, icon=None):
    if icon is None:
        icon = "https://admin.fernrie.com/static/assets/img/brand/uploaded_logo.png"

    devices = FCMDevice.objects.filter(user__in=users, active=True)
    if not devices.exists():
        print("No active FCM devices found")
        return

    try:
        payload = {
            "title": str(title),
            "body": str(body),
            "message": str(body),
        }

        if icon:
            payload["icon"] = str(icon)

        if data:
            for k, v in data.items():
                payload[k] = str(v)

        message_obj = Message(data=payload)

        print("Sending FCM push to", devices.count(), "devices")
        devices.send_message(message_obj)

    except Exception as e:
        print(f"❌ Error sending FCM: {e}")
