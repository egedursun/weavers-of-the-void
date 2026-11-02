from collections import Counter
from collections.abc import Callable, Collection
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.ask import ask
from aerona.agents.context.scope import load_scope
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import sanitize
from aerona.catalog.bonds import BOND_KINDS, FATE_SUGGESTABLE_BOND_KINDS
from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.constants.bond_texts import SYSTEM_RELATED_DESCRIPTIONS
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondReviewRow, BondRow
from aerona.db.tables.entities import EntityRow, NetworkReviewRow
from aerona.db.tables.lore import ChronicleEntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMPANION_TYPES, EntityStatus, EntityType
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId
from aerona.prompts.contexts.cosmos import (
    GRAPH_KEY_PREFIX,
    BondCandidate,
    BondNameRelatedContext,
    BondSuggestContext,
    CandidateReason,
    GraphNode,
    GraphNodeKind,
    RelatedBond,
    SuggestRecord,
)
from aerona.prompts.schemas.cosmos import BondDirection, BondNameRelatedOutput, BondSuggestOutput
from aerona.rules.registry import Rules

REVIEW_STATUSES = (EntityStatus.CANON, EntityStatus.DEAD, EntityStatus.FULFILLED)
PRIORITY_TYPES = (EntityType.EVENT, EntityType.LEGEND, EntityType.TRADITION)
CLOSE_DECISION = "close"
CLOSED_PREFIX = "closed: "
CANDIDATE_FACTOR = 2
UNLIMITED = 10**9
PERCENT = 100
StopCheck = Callable[[], bool]


@dataclass
class RepairSummary:
    looked: int = 0
    built: int = 0
    named: int = 0
    closed: int = 0
    bonds: list[str] = field(default_factory=list)


def entity_node(entity: EntityRow, rules: Rules) -> GraphNode:
    return GraphNode(
        kind=GraphNodeKind.ENTITY,
        id=entity.id,
        name=entity.name,
        type_label=ENTITY_TYPES[entity.entity_type].label,
        subtype=entity.subtype,
        status_label=None if entity.status is EntityStatus.CANON else entity.status.value,
        description=entity.description[: rules.link_graph.description_trim_chars],
    )


def son_node(son: SonRow) -> GraphNode:
    return GraphNode(kind=GraphNodeKind.SON, id=son.id, name=son.name, title=son.title)


async def weak_records(session: AsyncSession, rules: Rules, epoch: int, limit: int) -> list[EntityRow]:
    degree = (
        select(func.count())
        .select_from(BondRow)
        .where(BondRow.state == BondState.ACTIVE, (BondRow.source_node_id == EntityRow.id) | (BondRow.target_node_id == EntityRow.id))
        .correlate(EntityRow)
        .scalar_subquery()
    )
    recent = select(NetworkReviewRow.entity_id).where(NetworkReviewRow.epoch > epoch - rules.link_graph.revisit_epochs)
    statement = (
        select(EntityRow)
        .where(EntityRow.status.in_(REVIEW_STATUSES), EntityRow.pending_name.is_(False), EntityRow.id.not_in(recent), degree <= rules.link_graph.weak_degree)
        .order_by(degree, func.coalesce(EntityRow.importance, 0).desc(), EntityRow.id)
        .limit(limit)
    )
    return list(await session.scalars(statement))


async def co_mentions(session: AsyncSession, entity_id: int) -> Counter[int]:
    rows = await session.execute(
        select(ChronicleEntityRow.entity_id).where(
            ChronicleEntityRow.chronicle_id.in_(select(ChronicleEntityRow.chronicle_id).where(ChronicleEntityRow.entity_id == entity_id)),
            ChronicleEntityRow.entity_id != entity_id,
        )
    )
    return Counter(row[0] for row in rows)


async def unbonded_mentions(session: AsyncSession, entity_id: int) -> int:
    bonds = BondRepository(session)
    count = 0
    for other in await co_mentions(session, entity_id):
        if not await bonds.active_between(entity_id, other, list(BondKind)):
            count += 1
    return count


async def priority_records(session: AsyncSession, rules: Rules, epoch: int, limit: int) -> list[EntityRow]:
    recent = select(NetworkReviewRow.entity_id).where(NetworkReviewRow.epoch > epoch - rules.link_graph.revisit_epochs)
    rows = list(
        await session.scalars(
            select(EntityRow).where(
                EntityRow.entity_type.in_(PRIORITY_TYPES), EntityRow.status.in_(REVIEW_STATUSES), EntityRow.pending_name.is_(False), EntityRow.id.not_in(recent)
            )
        )
    )
    scored = [(await unbonded_mentions(session, row.id), row) for row in rows]
    ranked = sorted((item for item in scored if item[0] > 0), key=lambda item: (-item[0], -(item[1].importance or 0), item[1].id))
    return [row for _, row in ranked[:limit]]


def proposal_cap(rules: Rules, entity: EntityRow) -> int:
    graph = rules.link_graph
    return max(graph.proposal_cap, graph.event_proposal_cap) if entity.entity_type is EntityType.EVENT else graph.proposal_cap


async def candidates_for(session: AsyncSession, rules: Rules, entity: EntityRow) -> list[BondCandidate]:
    graph = rules.link_graph
    cap = proposal_cap(rules, entity)
    found: dict[str, BondCandidate] = {}

    def add(node: GraphNode, reason: CandidateReason, mentions: int = 0) -> None:
        if node.key not in found and not (node.kind is GraphNodeKind.ENTITY and node.id == entity.id):
            found[node.key] = BondCandidate(node=node, reason=reason, mentions=mentions)

    for other_id, count in (await co_mentions(session, entity.id)).most_common(max(graph.candidates, cap * CANDIDATE_FACTOR)):
        other = await session.get(EntityRow, other_id)
        if other is not None and other.status in REVIEW_STATUSES:
            add(entity_node(other, rules), CandidateReason.MENTIONED_TOGETHER, count)
    for related_id, reason in ((entity.location_id, CandidateReason.LOCATION), (entity.maker_entity_id, CandidateReason.MAKER)):
        related = await session.get(EntityRow, related_id) if related_id is not None else None
        if related is not None:
            add(entity_node(related, rules), reason)
    son = await session.get(SonRow, entity.creator_son_id) if entity.creator_son_id is not None else None
    if son is not None:
        add(son_node(son), CandidateReason.CREATOR)
    if entity.location_id is not None:
        neighbours = await session.scalars(
            select(EntityRow)
            .where(EntityRow.location_id == entity.location_id, EntityRow.status == EntityStatus.CANON, EntityRow.id != entity.id)
            .order_by(func.coalesce(EntityRow.importance, 0).desc())
            .limit(graph.candidates)
        )
        for neighbour in neighbours:
            add(entity_node(neighbour, rules), CandidateReason.SAME_PLACE)
    notable = await session.scalars(
        select(EntityRow)
        .where(
            EntityRow.world_id == entity.world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type != EntityType.REGION, EntityRow.id != entity.id
        )
        .order_by(func.coalesce(EntityRow.importance, 0).desc(), EntityRow.id)
        .limit(graph.candidates)
    )
    for other in notable:
        add(entity_node(other, rules), CandidateReason.NOTABLE_OF_WORLD)
    return list(found.values())[: max(graph.candidates, cap * CANDIDATE_FACTOR) * CANDIDATE_FACTOR]


def companion_ok(rules: Rules, reason: str, ends: list[EntityRow | SonRow]) -> bool:
    graph = rules.link_graph
    if len(reason) < graph.companion_reason_min_chars or len(reason.split()) < graph.companion_reason_min_words:
        return False
    return all(isinstance(end, SonRow) or end.entity_type in COMPANION_TYPES for end in ends)


async def node_of(session: AsyncSession, node: GraphNode) -> EntityRow | SonRow | None:
    return await session.get(SonRow, node.id) if node.kind is GraphNodeKind.SON else await session.get(EntityRow, node.id)


def node_key(raw: str, known: Collection[str]) -> str:
    cleaned = raw.strip().casefold().lstrip("#")
    if cleaned in known or not cleaned.isdigit():
        return cleaned
    for prefix in (GRAPH_KEY_PREFIX[GraphNodeKind.ENTITY], GRAPH_KEY_PREFIX[GraphNodeKind.SON]):
        if f"{prefix}{cleaned}" in known:
            return f"{prefix}{cleaned}"
    return cleaned


async def apply_suggestions(session: AsyncSession, rules: Rules, epoch: int, records: list[SuggestRecord], output: BondSuggestOutput) -> list[str]:
    targets = {record.node.key: record for record in records}
    made: Counter[str] = Counter()
    bonds = BondRepository(session)
    built: list[str] = []
    for suggestion in output.bonds:
        record = targets.get(node_key(suggestion.record, targets))
        if record is None:
            continue
        other_key = node_key(suggestion.other, {item.node.key for item in record.candidates})
        candidate = next((item for item in record.candidates if item.node.key == other_key), None)
        reason = sanitize(suggestion.reason)
        entity = await session.get(EntityRow, record.node.id)
        if candidate is None or entity is None or suggestion.type not in FATE_SUGGESTABLE_BOND_KINDS or suggestion.shared_theme:
            continue
        if len(reason) < rules.link_graph.reason_min_chars or made[record.node.key] >= proposal_cap(rules, entity):
            continue
        other = await node_of(session, candidate.node)
        if other is None or await bonds.active_between(entity.id, other.id, list(BondKind)):
            continue
        if suggestion.type is BondKind.COMPANION and not companion_ok(rules, reason, [entity, other]):
            continue
        source, target = (entity.id, other.id) if suggestion.direction is BondDirection.FROM_RECORD else (other.id, entity.id)
        await bonds.connect(BondDraft(source, target, suggestion.type, epoch, reason))
        made[record.node.key] += 1
        built.append(f"{entity.name} {BOND_KINDS[suggestion.type].label} {other.name}")
    for record in records:
        row = await session.get(NetworkReviewRow, record.node.id)
        if row is None:
            session.add(NetworkReviewRow(entity_id=record.node.id, epoch=epoch))
        else:
            row.epoch = epoch
    return built


async def suggest_bonds(runtime: AgentRuntime, entity_ids: list[int]) -> RepairSummary:
    runtime.require_llm("bond suggestion")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        entities = [entity for entity in [await session.get(EntityRow, entity_id) for entity_id in entity_ids] if entity is not None]
        records = [SuggestRecord(node=entity_node(entity, rules), candidates=await candidates_for(session, rules, entity)) for entity in entities]
        records = [record for record in records if record.candidates]
        context = BondSuggestContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            world_name=scope.cosmos.name,
            bond_types=sorted(kind.value for kind in FATE_SUGGESTABLE_BOND_KINDS),
            records=records,
        )
    summary = RepairSummary(looked=len(entities))
    if not records:
        return summary
    runtime.note(f"Fate is looking at {len(records)} weakly connected records…")
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.BOND_SUGGESTION,
        system=(PromptId.BOND_SUGGEST_SYSTEM, context),
        user=(PromptId.BOND_SUGGEST_USER, context),
        output=BondSuggestOutput,
    )
    async with runtime.database.write() as session:
        summary.bonds = await apply_suggestions(session, rules, scope.epoch, records, output)
    summary.built = len(summary.bonds)
    text = (
        f"Fate looked at {summary.looked} records and made {summary.built} reasoned bonds."
        if summary.built
        else f"Fate looked at {summary.looked} records; it found no bond with enough evidence."
    )
    runtime.publish(EventKind.NETWORK_REPAIRED, {"type": "fate", "text": text, "bonds": summary.bonds})
    return summary


async def name_related_bonds(runtime: AgentRuntime, cursor: int, limit: int) -> tuple[RepairSummary, int]:
    runtime.require_llm("related bond naming")
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        batch = min(limit, rules.link_graph.related_batch)
        rows = list(
            await session.scalars(
                select(BondRow)
                .where(BondRow.kind == BondKind.RELATED, BondRow.state == BondState.ACTIVE, BondRow.description.is_(None), BondRow.id > cursor)
                .order_by(BondRow.id)
                .limit(batch)
            )
        )
        described = await justified_related(session, batch - len(rows))
        trim = rules.link_graph.description_trim_chars
        pairs: list[tuple[BondRow, RelatedBond]] = []
        for row in [*rows, *described]:
            source = await session.get(EntityRow, row.source_node_id)
            target = await session.get(EntityRow, row.target_node_id)
            if source is not None and target is not None:
                reason = row.description[:trim] if row.description else None
                pairs.append((row, RelatedBond(source=entity_node(source, rules), target=entity_node(target, rules), reason=reason)))
        context = BondNameRelatedContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            world_name=scope.cosmos.name,
            bond_types=sorted(kind.value for kind in FATE_SUGGESTABLE_BOND_KINDS),
            bonds=[pair for _, pair in pairs],
        )
    summary = RepairSummary(looked=len(rows) + len(described))
    last = rows[-1].id if rows else cursor
    if not pairs:
        await mark_reviewed_bonds(runtime, [row.id for row in described], scope.epoch)
        return summary, last
    runtime.note(f'Fate is naming {len(pairs)} vague "related" bonds…')
    output = await ask(
        runtime.model,
        rules,
        label=AgentRole.BOND_NAMING,
        system=(PromptId.BOND_NAME_RELATED_SYSTEM, context),
        user=(PromptId.BOND_NAME_RELATED_USER, context),
        output=BondNameRelatedOutput,
    )
    async with runtime.database.write() as session:
        repository = BondRepository(session)
        for decision in output.decisions:
            if not 1 <= decision.number <= len(pairs):
                continue
            current = await session.get(BondRow, pairs[decision.number - 1][0].id)
            reason = sanitize(decision.reason)
            if current is None or not current.active:
                continue
            bond = current
            if decision.decision == CLOSE_DECISION or decision.theme_only or (decision.decision == BondKind.RELATED.value and decision.denies_bond):
                await repository.deactivate(bond, scope.epoch, (CLOSED_PREFIX + reason)[:trim])
                summary.closed += 1
            elif len(reason) >= rules.link_graph.reason_min_chars and decision.decision in {kind.value for kind in BondKind}:
                bond.kind = BondKind(decision.decision)
                bond.description = reason[:trim]
                summary.named += 1
        for row, _ in pairs:
            await session.merge(BondReviewRow(bond_id=row.id, epoch=scope.epoch))
    await mark_reviewed_bonds(runtime, [row.id for row in described], scope.epoch)
    runtime.publish(
        EventKind.NETWORK_REPAIRED, {"type": "related", "text": f"Fate looked at {summary.looked} vague bonds: {summary.named} named, {summary.closed} closed."}
    )
    return summary, last


async def justified_related(session: AsyncSession, room: int) -> list[BondRow]:
    if room <= 0:
        return []
    reviewed = select(BondReviewRow.bond_id)
    statement = (
        select(BondRow)
        .where(
            BondRow.kind == BondKind.RELATED,
            BondRow.state == BondState.ACTIVE,
            BondRow.description.is_not(None),
            BondRow.role.is_(None),
            BondRow.description.not_in(list(SYSTEM_RELATED_DESCRIPTIONS)),
            BondRow.id.not_in(reviewed),
        )
        .order_by(BondRow.id)
        .limit(room)
    )
    return list(await session.scalars(statement))


async def mark_reviewed_bonds(runtime: AgentRuntime, bond_ids: list[int], epoch: int) -> None:
    if not bond_ids:
        return
    async with runtime.database.write() as session:
        for bond_id in bond_ids:
            await session.merge(BondReviewRow(bond_id=bond_id, epoch=epoch))


async def network_fate_repair(
    runtime: AgentRuntime, ids: list[int] | None = None, *, related: bool = True, automatic: bool = False, full: bool = False, stop: StopCheck | None = None
) -> RepairSummary:
    del automatic
    rules = await runtime.current_rules()
    graph = rules.link_graph
    total = RepairSummary()
    if ids:
        for start in range(0, len(ids), graph.fate_batch):
            if stop is not None and stop():
                break
            part = await suggest_bonds(runtime, ids[start : start + graph.fate_batch])
            total.looked += part.looked
            total.built += part.built
        return total
    remaining = UNLIMITED if full else graph.fate_epoch_cap
    priority = UNLIMITED if full else round(remaining * graph.priority_share_pct / PERCENT)
    while remaining > 0 and not (stop is not None and stop()):
        async with runtime.database.read() as session:
            epoch = (await load_scope(session, rules)).epoch
            batch = await priority_records(session, rules, epoch, min(priority, graph.fate_batch)) if priority > 0 else []
            if batch:
                priority -= len(batch)
            else:
                batch = await weak_records(session, rules, epoch, min(remaining, graph.fate_batch))
        if not batch:
            break
        part = await suggest_bonds(runtime, [entity.id for entity in batch])
        if part.looked == 0:
            break
        total.looked += part.looked
        total.built += part.built
        remaining -= part.looked
    if related:
        left = UNLIMITED if full else graph.related_epoch_cap
        cursor = 0
        while left > 0 and not (stop is not None and stop()):
            part, cursor = await name_related_bonds(runtime, cursor, left)
            if part.looked == 0:
                break
            total.named += part.named
            total.closed += part.closed
            left -= part.looked
    return total


async def repair_loose_ends(session: AsyncSession, epoch: int) -> int:
    bonds = BondRepository(session)
    repaired = 0
    located = await session.scalars(select(EntityRow).where(EntityRow.location_id.is_not(None), EntityRow.status == EntityStatus.CANON))
    for entity in located:
        if not await bonds.active_between(entity.id, entity.location_id or 0, [BondKind.INSIDE]):
            await bonds.refresh_location(entity.id, entity.location_id, epoch)
            repaired += 1
    return repaired


async def network_rule_repair(runtime: AgentRuntime, epoch: int) -> int:
    async with runtime.database.write() as session:
        repaired = await repair_loose_ends(session, epoch)
    if repaired:
        runtime.publish(
            EventKind.NETWORK_REPAIRED, {"type": "rule", "text": f"Network repaired: {repaired} loose ends bonded.", "counts": {"location": repaired}}
        )
    return repaired
