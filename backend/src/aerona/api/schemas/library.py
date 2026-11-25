from datetime import datetime

from pydantic import Field

from aerona.api.schemas.common import ApiModel, RequestModel
from aerona.constants.library import COVER_PROMPT_MAX_LENGTH, UNIVERSE_NAME_MAX_LENGTH, UNIVERSE_NOTES_MAX_LENGTH, UNIVERSE_TAGS_MAX
from aerona.domain.enums.accounts import Permission, UniverseRole
from aerona.domain.enums.library import LibraryEventKind, UniverseOrigin, UniverseStatus
from aerona.domain.enums.library_jobs import LibraryJobKind, LibraryJobStage, LibraryJobStatus, LibraryStreamKind

SUMMARY_MAX_LENGTH = 4000
FILE_NAME_MAX_LENGTH = 200


class UniverseView(ApiModel):
    id: str
    name: str
    summary: str
    notes: str
    cover_path: str | None
    status: UniverseStatus
    pinned: bool
    created_at: datetime
    opened_at: datetime | None
    updated_at: datetime
    epoch: int
    year: int
    population: int
    sons: int
    size_bytes: int
    schema_revision: str
    app_version: str
    origin: UniverseOrigin
    origin_note: str
    tags: list[str]
    media_prefix: str
    is_open: bool
    running_jobs: list[str]
    workspace_id: int | None
    canon_approval: bool
    legacy_author_name: str
    role: UniverseRole
    permissions: list[Permission]


class UniverseTagFacet(ApiModel):
    value: str
    count: int


class UniverseOriginFacet(ApiModel):
    value: UniverseOrigin
    count: int


class UniverseStatusFacet(ApiModel):
    value: UniverseStatus
    count: int


class UniverseFacets(ApiModel):
    tags: list[UniverseTagFacet]
    origins: list[UniverseOriginFacet]
    statuses: list[UniverseStatusFacet]


class UniverseList(ApiModel):
    items: list[UniverseView]
    total: int
    offset: int
    limit: int
    facets: UniverseFacets


class LibraryEventView(ApiModel):
    id: int
    at: datetime
    kind: LibraryEventKind
    universe_id: str
    universe_name: str
    detail: str
    account_name: str


class LibraryEventPage(ApiModel):
    items: list[LibraryEventView]
    total: int
    offset: int
    limit: int


class PackagePreviewView(ApiModel):
    name: str
    summary: str
    notes: str
    tags: list[str]
    source_id: str
    created_at: datetime | None
    exported_at: datetime | None
    app_version: str
    schema_revision: str
    epoch: int
    year: int
    population: int
    sons: int
    files: int
    size_bytes: int
    legacy: bool
    dropped: int


class LibraryJobView(ApiModel):
    id: str
    kind: LibraryJobKind
    status: LibraryJobStatus
    stage: LibraryJobStage
    universe_id: str | None
    universe_name: str
    progress: float
    done: int
    total: int
    error: str
    notes: list[str]
    file_name: str
    size_bytes: int
    preview: PackagePreviewView | None


class UniverseDetail(UniverseView):
    events: list[LibraryEventView]


class TrashEntryView(ApiModel):
    id: str
    universe_id: str
    name: str
    deleted_at: datetime
    purge_at: datetime
    size_bytes: int


class TrashPageView(ApiModel):
    items: list[TrashEntryView]
    total: int
    offset: int
    limit: int
    held_bytes: int
    keep_days: int


class TrashEmptied(ApiModel):
    purged: int


class LibraryStreamEvent(ApiModel):
    id: int
    kind: LibraryStreamKind
    at: datetime
    universe_id: str | None
    universe: UniverseView | None
    job: LibraryJobView | None


class UniverseCreate(RequestModel):
    name: str = Field(min_length=1, max_length=UNIVERSE_NAME_MAX_LENGTH)
    notes: str = Field(default="", max_length=UNIVERSE_NOTES_MAX_LENGTH)
    summary: str = Field(default="", max_length=SUMMARY_MAX_LENGTH)
    tags: list[str] = Field(default_factory=list, max_length=UNIVERSE_TAGS_MAX)


class UniversePatch(RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=UNIVERSE_NAME_MAX_LENGTH)
    notes: str | None = Field(default=None, max_length=UNIVERSE_NOTES_MAX_LENGTH)
    summary: str | None = Field(default=None, max_length=SUMMARY_MAX_LENGTH)
    tags: list[str] | None = Field(default=None, max_length=UNIVERSE_TAGS_MAX)
    pinned: bool | None = None
    status: UniverseStatus | None = None


class UniverseDuplicate(RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=UNIVERSE_NAME_MAX_LENGTH)


class ImportConfirm(RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=UNIVERSE_NAME_MAX_LENGTH)


class CoverPaint(RequestModel):
    prompt: str = Field(min_length=1, max_length=COVER_PROMPT_MAX_LENGTH)


class CoverPaintPrompt(ApiModel):
    prompt: str


class CoverFromMedia(RequestModel):
    file_name: str = Field(min_length=1, max_length=FILE_NAME_MAX_LENGTH)
