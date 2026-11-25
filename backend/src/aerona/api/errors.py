import logging
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from aerona.api.schemas.common import ErrorCode, ErrorResponse
from aerona.constants.api import CORRELATION_ID_LENGTH, SCRUBBED_PATH
from aerona.constants.http import CORRELATION_ID_HEADER
from aerona.core.errors import (
    AeronaError,
    BusyError,
    ConflictError,
    InsufficientResourcesError,
    NotFoundError,
    ReadOnlyError,
    UniverseRequiredError,
    ValidationFailedError,
)
from aerona.imaging.errors import ImageWorkerError
from aerona.llm.errors import LlmDisabledError, LlmError, LlmTransientError
from aerona.media.errors import MediaStoreError

logger = logging.getLogger(__name__)

RULE_REFERENCE = re.compile(r"rule ([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*) = (-?\d+(?:\.\d+)?)")
ABSOLUTE_PATH = re.compile(r"(?:/Users|/home|/private|/tmp|/var|/app|/data)(?:/[^\s'\"():,]+)+")
INTERNAL_ERROR = "Server error; details are in the log"
INVALID_REQUEST = "The request is not valid."
LLM_FAILED = "The language model could not answer."
STATUS_CODES: dict[int, ErrorCode] = {
    400: ErrorCode.INVALID,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.INVALID,
    409: ErrorCode.CONFLICT,
    413: ErrorCode.TOO_LARGE,
    415: ErrorCode.INVALID,
    423: ErrorCode.READ_ONLY,
}
ERROR_CODES: tuple[tuple[type[AeronaError], ErrorCode], ...] = (
    (NotFoundError, ErrorCode.NOT_FOUND),
    (BusyError, ErrorCode.BUSY),
    (UniverseRequiredError, ErrorCode.UNIVERSE_REQUIRED),
    (ConflictError, ErrorCode.CONFLICT),
    (ReadOnlyError, ErrorCode.READ_ONLY),
    (InsufficientResourcesError, ErrorCode.INSUFFICIENT),
    (ValidationFailedError, ErrorCode.INVALID),
    (ImageWorkerError, ErrorCode.UNAVAILABLE),
    (MediaStoreError, ErrorCode.UNAVAILABLE),
)
LOCATION_SKIPPED = frozenset({"body", "query", "path"})


def scrub(message: str, roots: tuple[Path, ...] = ()) -> str:
    cleaned = message
    for root in roots:
        cleaned = cleaned.replace(str(root), SCRUBBED_PATH)
    return ABSOLUTE_PATH.sub(SCRUBBED_PATH, cleaned)


def code_of(error: AeronaError) -> ErrorCode:
    return next((code for kind, code in ERROR_CODES if isinstance(error, kind)), ErrorCode.INVALID)


def error_body(message: str, code: ErrorCode) -> ErrorResponse:
    match = RULE_REFERENCE.search(message)
    if match is None:
        return ErrorResponse(error=message, code=code)
    return ErrorResponse(error=message, code=code, rule_key=match.group(1), rule_value=float(match.group(2)))


def error_response(status: int, message: str, code: ErrorCode) -> JSONResponse:
    return JSONResponse(status_code=status, content=error_body(scrub(message), code).model_dump(mode="json", exclude_none=True))


def validation_message(error: RequestValidationError) -> str:
    details = list(error.errors())
    if not details:
        return INVALID_REQUEST
    first = details[0]
    location = ".".join(str(part) for part in first.get("loc", ()) if part not in LOCATION_SKIPPED)
    text = str(first.get("msg", INVALID_REQUEST))
    return f'"{location}": {text}' if location else text


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AeronaError)
    async def handle_domain_error(_request: Request, error: AeronaError) -> JSONResponse:
        return error_response(error.status_code, error.message, code_of(error))

    @app.exception_handler(LlmError)
    async def handle_llm_error(_request: Request, error: LlmError) -> JSONResponse:
        status = 409 if isinstance(error, LlmDisabledError) else 503 if isinstance(error, LlmTransientError) else 502
        return error_response(status, str(error) or LLM_FAILED, ErrorCode.UNAVAILABLE)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(400, validation_message(error), ErrorCode.INVALID)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_request: Request, error: StarletteHTTPException) -> JSONResponse:
        return error_response(error.status_code, str(error.detail), STATUS_CODES.get(error.status_code, ErrorCode.INVALID))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, error: Exception) -> JSONResponse:
        correlation_id = uuid.uuid4().hex[:CORRELATION_ID_LENGTH]
        logger.error("unhandled error %s on %s %s", correlation_id, request.method, request.url.path, exc_info=error)
        body = ErrorResponse(error=f"{INTERNAL_ERROR} (record {correlation_id}).", code=ErrorCode.INTERNAL, correlation_id=correlation_id)
        return JSONResponse(status_code=500, content=body.model_dump(mode="json", exclude_none=True), headers={CORRELATION_ID_HEADER: correlation_id})
