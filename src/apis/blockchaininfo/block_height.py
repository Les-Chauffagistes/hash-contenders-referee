from ..base import make_request
from .models.Blockheight import BlockHeight


from cachetools import TTLCache
import asyncio

# Créer un cache avec TTL de 60 secondes
_cache = TTLCache(maxsize=1, ttl=60)
_cache_lock = asyncio.Lock()

async def get_block_height() -> BlockHeight:
    cache_key = "block_height"
    
    async with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]
          
        result = await make_request("https://blockchain.info", "/latestblock", {})
        _cache[cache_key] = result
        return result