from prisma import Prisma
from aiohttp import web
from chauff_cmn.logging import logger as log


async def init_prisma(app: web.Application):
    log.info("Prisma ready")
    prisma = Prisma()
    await prisma.connect()
    app["prisma"] = prisma

async def close_prisma(app: web.Application):
    await app["prisma"].disconnect()