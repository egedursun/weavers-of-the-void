import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, or_, select

from aerona.agents.context.chronicle_facts import epoch_facts
from aerona.agents.context.entity_line import line_items
from aerona.agents.context.happenings import event_phase_lines
from aerona.agents.context.prehistory_lines import prehistory_digests
from aerona.agents.context.recent_chronicle import prompt_text
from aerona.agents.context.scope import Scope
from aerona.agents.context.world_header import world_header
from aerona.agents.text import sentences
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.core.grammar import spoken
from aerona.db.repositories.chronicle import kept_lines
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import EpochRow
from aerona.db.tables.lore import ChronicleEntityRow
from aerona.db.tables.lore import ChronicleRow as ChronicleRecord
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.interconnect.incidents import chains_in
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.chronicler import ChroniclerContinuity, ChroniclerLink, ChroniclerUserContext, NameKind
from aerona.prompts.contexts.common import WorldItem
from aerona.prompts.contexts.fate import AgeEventRow, AgeEventsContext, WorldEvents

DIGITS = re.compile(r"\d+")
PREVIOUS_VERDICT_KEYS = ("fate.thread_advanced",)
CREATOR_FOLD_KINDS = frozenset({ChronicleKind.CREATOR_HAND, ChronicleKind.DIVINE_SIGN, ChronicleKind.STAR})


@dataclass(frozen=True)
class EventRow:
    text: str
    repeats: int
    world_id: int | None


def fold_key(text: str) -> str:
    return " ".join(DIGITS.sub("#", text).split()).casefold()


def row_fold_key(row: ChronicleRecord, entity_ids: tuple[int, ...]) -> str:
    if row.kind in CREATOR_FOLD_KINDS and row.template_key:
        return f"{spoken(row.kind)}|{row.template_key}|{row.son_id or ''}|{entity_ids}"
    return fold_key(row.text)


async def epoch_event_rows(scope: Scope, epoch: int) -> list[EventRow]:
    rejected = select(EntityRow.id).where(EntityRow.status == EntityStatus.REJECTED)
    tainted = select(ChronicleEntityRow.chronicle_id).where(ChronicleEntityRow.entity_id.in_(rejected))
    rows = list(
        await scope.session.scalars(
            select(ChronicleRecord)
            .where(
                ChronicleRecord.epoch == epoch,
                kept_lines(),
                or_(ChronicleRecord.kind == ChronicleKind.FATE, ChronicleRecord.id.not_in(tainted)),
            )
            .order_by(ChronicleRecord.id)
        )
    )
    links: dict[int, list[int]] = {}
    if rows:
        for chronicle_id, entity_id in await scope.session.execute(
            select(ChronicleEntityRow.chronicle_id, ChronicleEntityRow.entity_id)
            .where(ChronicleEntityRow.chronicle_id.in_([row.id for row in rows if row.kind in CREATOR_FOLD_KINDS]))
            .order_by(ChronicleEntityRow.position)
        ):
            links.setdefault(chronicle_id, []).append(entity_id)
    folded: dict[str, list[ChronicleRecord]] = {}
    for row in rows:
        folded.setdefault(row_fold_key(row, tuple(links.get(row.id, []))), []).append(row)
    limit = scope.rules.fate.council_sentences
    events = []
    for group in folded.values():
        first = group[0]
        text = prompt_text(first.text)
        if first.kind is ChronicleKind.COUNCIL:
            text = " ".join(sentences(text)[:limit])
        events.append(EventRow(text, len(group), first.world_id))
    return events


async def age_events(scope: Scope, epoch: int, limit: int | None = None) -> str:
    rows = await epoch_event_rows(scope, epoch)
    if not rows:
        return ""
    context = AgeEventsContext(
        rows=[AgeEventRow(text=row.text, repeats=row.repeats) for row in rows],
        limit=limit or scope.rules.fate.budget_epoch_events_chars,
        trim_min=scope.rules.context.budget_trim_min_chars,
    )
    return render(PromptId.AGE_EVENTS, context)


async def events_by_world(scope: Scope, epoch: int, worlds: Sequence[WorldItem]) -> list[WorldEvents]:
    rows = await epoch_event_rows(scope, epoch)
    if len(worlds) < 2:
        return [WorldEvents(rows=[AgeEventRow(text=row.text, repeats=row.repeats) for row in rows])] if rows else []
    known = {world.id for world in worlds}
    grouped: dict[int | None, list[AgeEventRow]] = defaultdict(list)
    for row in rows:
        grouped[row.world_id if row.world_id in known else None].append(AgeEventRow(text=row.text, repeats=row.repeats))
    sections = [WorldEvents(world_id=world.id, world_name=world.name, rows=grouped.get(world.id, [])) for world in worlds]
    if grouped.get(None):
        sections.append(WorldEvents(rows=grouped[None]))
    return sections


async def previous_names(scope: Scope, epoch: int) -> list[str]:
    rows = await scope.session.scalars(select(EpochRow.name).where(EpochRow.epoch < epoch, EpochRow.name.is_not(None)).order_by(EpochRow.epoch))
    return [name for name in rows if name]


async def continuity(scope: Scope, epoch: int) -> ChroniclerContinuity:
    rows = list(
        await scope.session.scalars(select(EpochRow).where(EpochRow.epoch < epoch, EpochRow.chronicler_name.is_not(None)).order_by(EpochRow.epoch.desc()))
    )
    if not rows:
        return ChroniclerContinuity()
    current = rows[0]
    streak = 0
    for row in rows:
        if row.chronicler_name != current.chronicler_name:
            break
        streak += 1
    links = [
        ChroniclerLink(age=row.epoch, name=row.chronicler_name or "", who=row.chronicler_identity or "")
        for row in reversed(rows[: scope.rules.fate.banned_previous_openings])
    ]
    head = ChroniclerLink(age=current.epoch, name=current.chronicler_name or "", who=current.chronicler_identity or "")
    return ChroniclerContinuity(current=head, streak=streak, chain=links)


async def name_kinds(scope: Scope, epoch: int) -> list[NameKind]:
    limit = scope.rules.fate.name_type_lines
    rows = await scope.session.execute(
        select(EntityRow, func.count())
        .join(ChronicleEntityRow, ChronicleEntityRow.entity_id == EntityRow.id)
        .join(ChronicleRecord, ChronicleRecord.id == ChronicleEntityRow.chronicle_id)
        .where(ChronicleRecord.epoch == epoch)
        .group_by(EntityRow.id)
        .order_by(func.count().desc(), EntityRow.id)
        .limit(limit)
    )
    return [
        NameKind(name=entity.name, type_label=ENTITY_TYPES[entity.entity_type].label, mortal=entity.entity_type is EntityType.MORTAL, subtype=entity.subtype)
        for entity, _ in rows
    ]


async def previous_verdicts(scope: Scope, epoch: int) -> list[str]:
    rows = await scope.session.scalars(
        select(ChronicleRecord.text)
        .where(ChronicleRecord.epoch == epoch - 1, ChronicleRecord.template_key.in_(PREVIOUS_VERDICT_KEYS))
        .order_by(ChronicleRecord.id)
    )
    return [prompt_text(text) for text in rows]


def living_world_items(scope: Scope, epoch: int | None = None) -> list[WorldItem]:
    return [WorldItem(id=world.id, name=world.name) for world in scope.living_worlds if epoch is None or world.created_epoch <= epoch]


async def pending_items(scope: Scope) -> list[EntityRow]:
    return list(await scope.session.scalars(select(EntityRow).where(EntityRow.pending_name.is_(True)).order_by(EntityRow.world_id, EntityRow.id)))


CHAIN_MINIMUM = 2


async def chronicler_context(
    scope: Scope,
    epoch: int,
    engine_notes: Sequence[str] = (),
    *,
    worlds: Sequence[WorldItem] | None = None,
    missing: Sequence[WorldItem] = (),
    with_pending: bool = True,
) -> ChroniclerUserContext:
    chosen = list(worlds) if worlds is not None else living_world_items(scope, epoch)
    names = await previous_names(scope, epoch)
    pending = await line_items(scope.session, await pending_items(scope)) if with_pending else []
    return ChroniclerUserContext(
        lore_language=scope.cosmos.lore_language,
        rules=scope.rules,
        world_header=await world_header(scope),
        age=epoch,
        worlds=chosen,
        missing_worlds=list(missing),
        previous_names=names,
        continuity=await continuity(scope, epoch),
        name_kinds=await name_kinds(scope, epoch),
        previous_verdicts=await previous_verdicts(scope, epoch),
        events=await events_by_world(scope, epoch, chosen),
        engine_notes=list(engine_notes),
        chains=[chain.line for chain in await chains_in(scope.session, epoch, CHAIN_MINIMUM, scope.rules.incidents.chain_depth)],
        event_phases=await event_phase_lines(scope.session, epoch),
        pending=pending,
        facts=(await epoch_facts(scope, epoch)).sheet,
        prehistories=await prehistory_digests(scope.session, epoch),
    )
