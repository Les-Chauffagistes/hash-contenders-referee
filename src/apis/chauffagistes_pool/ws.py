import asyncio
from enum import Enum
import json
import random
import websockets
from chauff_cmn.models import PoolWebsocketShareElement
from chauff_cmn.logging import logger as log
from typing import Any, Awaitable, Callable
from src.database.share_cursors import Cursor, StreamCursor
from src.settings import settings
from src.utils.shares import get_worker_name
from src.utils.converter import from_number_to_string

CLOSE_BAD_CURSOR = 4400  # curseur invalide ou epoch inconnue
CLOSE_OUT_OF_RETENTION = 4410  # curseur plus ancien que l'historique retenu: des shares sont perdus


class Status(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"


def parse_cursor(value: Any) -> Cursor | None:
    """`<epoch>:<seq>` -> (epoch, seq); None si absent ou illisible."""
    try:
        epoch, seq = str(value).split(":")
        return int(epoch), int(seq)
    except ValueError:
        return None


def with_cursor(uri: str, cursor: Cursor | None) -> str:
    if cursor is None:
        return uri
    return f"{uri}{'&' if '?' in uri else '?'}from={cursor[0]}:{cursor[1]}"


class WebsocketWrapper:
    """Connexion persistante au flux des shares du pool, avec reprise là où le traitement s'est arrêté.

    Si un `cursor` est fourni, le (epoch, seq) du dernier share *traité* est lu en base à chaque connexion
    (`?from=`) et écrit en base après chaque `on_message` réussi. Jamais d'état de reprise en local: la queue
    n'est qu'un tampon, vidé à chaque connexion, et ce qu'elle contient est rejoué par le pool si on la perd.
    """

    def __init__(
        self,
        uri: str,
        on_message: Callable[[PoolWebsocketShareElement], Awaitable[Any]],
        cursor: StreamCursor | None = None,
        *,
        queue_size: int = 5000,
        process_attempts: int = 5,
        retry_delay: float = 1.0,
        reconnect_delay: float = 5.0,
        max_reconnect_delay: float = 60.0,
    ):
        self.uri = uri
        self.on_message = on_message
        self.cursor = cursor
        self.queue_size = queue_size
        self.process_attempts = process_attempts
        self.retry_delay = retry_delay
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.status: Status = Status.DISCONNECTED
        self._running = True
        self._ws: websockets.ClientConnection | None = None
        self._last: Cursor | None = None  # dernier curseur traité sur cette connexion (garde anti-doublon)
        self._reset_on_hello = False  # l'historique demandé n'existe plus: repartir du présent
        self._failures = 0  # connexions consécutives sans `hello`, pour le backoff

    async def stop(self):
        self._running = False
        if self._ws is not None:
            await self._ws.close()

    # ---- reconnexion

    def _reconnect_delay(self, close_code: int | None, had_cursor: bool) -> float:
        if close_code == CLOSE_BAD_CURSOR and not had_cursor:
            return self.max_reconnect_delay  # erreur de configuration: ne pas marteler le serveur
        if close_code in (CLOSE_BAD_CURSOR, CLOSE_OUT_OF_RETENTION) and had_cursor:
            return self.reconnect_delay / 5
        delay = min(self.max_reconnect_delay, self.reconnect_delay * 2 ** max(0, self._failures - 1))
        return delay * random.uniform(0.8, 1.2)

    async def _on_closed(self, close_code: int | None, had_cursor: bool):
        if close_code in (CLOSE_BAD_CURSOR, CLOSE_OUT_OF_RETENTION) and had_cursor:
            log.error(
                f"{self.uri}: curseur refusé par le pool (close {close_code}), des shares sont perdus. "
                f"Reprise au présent."
            )
            self._reset_on_hello = True
            if self.cursor is not None:
                await self.cursor.mark_gap()

    async def _wait_before_reconnect(self, reason: str, e: BaseException | None, close_code: int | None, had_cursor: bool):
        self.status = Status.DISCONNECTED
        if not self._running:
            return
        delay = self._reconnect_delay(close_code, had_cursor)
        log.warning(f"{reason}\n.{e}\nReconnexion dans {delay:.1f} secondes...")
        await asyncio.sleep(delay)

    # ---- traitement des messages

    async def _handle_hello(self, data: dict):
        self._failures = 0
        start, head = parse_cursor(data.get("cursor")), parse_cursor(data.get("head"))
        if self.cursor is not None and start is not None:
            if self._reset_on_hello:
                await self.cursor.reset(start)
                self._reset_on_hello = False
                self._last = start
            elif self._last is None:
                await self.cursor.init(start)  # premier démarrage: point de départ du flux
                self._last = start
        if head is not None and self._last is not None and head[0] == self._last[0] and head[1] > self._last[1]:
            log.info(f"{self.uri}: rattrapage, {head[1] - self._last[1]} seq de retard (tous flux confondus)")

    async def _deliver(self, share: PoolWebsocketShareElement) -> bool:
        """Traite un share, avec retries. False si abandonné (la bataille ne doit pas rester bloquée dessus)."""
        for attempt in range(1, self.process_attempts + 1):
            try:
                await self.on_message(share)
                return True
            except Exception:
                log.exception(f"Error while processing share {share.share_id} (attempt {attempt}/{self.process_attempts})")
                if attempt < self.process_attempts:
                    await asyncio.sleep(self.retry_delay * attempt)
        return False

    async def _advance(self, cursor: Cursor, gap: bool = False):
        if self.cursor is None:
            return
        # Un échec ici n'est pas grave: le curseur suivant rattrapera (écriture monotone) et, au pire,
        # un redémarrage rejoue quelques shares, que le traitement supporte.
        for attempt in range(1, self.process_attempts + 1):
            try:
                await self.cursor.advance(cursor, gap=gap)
                return
            except Exception:
                log.exception(f"Error while saving cursor {cursor} (attempt {attempt}/{self.process_attempts})")
                if attempt < self.process_attempts:
                    await asyncio.sleep(self.retry_delay * attempt)

    async def _handle_share(self, data: dict):
        try:
            share = PoolWebsocketShareElement(**data)
        except ValueError as e:
            log.error(f"Invalid share, skipped: {e}")
            cursor = parse_cursor(f"{data.get('epoch')}:{data.get('seq')}")
            if cursor is not None and (self._last is None or cursor > self._last):
                await self._advance(cursor, gap=True)
                self._last = cursor
            return

        cursor = (share.epoch, share.seq)
        if self._last is not None and cursor <= self._last:
            log.debug(f"Share {share.share_id} déjà traité (curseur {self._last}), ignoré")
            return

        log.debug(
            f"{from_number_to_string(int(share.sdiff))} from {get_worker_name(share)} "
            f"at {share.created_at.strftime('%H:%M:%S')} "
            f"at block {share.block_height}"
        )
        delivered = await self._deliver(share)
        if not delivered:
            log.error(f"Share {share.share_id} abandonné après {self.process_attempts} essais")
        await self._advance(cursor, gap=not delivered)
        self._last = cursor

    async def handle_message(self, message: websockets.Data):
        try:
            data: dict = json.loads(message)
        except json.JSONDecodeError as e:
            log.warning(f"Invalid JSON {e}")
            return

        kind = data.get("type")
        if kind == "hello":
            await self._handle_hello(data)
        elif kind == "share":
            await self._handle_share(data)
        elif kind in ("heartbeat", "watermark"):
            return
        else:
            log.warning(f"Unknown message type {data}")

    async def _message_worker(self, queue: asyncio.Queue, receiving_done: asyncio.Event):
        """Traite les messages de la connexion, dans l'ordre, découplé de la lecture du socket (qui doit
        continuer à répondre aux pings pendant un traitement lent). Finit de vider ce qui a été reçu."""
        while self._running:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=0.2)
            except asyncio.TimeoutError:
                if receiving_done.is_set() and queue.empty():
                    return
                continue
            try:
                await self.handle_message(message)
            except Exception:
                log.exception("Error while handling message")

    # ---- connexion

    async def _run_connection(self, start: Cursor | None) -> int | None:
        """Une connexion, de l'ouverture à la fermeture. Renvoie le code de fermeture reçu."""
        self._last = start
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.queue_size)
        receiving_done = asyncio.Event()
        worker = asyncio.create_task(self._message_worker(queue, receiving_done))
        ws: websockets.ClientConnection | None = None
        try:
            async with websockets.connect(
                with_cursor(self.uri, start),
                additional_headers={"Authorization": f"Bearer {settings.api_token}"},
                max_size=10 * 1024 * 1024,  # 10MB pour les gros messages
            ) as ws:
                self._ws = ws
                self.status = Status.CONNECTED
                log.info(f"Connected to {with_cursor(self.uri, start)}")
                closing: asyncio.Task | None = None
                async for message in ws:
                    if closing is not None:
                        continue  # on continue de lire (et jeter) pour que le pool reçoive notre close sans attendre
                    try:
                        queue.put_nowait(message)
                    except asyncio.QueueFull:
                        # Le traitement ne suit pas: on repart du curseur en base, le pool rejoue ce qu'on jette.
                        log.warning(f"{self.uri}: queue pleine ({self.queue_size}), reconnexion depuis le curseur")
                        closing = asyncio.create_task(ws.close(1001, "client queue full"))
                if closing is not None:
                    await closing
        finally:
            receiving_done.set()
            await asyncio.gather(worker, return_exceptions=True)
            self._ws = None
        return ws.close_code if ws is not None else None

    async def continuous_listener(self):
        try:
            while self._running:
                reason, error, close_code, had_cursor = "Connexion fermée", None, None, False
                try:
                    self.status = Status.CONNECTING
                    start = None if self._reset_on_hello or self.cursor is None else await self.cursor.load()
                    had_cursor = start is not None
                    self._failures += 1  # remis à zéro par le `hello` de cette connexion
                    close_code = await self._run_connection(start)
                    await self._on_closed(close_code, had_cursor)
                except websockets.ConnectionClosed as e:
                    reason, error = "Déconnecté", e
                    close_code = e.rcvd.code if e.rcvd else None
                    await self._on_closed(close_code, had_cursor)
                except websockets.WebSocketException as e:
                    reason, error = "Déconnecté", e
                except OSError as e:
                    reason, error = "Connexion refusée", e
                except Exception as e:
                    reason, error = str(e), e
                finally:
                    await self._wait_before_reconnect(reason, error, close_code, had_cursor)
        finally:
            self._running = False
            self.status = Status.DISCONNECTED
            log.info(f"Listener stopped for {self.uri}")
