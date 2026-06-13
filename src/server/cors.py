import aiohttp_cors
from init import app

cors = aiohttp_cors.setup(
    app,
    defaults={
        "https://contenders.chauffagistes-btc.fr": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        ),
        "https://contenders.staging.chauffagistes-btc.fr": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        ),
    }
)