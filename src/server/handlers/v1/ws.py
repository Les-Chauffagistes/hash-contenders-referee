from aiohttp import web
from aiohttp.web_request import Request
from .base import routes
from state import client_webosckets
from chauff_cmn.logging import logger as log


log.debug("Adding ws handler")

@routes.get("/ws/{battle_id}")
async def ws_handler(request: Request):
    battle_id = request.match_info["battle_id"]
    if battle_id is None:
        return web.HTTPBadRequest()

    ws = web.WebSocketResponse(heartbeat=20, autoping=True)
    await ws.prepare(request)
    client_webosckets.add(battle_id, ws)
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT and msg.data == "ping":
                await ws.send_str("pong")
    finally:
        client_webosckets.remove(battle_id, ws)

    return ws
