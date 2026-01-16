import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close()
        else:
            # Create a group for the user
            self.group_name = f"user_{self.user.id}"
            
            # Join room group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if not self.user.is_anonymous:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    # Receive message from WebSocket (optional, if you want client-to-server)
    async def receive(self, text_data):
        pass

    # Receive message from room group
    async def send_notification(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))
