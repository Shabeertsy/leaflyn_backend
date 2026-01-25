import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leafin_backend.settings')
django.setup()

from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification

def test_push():
    device = FCMDevice.objects.first()
    if not device:
        print("No devices found in DB.")
        return

    print(f"Targeting device: {device.registration_id[:10]}... for user {device.user}")

    try:
        message_obj = Message(
            notification=Notification(title="Test Notification", body="This is a test message from Django Shell"),
        )
        
        # Testing single device send
        # Note: device.send_message() returns a string (message_id) on success with V1 API usually, 
        # OR a SendResponse object if using batch methods?
        # Let's inspect the return type.
        
        response = device.send_message(message_obj)
        
        print(f"Raw Response: {response}")
        print(f"Type: {type(response)}")
        
        # Check if it's a string (Message ID) or an object
        if hasattr(response, 'success'):
            print(f"Success: {response.success}")
            if not response.success:
                print(f"Error: {response.exception}")
        
    except Exception as e:
        print(f"Failed to send: {e}")

if __name__ == "__main__":
    test_push()
