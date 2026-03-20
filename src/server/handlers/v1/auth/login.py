from json import JSONDecodeError

from prisma import Prisma
from aiohttp.web_request import Request
from aiohttp.web_response import json_response

import zon

from src.server.handlers.v1.base import routes
from src.server.auth.security import normalize_username, verify_password
from src.server.auth.session import attach_session_cookie, create_user_session


validator = zon.record({
    "username": zon.string(),
    "password": zon.string(),
})


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


@routes.post("/auth/login")
async def login(request: Request):
    prisma: Prisma = request.config_dict["prisma"]

    try:
        data = await request.json()
        validated_data = validator.validate(data)

        username = normalize_username(validated_data["username"])
        password = validated_data["password"]

        account = await prisma.password_accounts.find_unique(
            where={"username": username},
            include={"user": True},
        )

        if not account or not account.user:
            return json_response({"error": "Identifiants invalides."}, status=401)

        if not account.user.is_active:
            return json_response({"error": "Compte désactivé."}, status=403)

        if not verify_password(password, account.password_hash):
            return json_response({"error": "Identifiants invalides."}, status=401)

        token = await create_user_session(request, int(account.user.id))

    except JSONDecodeError:
        return json_response({"error": "Invalid JSON"}, status=400)

    except zon.ZonError:
        return json_response({"error": "Invalid data"}, status=400)

    response = json_response(
        {
            "ok": True,
            "user": serialize_user(account.user),
        }
    )
    attach_session_cookie(request, response, token)
    return response