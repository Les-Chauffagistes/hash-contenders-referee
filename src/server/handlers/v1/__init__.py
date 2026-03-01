from .base import subapp, routes
from init import app, log
from . import status, ws, list, create, health

subapp.add_routes(routes)
app.add_subapp("/v1", subapp)
log.debug("routes added")