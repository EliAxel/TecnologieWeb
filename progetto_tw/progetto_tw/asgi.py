import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import progetto_tw.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'progetto_tw.settings')
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            progetto_tw.routing.websocket_urlpatterns
        )
    ),
})