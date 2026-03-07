import asyncio
from enum import Enum
import json
import websockets
from src.apis.chauffagistes_pool.models.Share import Share
from init import API_TOKEN, log
from typing import Any, Awaitable, Callable, Optional


class Status(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"


class WebsocketWrapper:
    def __init__(self, uri: str, on_message: Callable[[Share], Awaitable[Any]]):
        self.uri = uri
        self.on_message = on_message
        self.status: Status = Status.DISCONNECTED
        self._running = True
        self._ws: websockets.ClientConnection | None = None

    async def stop(self):
        self._running = False
        if self._ws is not None:
            await self._ws.close()

    async def _discontect_and_reconnect(self, reason: str, e: Optional[Exception]):
        self.status = Status.DISCONNECTED
        if not self._running:
            return
        log.warn(f"{reason}\n.{e}\nReconnexion dans 5 secondes...")
        await asyncio.sleep(5)

    async def hanlde_message(self, message: websockets.Data):
        try:
            data: dict = json.loads(message)
            log.debug(data.get("type"))
            if data.get("type") == "hello":
                return
            
            elif data.get("type") == "share":
                parsed_data = Share.from_any(data["share"])
            
            else:
                log.warn("Unknown message type", data)
                return

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
        while self._running:
            reason = "Connxion fermée"
            try:
                self.status = Status.CONNECTING
                line = log.info("Connecting to", self.uri)
                async with websockets.connect(
                    self.uri,
                    additional_headers={"Authorization": f"Bearer {API_TOKEN}"},
                ) as ws:
                    self._ws = ws
                    self.status = Status.CONNECTED
                    line.add_text("OK")
                    line.edit_print()

                    async for message in ws:
                        try:
                            await self.hanlde_message(message)

                        except Exception as e:
                            log.error()

            except websockets.WebSocketException as e:
                reason, error = "Déconnecté", e

            except OSError as e:
                reason, error = "Connexion refusée", e

            except Exception as e:
                reason, error = str(e), e

            finally:
                self._ws = None
                await self._discontect_and_reconnect(reason, error)

        self.status = Status.DISCONNECTED
        log.info("Listener stopped for", self.uri)
