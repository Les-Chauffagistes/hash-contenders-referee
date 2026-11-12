from .base import subapp, routes
from init import app
from chauff_cmn.logging import logger as log
from . import status, ws, list, create, health, delete

subapp.add_routes(routes)
app.add_subapp("/v1", subapp)
log.debug("routes added")