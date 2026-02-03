from aiohttp.web import Application, RouteTableDef
from init import log

log.debug("defining subapp and route table")

subapp = Application()
routes = RouteTableDef()