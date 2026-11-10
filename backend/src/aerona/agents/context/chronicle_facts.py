from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import or_, select

from aerona.agents.context.recent_chronicle import prompt_text
from aerona.agents.context.scope import Scope
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import GodConflictRow
from aerona.db.tables.gatherings import CollectionRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.chronicle import ChronicleKind, MajorEventCategory
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import GodConflictOutcome
from aerona.prompts.contexts.chronicler import (
    ChroniclerFactSheet,
    ContestKind,
    FactActor,
    FactDraw,
    FactEvent,
    FactHistory,
    FactOutcome,
    FactRecord,
    FactVerdict,
)

CREATOR_REF = "creator"
TIMES_SUFFIX = " ({count} times)"
ELLIPSIS = "…"
VERDICT_KEYS = ("fate.thread_closed", "fate.prophecy_fulfilled")
NOT_DEEDS = frozenset(
    {
        ChronicleKind.SPEECH,
        ChronicleKind.MESSAGE,
        ChronicleKind.PRAYER,
        ChronicleKind.FATE,
        ChronicleKind.SYSTEM,
        ChronicleKind.ENGINE_RAW,
        ChronicleKind.CREATOR_HAND,
        ChronicleKind.CREATOR_REPUTATION,
        ChronicleKind.DIVINE_SIGN,
        ChronicleKind.STAR,
        ChronicleKind.WORLD,
    }
)
CATEGORY_KINDS: tuple[tuple[MajorEventCategory, frozenset[ChronicleKind], tuple[str, ...]], ...] = (
    (MajorEventCategory.CIVILIZATION, frozenset({ChronicleKind.CIVILIZATION}), ()),
    (MajorEventCategory.LEGENDARY_QUEST, frozenset({ChronicleKind.LEGENDARY_QUEST, ChronicleKind.EXPEDITION}), ()),
    (MajorEventCategory.DISASTER, frozenset({ChronicleKind.DISASTER, ChronicleKind.APOCALYPSE}), ("disasters.",)),
    (MajorEventCategory.SCHISM, frozenset({ChronicleKind.REBELLION}), ("schism", "speciation", "dialects.")),
    (MajorEventCategory.INVASION, frozenset({ChronicleKind.MIGRATION}), ("invasi",)),
    (MajorEventCategory.RETURN_AND_BIRTH, frozenset({ChronicleKind.RESURRECTION, ChronicleKind.ASCENSION}), ("births.", "heroes.")),
    (MajorEventCategory.LEGEND_AND_WONDER, frozenset(), ("wonders.", "legend")),
    (MajorEventCategory.WAR, frozenset({ChronicleKind.WAR, ChronicleKind.WAR_OF_GODS}), ("war.",)),
    (MajorEventCategory.FAITH, frozenset({ChronicleKind.WORSHIP}), ("religion.",)),
)


@dataclass
class EpochFacts:
    epoch: int
    creator: FactActor
    sons: list[FactActor] = field(default_factory=list)
    outcomes: list[FactOutcome] = field(default_factory=list)
    draws: list[FactDraw] = field(default_factory=list)
    events: list[FactEvent] = field(default_factory=list)
    histories: list[FactHistory] = field(default_factory=list)
    verdicts: list[FactVerdict] = field(default_factory=list)
    rejected_recent: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    names: dict[str, list[str]] = field(default_factory=dict)
    deed_owner: dict[int, int] = field(default_factory=dict)
    actor_deeds: dict[int, int] = field(default_factory=dict)
    actor_names: dict[int, str] = field(default_factory=dict)
    winners: dict[str, int] = field(default_factory=dict)
    rejected: dict[int, str] = field(default_factory=dict)
    record_names: dict[int, str] = field(default_factory=dict)
    world_of: dict[str, int | None] = field(default_factory=dict)

    @property
    def sheet(self) -> ChroniclerFactSheet:
        return ChroniclerFactSheet(
            creator=self.creator,
            sons=self.sons,
            outcomes=self.outcomes,
            draws=self.draws,
            events=self.events,
            histories=self.histories,
            verdicts=self.verdicts,
            rejected=self.rejected_recent,
        )


def son_ref(son_id: int) -> str:
    return f"son-{son_id}"


def event_ref(chronicle_id: int) -> str:
    return f"event-{chronicle_id}"


def verdict_ref(chronicle_id: int) -> str:
    return f"verdict-{chronicle_id}"


def war_ref(war_id: int) -> str:
    return f"war-{war_id}"


def conflict_ref(conflict_id: int) -> str:
    return f"conflict-{conflict_id}"


def shorten(text: str, limit: int) -> str:
    cleaned = " ".join(prompt_text(text).split())
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit].rsplit(" ", 1)[0]
    return cut + ELLIPSIS


def category_of(row: ChronicleRow) -> MajorEventCategory | None:
    key = row.template_key or ""
    for category, kinds, keys in CATEGORY_KINDS:
        if row.kind in kinds or any(fragment in key for fragment in keys):
            return category
    return None


async def linked_entities(scope: Scope, chronicle_ids: list[int]) -> dict[int, list[EntityRow]]:
    found: dict[int, list[EntityRow]] = defaultdict(list)
    if not chronicle_ids:
        return found
    rows = await scope.session.execute(
        select(ChronicleEntityRow.chronicle_id, EntityRow)
        .join(EntityRow, EntityRow.id == ChronicleEntityRow.entity_id)
        .where(ChronicleEntityRow.chronicle_id.in_(chronicle_ids))
        .order_by(ChronicleEntityRow.chronicle_id, ChronicleEntityRow.position)
    )
    for chronicle_id, entity in rows:
        found[chronicle_id].append(entity)
    return found


async def unique_rejected(scope: Scope) -> dict[int, str]:
    rejected = list(await scope.session.execute(select(EntityRow.id, EntityRow.name).where(EntityRow.status == EntityStatus.REJECTED)))
    if not rejected:
        return {}
    alive = set(
        await scope.session.scalars(select(EntityRow.name).where(EntityRow.status != EntityStatus.REJECTED, EntityRow.name.in_([row[1] for row in rejected])))
    )
    return {entity_id: name for entity_id, name in rejected if name not in alive}


async def epoch_rows(scope: Scope, epoch: int, rejected: set[int]) -> tuple[list[ChronicleRow], dict[int, list[EntityRow]]]:
    rows = list(
        await scope.session.scalars(
            select(ChronicleRow)
            .where(ChronicleRow.epoch == epoch, ChronicleRow.visible.is_(True), ChronicleRow.kind.not_in([ChronicleKind.ENGINE_RAW, ChronicleKind.SYSTEM]))
            .order_by(ChronicleRow.id)
        )
    )
    links = await linked_entities(scope, [row.id for row in rows])
    kept = [row for row in rows if row.kind is ChronicleKind.FATE or not any(entity.id in rejected for entity in links.get(row.id, []))]
    return kept, links


async def creator_actor(scope: Scope, epoch: int, limit: int) -> FactActor:
    records = list(
        await scope.session.scalars(
            select(ActionRecordRow).where(ActionRecordRow.epoch == epoch, ActionRecordRow.actor_kind == ActorKind.CREATOR).order_by(ActionRecordRow.id)
        )
    )
    folded: dict[str, list[ActionRecordRow]] = {}
    for record in records:
        folded.setdefault(record.kind.value, []).append(record)
    deeds = []
    for group in folded.values():
        text = shorten(group[0].summary or group[0].kind.value.replace("_", " "), limit)
        deeds.append(text + (TIMES_SUFFIX.format(count=len(group)) if len(group) > 1 else ""))
    return FactActor(ref=CREATOR_REF, id=scope.creator.id, name=scope.creator.name, deeds=deeds, deed_count=len(records))


async def contest_outcomes(scope: Scope, epoch: int) -> list[FactOutcome]:
    found: list[FactOutcome] = []
    wars = await scope.session.scalars(
        select(WarRow).where(WarRow.ended_epoch == epoch, WarRow.victor_entity_id.is_not(None), WarRow.loser_entity_id.is_not(None)).order_by(WarRow.id)
    )
    for war in wars:
        event = await scope.session.get(EntityRow, war.event_entity_id)
        winner = await scope.session.get(EntityRow, war.victor_entity_id) if war.victor_entity_id is not None else None
        loser = await scope.session.get(EntityRow, war.loser_entity_id) if war.loser_entity_id is not None else None
        if winner is None or loser is None:
            continue
        found.append(
            FactOutcome(
                ref=war_ref(war.id),
                kind=ContestKind.WAR,
                contest=event.name if event else None,
                winner_id=winner.id,
                winner=winner.name,
                loser_id=loser.id,
                loser=loser.name,
            )
        )
    conflicts = await scope.session.scalars(
        select(GodConflictRow).where(GodConflictRow.epoch == epoch, GodConflictRow.outcome != GodConflictOutcome.DRAW).order_by(GodConflictRow.id)
    )
    for conflict in conflicts:
        attacker = await scope.session.get(NodeRow, conflict.attacker_node_id)
        defender = await scope.session.get(NodeRow, conflict.defender_node_id)
        if attacker is None or defender is None:
            continue
        victor, beaten = (attacker, defender) if conflict.outcome is GodConflictOutcome.ATTACKER_WON else (defender, attacker)
        kind = ContestKind.DUEL if conflict.duel else ContestKind.GOD_CONFLICT
        found.append(FactOutcome(ref=conflict_ref(conflict.id), kind=kind, winner_id=victor.id, winner=victor.name, loser_id=beaten.id, loser=beaten.name))
    return found


async def previous_verdict_facts(scope: Scope, epoch: int, limit: int, son_names: set[str]) -> tuple[list[FactVerdict], dict[str, list[str]]]:
    rows = list(
        await scope.session.scalars(
            select(ChronicleRow).where(ChronicleRow.epoch == epoch - 1, ChronicleRow.template_key.in_(VERDICT_KEYS)).order_by(ChronicleRow.id).limit(limit)
        )
    )
    links = await linked_entities(scope, [row.id for row in rows])
    verdicts = [FactVerdict(ref=verdict_ref(row.id), text=shorten(row.text, scope.rules.chronicle_audit.deed_chars)) for row in rows]
    keys = {verdict_ref(row.id): [entity.name for entity in links.get(row.id, []) if entity.name not in son_names] for row in rows}
    return verdicts, keys


async def add_son(scope: Scope, facts: EpochFacts, son: SonRow, rows: list[ChronicleRow], links: dict[int, list[EntityRow]]) -> set[int]:
    settings = scope.rules.chronicle_audit
    own = [row for row in rows if row.son_id == son.id and row.kind not in NOT_DEEDS]
    deeds = list(dict.fromkeys(shorten(row.text, settings.deed_chars) for row in own))[: settings.son_deeds_shown]
    made = list(
        await scope.session.scalars(
            select(EntityRow)
            .where(EntityRow.creator_son_id == son.id, EntityRow.birth_epoch == facts.epoch, EntityRow.status != EntityStatus.REJECTED)
            .order_by(EntityRow.id)
        )
    )
    blessed = [entity for row in own if row.kind is ChronicleKind.MIRACLE for entity in links.get(row.id, [])[:1]]
    records = list({entity.id: entity for entity in [*made, *blessed]}.values())
    ref = son_ref(son.id)
    world = scope.world_name(son.current_world_id) if scope.multi_world else None
    facts.sons.append(
        FactActor(
            ref=ref,
            id=son.id,
            name=son.name,
            world=world or None,
            deeds=deeds,
            deed_count=len(own),
            records=[FactRecord(id=entity.id, name=entity.name) for entity in records],
        )
    )
    facts.counts[ref] = len(own)
    facts.names[ref] = [son.name]
    facts.world_of[ref] = son.current_world_id if scope.multi_world else None
    facts.actor_deeds[son.id] = len(own)
    facts.actor_names[son.id] = son.name
    for entity in records:
        facts.deed_owner[entity.id] = son.id
        facts.record_names[entity.id] = entity.name
    return {row.id for row in own}


def add_events(scope: Scope, facts: EpochFacts, rows: list[ChronicleRow], links: dict[int, list[EntityRow]], *, skip: set[int], generic: set[str]) -> None:
    settings = scope.rules.chronicle_audit
    folded: dict[tuple[object, ...], int] = {}
    per_category: dict[MajorEventCategory, int] = defaultdict(int)
    for category, _, _ in CATEGORY_KINDS:
        for row in rows:
            if len(facts.events) >= settings.major_events or per_category[category] >= settings.major_events_per_category:
                break
            if row.id in skip or row.kind is ChronicleKind.FATE or category_of(row) is not category:
                continue
            fold = (row.template_key or row.text, tuple(entity.id for entity in links.get(row.id, [])))
            if fold in folded:
                ref = event_ref(folded[fold])
                facts.counts[ref] = facts.counts.get(ref, 1) + 1
                continue
            folded[fold] = row.id
            ref = event_ref(row.id)
            per_category[category] += 1
            world = scope.world_name(row.world_id) if scope.multi_world and row.world_id is not None else None
            facts.events.append(FactEvent(ref=ref, category=category.value, world=world or None, text=shorten(row.text, settings.deed_chars)))
            facts.counts[ref] = 1
            facts.names[ref] = list(dict.fromkeys(entity.name for entity in links.get(row.id, []) if entity.name not in generic))
            facts.world_of[ref] = row.world_id if scope.multi_world else None
    facts.events = [event.model_copy(update={"repeats": facts.counts.get(event.ref, 1)}) for event in facts.events]


def add_outcomes(facts: EpochFacts, found: list[FactOutcome]) -> None:
    facts.outcomes.extend(found)
    for outcome in found:
        facts.winners[outcome.ref] = outcome.winner_id
        facts.names[outcome.ref] = [outcome.winner, outcome.loser]
        facts.actor_names.setdefault(outcome.winner_id, outcome.winner)
        facts.actor_names.setdefault(outcome.loser_id, outcome.loser)


async def recent_rejections(scope: Scope, rejected: dict[int, str], epoch: int) -> list[str]:
    if not rejected:
        return []
    recent = await scope.session.scalars(select(EntityRow.id).where(EntityRow.id.in_(list(rejected)), EntityRow.birth_epoch >= epoch - 1))
    return sorted(rejected[entity_id] for entity_id in recent)


async def history_facts(scope: Scope, epoch: int) -> list[FactHistory]:
    rows = list(
        await scope.session.scalars(
            select(CollectionRow)
            .where(CollectionRow.start_epoch <= epoch, or_(CollectionRow.end_epoch.is_(None), CollectionRow.end_epoch >= epoch))
            .order_by(CollectionRow.start_epoch, CollectionRow.id)
            .limit(scope.rules.chronicle_audit.major_events)
        )
    )
    names = {row.id: row.name for row in rows}
    parents = {row.parent_id for row in rows if row.parent_id is not None and row.parent_id not in names}
    if parents:
        names.update({row.id: row.name for row in await scope.session.scalars(select(CollectionRow).where(CollectionRow.id.in_(parents)))})
    return [
        FactHistory(
            name=row.name,
            kind=row.kind.value.replace("_", " "),
            since=row.start_epoch,
            ended=row.end_epoch,
            within=names.get(row.parent_id) if row.parent_id is not None else None,
        )
        for row in rows
    ]


async def epoch_facts(scope: Scope, epoch: int) -> EpochFacts:
    settings = scope.rules.chronicle_audit
    rejected = await unique_rejected(scope)
    rows, links = await epoch_rows(scope, epoch, set(rejected))
    lit = {row.spotlight_entity_id for row in await scope.session.scalars(select(StorytellerRow)) if row.spotlight_entity_id is not None}
    rows = sorted(rows, key=lambda row: (not any(entity.id in lit for entity in links.get(row.id, [])), row.id))
    creator = await creator_actor(scope, epoch, settings.deed_chars)
    facts = EpochFacts(epoch=epoch, creator=creator, rejected=rejected)
    facts.counts[CREATOR_REF] = creator.deed_count
    facts.actor_deeds[creator.id] = creator.deed_count
    facts.actor_names[creator.id] = creator.name
    facts.names[CREATOR_REF] = [creator.name]
    sons = list(await scope.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.birth_epoch <= epoch).order_by(SonRow.id)))
    son_rows: set[int] = set()
    for son in sons:
        son_rows |= await add_son(scope, facts, son, rows, links)
    add_outcomes(facts, await contest_outcomes(scope, epoch))
    son_names = {son.id: son.name for son in sons}
    facts.draws.extend(
        FactDraw(son=son_names[row.son_id], text=shorten(row.text, settings.deed_chars))
        for row in rows
        if row.kind is ChronicleKind.RESOURCE and row.son_id in son_names
    )
    generic = {scope.creator.name, *son_names.values(), *(world.name for world in scope.worlds.values())}
    add_events(scope, facts, rows, links, skip=son_rows, generic=generic)
    facts.histories.extend(await history_facts(scope, epoch))
    verdicts, keys = await previous_verdict_facts(scope, epoch, settings.previous_verdicts, set(son_names.values()))
    facts.verdicts.extend(verdicts)
    facts.names.update(keys)
    facts.rejected_recent.extend(await recent_rejections(scope, rejected, epoch))
    return facts
