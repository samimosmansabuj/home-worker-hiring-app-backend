from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import close_old_connections

from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

User = get_user_model()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        close_old_connections()
        
        existing = scope.get("user", AnonymousUser())
        if getattr(existing, 'is_authenticated', False):
            return await super().__call__(scope, receive, send)

        raw = None
        user = AnonymousUser()
        headers = dict(scope.get("headers") or ())
        auth = headers.get(b"authorization")
        if auth:
            auth_parts = auth.split()
            if len(auth_parts) == 2 and auth_parts[0].lower() == b"bearer":
                raw = auth_parts[1].decode()
            elif len(auth_parts) == 1:
                raw = auth_parts[0].decode()

        # Fallback: token in query string, e.g. ws://.../?token=xxx
        if not raw:
            query = scope.get("query_string", b"").decode()
            for part in query.split("&"):
                if part.startswith("token="):
                    raw = part.split("=", 1)[1]
                    break
        
        if raw:
            try:
                validated = UntypedToken(raw)
                user_id_claim = settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id")
                user_id = validated.get(user_id_claim)
                if user_id is not None:
                    from asgiref.sync import sync_to_async
                    user = await sync_to_async(User.objects.get)(pk=user_id)
                else:
                    user = AnonymousUser()
            except (TokenError, InvalidToken, User.DoesNotExist):
                user = AnonymousUser()
        else:
            user = AnonymousUser()
        
        scope["user"] = user
        return await super().__call__(scope, receive, send)

    async def _get_user_async(self, user_id):
        from asgiref.sync import sync_to_async
        return await sync_to_async(User.objects.get)(pk=user_id)