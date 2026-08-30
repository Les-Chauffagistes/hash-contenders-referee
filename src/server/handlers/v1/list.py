from json import JSONDecodeError
from aiohttp.web import Request
from aiohttp.web_response import json_response

from src.server.utils import formatter
from src.server.core.list.v1 import get_battles, get_battles_by_ids
from .base import routes

@routes.get("/battles")
async def list_battles(request: Request):
    return json_response(list(formatter.format_rows(await get_battles())))

@routes.post("/battles/by-ids")
async def list_battles_by_id(request: Request):
    try:
        data = await request.json()
        ids = data["ids"]
        if isinstance(ids, list) and all(isinstance(id, int) for id in ids):
            return json_response(list(formatter.format_rows(await get_battles_by_ids(ids))))
        else:
            return json_response({"error", "invalid payload, list of ids integers required"}, status=400)

    except JSONDecodeError:
        return json_response({"error": "Ye great json bro"}, status=400)
