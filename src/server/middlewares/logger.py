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
            line = log.get(request.path)
        
        case "POST":
            line = log.post(request.path)
        
        case "DELETE":
            line = log.delete(request.path)
        
        case _:
            line = log.info(request.path)
    
    assert line
    try:
        response = await handler(request)
        line.add_text("HTTP", response.status)
        line.edit_print()
        return response

    except Exception as e:
        if isinstance(e, web_exceptions.HTTPUnauthorized):
            line.add_text("HTTP 401")
            return json_response({"error": "Unauthorized"}, status=401)

        elif isinstance(e, web_exceptions.HTTPNotFound):
            line.add_text("HTTP 404")
            return json_response({"error": "Not Found"}, status=404)

        else:
            log.error("Unhandled exception while handling request", request.path)
            line.add_text("HTTP 500")
            return json_response({"error": "Internal Server Error"}, status=500)
    
    finally:
        line.edit_print()