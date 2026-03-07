from init import app
from prisma import Prisma


async def get_battles():
    prisma: Prisma = app["prisma"]
    return await prisma.battles.find_many()