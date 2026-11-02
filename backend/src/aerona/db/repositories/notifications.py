from dataclasses import dataclass

from aerona.catalog.chronicle import NOTIFICATION_CATEGORIES
from aerona.constants.schema import NOTIFICATION_BODY_MAX_LENGTH, NOTIFICATION_TITLE_MAX_LENGTH
from aerona.db.repositories.base import Repository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.meta import NotificationRow
from aerona.domain.enums.chronicle import NotificationCategory

ELLIPSIS = "…"


@dataclass(frozen=True)
class NotificationDraft:
    category: NotificationCategory
    title: str
    body: str | None = None
    severity: int | None = None
    epoch: int | None = None
    target_node_id: int | None = None
    chronicle_id: int | None = None
    forced: bool = False
    job_id: str | None = None


def effective_settings(prefs: dict[NotificationCategory, bool] | None) -> dict[NotificationCategory, bool]:
    saved = prefs or {}
    return {category: saved.get(category, spec.enabled_by_default) for category, spec in NOTIFICATION_CATEGORIES.items()}


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + ELLIPSIS


def fitted_texts(raw: str, shown: str, body: str | None) -> tuple[str, str | None]:
    detail = body
    if (shown != raw or len(shown) > NOTIFICATION_TITLE_MAX_LENGTH) and not detail:
        detail = raw
    final_title = truncate(shown, NOTIFICATION_TITLE_MAX_LENGTH)
    final_body = truncate(detail, NOTIFICATION_BODY_MAX_LENGTH) if detail and detail != final_title else None
    return final_title, final_body


def raw_title(category: NotificationCategory, title: str | None, body: str | None) -> str:
    return " ".join((title or body or NOTIFICATION_CATEGORIES[category].label).split())


class NotificationRepository(Repository):
    async def add(self, draft: NotificationDraft) -> NotificationRow | None:
        spec = NOTIFICATION_CATEGORIES[draft.category]
        cosmos = await CosmosRepository(self.session).get()
        enabled = effective_settings(cosmos.notification_prefs if cosmos else None)
        if not (draft.forced or spec.forced or enabled[draft.category]):
            return None
        row = NotificationRow(
            epoch=draft.epoch if draft.epoch is not None else (cosmos.epoch if cosmos else None),
            category=draft.category,
            severity=draft.severity if draft.severity is not None else spec.severity,
            title=draft.title,
            body=draft.body,
            target_node_id=draft.target_node_id,
            chronicle_id=draft.chronicle_id,
            job_id=draft.job_id,
        )
        self.session.add(row)
        await self.session.flush()
        return row
