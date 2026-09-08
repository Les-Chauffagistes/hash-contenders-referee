import asyncio

from src.apis.chauffagistes_pool.http import PoolAPIClient
from chauff_cmn.logging import logger as log
from chauff_cmn.models import PoolUser

POLL_INTERVAL_SECONDS = 15


class HashrateFetch:
    """Poll le hashrate d'une adresse pool en tâche de fond, une seule tâche par
    adresse quel que soit le nombre de battles/contenders qui l'utilisent.

    Le cycle de vie est piloté par référence : une adresse n'est pollée que tant
    qu'au moins une battle active la retient (`acquire`/`release`), pour ne jamais
    laisser tourner un poller (et sa ClientSession aiohttp) pour une battle
    terminée.
    """

    event_dispatcher = None  # injecté dans main.py, comme Referee

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}
        self._subscribers: dict[str, set[int]] = {}
        self._latest: dict[str, PoolUser] = {}

    def get_latest(self, address: str) -> PoolUser | None:
        """Dernière donnée connue pour cette adresse, sans appel réseau. Utilisé
        par l'API HTTP à la demande."""
        return self._latest.get(address)

    def acquire(self, address: str, battle_id: int) -> None:
        """Abonne `battle_id` au polling de `address`, en démarrant la tâche de
        fetch si c'est le premier abonné. Idempotent : peut être rappelé sans
        risque pour une battle déjà abonnée."""
        subscribers = self._subscribers.setdefault(address, set())
        subscribers.add(battle_id)
        if address not in self._tasks:
            log.info(f"Starting hashrate poll for {address}")
            self._tasks[address] = asyncio.create_task(self._poll(address))

    async def release(self, address: str, battle_id: int) -> None:
        """Désabonne `battle_id`. Arrête la tâche et purge l'état dès que plus
        aucune battle active n'utilise cette adresse. Idempotent : peut être
        rappelé même si `battle_id` n'était plus (ou jamais) abonné."""
        subscribers = self._subscribers.get(address)
        if subscribers is None:
            return

        subscribers.discard(battle_id)
        if subscribers:
            return

        del self._subscribers[address]
        self._latest.pop(address, None)
        task = self._tasks.pop(address, None)
        if task is None:
            return

        log.info(f"Stopping hashrate poll for {address}, no more subscribers")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def release_all(self) -> None:
        """Arrête tous les pollers en cours. Utilisé à l'extinction du service."""
        for address, subscribers in list(self._subscribers.items()):
            for battle_id in list(subscribers):
                await self.release(address, battle_id)

    async def _poll(self, address: str) -> None:
        client = PoolAPIClient()
        try:
            while True:
                try:
                    data = await client.get_pool_data(address)
                    if data != self._latest.get(address):
                        self._latest[address] = data
                        await self._broadcast(address, data)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.exception(f"Hashrate fetch failed for {address}")

                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        finally:
            await client.close()

    async def _broadcast(self, address: str, data: PoolUser) -> None:
        if self.event_dispatcher is None:
            return
        for battle_id in self._subscribers.get(address, ()):
            await self.event_dispatcher.hashrate_update(battle_id, address, data)
