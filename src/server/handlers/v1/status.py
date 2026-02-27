from src.server.utils import formatter
from src.server.core.status.v1 import get_battle_hits, get_battle_status
from .base import routes
from aiohttp.web_request import Request
from aiohttp.web import json_response
from init import log

log.debug("loading handlers")

@routes.get("/status/{battle_id}")
async def get_status(request: Request):
    battle_id = request.match_info["battle_id"]
    include_hits = "hits" in request.query.get("includes", "")
    if not battle_id:
        return json_response({"error": "Missing battle id"}, status=400)
    try:
        data = await get_battle_status(battle_id, include_hits)
    
    except Exception:
        log.error()
        return json_response({"error": "Battle not found"}, status=404)
    
    return json_response(formatter.format_row(data))

@routes.get("/hits/{battle_id}")
async def get_hits(request: Request):
    battle_id = request.match_info["battle_id"]
    if not battle_id:
        return json_response({"error": "Missing battle id"}, status=400)
    
    try:
        data = await get_battle_hits(battle_id)

    except Exception:
        return json_response({"error": "Battle not found"}, status=404)
    
    return json_response(list(formatter.format_row(row) for row in data))