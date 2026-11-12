from aiohttp.web import Application, RouteTableDef
from chauff_cmn.logging import logger as log


log.debug("defining subapp and route table")

subapp = Application()
routes = RouteTableDef()