import re

from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.db.repositories.chronicle import in_world, kept_lines
from aerona.db.tables.lore import ChronicleRow as ChronicleRecord
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import RecentChronicleContext
from aerona.prompts.contexts.common import ChronicleRow

FROM_TO = re.compile(r"\s*from \d+ to \d+", re.IGNORECASE)
FELL_TO = re.compile(r"\b(fell|dropped|sank) to \d+", re.IGNORECASE)
ROSE_TO = re.compile(r"\b(rose|grew|climbed) to \d+", re.IGNORECASE)
DICE = re.compile("\\s*\\(\\s*\\d+\\s*[\u2013-]\\s*\\d+\\s*\\)")
COUNTED_NOUN = re.compile(r"\b\d+\s+(life|essence|fame|xp|faith|actions?)\b", re.IGNORECASE)


def prompt_text(text: str) -> str:
    cleaned = FROM_TO.sub("", text)
    cleaned = FELL_TO.sub("decreased", cleaned)
    cleaned = ROSE_TO.sub("increased", cleaned)
    cleaned = DICE.sub("", cleaned)
    return COUNTED_NOUN.sub(lambda match: match.group(1), cleaned)


async def recent_rows(scope: Scope, limit: int, world_id: int | None = None) -> list[ChronicleRow]:
    statement = select(ChronicleRecord).where(kept_lines()).order_by(ChronicleRecord.id.desc())
    if world_id is not None and scope.multi_world:
        statement = statement.where(in_world(world_id, scope.primary_world_id))
    rows = list(await scope.session.scalars(statement.limit(limit)))
    return [ChronicleRow(age=row.epoch, text=prompt_text(row.text)) for row in reversed(rows)]


async def recent_chronicle(scope: Scope, limit: int, world_id: int | None = None) -> str:
    rows = await recent_rows(scope, limit, world_id)
    return render(PromptId.RECENT_CHRONICLE, RecentChronicleContext(rows=rows)) if rows else ""
