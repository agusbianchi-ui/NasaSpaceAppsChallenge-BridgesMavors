import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_v1_router
from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    422: "validation_error",
    500: "internal_error",
    501: "not_implemented",
    502: "upstream_unavailable",
}


def _error_response(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message)
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        headers=headers,
    )


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "MARS OPS API. The Mars catalog is static reference data; it does "
            "not represent live mission telemetry and does not download NASA "
            "products."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error."
        code = _ERROR_CODES.get(exc.status_code, "http_error")
        return _error_response(
            exc.status_code,
            code,
            message,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            422, "validation_error", "Request validation failed."
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, _exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return _error_response(
            500, "internal_error", "An unexpected error occurred."
        )

    return app


app = create_app()
