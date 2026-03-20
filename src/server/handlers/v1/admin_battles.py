import json

from aiohttp.web import Request
from aiohttp.web_response import Response
from pydantic import ValidationError

from .base import routes
from src.admin.schemas.battle import BattleCreateSchema, BattleUpdateSchema
from src.admin.services.BattleAdminService import BattleAdminError, BattleAdminService


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


@routes.get("/admin/battles")
async def list_battles(request: Request):
    service = BattleAdminService(request.config_dict["prisma"])
    battles = await service.list_battles()
    return _json(battles)


@routes.get(r"/admin/battles/{battle_id:\d+}")
async def get_battle(request: Request):
    service = BattleAdminService(request.config_dict["prisma"])
    battle_id = int(request.match_info["battle_id"])

    try:
        battle = await service.get_battle(battle_id)
        return _json(battle)
    except BattleAdminError as e:
        return _json({"error": str(e)}, status=404)


@routes.post("/admin/battles")
async def create_battle(request: Request):
    service = BattleAdminService(request.config_dict["prisma"])

    try:
        payload = BattleCreateSchema(**await request.json())
        battle = await service.create_battle(payload)
        return _json(battle, status=201)
    except ValidationError as e:
        return _json({"error": "Payload invalide", "details": e.errors()}, status=400)
    except BattleAdminError as e:
        return _json({"error": str(e)}, status=400)


@routes.patch(r"/admin/battles/{battle_id:\d+}")
async def update_battle(request: Request):
    service = BattleAdminService(request.config_dict["prisma"])
    battle_id = int(request.match_info["battle_id"])

    try:
        payload = BattleUpdateSchema(**await request.json())
        battle = await service.update_battle(battle_id, payload)
        return _json(battle)
    except ValidationError as e:
        return _json({"error": "Payload invalide", "details": e.errors()}, status=400)
    except BattleAdminError as e:
        return _json({"error": str(e)}, status=400)


@routes.delete(r"/admin/battles/{battle_id:\d+}")
async def delete_battle(request: Request):
    service = BattleAdminService(request.config_dict["prisma"])
    battle_id = int(request.match_info["battle_id"])

    try:
        result = await service.delete_battle(battle_id)
        return _json(result)
    except BattleAdminError as e:
        return _json({"error": str(e)}, status=400)


@routes.post(r"/admin/battles/{battle_id:\d+}/schedule")
async def schedule_battle(request: Request):
    service = BattleAdminService(request.config_dict["prisma"])
    battle_id = int(request.match_info["battle_id"])

    try:
        battle = await service.schedule_battle(battle_id)
        return _json(battle)
    except BattleAdminError as e:
        return _json({"error": str(e)}, status=400)


@routes.post(r"/admin/battles/{battle_id:\d+}/start")
async def start_battle(request: Request):
    service = BattleAdminService(request.config_dict["prisma"])
    battle_id = int(request.match_info["battle_id"])

    try:
        battle = await service.start_battle(battle_id)
        return _json(battle)
    except BattleAdminError as e:
        return _json({"error": str(e)}, status=400)


@routes.post(r"/admin/battles/{battle_id:\d+}/stop")
async def stop_battle(request: Request):
    service = BattleAdminService(request.config_dict["prisma"])
    battle_id = int(request.match_info["battle_id"])

    try:
        battle = await service.stop_battle(battle_id)
        return _json(battle)
    except BattleAdminError as e:
        return _json({"error": str(e)}, status=400)


@routes.post(r"/admin/battles/{battle_id:\d+}/cancel")
async def cancel_battle(request: Request):
    service = BattleAdminService(request.config_dict["prisma"])
    battle_id = int(request.match_info["battle_id"])

    try:
        battle = await service.cancel_battle(battle_id)
        return _json(battle)
    except BattleAdminError as e:
        return _json({"error": str(e)}, status=400)