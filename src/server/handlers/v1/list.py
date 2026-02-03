from aiohttp.web import Request
from aiohttp.web_response import json_response

from src.server.utils import formatter
from src.server.core.list.v1 import get_battles
from .base import routes

@routes.get("/battles")
async def list_battles(request: Request):
    return json_response(list(formatter.format_rows(await get_battles())))