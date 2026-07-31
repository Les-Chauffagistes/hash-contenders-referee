from aiohttp import web_exceptions
from aiohttp.web import middleware, StreamResponse, json_response
from aiohttp.web_request import Request
from typing import Awaitable, Callable


@middleware
async def error_handler(request: Request, handler: Callable[[Request], Awaitable[StreamResponse]]) -> StreamResponse:
    # importer paresseusement le logger central pour éviter les importations circulaires
    import init as hs_init
    log = hs_init.log
    method = request.method
    match method:
        case "GET":
            log_request = log.get

        case "POST":
            log_request = log.post

        case "DELETE":
            log_request = log.delete

        case _:
            log_request = log.info

    status = None
    try:
        response = await handler(request)
        status = response.status
        return response

    except Exception as e:
        if isinstance(e, web_exceptions.HTTPUnauthorized):
            status = 401
            return json_response({"error": "Unauthorized"}, status=401)

        elif isinstance(e, web_exceptions.HTTPNotFound):
            status = 404
            return json_response({"error": "Not Found"}, status=404)

        else:
            log.error("Unhandled exception while handling request", request.path)
            status = 500
            return json_response({"error": "Internal Server Error"}, status=500)

    finally:
        log_request(request.path, status if status is not None else "ERROR")