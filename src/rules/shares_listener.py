from prisma import Prisma
from src.apis.chauffagistes_pool.ws import WebsocketWrapper
from init import API_URL, log, app, referee
from asyncio import Task, create_task, sleep, gather
from functools import partial

prisma: Prisma = app["prisma"]


async def shares_listener():
    log.info("Starting match loop...")

    # Stocker les 2 ws et leurs tasks pour chaque battle
    active: dict[int, tuple[WebsocketWrapper, WebsocketWrapper, Task, Task]] = {}
    assert API_URL is not None

    while True:
        try:
            battles = await prisma.battles.find_many(where={"is_finished": False})
            active_ids = {b.id for b in battles}

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
                if battle.id not in active:
                    log.info(
                        f"Added ws for battle {battle.id}",
                        battle.contender_1_address,
                        battle.contender_2_address,
                    )
                    ws1 = WebsocketWrapper(
                        f"{API_URL}/shares?address={battle.contender_1_address}",
                        partial(referee.on_share, battle),
                    )
                    ws2 = WebsocketWrapper(
                        f"{API_URL}/shares?address={battle.contender_2_address}",
                        partial(referee.on_share, battle),
                    )
                    t1 = create_task(ws1.continuous_listener())
                    t2 = create_task(ws2.continuous_listener())
                    active[battle.id] = ws1, ws2, t1, t2

        except Exception:
            log.error("Error in match loop")

        await sleep(3)
