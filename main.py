from dotenv import load_dotenv

load_dotenv(".env")

from init import log, routes, app, log, event_dispatcher
from src.server.cors import cors
from os import getenv
from aiohttp import web
from asyncio import create_task, gather, new_event_loop, set_event_loop
from src.rules.Referee import Referee
from state import client_webosckets


async def main():
    log.info("Démarrage du serveur...")

    PORT = getenv("SERVER_PORT")
    if not PORT:
        log.crit("PORT NOT SET")
        exit(1)

    else:
        PORT = int(PORT)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"Serveur interne en ligne sur localhost:{PORT}")

    # Injection de dépendances
    # charger les modules qui necessitent prisma à partir de là
    from src.rules.shares_listener import shares_listener
    
    event_dispatcher.client_websockets = client_webosckets

    Referee.prisma = app["prisma"]
    Referee.log = log
    Referee.event_dispatcher = event_dispatcher


    listener_task = create_task(shares_listener())
    await gather(*[listener_task])


if __name__ == "__main__":
    import src.server.handlers.v1

    app.add_routes(routes)
    paths = []
    for route in app.router.routes():
        log.info("added cors on", route.method, route.handler.__name__)
        cors.add(route)

    loop = new_event_loop()
    set_event_loop(loop)
    try:
        loop.run_until_complete(main())

    except KeyboardInterrupt:
        log.info("Bye")
        exit(0)
