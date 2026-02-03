import asyncio
from enum import Enum
import json
import websockets
from src.apis.chauffagistes_pool.models.Share import Share
from init import log
from typing import Any, Awaitable, Callable

class Status(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"

class WebsocketWrapper():
    def __init__(self, uri: str, on_message: Callable[[Share], Awaitable[Any]]):
        self.uri = uri
        self.on_message = on_message
        self.status: Status = Status.DISCONNECTED
    
    async def _discontect_and_reconnect(self, reason: str):
        self.status = Status.DISCONNECTED
        log.warn(f"{reason}. Reconnexion dans 5 secondes...")
        await asyncio.sleep(5)
        
    
    async def hanlde_message(self, message: websockets.Data):
        try:
            data = json.loads(message)
            parsed_data = Share.from_any(data)
        
        except json.JSONDecodeError as e:
            log.warn("Invalid JSON", e)
            raise
        except ValueError as e:
            log.warn("Invalid data", e)
            raise

        try:
            await self.on_message(parsed_data)
        
        except Exception as e:
            log.error(f"Error while processing message: {e}")
            raise

    async def continuous_listener(self):
        while True:
            reason = "Connxion fermée"
            try:
                self.status = Status.CONNECTING
                line = log.info("Connecting to", self.uri)
                async with websockets.connect(self.uri) as ws:
                    self.status = Status.CONNECTED
                    line.add_text("OK")
                    line.edit_print()
                    
                    async for message in ws:
                        try:
                            await self.hanlde_message(message)
                        
                        except Exception:
                            continue
                        
            except websockets.WebSocketException as e:
                reason = "Déconnecté"
            
            except OSError:
                reason = "Connexion refusée"

            except Exception as e:
                reason = str(e)
            
            finally:
                await self._discontect_and_reconnect(reason)