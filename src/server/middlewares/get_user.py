from aiohttp.web import StreamResponse, HTTPUnauthorized
from aiohttp.web_request import Request
from typing import Awaitable, Callable
from functools import wraps
from src.settings import settings
from chauff_cmn.models import User
import jwt


def get_user_or_raise(handler: Callable[[Request], Awaitable[StreamResponse]]):
    @wraps(handler)
    async def wrapper(request: Request):
        access_token = request.headers.get("Authorization", "")
        if not access_token:
            raise HTTPUnauthorized(body = '{"error": "missing jwt"}')
        payload = decode_access_token(access_token)
        request["user"] = User(user_id = payload["sub"], pseudo = payload["pseudo"])
        return await handler(request)

    return wrapper


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms = ["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload