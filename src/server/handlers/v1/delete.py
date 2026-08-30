from aiohttp.web_request import Request
from aiohttp import web
from init import app
from .base import routes
from ...middlewares.get_user import get_user_or_raise


@routes.delete("/battle/{id}")
@get_user_or_raise
async def delete_battle(request: Request):
    battle_id = request.match_info.get("id")
    assert battle_id
    user = request["user"]
    prisma = app["prisma"]

    battle = await prisma.battles.find_unique(where={"id": int(battle_id)})

    if not battle:
        return web.json_response({"error": "Battle not found"}, status=404)

    if battle.owner_user_id != int(user.user_id):
        return web.json_response({"error": "Unauthorized"}, status=403)

    await prisma.battles.delete(where={"id": int(battle_id)})

    return web.json_response({"message": "Battle deleted successfully"}, status=204)