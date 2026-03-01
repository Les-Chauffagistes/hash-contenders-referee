from aiohttp.web import json_response
from .base import routes


@routes.get("/health")
async def health(request):
    try:
        prisma = request.app["prisma"]
        await prisma.execute_raw("SELECT 1")
        return json_response({"status": "ok"})
    except Exception:
        return json_response({"status": "error"}, status=503)
