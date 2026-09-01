from src.server.middlewares.get_user import get_user_or_raise
from json import JSONDecodeError
from prisma import Prisma
from chauff_cmn.models import User
from .base import routes
from init import app
from aiohttp.web_request import Request
from aiohttp.web_response import json_response
import zon
from src.server.utils import formatter
from prisma import types

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
@get_user_or_raise
async def create_battle(request: Request):
    user: User = request["user"]
    prisma: Prisma = app["prisma"]
    try:
        data: types.battlesCreateInput = await request.json()
        validated_data = validator.validate(data)
        validated_data["owner_user_id"] = int(user.user_id)
        battle = await prisma.battles.create(validated_data)

    except JSONDecodeError:
        return json_response({"error": "Invalid JSON"}, status = 400)

    except zon.ZonError:
        return json_response({"error": "Invalid data"}, status = 400)

    return json_response(formatter.format_row(battle))
