import json

from aiohttp.web import Request
from aiohttp.web_response import Response
from pydantic import ValidationError

from .base import routes
from src.admin.schemas.contender import ContenderCreateSchema, ContenderUpdateSchema
from src.admin.services.ContenderAdminService import (
    ContenderAdminError,
    ContenderAdminService,
)


def _serialize(data):
    if isinstance(data, list):
        return [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in data
        ]
    if hasattr(data, "model_dump"):
        return data.model_dump(mode="json")
    return data


def _json(data, status=200):
    return Response(
        text=json.dumps(_serialize(data), default=str),
        status=status,
        content_type="application/json",
    )


@routes.get(r"/admin/battles/{battle_id:\d+}/contenders")
async def list_contenders(request: Request):
    service = ContenderAdminService(request.config_dict["prisma"])
    battle_id = int(request.match_info["battle_id"])

    try:
        contenders = await service.list_contenders(battle_id)
        return _json(contenders)
    except ContenderAdminError as e:
        return _json({"error": str(e)}, status=404)


@routes.post(r"/admin/battles/{battle_id:\d+}/contenders")
async def add_contender(request: Request):
    service = ContenderAdminService(request.config_dict["prisma"])
    battle_id = int(request.match_info["battle_id"])

    try:
        payload = ContenderCreateSchema(**await request.json())
        contender = await service.add_contender(battle_id, payload)
        return _json(contender, status=201)
    except ValidationError as e:
        return _json({"error": "Payload invalide", "details": e.errors()}, status=400)
    except ContenderAdminError as e:
        return _json({"error": str(e)}, status=400)


@routes.patch(r"/admin/contenders/{contender_id:\d+}")
async def update_contender(request: Request):
    service = ContenderAdminService(request.config_dict["prisma"])
    contender_id = int(request.match_info["contender_id"])

    try:
        payload = ContenderUpdateSchema(**await request.json())
        contender = await service.update_contender(contender_id, payload)
        return _json(contender)
    except ValidationError as e:
        return _json({"error": "Payload invalide", "details": e.errors()}, status=400)
    except ContenderAdminError as e:
        return _json({"error": str(e)}, status=400)


@routes.delete(r"/admin/contenders/{contender_id:\d+}")
async def delete_contender(request: Request):
    service = ContenderAdminService(request.config_dict["prisma"])
    contender_id = int(request.match_info["contender_id"])

    try:
        result = await service.delete_contender(contender_id)
        return _json(result)
    except ContenderAdminError as e:
        return _json({"error": str(e)}, status=400)