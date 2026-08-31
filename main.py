from src.settings import settings
import asyncio
import signal

from dotenv import load_dotenv

load_dotenv(".env")

from init import log, routes, app, log, event_dispatcher
from src.server.cors import cors
from os import getenv
from aiohttp import web
from src.rules.Referee import Referee
from state import client_webosckets


async def main():
    log.info("Starting server...")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_shutdown(received_signal: signal.Signals):
        if not stop_event.is_set():
            log.info(f"{received_signal.name} received, stopping...")
            stop_event.set()

    handled_signals = (signal.SIGINT, signal.SIGTERM)
    for handled_signal in handled_signals:
        loop.add_signal_handler(
            handled_signal, request_shutdown, handled_signal
        )

    runner = web.AppRunner(app)
    listener_task = None
    stop_task = None
    runner_started = False

    try:
        await runner.setup()
        runner_started = True

        site = web.TCPSite(runner, "0.0.0.0", settings.server_port)
        await site.start()
        log.info(f"Server listening on port {settings.server_port}")

        # Injection de dépendances
        # charger les modules qui necessitent prisma à partir de là
        from src.rules.shares_listener import shares_listener

        event_dispatcher.client_websockets = client_webosckets

        Referee.prisma = app["prisma"]
        Referee.log = log
        Referee.event_dispatcher = event_dispatcher

        listener_task = asyncio.create_task(shares_listener())
        stop_task = asyncio.create_task(stop_event.wait())
        done, _ = await asyncio.wait(
            (listener_task, stop_task),
            return_when=asyncio.FIRST_COMPLETED,
        )

        if listener_task in done:
            await listener_task
    finally:
        for handled_signal in handled_signals:
            loop.remove_signal_handler(handled_signal)

        tasks = [task for task in (listener_task, stop_task) if task is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        if runner_started:
            await runner.cleanup()

    log.info("Bye")


if __name__ == "__main__":
    import src.server.handlers.v1
    import src.server.health

    app.add_routes(routes)
    paths = []
    for route in app.router.routes():
        log.info(f"added cors on {route.method} {route.handler.__name__}")
        cors.add(route)

    asyncio.run(main())
