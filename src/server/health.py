from prisma import Prisma

from init import routes
from aiohttp.web_request import Request
from aiohttp.web import HTTPOk, HTTPServiceUnavailable
from init import app

@routes.get("/health")
async def health(_: Request):
    prisma: Prisma = app["prisma"]
    if prisma.is_connected():
        return HTTPOk()
    else:
        return HTTPServiceUnavailable()