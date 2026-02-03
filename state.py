from typing import Any
from aiohttp.web import WebSocketResponse



class ClientWebsockets():
    def __init__(self):
        self.__websockets: dict[int, list[WebSocketResponse]] = {}
    
    def add(self, battle_id: int | str, ws: WebSocketResponse):
        if battle_id not in self.__websockets:
            self.__websockets[int(battle_id)] = []
        self.__websockets[int(battle_id)].append(ws)
    
    async def broadcast(self, battle_id: int, data: dict[str, Any]):
        from init import log
        candidates = self.__websockets.get(battle_id, []).copy()
        for ws in candidates:
            try:
                await ws.send_json(data)
            except Exception:
                log.warn("Failed to send message to client. Removing client...")
                self.__websockets[battle_id].remove(ws)
                await ws.close()

client_webosckets = ClientWebsockets()