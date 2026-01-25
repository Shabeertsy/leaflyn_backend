import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leafin_backend.settings')
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from authentication.middleware import JWTAuthMiddleware
import notifications.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            notifications.routing.websocket_urlpatterns
        )
    ),
})
