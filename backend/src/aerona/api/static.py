from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from aerona.constants.api import IMMUTABLE_CACHE, NO_CACHE, PUBLIC_FILE_CACHE, STATIC_INDEX
from aerona.constants.http import API_PREFIX
from aerona.core.errors import NotFoundError
from aerona.settings import Settings

UNKNOWN_ENDPOINT = "Unknown endpoint."
ASSETS_DIRNAME = "assets"
OK_STATUS = 200


class HashedAssets(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == OK_STATUS:
            response.headers["cache-control"] = IMMUTABLE_CACHE
        return response


def mount_static(app: FastAPI, settings: Settings) -> None:
    root = settings.static_dir
    if root is None or not (root / STATIC_INDEX).is_file():
        return
    assets = root / ASSETS_DIRNAME
    if assets.is_dir():
        app.mount(f"/{ASSETS_DIRNAME}", HashedAssets(directory=assets), name=ASSETS_DIRNAME)
    resolved_root = root.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    async def serve(path: str) -> FileResponse:
        if path.startswith(API_PREFIX.strip("/")):
            raise NotFoundError(UNKNOWN_ENDPOINT)
        candidate = (resolved_root / path).resolve() if path else resolved_root / STATIC_INDEX
        if not candidate.is_relative_to(resolved_root) or not candidate.is_file():
            candidate = resolved_root / STATIC_INDEX
        cache = NO_CACHE if candidate.name == STATIC_INDEX else PUBLIC_FILE_CACHE
        return FileResponse(Path(candidate), headers={"cache-control": cache})
