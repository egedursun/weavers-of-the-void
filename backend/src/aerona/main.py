from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from aerona.agents.ports import LanguageModel
from aerona.api.app import body_limits, build_api_router
from aerona.api.errors import install_error_handlers
from aerona.api.lifespan import lifespan_for
from aerona.api.security import OriginGuard
from aerona.api.static import mount_static
from aerona.constants.app import APP_NAME, APP_VERSION
from aerona.constants.http import GZIP_LEVEL, GZIP_MINIMUM_BYTES
from aerona.settings import Settings, get_settings


def create_app(settings: Settings | None = None, *, model: LanguageModel | None = None) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan_for(resolved, model))
    app.add_middleware(OriginGuard, allowed_origins=resolved.allowed_origins, limits=body_limits(resolved))
    app.add_middleware(CORSMiddleware, allow_origins=resolved.allowed_origins, allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_BYTES, compresslevel=GZIP_LEVEL)
    install_error_handlers(app)
    app.include_router(build_api_router())
    mount_static(app, resolved)
    return app
