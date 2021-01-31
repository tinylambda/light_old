from channels.auth import AuthMiddlewareStack


class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope['role'] = 'Role'
        return await self.app(scope, receive, send)


def TokenAuthMiddlewareStack(app):
    return TokenAuthMiddleware(AuthMiddlewareStack(app))

