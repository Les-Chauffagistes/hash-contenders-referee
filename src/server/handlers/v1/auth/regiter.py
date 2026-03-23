from json import JSONDecodeError

from prisma import Prisma
from aiohttp.web_request import Request
from aiohttp.web_response import json_response

import zon
from src.server.handlers.v1.base import routes
from src.server.auth.security import (
    hash_password,
    is_valid_password,
    is_valid_username,
    normalize_username,
)
from src.server.auth.session import attach_session_cookie, create_user_session


validator = zon.record({
    "username": zon.string(),
    "password": zon.string(),
    "pseudo": zon.string().optional(),
    "email": zon.string().optional(),
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


@routes.post("/auth/register")
async def register(request: Request):
    prisma: Prisma = request.config_dict["prisma"]

    try:
        data = await request.json()
        validated_data = validator.validate(data)

        username = normalize_username(validated_data["username"])
        password = validated_data["password"]
        pseudo = validated_data.get("pseudo")
        email = validated_data.get("email")

        pseudo = pseudo.strip() if pseudo else None
        email = email.strip() if email else None

        if not is_valid_username(username):
            return json_response(
                {
                    "error": "Nom d'utilisateur invalide. Utilise 3 à 30 caractères alphanumériques ou underscore."
                },
                status=400,
            )

        if not is_valid_password(password):
            return json_response(
                {"error": "Mot de passe invalide. Minimum 8 caractères."},
                status=400,
            )

        existing = await prisma.password_accounts.find_unique(
            where={"username": username}
        )
        if existing:
            return json_response(
                {"error": "Nom d'utilisateur déjà utilisé."},
                status=409,
            )

        if email:
            existing_email = await prisma.users.find_unique(where={"email": email})
            if existing_email:
                return json_response(
                    {"error": "Adresse email déjà utilisée."},
                    status=409,
                )

        user = await prisma.users.create(
            data={
                "pseudo": pseudo,
                "email": email,
                "role": "USER",
                "is_active": True,
            }
        )

        await prisma.password_accounts.create(
            data={
                "user_id": user.id,
                "username": username,
                "password_hash": hash_password(password),
            }
        )

        token = await create_user_session(request, int(user.id))

    except JSONDecodeError:
        return json_response({"error": "Invalid JSON"}, status=400)

    except zon.ZonError:
        return json_response({"error": "Invalid data"}, status=400)

    response = json_response(
        {
            "ok": True,
            "user": serialize_user(user),
        },
        status=201,
    )
    attach_session_cookie(request, response, token)
    return response