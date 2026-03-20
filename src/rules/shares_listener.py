from asyncio import Task, create_task, sleep
from functools import partial

from prisma import Prisma

from src.apis.chauffagistes_pool.ws import WebsocketWrapper
from init import API_URL, log, app, referee

prisma: Prisma = app["prisma"]


def get_duel_contenders(battle):
    contenders = getattr(battle, "contenders", None) or []

    contender_1 = next((c for c in contenders if c.slot == 1), None)
    contender_2 = next((c for c in contenders if c.slot == 2), None)

    return contender_1, contender_2


async def shares_listener():
    log.info("Starting match loop...")

    # battle_id -> (ws1, ws2, t1, t2)
    active: dict[int, tuple[WebsocketWrapper, WebsocketWrapper, Task, Task]] = {}
    assert API_URL is not None

    while True:
        try:
            battles = await prisma.battles.find_many(
                where={"is_finished": False},
                include={"contenders": True},
            )
            active_ids = {int(b.id) for b in battles}

            # Couper les ws des batailles terminées
            finished_ids = set(active.keys()) - active_ids
            for battle_id in finished_ids:
                ws1, ws2, t1, t2 = active.pop(battle_id)
                log.info(f"Stopping ws for finished battle {battle_id}")
                await ws1.stop()
                await ws2.stop()
                t1.cancel()
                t2.cancel()

            # Démarrer les ws des nouvelles batailles
            for battle in battles:
                battle_id = int(battle.id)

                if battle_id in active:
                    continue

                contender_1, contender_2 = get_duel_contenders(battle)

                if contender_1 is None or contender_2 is None:
                    log.warning(
                        f"Battle {battle_id} ignored: expected 2 contenders with slots 1 and 2"
                    )
                    continue

                log.info(
                    f"Added ws for battle {battle_id}",
                    contender_1.address,
                    contender_2.address,
                )

                ws1 = WebsocketWrapper(
                    f"{API_URL}/shares?address={contender_1.address}",
                    partial(referee.on_share, battle),
                )
                ws2 = WebsocketWrapper(
                    f"{API_URL}/shares?address={contender_2.address}",
                    partial(referee.on_share, battle),
                )

                t1 = create_task(ws1.continuous_listener())
                t2 = create_task(ws2.continuous_listener())
                active[battle_id] = (ws1, ws2, t1, t2)

        except Exception:
            log.exception("Error in match loop")

        await sleep(3)