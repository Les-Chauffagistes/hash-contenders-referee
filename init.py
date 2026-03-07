from src.event_dispatcher.WebsocketBroadcaster import WebsocketBroadcaster
from src.rules.Referee import Referee
from src.database.prisma import close_prisma, init_prisma
from src.server.middlewares.logger import error_handler
from src.modules import logger
from aiohttp.web import Application, RouteTableDef
from os import getenv

log = logger.Logger()

app = Application(
    middlewares=(error_handler,)
)

app.on_startup.append(init_prisma) # enregistre prisma dans app["prisma"]
app.on_cleanup.append(close_prisma)
routes = RouteTableDef()

referee = Referee()
event_dispatcher = WebsocketBroadcaster()

API_URL = getenv("API_URL")
if not API_URL:
    log.crit("API_URL not set")
    exit(1)

API_TOKEN = getenv("API_TOKEN")
if not API_TOKEN:
    log.crit("API_TOKEN not set")
    exit(1)