import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'find_worker_config.settings')

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

django.setup()

from chat_notify import routing
from chat_notify.middleware import JWTAuthMiddleware


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(routing.websocket_urlpatterns)
    )
})