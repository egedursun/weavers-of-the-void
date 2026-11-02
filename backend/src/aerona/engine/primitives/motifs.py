from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.repositories.names import normalize_name
from aerona.db.tables.entities import CreationMotifRow, EntityRow
from aerona.domain.enums.meta import MotifCategory

WORD_JOINERS = ("_", "-")


def motif_words(motif: str) -> list[str]:
    text = motif
    for joiner in WORD_JOINERS:
        text = text.replace(joiner, " ")
    return [word for word in normalize_name(text).split(" ") if word]


def motif_key(motif: str) -> str:
    return " ".join(motif_words(motif))[:KEY_MAX_LENGTH]


async def record_motifs(
    session: AsyncSession, entity: EntityRow, motifs: Sequence[tuple[str, MotifCategory | None]], epoch: int, *, replace: bool = False
) -> int:
    keyed = {key: category for motif, category in motifs if (key := motif_key(motif))}
    if replace and keyed:
        await session.execute(delete(CreationMotifRow).where(CreationMotifRow.entity_id == entity.id))
    written = 0
    for key, category in keyed.items():
        if await session.get(CreationMotifRow, (entity.id, key)) is not None:
            continue
        session.add(CreationMotifRow(entity_id=entity.id, motif=key, category=category, world_id=entity.world_id, epoch=epoch))
        written += 1
    await session.flush()
    return written


def plain(motifs: Sequence[str]) -> list[tuple[str, MotifCategory | None]]:
    return [(motif, None) for motif in motifs]
