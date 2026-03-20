from datetime import UTC, datetime
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from prisma import Prisma

from src.server.auth.security import hash_session_token

SESSION_COOKIE_NAME = "hash-contenders-session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


def _is_cookie_secure(request: Request) -> bool:
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
    if forwarded_proto.lower() == "https":
        return True
    return request.scheme == "https"


async def get_current_user(request: Request):
    prisma: Prisma = request.config_dict["prisma"]
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if not token:
        return None

    token_hash = hash_session_token(token)

    session = await prisma.user_sessions.find_unique(
        where={"token_hash": token_hash},
        include={"user": True},
    )

    if not session or not session.user:
        return None

    now = datetime.now(UTC)
    expires_at = session.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at < now:
        return None

    if not session.user.is_active:
        return None

    await prisma.user_sessions.update(
        where={"id": session.id},
        data={"last_seen_at": now},
    )

    return session.user


async def create_user_session(request: Request, user_id: int):
    prisma: Prisma = request.config_dict["prisma"]

    from src.server.auth.security import (
        generate_session_token,
        hash_session_token,
        session_expiry,
    )

    token = generate_session_token()
    token_hash = hash_session_token(token)

    await prisma.user_sessions.create(
        data={
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": session_expiry(),
            "ip_address": request.remote,
            "user_agent": request.headers.get("User-Agent"),
        }
    )

    return token


async def delete_current_session(request: Request):
    prisma: Prisma = request.config_dict["prisma"]
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if not token:
        return

    token_hash = hash_session_token(token)

    session = await prisma.user_sessions.find_unique(
        where={"token_hash": token_hash}
    )

    if session:
        await prisma.user_sessions.delete(where={"id": session.id})


def attach_session_cookie(request: Request, response: Response, token: str):
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=_is_cookie_secure(request),
        samesite="Lax",
        max_age=SESSION_COOKIE_MAX_AGE,
        path="/",
    )


def clear_session_cookie(response: Response):
    response.del_cookie(SESSION_COOKIE_NAME, path="/")