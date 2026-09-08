from src.event_dispatcher.WebsocketBroadcaster import WebsocketBroadcaster
from src.rules.Referee import Referee
from src.rules.hashrate_fetch import HashrateFetch
from src.database.prisma import close_prisma, init_prisma
from src.server.middlewares.logger import error_handler
from chauff_cmn.logging import configure
from aiohttp.web import Application, RouteTableDef
from os import getenv

configure(service="hash-contenders-referee", level=getenv("LOG_LEVEL", "DEBUG"))

app = Application(
    middlewares=(error_handler,)
)

app.on_startup.append(init_prisma) # enregistre prisma dans app["prisma"]
app.on_cleanup.append(close_prisma)
routes = RouteTableDef()

referee = Referee()
event_dispatcher = WebsocketBroadcaster()
hashrate_fetch = HashrateFetch()