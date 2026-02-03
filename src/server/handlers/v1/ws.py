from aiohttp import web
from aiohttp.web_request import Request
from .base import routes
from init import log
from state import client_webosckets

log.debug("Adding ws handler")

@routes.get("/ws/{battle_id}")
async def ws_handler(request: Request):
    battle_id = request.match_info["battle_id"]
    if battle_id is None:
        return web.HTTPBadRequest()

    ws = web.WebSocketResponse(heartbeat=20, autoping=True)
    client_webosckets.add(battle_id, ws)
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            await ws.send_str("ack")

    return ws