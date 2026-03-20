import aiohttp_cors
from init import app

cors = aiohttp_cors.setup(
    app,
    defaults={
        "https://contenders.chauffagistes-pool.fr": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        ),
        "https://contenders.swakraft.fr": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        ),
        "http://localhost:3003": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        ),
        "https://hash-contenders.chauffagistes-btc.fr": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        ),
    }
)