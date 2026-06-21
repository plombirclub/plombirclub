from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from urllib.parse import unquote

from app.api.auth import router as auth_router
from app.api.distributors import router as distributors_router
from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.points import router as points_router
from app.api.tasks import router as tasks_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.exceptions import (
    error_response,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.security import decode_jwt_token, verify_csrf_token

app = FastAPI(
    title="Промо-портал «Чистая Линия»",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(distributors_router, prefix="/api")
app.include_router(points_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(imports_router, prefix="/api")

_CSRF_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/forgot-password",
    "/api/auth/logout",
}


@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api"):
        if request.url.path not in _CSRF_EXEMPT_PATHS:
            access_token = request.cookies.get(settings.jwt_access_cookie_name)
            if access_token:
                try:
                    payload = decode_jwt_token(access_token)
                    user_id = payload.get("sub", "")
                except ValueError:
                    user_id = ""

                csrf_cookie = unquote(request.cookies.get(settings.csrf_cookie_name, "")).strip('"')
                csrf_header = unquote(request.headers.get("X-CSRF-Token", "")).strip('"')
                if (
                    not user_id
                    or not csrf_cookie
                    or not csrf_header
                    or csrf_cookie != csrf_header
                    or not verify_csrf_token(csrf_cookie, user_id)
                ):
                    return error_response(
                        status_code=403,
                        code="FORBIDDEN",
                        message="CSRF токен отсутствует или неверен",
                    )
    return await call_next(request)
