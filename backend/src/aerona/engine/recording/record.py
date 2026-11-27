from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select

from aerona.catalog.incident_kinds.amounts import NEVER_ZERO
from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import FactSpec, IncidentKindSpec
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.fast_session import rows_by_id
from aerona.db.record_context import Term, current_scope, untold_terms
from aerona.db.repositories.chronicle import ChronicleDraft, ChronicleRepository, scoped_cause
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow, IncidentStepStateRow, IncidentTermRow
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import (
    FactUnit,
    FactValue,
    IncidentTier,
    InstrumentKind,
    PlaceRule,
    ProcessClock,
    StepAction,
    StepLocus,
    StepOutcome,
    StepState,
)
from aerona.domain.models.moment import Moment, latest
from aerona.engine.context import TickContext
from aerona.engine.recording.births import born_floor, mark_born
from aerona.engine.recording.chains import anchored, followed, happening_clock, principals
from aerona.engine.recording.deaths import death_floor, mortal_floor
from aerona.engine.recording.moments import incident_moment, moment_for, next_after, step_moments
from aerona.engine.recording.render import indexed, render_incident
from aerona.events.kinds import EventKind

RoleValue = int | Sequence[int] | None
FactInput = int | float | str | Enum | Sequence[int | float | str | Enum] | None


@dataclass(frozen=True)
class StepDraft:
    action: StepAction
    actor: int | None = None
    target: int | None = None
    round: int | None = None
    parent: int | None = None
    instrument_kind: InstrumentKind = InstrumentKind.NONE
    instrument_node: int | None = None
    instrument_key: str | None = None
    locus_kind: StepLocus = StepLocus.NONE
    locus_key: str | None = None
    locus_node: int | None = None
    damage_type: DamageType | None = None
    amount: float | None = None
    unit: FactUnit | None = None
    outcome: StepOutcome | None = None
    record_table: str | None = None
    record_key: str | None = None
    states: tuple[tuple[int, StepState], ...] = ()
    moment: Moment | None = None


@dataclass(frozen=True)
class Recorded:
    row: ChronicleRow
    incident_id: int
    text: str


@dataclass(frozen=True)
class Typed:
    participants: tuple[tuple[int, IncidentRole], ...]
    facts: tuple[IncidentFactRow, ...]


def kind_of(key: str) -> IncidentKindSpec:
    spec = INCIDENT_KINDS.get(key)
    if spec is None:
        raise ValidationFailedError(f"There is no kind of happening called {key!r}.")
    return spec


KNOWERS = frozenset({IncidentRole.WITNESS, IncidentRole.TELLER})
DATED_FACT = "year"


def nodes_of(value: RoleValue) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    return [node for node in value if node is not None]


def typed_roles(spec: IncidentKindSpec, roles: Mapping[IncidentRole, RoleValue]) -> list[tuple[int, IncidentRole]]:
    found: list[tuple[int, IncidentRole]] = []
    for role, value in roles.items():
        declared = spec.role(role)
        nodes = nodes_of(value)
        if declared is None and role in KNOWERS:
            found.extend((node, role) for node in nodes)
            continue
        if declared is None:
            if nodes:
                raise ValidationFailedError(f"A happening of kind {spec.key} has no role {spoken(role)}.")
            continue
        if len(nodes) > 1 and not declared.many:
            raise ValidationFailedError(f"A happening of kind {spec.key} takes one {spoken(role)}, not {len(nodes)}.")
        found.extend((node, role) for node in nodes)
    given = {role for _, role in found}
    missing = [declared.role.value for declared in spec.roles if declared.required and declared.role not in given]
    if missing:
        raise ValidationFailedError(f"A happening of kind {spec.key} needs its {', '.join(missing)}.")
    for declared in spec.roles:
        needed = indexed(spec.template).get(declared.role.value, 0)
        if sum(1 for _, role in found if role is declared.role) < needed:
            raise ValidationFailedError(f"A happening of kind {spec.key} names {needed} of its {spoken(declared.role)}.")
    return found


def fact_rows(spec: FactSpec, value: FactInput, kind_key: str) -> list[IncidentFactRow]:
    values = list(value) if isinstance(value, (list, tuple)) else [value]
    if len(values) > 1 and not spec.many:
        raise ValidationFailedError(f"The fact {spec.key} of {kind_key} holds one value, not {len(values)}.")
    return [fact_row(spec, item, position, kind_key) for position, item in enumerate(values) if item is not None]


def fact_row(spec: FactSpec, value: object, position: int, kind_key: str) -> IncidentFactRow:
    wrong = ValidationFailedError(f"The fact {spec.key} of {kind_key} must be {spoken(spec.value)}, not {type(value).__name__}.")
    if spec.value is FactValue.NODE:
        if not isinstance(value, int) or isinstance(value, bool):
            raise wrong
        return IncidentFactRow(key=spec.key, position=position, node_id=value)
    if spec.value is FactValue.NUMBER:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise wrong
        return IncidentFactRow(key=spec.key, position=position, number=float(value), unit=spec.unit)
    if spec.value is FactValue.ENUM:
        if not isinstance(value, Enum) or (spec.enum is not None and not isinstance(value, spec.enum)):
            raise wrong
        return IncidentFactRow(key=spec.key, position=position, enum_name=type(value).__name__, enum_value=str(value.value))
    if not isinstance(value, str):
        raise wrong
    return IncidentFactRow(key=spec.key, position=position, name=value)


def typed_facts(spec: IncidentKindSpec, facts: Mapping[str, FactInput]) -> list[IncidentFactRow]:
    rows: list[IncidentFactRow] = []
    for key, value in facts.items():
        declared = spec.fact(key)
        if declared is None:
            raise ValidationFailedError(f"A happening of kind {spec.key} has no fact {key}.")
        rows.extend(fact_rows(declared, value, spec.key))
    empty = sorted({row.key for row in rows if (spec.key, row.key) in NEVER_ZERO and (row.number or 0) <= 0})
    if empty:
        raise ValidationFailedError(f"A happening of kind {spec.key} tells what it moved, so it cannot be told with no {', '.join(empty)}.")
    given = {row.key for row in rows}
    missing = [declared.key for declared in spec.facts if declared.required and declared.key not in given]
    if missing:
        raise ValidationFailedError(f"A happening of kind {spec.key} needs the facts {', '.join(missing)}.")
    return rows


def checked_steps(spec: IncidentKindSpec, steps: Sequence[StepDraft]) -> None:
    for position, step in enumerate(steps):
        if step.action not in spec.steps:
            raise ValidationFailedError(f"A happening of kind {spec.key} has no step {spoken(step.action)}.")
        if step.parent is not None and not 0 <= step.parent < position:
            raise ValidationFailedError(f"Step {position} of {spec.key} nests under a step that does not come before it.")
        if step.unit is not None and step.amount is None:
            raise ValidationFailedError(f"Step {position} of {spec.key} has a unit but no amount.")


async def names_of(ctx: TickContext, nodes: Sequence[int]) -> dict[int, NodeRow]:
    wanted = sorted(set(nodes))
    if not wanted:
        return {}
    return await rows_by_id(ctx.session, NodeRow, wanted)


async def accepted(ctx: TickContext, spec: IncidentKindSpec, participants: Sequence[tuple[int, IncidentRole]], known: Mapping[int, NodeRow]) -> None:
    for node, role in participants:
        declared = spec.role(role)
        row = known.get(node)
        if row is None:
            raise ValidationFailedError(f"The {spoken(role)} of {spec.key} names no node.")
        if declared is None or not declared.accepts:
            continue
        entity_type = row.entity_type if isinstance(row, EntityRow) else None
        if row.kind not in declared.accepts and entity_type not in declared.accepts:
            raise ValidationFailedError(f"The {spoken(role)} of {spec.key} cannot be {row.name}.")


def told_facts(facts: Mapping[str, FactInput], known: Mapping[int, NodeRow], spec: IncidentKindSpec) -> dict[str, object]:
    shown: dict[str, object] = {}
    for key, value in facts.items():
        declared = spec.fact(key)
        if declared is not None and declared.value is FactValue.NODE:
            nodes = nodes_of(value if isinstance(value, (int, list, tuple)) else None)
            names = [known[node].name for node in nodes if node in known]
            shown[key] = names if declared.many else (names[0] if names else "")
        else:
            shown[key] = value
    return shown


def tier_of(text: str | None, steps: Sequence[StepDraft]) -> IncidentTier:
    if steps:
        return IncidentTier.STEPS
    return IncidentTier.LINE if text is not None else IncidentTier.ACCOUNT


def dated_year(spec: IncidentKindSpec, facts: Mapping[str, FactInput]) -> int | None:
    declared = spec.fact(DATED_FACT)
    value = facts.get(DATED_FACT)
    if declared is None or declared.unit is not FactUnit.YEARS or not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return int(value)


async def lift_followers(ctx: TickContext, cause_id: int, floor: Moment) -> None:
    for follower in await ctx.session.scalars(select(IncidentRow).where(IncidentRow.cause_incident_id == cause_id).order_by(IncidentRow.id)):
        own = Moment(follower.year, follower.season, follower.day, follower.hour) if follower.year is not None else None
        if own is None or not own.before(floor):
            continue
        follower.year, follower.season, follower.day, follower.hour = floor.year, floor.season, floor.day, floor.hour
        line = await ctx.session.get(ChronicleRow, follower.chronicle_id) if follower.chronicle_id is not None else None
        if line is not None:
            line.year = floor.year
        await lift_followers(ctx, follower.id, floor)


async def moment_of(
    ctx: TickContext, spec: IncidentKindSpec, nodes: Sequence[int], cause: int | None, world_id: int | None, *, principal: Sequence[int] = ()
) -> Moment:
    scope = current_scope()
    if scope is not None and scope.key == spec.key and scope.incident_id is not None and scope.moment is not None:
        floor = latest(await born_floor(ctx.session, nodes), await mortal_floor(ctx.session, nodes))
        if floor is not None and scope.moment.before(floor):
            scope.moment = floor
            incident = await ctx.session.get(IncidentRow, scope.incident_id)
            if incident is not None:
                incident.year, incident.season, incident.day, incident.hour = floor.year, floor.season, floor.day, floor.hour
                await lift_followers(ctx, incident.id, floor)
        return scope.moment
    clock = happening_clock(spec)
    floor = latest(await incident_moment(ctx.session, cause), await followed(ctx, spec.key, principal))
    prior = anchored(ctx, principal)
    if prior is not None:
        return await next_after(ctx, clock, latest(prior, floor) or prior, participants=nodes, world_id=world_id)
    return await moment_for(ctx, clock, key=spec.key, participants=nodes, cause_moment=floor, world_id=world_id)


async def happening_moment(
    ctx: TickContext,
    spec: IncidentKindSpec,
    participants: Sequence[tuple[int, IncidentRole]],
    named: Sequence[int],
    cause_id: int | None,
    *,
    world_id: int | None,
    at_moment: Moment | None,
    dated: int | None,
    place: int | None,
) -> Moment:
    principal = principals(participants)
    moment = at_moment if at_moment is not None else await moment_of(ctx, spec, named, cause_id, world_id, principal=principal)
    if dated is None:
        moment = await lifted_to_births(ctx, moment, named if at_moment is not None else [], place)
    return moment


async def lifted_to_births(ctx: TickContext, moment: Moment, named: Sequence[int], place: int | None) -> Moment:
    return moment.at_least(await born_floor(ctx.session, [*named, *([place] if place is not None else [])])).at_least(await death_floor(ctx.session, named))


async def placed(ctx: TickContext, spec: IncidentKindSpec, place: int | None, origin: int | None, destination: int | None) -> None:
    if spec.place is PlaceRule.REQUIRED and place is None:
        raise ValidationFailedError(f"A happening of kind {spec.key} needs its place.")
    for label, node in (("place", place), ("origin", origin), ("destination", destination)):
        if node is not None and await ctx.session.get(EntityRow, node) is None:
            raise ValidationFailedError(f"The {label} of {spec.key} must be a place on record, not node {node}.")


async def record(
    ctx: TickContext,
    key: str,
    *,
    roles: Mapping[IncidentRole, RoleValue] | None = None,
    facts: Mapping[str, FactInput] | None = None,
    place: int | None = None,
    origin: int | None = None,
    destination: int | None = None,
    steps: Sequence[StepDraft] = (),
    terms: Sequence[Term] | None = None,
    cause: int | None = None,
    son_id: int | None = None,
    world_id: int | None = None,
    magnitude: int = 0,
    kind: ChronicleKind | None = None,
    feed: FeedCategory | None = None,
    text: str | None = None,
    ids: Sequence[int] = (),
    positional: Mapping[int, IncidentRole] | None = None,
    at_epoch: int | None = None,
    at_moment: Moment | None = None,
) -> Recorded:
    spec = kind_of(key)
    epoch = ctx.epoch if at_epoch is None else at_epoch
    if epoch > ctx.epoch:
        raise ValidationFailedError("A happening cannot be written ahead of the present epoch.")
    await placed(ctx, spec, place, origin, destination)
    if not spec.told:
        raise ValidationFailedError(f"The kind {key} keeps changes only and is never told as a happening.")
    given_facts = dict(facts or {})
    participants = typed_roles(spec, roles or {}) if text is None else []
    fact_rows_found = typed_facts(spec, given_facts) if text is None else []
    checked_steps(spec, steps)
    known = await names_of(
        ctx, [*(node for node, _ in participants), *(row.node_id for row in fact_rows_found if row.node_id is not None), *([place] if place else [])]
    )
    await accepted(ctx, spec, participants, known)
    if text is None:
        names: dict[IncidentRole, list[str]] = {}
        for node, role in participants:
            names.setdefault(role, []).append(known[node].name)
        text = render_incident(spec, names, told_facts(given_facts, known, spec))
        tier = tier_of(None, steps)
    else:
        tier = tier_of(text, steps)
    scope = current_scope()
    filling = scope.incident_id if scope is not None and scope.key == key and scope.incident_id is not None else None
    cause_id = cause if cause is not None else scope.cause_incident_id if filling is not None and scope is not None else scoped_cause()
    linked = [node for node, _ in participants if isinstance(known.get(node), EntityRow)] if participants else list(ids)
    dated = dated_year(spec, given_facts)
    if at_moment is None and dated is not None:
        at_moment = Moment(dated)
    if at_moment is not None and dated is not None and at_moment.year != dated:
        raise ValidationFailedError(f"A happening of kind {key} told as of year {dated} cannot stand in year {at_moment.year}.")
    named = [node for node, _ in participants] or list(ids)
    moment = await happening_moment(ctx, spec, participants, named, cause_id, world_id=world_id, at_moment=at_moment, dated=dated, place=place)
    cause_moment = await incident_moment(ctx.session, cause_id)
    if at_moment is not None and cause_moment is not None and at_moment.before(cause_moment):
        raise ValidationFailedError(f"A happening of kind {key} cannot come before what caused it.")
    draft = ChronicleDraft(
        epoch=epoch,
        kind=kind or spec.chronicle_kind,
        text=text,
        entity_ids=linked,
        son_id=son_id,
        world_id=world_id,
        feed_category=feed or spec.feed,
        template_key=key,
        cause_incident_id=cause_id,
        place_entity_id=place,
        magnitude=magnitude or spec.magnitude,
        year=moment.year,
        roles=positional or {},
        participants=tuple(participants),
        incident_id=filling,
        season=moment.season,
        day=moment.day,
        hour=moment.hour,
        origin_entity_id=origin,
        destination_entity_id=destination,
        tier=tier,
    )
    write = await ChronicleRepository(ctx.session).append(draft)
    incident_id = write.incident_id
    if incident_id is None:
        raise ValidationFailedError(f"The happening {key} got no record.")
    for row in fact_rows_found:
        row.incident_id = incident_id
    ctx.session.add_all(fact_rows_found)
    ctx.session.add_all(term_rows(incident_id, terms if terms is not None else untold_terms()))
    if steps:
        await write_steps(ctx, incident_id, steps, moment, happening_clock(spec), world_id=world_id)
    await mark_born(ctx.session, [*participants, *([(place, IncidentRole.PLACE)] if place is not None else [])], moment, epoch, known)
    ctx.count("records")
    ctx.publish(
        EventKind.ENGINE_NOTE,
        {
            "epoch": ctx.epoch,
            "phase": ctx.phase,
            "kind": draft.kind.value,
            "text": write.row.text,
            "entity_ids": list(linked),
            "feed": draft.feed_category.value if draft.feed_category is not None else None,
        },
    )
    return Recorded(write.row, incident_id, write.row.text)


def term_rows(incident_id: int, terms: Sequence[Term]) -> list[IncidentTermRow]:
    return [
        IncidentTermRow(
            incident_id=incident_id,
            position=position,
            term=term.key,
            source_node_id=term.source_node_id,
            source_incident_id=term.source_incident_id,
            op=term.op,
            amount=term.amount,
        )
        for position, term in enumerate(terms)
    ]


async def write_steps(
    ctx: TickContext, incident_id: int, steps: Sequence[StepDraft], start: Moment, clock: ProcessClock, *, world_id: int | None = None
) -> list[IncidentStepRow]:
    rows: list[IncidentStepRow] = []
    spaced = await step_moments(ctx, start, clock, len(steps), world_id=world_id)
    previous = start
    for position, step in enumerate(steps):
        moment = (step.moment or spaced[position]).at_least(previous)
        previous = moment
        rows.append(
            IncidentStepRow(
                incident_id=incident_id,
                position=position,
                round=step.round,
                year=moment.year,
                season=moment.season,
                day=moment.day,
                hour=moment.hour,
                actor_node_id=step.actor,
                target_node_id=step.target,
                action=step.action,
                instrument_kind=step.instrument_kind,
                instrument_node_id=step.instrument_node,
                instrument_key=step.instrument_key,
                locus_kind=step.locus_kind,
                locus_key=step.locus_key,
                locus_node_id=step.locus_node,
                damage_type=step.damage_type,
                amount=step.amount,
                unit=step.unit,
                outcome=step.outcome,
                record_table=step.record_table,
                record_key=step.record_key,
            )
        )
    ctx.session.add_all(rows)
    await ctx.session.flush()
    for row, step in zip(rows, steps, strict=True):
        if step.parent is not None:
            row.parent_step_id = rows[step.parent].id
        ctx.session.add_all(IncidentStepStateRow(step_id=row.id, node_id=node, state=state) for node, state in dict.fromkeys(step.states))
    return rows
