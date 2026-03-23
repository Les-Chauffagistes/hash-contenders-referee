from asyncio import Task, create_task, sleep
from functools import partial
from urllib.parse import quote_plus

from prisma import Prisma

from src.apis.chauffagistes_pool.ws import WebsocketWrapper
from init import API_URL, log, app, referee

prisma: Prisma = app["prisma"]


def get_duel_entries(battle):
    entries = getattr(battle, "entries", None) or []

    entry_1 = next((e for e in entries if e.slot == 1), None)
    entry_2 = next((e for e in entries if e.slot == 2), None)

    return entry_1, entry_2


def build_share_ws_url(address: str, worker: str | None) -> str:
    url = f"{API_URL}/shares?address={quote_plus(address)}"
    if worker:
        url += f"&worker={quote_plus(worker)}"
    return url


async def forward_share_to_referee(battle_id: int, payload, replay: bool):
    battle = await prisma.battles.find_unique(
        where={"id": battle_id},
        include={"entries": True},
    )

    if battle is None:
        log.warning(f"Share ignored: battle {battle_id} not found")
        return

    await referee.on_share(battle, payload, replay)


async def shares_listener():
    log.info("Starting match loop...")

    # battle_id -> list[(ws, task)]
    active: dict[int, list[tuple[WebsocketWrapper, Task]]] = {}
    assert API_URL is not None

    while True:
        try:
            battles = await prisma.battles.find_many(
                where={"status": {"in": ["WAITING_FOR_START", "LIVE"]}},
                include={"entries": True},
            )
            active_ids = {int(b.id) for b in battles}

            stale_ids = set(active.keys()) - active_ids
            for battle_id in stale_ids:
                listeners = active.pop(battle_id)
                log.info(f"Stopping ws for inactive battle {battle_id}")
                for ws, task in listeners:
                    await ws.stop()
                    task.cancel()

            for battle in battles:
                battle_id = int(battle.id)

                if battle_id in active:
                    continue

                entry_1, entry_2 = get_duel_entries(battle)

                if entry_1 is None or entry_2 is None:
                    log.warning(
                        f"Battle {battle_id} ignored: expected 2 entries with slots 1 and 2"
                    )
                    continue

                listeners: list[tuple[WebsocketWrapper, Task]] = []

                for entry in [entry_1, entry_2]:
                    ws_url = build_share_ws_url(entry.address, entry.worker_name)

                    log.info(
                        f"Added ws for battle {battle_id} | slot={entry.slot} | "
                        f"address={entry.address} | worker={entry.worker_name}"
                    )

                    ws = WebsocketWrapper(
                        ws_url,
                        partial(forward_share_to_referee, battle_id),
                    )
                    task = create_task(ws.continuous_listener())
                    listeners.append((ws, task))

                active[battle_id] = listeners

        except Exception:
            log.exception("Error in match loop")

        await sleep(3)