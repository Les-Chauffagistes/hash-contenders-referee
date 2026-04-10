import asyncio
from datetime import datetime
from enum import Enum
import json
import websockets
from pool_api_types.models import Share
from init import API_TOKEN, log
from typing import Any, Awaitable, Callable, Optional
from src.utils.converter import from_number_to_string


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
        self._queue: asyncio.Queue[websockets.Data] = asyncio.Queue()

    async def stop(self):
        self._running = False
        if self._ws is not None:
            await self._ws.close()

    async def _disconect_and_reconnect(self, reason: str, e: Optional[Exception]):
        self.status = Status.DISCONNECTED
        if not self._running:
            return
        log.warn(f"{reason}\n.{e}\nReconnexion dans 5 secondes...")
        await asyncio.sleep(5)

    async def hanlde_message(self, message: websockets.Data):
        try:
            data: dict = json.loads(message)
            if data.get("type") == "hello":
                return

            elif data.get("type") == "share":
                parsed_data = Share(**data["share"])
                log.debug(from_number_to_string(int(parsed_data.sdiff)), "from", parsed_data.worker, "at", datetime.fromtimestamp(parsed_data.ts).strftime("%H:%M:%S"), "at block", int(parsed_data.round, 16))

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

    async def _message_worker(self):
        """Process messages from the queue sequentially, decoupled from the receive loop."""
        while self._running:
            try:
                message = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                try:
                    await self.hanlde_message(message)
                except Exception:
                    log.error()
                finally:
                    self._queue.task_done()
            except asyncio.TimeoutError:
                continue

    async def continuous_listener(self):
        worker_task = asyncio.create_task(self._message_worker())
        while self._running:
            reason = "Connexion fermée"
            error = None
            try:
                self.status = Status.CONNECTING
                line = log.info("Connecting to", self.uri)
                async with websockets.connect(
                    self.uri,
                    additional_headers={"Authorization": f"Bearer {API_TOKEN}"},
                    max_size=10 * 1024 * 1024,  # 10MB pour les gros messages
                ) as ws:
                    self._ws = ws
                    self.status = Status.CONNECTED
                    line.add_text("OK")
                    line.edit_print()

                    async for message in ws:
                        await self._queue.put(message)

            except websockets.WebSocketException as e:
                reason, error = "Déconnecté", e
            except OSError as e:
                reason, error = "Connexion refusée", e
            except Exception as e:
                reason, error = str(e), e
            finally:
                self._ws = None
                await self._disconect_and_reconnect(reason, error)

        worker_task.cancel()
        self.status = Status.DISCONNECTED
        log.info("Listener stopped for", self.uri)
