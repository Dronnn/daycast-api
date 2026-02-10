from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, error: str, detail: str | None = None):
        self.code = code
        self.error = error
        super().__init__(status_code=status_code, detail=detail)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "code": exc.code, "detail": exc.detail},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_map = {
        400: "validation_error",
        401: "unauthorized",
        404: "not_found",
        413: "payload_too_large",
        422: "validation_error",
        429: "rate_limited",
        502: "ai_provider_error",
    }
    code = code_map.get(exc.status_code, "internal_error")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": str(exc.detail) if exc.detail else code,
            "code": code,
            "detail": None,
        },
    )
