from chauff_cmn.models import PoolUser
from aiohttp import ClientSession
from chauff_cmn.models import PoolApiDataPayload, Worker
from src.settings import settings


class PoolAPIClient:
    def __init__(self):
        self._session = ClientSession(settings.pool_api_url)


    async def close(self):
        if self._session is not None:
            try:
                await self._session.close()
            except Exception:
                pass


    async def get_pool_data(self, pool_address: str) -> PoolUser:
        async with self._session.get(f"/api/stats/{pool_address}") as response:
            response.raise_for_status()
            return PoolUser(**await response.json())


    async def get_worker_data(self, pool_address: str, workername: str) -> Worker:
        async with self._session.get(f"/api/stats/{pool_address}") as response:
            response.raise_for_status()
            data = PoolUser(**await response.json())
            worker = [w for w in data.worker if w.workername.lower() == workername.lower()]
            if worker:
                return worker[0]
            raise ValueError("Worker not found")