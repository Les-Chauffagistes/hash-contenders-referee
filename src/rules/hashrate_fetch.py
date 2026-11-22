from src.settings import settings
import asyncio

from chauff_cmn.logging import logger as log
from chauff_cmn.models import PoolStats
from chauff_cmn.callers.pools import PoolAPIClient

POLL_INTERVAL_SECONDS = 15


def worker_hashrate(stats: PoolStats, address: str, worker: str | None) -> str | None:
    """Hashrate 1m d'un contender : celui du worker ciblé, sinon celui de toute l'adresse."""
    if not worker:
        return stats.globalStats.hashrate1m
    match = next(
        (w for w in stats.workers if w.workername.removeprefix(f"{address}.").casefold() == worker.casefold()),
        None,
    )
    return match.hashrate1m if match else None


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
        # adresse -> battle_id -> [(contender, worker)] : ce que la battle suit sur cette adresse
        self._subscribers: dict[str, dict[int, list[tuple[str, str | None]]]] = {}
        self._latest: dict[str, PoolStats] = {}

    def get_latest(self, address: str) -> PoolStats | None:
        """Dernière donnée connue pour cette adresse, sans appel réseau. Utilisé
        par l'API HTTP à la demande."""
        return self._latest.get(address)

    def acquire(self, address: str, battle) -> None:
        """Abonne `battle` au polling de `address`, en démarrant la tâche de
        fetch si c'est le premier abonné. Idempotent : peut être rappelé sans
        risque pour une battle déjà abonnée.

        On retient les contenders de la battle qui utilisent cette adresse : seul
        leur hashrate est diffusé, jamais l'adresse ni les workers du pool."""
        targets = [
            (f"contender_{number}", getattr(battle, f"contender_{number}_worker") or None)
            for number in (1, 2)
            if getattr(battle, f"contender_{number}_address") == address
        ]
        self._subscribers.setdefault(address, {})[battle.id] = targets
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

        subscribers.pop(battle_id, None)
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
        client = PoolAPIClient(settings.pool_api_url, "")
        try:
            while True:
                try:
                    data = await client.get_pool_stats(address)
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

    async def _broadcast(self, address: str, data: PoolStats) -> None:
        if self.event_dispatcher is None:
            return
        for battle_id, targets in list(self._subscribers.get(address, {}).items()):
            for contender, worker in targets:
                await self.event_dispatcher.hashrate_update(
                    battle_id, contender, worker_hashrate(data, address, worker)
                )
