from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # If detail is a dict, attempt to extract 'code'
    detail = exc.detail
    code = "HTTP_ERROR"
    
    if isinstance(detail, dict):
        code = detail.get("code", "HTTP_ERROR")
        detail = detail.get("detail", str(detail))
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": detail,
            "code": code
        },
    )

async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {exc}",
            "code": "INTERNAL_SERVER_ERROR"
        },
    )
