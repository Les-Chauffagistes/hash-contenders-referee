from prisma import Prisma
from src.apis.chauffagistes_pool.ws import WebsocketWrapper
from init import app, referee, hashrate_fetch
from asyncio import Task, create_task, sleep, gather
from functools import partial
from chauff_cmn.logging import logger as log
from src.settings import settings


prisma: Prisma = app["prisma"]


async def _stop_battle_connections(connections: list[tuple[WebsocketWrapper, Task]]):
    stop_results = await gather(
        *(ws.stop() for ws, _ in connections), return_exceptions=True
    )
    for result in stop_results:
        if isinstance(result, BaseException):
            log.error(f"Error while stopping websocket: {result}")

    tasks = [t for _, t in connections]
    for t in tasks:
        t.cancel()
    await gather(*tasks, return_exceptions=True)


async def _release_hashrate_polling(battle_id: int, addresses: set[str]):
    for address in addresses:
        await hashrate_fetch.release(address, battle_id)


async def shares_listener():
    log.info("Starting match loop...")

    # Stocker les ws (et leurs tasks), et les adresses associées, pour chaque battle
    active: dict[int, tuple[set[str], list[tuple[WebsocketWrapper, Task]]]] = {}
    assert settings.api_url is not None

    try:
        while True:
            try:
                battles = await prisma.battles.find_many(where={"is_finished": False})
                active_ids = {b.id for b in battles}

                # Couper les ws des batailles terminées, et libérer le polling de
                # hashrate des adresses que cette battle était la seule à retenir.
                finished_ids = set(active.keys()) - active_ids
                for battle_id in finished_ids:
                    addresses, connections = active.pop(battle_id)
                    log.info(f"Stopping ws for finished battle {battle_id}")
                    await _stop_battle_connections(connections)
                    await _release_hashrate_polling(battle_id, addresses)

                # Démarrer les ws des nouvelles batailles
                for battle in battles:
                    if battle.id not in active:
                        log.info(
                            f"Added ws for battle {battle.id} "
                            f"{battle.contender_1_address} {battle.contender_2_address}"
                        )
                        # Toujours souscrire à l'adresse entière, sans filtrer par worker
                        # côté requête : le filtre `&worker=` du pool s'est avéré peu
                        # fiable en pratique (sensible à la casse alors que le champ
                        # `worker` renvoyé dans les shares ne l'est pas forcément,
                        # provoquant un flux vide et silencieux côté pool). Le
                        # rapprochement par worker est déjà fait, de façon fiable et
                        # insensible à la casse, par `Referee._identify_contender`.
                        #
                        # Une seule connexion par adresse *distincte* : en mode Mineur
                        # vs Mineur sur un même compte pool, les deux contenders
                        # partagent la même adresse. Ouvrir deux connexions identiques
                        # ferait recevoir (et traiter) chaque share deux fois.
                        addresses = dict.fromkeys(
                            (battle.contender_1_address, battle.contender_2_address)
                        )
                        for address in addresses:
                            hashrate_fetch.acquire(address, battle.id)
                        connections: list[tuple[WebsocketWrapper, Task]] = []
                        for address in addresses:
                            ws = WebsocketWrapper(
                                f"{settings.api_url}/shares?address={address}",
                                partial(referee.on_share, battle),
                            )
                            task = create_task(ws.continuous_listener())
                            connections.append((ws, task))
                        active[battle.id] = (set(addresses), connections)

            except Exception:
                log.exception("Error in match loop")

            await sleep(3)
    finally:
        log.info("Stopping match loop...")
        await gather(
            *(
                _stop_battle_connections(connections)
                for _, connections in active.values()
            )
        )
        await gather(
            *(
                _release_hashrate_polling(battle_id, addresses)
                for battle_id, (addresses, _) in active.items()
            )
        )
        active.clear()
        log.info("Match loop stopped")
