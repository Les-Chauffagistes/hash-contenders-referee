import os
from typing import cast
from ..base import make_request

BASE_URL = "https://chauffagistes-pool.fr:3000/api/"
TOKEN = cast(str, os.getenv("STATS_API_TOKEN"))

async def send_request(path: str):
    headers={"Authorization": "Bearer " + TOKEN}
    return await make_request(BASE_URL, path, headers)