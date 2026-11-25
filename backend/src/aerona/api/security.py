from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from aerona.api.schemas.common import ErrorCode, ErrorResponse
from aerona.constants.api import (
    ALLOWED_FETCH_SITES,
    IMAGE_CONTENT_PREFIX,
    JSON_BODY_MAX_BYTES,
    JSON_CONTENT_TYPE,
    LOCAL_HOSTS,
    MEGABYTE,
    MULTIPART_CONTENT_TYPE,
    NULL_ORIGIN,
    OCTET_STREAM,
    SAFE_METHODS,
    SIMPLE_CONTENT_TYPES,
)

LOCAL_ONLY = "This server can only be used via localhost."
FOREIGN_ORIGIN = "Requests from another site are refused."
WRONG_CONTENT_TYPE = "Writes must send JSON, or raw bytes for uploads."
TOO_LARGE = "File too large (max {limit} MB)."
UNSIGNED_FORM = "A file upload must come from this app's own page."


@dataclass(frozen=True)
class BodyLimit:
    path_suffix: str
    max_bytes: int
    binary: bool
    multipart: bool = False


class RefusalError(Exception):
    def __init__(self, status: int, message: str, code: ErrorCode) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


def host_name(value: str) -> str:
    if value.startswith("["):
        return value.split("]", 1)[0] + "]"
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def origin_host(origin: str) -> str:
    parts = urlsplit(origin)
    return parts.netloc


def media_type(headers: Headers) -> str:
    return headers.get("content-type", "").split(";", 1)[0].strip().lower()


class OriginGuard:
    def __init__(self, app: ASGIApp, *, allowed_origins: Iterable[str], limits: Iterable[BodyLimit]) -> None:
        self.app = app
        self.allowed_origins = frozenset(origin.rstrip("/") for origin in allowed_origins)
        self.allowed_hosts = LOCAL_HOSTS | {host_name(origin_host(origin)) for origin in self.allowed_origins}
        self.limits = tuple(limits)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        method = str(scope["method"]).upper()
        path = str(scope["path"])
        try:
            limit = self.check(headers, method, path)
        except RefusalError as refusal:
            await self.refuse(refusal, scope, receive, send)
            return
        if limit is None:
            await self.app(scope, receive, send)
            return
        await self.app(scope, self.limited(receive, limit), send)

    def limit_for(self, path: str) -> BodyLimit:
        found = next((limit for limit in self.limits if path.endswith(limit.path_suffix)), None)
        return found or BodyLimit("", JSON_BODY_MAX_BYTES, binary=False)

    def check(self, headers: Headers, method: str, path: str) -> BodyLimit | None:
        if host_name(headers.get("host", "")).lower() not in self.allowed_hosts:
            raise RefusalError(403, LOCAL_ONLY, ErrorCode.FORBIDDEN)
        origin = headers.get("origin")
        write = method not in SAFE_METHODS
        if origin is not None:
            self.check_origin(origin.rstrip("/"), headers.get("host", ""), write)
        if not write:
            return None
        site = headers.get("sec-fetch-site")
        if site is not None and site not in ALLOWED_FETCH_SITES and (origin or "").rstrip("/") not in self.allowed_origins:
            raise RefusalError(403, FOREIGN_ORIGIN, ErrorCode.FORBIDDEN)
        limit = self.limit_for(path)
        self.check_content(headers, limit)
        return limit

    def check_origin(self, origin: str, host: str, write: bool) -> None:
        if origin == NULL_ORIGIN:
            if write:
                raise RefusalError(403, FOREIGN_ORIGIN, ErrorCode.FORBIDDEN)
            return
        if origin in self.allowed_origins:
            return
        netloc = origin_host(origin)
        if host_name(netloc).lower() not in LOCAL_HOSTS:
            raise RefusalError(403, FOREIGN_ORIGIN, ErrorCode.FORBIDDEN)
        if write and netloc.lower() != host.lower():
            raise RefusalError(403, FOREIGN_ORIGIN, ErrorCode.FORBIDDEN)

    def check_content(self, headers: Headers, limit: BodyLimit) -> None:
        length = headers.get("content-length")
        if length is not None and length.isdigit() and int(length) > limit.max_bytes:
            raise RefusalError(413, TOO_LARGE.format(limit=limit.max_bytes // MEGABYTE), ErrorCode.TOO_LARGE)
        kind = media_type(headers)
        if not kind:
            return
        if limit.multipart and kind == MULTIPART_CONTENT_TYPE:
            if headers.get("origin") is None and headers.get("sec-fetch-site") is None:
                raise RefusalError(403, UNSIGNED_FORM, ErrorCode.FORBIDDEN)
            return
        if kind in SIMPLE_CONTENT_TYPES:
            raise RefusalError(415, WRONG_CONTENT_TYPE, ErrorCode.INVALID)
        if limit.binary:
            if kind != OCTET_STREAM and not kind.startswith(IMAGE_CONTENT_PREFIX):
                raise RefusalError(415, WRONG_CONTENT_TYPE, ErrorCode.INVALID)
        elif kind != JSON_CONTENT_TYPE:
            raise RefusalError(415, WRONG_CONTENT_TYPE, ErrorCode.INVALID)

    @staticmethod
    def limited(receive: Receive, limit: BodyLimit) -> Receive:
        seen = 0

        async def wrapped() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit.max_bytes:
                    raise HTTPException(413, TOO_LARGE.format(limit=limit.max_bytes // MEGABYTE))
            return message

        return wrapped

    @staticmethod
    async def refuse(refusal: RefusalError, scope: Scope, receive: Receive, send: Send) -> None:
        body = ErrorResponse(error=refusal.message, code=refusal.code).model_dump(mode="json", exclude_none=True)
        await JSONResponse(status_code=refusal.status, content=body)(scope, receive, send)
