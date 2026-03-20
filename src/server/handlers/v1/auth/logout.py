from aiohttp.web_request import Request
from aiohttp.web_response import json_response

from src.server.handlers.v1.base import routes
from src.server.auth.session import clear_session_cookie, delete_current_session


@routes.post("/auth/logout")
async def logout(request: Request):
    await delete_current_session(request)

    response = json_response({"ok": True})
    clear_session_cookie(response)
    return response