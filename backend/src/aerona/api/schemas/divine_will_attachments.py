from datetime import datetime

from aerona.api.schemas.common import ApiModel
from aerona.domain.enums.divine_will import AttachmentKind, AttachmentStatus, ChunkSource, IndexStatus


class DivineWillAttachmentView(ApiModel):
    id: int
    cycle_id: int | None
    kind: AttachmentKind
    filename: str
    mime: str
    size: int
    status: AttachmentStatus
    seen_by_model: bool
    note: str
    created_at: datetime


class DivineWillAttachmentDetail(DivineWillAttachmentView):
    markdown: str


class DivineWillAttachmentUpload(ApiModel):
    attachments: list[DivineWillAttachmentView]


class DivineWillIndexSource(ApiModel):
    source: ChunkSource
    passages: int
    embedded: int


class DivineWillIndexView(ApiModel):
    status: IndexStatus
    note: str
    semantic: bool
    passages: int
    embedded: int
    pending: int
    share: float
    sources: list[DivineWillIndexSource]
    built_at: datetime | None
    model: str
