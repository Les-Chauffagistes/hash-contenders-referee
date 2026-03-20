from .base import subapp, routes
from init import app, log
from . import status, ws, list, create, health, admin_battles, admin_contenders
from src.server.handlers.v1.auth import register, login, me, logout

subapp.add_routes(routes)
app.add_subapp("/v1", subapp)
log.debug("routes added")