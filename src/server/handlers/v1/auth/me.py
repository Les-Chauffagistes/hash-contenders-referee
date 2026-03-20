from aiohttp.web_request import Request
from aiohttp.web_response import json_response
from src.server.handlers.v1.base import routes
from src.server.auth.session import get_current_user


def serialize_user(user):
    return {
        "id": int(user.id),
        "pseudo": user.pseudo,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


@routes.get("/auth/me")
async def me(request: Request):
    user = await get_current_user(request)

    if not user:
        return json_response({"error": "Auth required"}, status=401)

    return json_response(serialize_user(user))