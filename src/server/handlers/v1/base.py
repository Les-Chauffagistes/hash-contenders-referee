from aiohttp import web

from .create import create
from .join import join
from .list import list_battles
from .status import status

subapp = web.Application()

routes = [
    web.post("/battle/create", create),
    web.post("/battle/join", join),
    web.get("/battle/list", list_battles),
    web.get("/battle/{id}", status),
]

subapp.add_routes(routes)