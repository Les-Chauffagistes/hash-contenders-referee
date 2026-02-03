from aiohttp import ClientSession
from init import log


async def make_request(base: str, path: str, headers: dict[str, str]):
    log.info("Performing request", base, path)
    async with ClientSession(base, headers = headers) as session:
        async with session.get(path) as response:
            return await response.json()