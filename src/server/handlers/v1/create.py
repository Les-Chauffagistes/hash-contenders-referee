from json import JSONDecodeError
from prisma import Prisma
from .base import routes
from init import app
from aiohttp.web_request import Request
from aiohttp.web_response import json_response
import zon
from src.server.utils import formatter

validator = zon.record({
    "contender_1_address": zon.string(),
    "contender_1_name": zon.string(),
    "contender_2_address": zon.string(),
    "contender_2_name": zon.string(),
    "contenders_pv": zon.number().int(),
    "rounds": zon.number().int(),
    "start_height": zon.number().int(),
    "are_addresses_privates": zon.boolean()
})

@routes.post("/battle")
async def create_battle(request: Request):
    prisma: Prisma = app["prisma"]
    try:
        data = await request.json()
        validated_data = validator.validate(data)
        battle = await prisma.battles.create(validated_data)
    
    except JSONDecodeError:
        return json_response({"error": "Invalid JSON"}, status=400)
    
    except zon.ZonError:
        return json_response({"error": "Invalid data"}, status=400)
    
    return json_response(formatter.format_row(battle))