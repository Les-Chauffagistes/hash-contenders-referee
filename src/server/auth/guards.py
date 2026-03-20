from aiohttp import web
from src.server.auth.session import get_current_user


def require_auth(handler):
    async def wrapped(request: web.Request):
        user = await get_current_user(request)
        if not user:
            return web.json_response({"error": "Auth required"}, status=401)

        request["user"] = user
        return await handler(request)

    return wrapped


def require_admin(handler):
    async def wrapped(request: web.Request):
        user = await get_current_user(request)
        if not user:
            return web.json_response({"error": "Auth required"}, status=401)

        if user.role != "ADMIN":
            return web.json_response({"error": "Admin required"}, status=403)

        request["user"] = user
        return await handler(request)

    return wrapped