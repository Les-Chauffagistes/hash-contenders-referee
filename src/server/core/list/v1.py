from init import app
from prisma import Prisma


async def get_battles():
    prisma: Prisma = app["prisma"]
    return await prisma.battles.find_many(order={"start_height": "desc"})


async def get_battles_by_ids(ids: list[int]):
    prisma: Prisma = app["prisma"]
    return await prisma.battles.find_many(
        order={"start_height": "desc"}, where={"id": {"in": ids}}
    )
