import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from authentication.middleware import JWTAuthMiddleware
import user.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leafin_backend.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            user.routing.websocket_urlpatterns
        )
    ),
})
