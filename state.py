from typing import Any
from aiohttp.web import WebSocketResponse
from chauff_cmn.logging import logger as log



class ClientWebsockets:
    def __init__(self):
        self.__websockets: dict[int, list[WebSocketResponse]] = {}
    
    def add(self, battle_id: int | str, ws: WebSocketResponse):
        self.__websockets.setdefault(int(battle_id), []).append(ws)

    def remove(self, battle_id: int | str, ws: WebSocketResponse):
        battle_id = int(battle_id)
        sockets = self.__websockets.get(battle_id)
        if sockets is not None and ws in sockets:
            sockets.remove(ws)
            if not sockets:
                self.__websockets.pop(battle_id, None)
    
    async def broadcast(self, battle_id: int, data: dict[str, Any]):
        candidates = self.__websockets.get(battle_id, []).copy()
        for ws in candidates:
            try:
                await ws.send_json(data)
            except Exception:
                log.warning("Failed to send message to client. Removing client...")
                self.remove(battle_id, ws)
                await ws.close()

    async def close(self, battle_id: int):
        for ws in list(self.__websockets.get(battle_id, [])):
            await ws.close()
        self.__websockets.pop(battle_id, None)

client_webosckets = ClientWebsockets()
