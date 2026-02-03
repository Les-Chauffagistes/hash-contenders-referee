from .base import subapp, routes
from init import app, log
from . import status, ws, list, create

subapp.add_routes(routes)
app.add_subapp("/api/v1", subapp)
log.debug("routes added")