from prisma import Prisma
from src.apis.chauffagistes_pool.ws import WebsocketWrapper
from init import API_URL, log, app, referee
from asyncio import create_task, sleep, gather
from functools import partial

prisma: Prisma = app["prisma"]


async def shares_listener():
    log.info("Starting match loop...")

    # Stocker les 2 ws de chaque battle (1 par user)
    ws: dict[int, tuple[WebsocketWrapper, WebsocketWrapper]] = {}
    assert API_URL is not None

    while True:
        try:
            battles = await prisma.battles.find_many(where={"is_finished": False})

            for battle in battles:
                if battle.id not in ws:
                    log.info(
                        f"Added ws for battle {battle.id}",
                        battle.contender_1_address,
                        battle.contender_2_address,
                    )
                    ws1 = WebsocketWrapper(
                        f"{API_URL}/{battle.contender_1_address}",
                        partial(referee.on_share, battle),
                    )
                    ws2 = WebsocketWrapper(
                        f"{API_URL}/{battle.contender_2_address}",
                        partial(referee.on_share, battle),
                    )
                    ws[battle.id] = ws1, ws2

            tasks = []
            for battle_id, (ws1, ws2) in ws.items():
                tasks.append(create_task(ws1.continuous_listener()))
                tasks.append(create_task(ws2.continuous_listener()))

            # Chaque wrapper s'occupe de maintenir la connexion active
            await gather(*tasks)

        except Exception:
            log.error("Error in match loop")

        finally:
            await sleep(3)
