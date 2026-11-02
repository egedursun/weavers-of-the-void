from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.engine import FOLDED_TEMPLATE_SUFFIX
from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.engine.context import TickContext
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules

SENTENCE_ENDINGS = ".!"


@dataclass(frozen=True)
class FoldResult:
    folded_groups: int
    hidden_duplicates: int


async def note(
    ctx: TickContext,
    text: str,
    *,
    key: str,
    ids: Sequence[int] = (),
    son_id: int | None = None,
    kind: ChronicleKind = ChronicleKind.WORLD,
    feed: FeedCategory | None = None,
    world_id: int | None = None,
) -> ChronicleRow:
    write = await ctx.chronicle(kind, text, template_key=key, entity_ids=ids, son_id=son_id, feed_category=feed, world_id=world_id)
    ctx.count("notes")
    ctx.publish(
        EventKind.ENGINE_NOTE,
        {
            "epoch": ctx.epoch,
            "phase": ctx.phase,
            "kind": kind.value,
            "template_key": key,
            "text": write.row.text,
            "entity_ids": list(ids),
            "feed": feed.value if feed is not None else None,
        },
    )
    return write.row


async def last_chronicle_id(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.max(ChronicleRow.id))) or 0)


async def tick_rows(session: AsyncSession, epoch: int, since_id: int) -> list[ChronicleRow]:
    statement = select(ChronicleRow).where(ChronicleRow.epoch == epoch, ChronicleRow.id > since_id).order_by(ChronicleRow.id)
    return list(await session.scalars(statement))


async def engine_notes(session: AsyncSession, epoch: int, since_id: int) -> list[str]:
    return [row.text for row in await tick_rows(session, epoch, since_id)]


def _hide(row: ChronicleRow) -> None:
    row.kind = ChronicleKind.ENGINE_RAW
    row.visible = False


async def fold_tick_lines(session: AsyncSession, rules: Rules, epoch: int, since_id: int) -> FoldResult:
    repository = ChronicleRepository(session)
    rows = await tick_rows(session, epoch, since_id)
    ids_of = {row.id: tuple(await repository.entity_ids(row.id)) for row in rows}
    by_event: dict[tuple[str | None, frozenset[int]], list[ChronicleRow]] = defaultdict(list)
    for row in rows:
        by_event[(row.template_key, frozenset(ids_of[row.id]))].append(row)
    hidden = 0
    for group in by_event.values():
        if not any(row.kind not in (ChronicleKind.WORLD, ChronicleKind.ENGINE_RAW) for row in group):
            continue
        for row in group:
            if row.kind is ChronicleKind.WORLD:
                _hide(row)
                row.hidden_as_duplicate = True
                hidden += 1
    by_template: dict[str, list[ChronicleRow]] = defaultdict(list)
    for row in rows:
        if row.kind is ChronicleKind.WORLD and row.template_key:
            by_template[row.template_key].append(row)
    folded = 0
    threshold = rules.world_engine.chronicle_fold_threshold
    cap = rules.world_epoch_transition.folded_chronicle_ids_cap
    for template_key, group in by_template.items():
        if len(group) < threshold:
            continue
        linked = list(dict.fromkeys(entity_id for row in group for entity_id in ids_of[row.id]))[:cap]
        head = group[0].text.rstrip().rstrip(SENTENCE_ENDINGS)
        summary = f"{head}; {len(group) - 1} more events of the same kind happened this epoch."
        for row in group:
            _hide(row)
        await repository.append(
            ChronicleDraft(
                epoch=epoch,
                kind=ChronicleKind.WORLD,
                text=summary,
                entity_ids=linked,
                son_id=group[0].son_id,
                world_id=group[0].world_id,
                template_key=f"{template_key}{FOLDED_TEMPLATE_SUFFIX}",
            )
        )
        folded += 1
    await session.flush()
    return FoldResult(folded_groups=folded, hidden_duplicates=hidden)
