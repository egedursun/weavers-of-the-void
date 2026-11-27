from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.incident_kinds.registry import INCIDENT_KINDS
from aerona.catalog.incident_kinds.spec import IncidentKindSpec
from aerona.catalog.incident_kinds.tellings import CONTRADICTED, CORRECTED
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import fact_word
from aerona.core.random import SeededRandom
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.gatherings import CollectionIncidentRow, CollectionRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.made import InformationTrustRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.db.tables.tellings import RumourDistortionRow
from aerona.db.write_guard import held
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, IncidentTier, RumourDistortion, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record
from aerona.engine.recording.render import render_incident
from aerona.engine.recording.terms import explaining, term

LOAD_CHUNK = 500
DOERS = frozenset({IncidentRole.ACTOR, IncidentRole.CO_ACTOR, IncidentRole.SUBJECT})
DONE_TO = frozenset({IncidentRole.TARGET, IncidentRole.VICTIM, IncidentRole.OPPONENT})
UNSWAPPED = frozenset({*DOERS, *DONE_TO, IncidentRole.WITNESS, IncidentRole.TELLER, IncidentRole.PLACE})
YEARS_OFF = (-3, -2, -1, 1, 2, 3)
AMOUNT_FACTORS = (0.5, 0.75, 1.5, 2.0, 3.0)
COUNTED_UNITS = frozenset({FactUnit.PEOPLE, FactUnit.COIN, FactUnit.COUNT, FactUnit.WEALTH_POINTS})
OUTCOME_FAMILIES: tuple[frozenset[StepOutcome], ...] = (
    frozenset({StepOutcome.WOUNDED, StepOutcome.BROKEN, StepOutcome.SEVERED, StepOutcome.DOWNED, StepOutcome.KILLED}),
    frozenset(
        {
            StepOutcome.SUCCESS,
            StepOutcome.PARTIAL,
            StepOutcome.FAILURE,
            StepOutcome.MISSED,
            StepOutcome.BLOCKED,
            StepOutcome.PARRIED,
            StepOutcome.DODGED,
            StepOutcome.GLANCED,
            StepOutcome.ABSORBED,
        }
    ),
    frozenset({StepOutcome.DAMAGED, StepOutcome.DISABLED, StepOutcome.DESTROYED}),
    frozenset({StepOutcome.CAPTURED, StepOutcome.ESCAPED, StepOutcome.YIELDED}),
    frozenset({StepOutcome.ACCEPTED, StepOutcome.REFUSED, StepOutcome.DELAYED, StepOutcome.INTERRUPTED, StepOutcome.REVERSED, StepOutcome.NO_EFFECT}),
)


def outcome_family(outcome: StepOutcome) -> frozenset[StepOutcome]:
    return next(family for family in OUTCOME_FAMILIES if outcome in family)


@dataclass
class Telling:
    incident: IncidentRow
    roles: list[IncidentParticipantRow] = field(default_factory=list)
    facts: list[IncidentFactRow] = field(default_factory=list)
    steps: list[IncidentStepRow] = field(default_factory=list)


async def tellings_of(session: AsyncSession, incident_ids: Iterable[int]) -> dict[int, Telling]:
    ids = sorted(set(incident_ids))
    found: dict[int, Telling] = {}
    for start in range(0, len(ids), LOAD_CHUNK):
        chunk = ids[start : start + LOAD_CHUNK]
        for row in await session.scalars(select(IncidentRow).where(IncidentRow.id.in_(chunk)).order_by(IncidentRow.id)):
            found[row.id] = Telling(row)
        for part in await session.scalars(
            select(IncidentParticipantRow)
            .where(IncidentParticipantRow.incident_id.in_(chunk))
            .order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position)
        ):
            if part.incident_id in found:
                found[part.incident_id].roles.append(part)
        for fact in await session.scalars(
            select(IncidentFactRow)
            .where(IncidentFactRow.incident_id.in_(chunk))
            .order_by(IncidentFactRow.incident_id, IncidentFactRow.key, IncidentFactRow.position)
        ):
            if fact.incident_id in found:
                found[fact.incident_id].facts.append(fact)
        for step in await session.scalars(
            select(IncidentStepRow).where(IncidentStepRow.incident_id.in_(chunk)).order_by(IncidentStepRow.incident_id, IncidentStepRow.position)
        ):
            if step.incident_id in found:
                found[step.incident_id].steps.append(step)
    return found


async def distortions_of(session: AsyncSession, rumour_ids: Iterable[int]) -> dict[int, list[RumourDistortionRow]]:
    ids = sorted(set(rumour_ids))
    found: dict[int, list[RumourDistortionRow]] = defaultdict(list)
    for start in range(0, len(ids), LOAD_CHUNK):
        statement = select(RumourDistortionRow).where(RumourDistortionRow.rumour_id.in_(ids[start : start + LOAD_CHUNK]))
        for row in await session.scalars(statement.order_by(RumourDistortionRow.rumour_id, RumourDistortionRow.position)):
            found[row.rumour_id].append(row)
    return found


def target_of(row: RumourDistortionRow) -> tuple[RumourDistortion, IncidentRole | None, str | None, int | None]:
    return row.distortion, row.role, row.fact_key, row.step_id


def swapped_role(telling: Telling, roles: frozenset[IncidentRole], kind: RumourDistortion, rng: SeededRandom) -> RumourDistortionRow | None:
    holders = [row for row in telling.roles if row.role in roles]
    others = sorted({row.node_id for row in telling.roles if row.role not in {IncidentRole.TELLER, IncidentRole.PLACE}} - {row.node_id for row in holders})
    if not holders or not others:
        return None
    holder = rng.pick(holders)
    return RumourDistortionRow(distortion=kind, role=holder.role, told_node_id=rng.pick(others))


def changed_instrument(telling: Telling, rng: SeededRandom) -> RumourDistortionRow | None:
    others = [row for row in telling.roles if row.role not in UNSWAPPED]
    if others:
        holder = rng.pick(others)
        pool = sorted({row.node_id for row in telling.roles if row.role not in {IncidentRole.TELLER, IncidentRole.PLACE}} - {holder.node_id})
        if pool:
            return RumourDistortionRow(distortion=RumourDistortion.ROLE_CHANGED, role=holder.role, told_node_id=rng.pick(pool))
    armed = [step for step in telling.steps if step.instrument_key is not None or step.instrument_node_id is not None]
    if not armed:
        return None
    step = rng.pick(armed)
    keys = sorted({other.instrument_key for other in armed if other.instrument_key is not None and other.instrument_key != step.instrument_key})
    nodes = sorted(
        {other.instrument_node_id for other in armed if other.instrument_node_id is not None and other.instrument_node_id != step.instrument_node_id}
    )
    if keys:
        return RumourDistortionRow(distortion=RumourDistortion.ROLE_CHANGED, role=IncidentRole.INSTRUMENT, step_id=step.id, told_enum_value=rng.pick(keys))
    if nodes:
        return RumourDistortionRow(distortion=RumourDistortion.ROLE_CHANGED, role=IncidentRole.INSTRUMENT, step_id=step.id, told_node_id=rng.pick(nodes))
    return None


def changed_amount(telling: Telling, rng: SeededRandom) -> RumourDistortionRow | None:
    numbers = [fact for fact in telling.facts if fact.number is not None and fact.number != 0]
    if not numbers:
        return None
    fact = rng.pick(numbers)
    told = round((fact.number or 0) * rng.pick(AMOUNT_FACTORS), 2)
    return RumourDistortionRow(distortion=RumourDistortion.AMOUNT_CHANGED, fact_key=fact.key, told_number=told)


def changed_outcome(telling: Telling, rng: SeededRandom) -> RumourDistortionRow | None:
    stepped = [step for step in telling.steps if step.outcome is not None and len(outcome_family(step.outcome)) > 1]
    spec = INCIDENT_KINDS.get(telling.incident.kind)
    enums = []
    for fact in telling.facts:
        declared = spec.fact(fact.key) if spec is not None else None
        enum = declared.enum if declared is not None else None
        if fact.enum_value is not None and enum is not None and len(enum) > 1:
            enums.append((fact, sorted(str(member.value) for member in enum if str(member.value) != fact.enum_value)))
    if stepped and (not enums or rng.chance(50)):
        step = rng.pick(stepped)
        current = step.outcome or StepOutcome.SUCCESS
        return RumourDistortionRow(
            distortion=RumourDistortion.OUTCOME_CHANGED, step_id=step.id, told_outcome=rng.pick(sorted(outcome_family(current) - {current}))
        )
    if enums:
        fact, values = rng.pick(enums)
        return RumourDistortionRow(distortion=RumourDistortion.OUTCOME_CHANGED, fact_key=fact.key, told_enum_value=rng.pick(values))
    return None


async def changed_cause(session: AsyncSession, telling: Telling, rng: SeededRandom) -> RumourDistortionRow | None:
    if telling.incident.cause_incident_id is None:
        return None
    nodes = [row.node_id for row in telling.roles]
    if not nodes:
        return None
    others = list(
        await session.scalars(
            select(IncidentParticipantRow.incident_id)
            .where(
                IncidentParticipantRow.node_id.in_(nodes),
                IncidentParticipantRow.incident_id < telling.incident.id,
                IncidentParticipantRow.incident_id != telling.incident.cause_incident_id,
            )
            .order_by(IncidentParticipantRow.incident_id.desc())
            .limit(8)
        )
    )
    if not others:
        return None
    return RumourDistortionRow(distortion=RumourDistortion.CAUSE_CHANGED, told_incident_id=rng.pick(sorted(set(others))))


def changed_place(telling: Telling, atlas: RegionAtlas, rng: SeededRandom) -> RumourDistortionRow | None:
    place = telling.incident.place_entity_id
    region = atlas.top_region(place) if place is not None else None
    if region is None:
        return None
    nearby = sorted({community for other in atlas.neighbours(region) for community in atlas.communities_in(other)} - {place or 0})
    if not nearby:
        return None
    return RumourDistortionRow(distortion=RumourDistortion.PLACE_CHANGED, told_node_id=rng.pick(nearby))


def changed_moment(telling: Telling, rng: SeededRandom) -> RumourDistortionRow | None:
    year = telling.incident.year
    if year is None:
        return None
    return RumourDistortionRow(distortion=RumourDistortion.MOMENT_CHANGED, told_year=max(0, year + rng.pick(YEARS_OFF)))


def changed_steps(telling: Telling, rng: SeededRandom) -> RumourDistortionRow | None:
    if not telling.steps:
        return None
    step = rng.pick(telling.steps)
    spec = INCIDENT_KINDS.get(telling.incident.kind)
    actions = sorted((spec.steps if spec is not None else frozenset()) - {step.action}, key=lambda action: action.value)
    if actions and rng.chance(50):
        return RumourDistortionRow(distortion=RumourDistortion.STEP_ADDED, step_id=step.id, told_action=rng.pick(actions))
    return RumourDistortionRow(distortion=RumourDistortion.STEP_DROPPED, step_id=step.id)


def inflated_count(telling: Telling, held_before: Sequence[RumourDistortionRow], inflate_pct: int) -> RumourDistortionRow | None:
    spec = INCIDENT_KINDS.get(telling.incident.kind)
    counted = [
        fact
        for fact in telling.facts
        if fact.number is not None and fact.number > 0 and spec is not None and (declared := spec.fact(fact.key)) is not None and declared.unit in COUNTED_UNITS
    ]
    if not counted:
        return None
    fact = counted[0]
    told = max((row.told_number or 0.0 for row in held_before if row.fact_key == fact.key and row.told_number is not None), default=fact.number or 0.0)
    return RumourDistortionRow(distortion=RumourDistortion.COUNT_INFLATED, fact_key=fact.key, told_number=round(told * (PERCENT + inflate_pct) / PERCENT, 2))


async def added_motive(session: AsyncSession, telling: Telling, rng: SeededRandom) -> RumourDistortionRow | None:
    if telling.incident.cause_incident_id is not None:
        return None
    doers = [row.node_id for row in telling.roles if row.role in DOERS]
    if not doers:
        return None
    earlier = list(
        await session.scalars(
            select(IncidentParticipantRow.incident_id)
            .where(IncidentParticipantRow.node_id.in_(doers), IncidentParticipantRow.incident_id < telling.incident.id)
            .order_by(IncidentParticipantRow.incident_id.desc())
            .limit(8)
        )
    )
    if not earlier:
        return None
    return RumourDistortionRow(distortion=RumourDistortion.MOTIVE_ADDED, role=IncidentRole.ACTOR, told_incident_id=rng.pick(sorted(set(earlier))))


async def draft_distortion(
    session: AsyncSession, atlas: RegionAtlas, telling: Telling, held_before: Sequence[RumourDistortionRow], rng: SeededRandom, *, inflate_pct: int = 0
) -> RumourDistortionRow | None:
    known = {target_of(row) for row in held_before}
    drafts = [
        swapped_role(telling, DOERS, RumourDistortion.DOER_SWAPPED, rng),
        swapped_role(telling, DONE_TO, RumourDistortion.TARGET_SWAPPED, rng),
        changed_instrument(telling, rng),
        changed_amount(telling, rng),
        changed_outcome(telling, rng),
        await changed_cause(session, telling, rng),
        changed_place(telling, atlas, rng),
        changed_moment(telling, rng),
        changed_steps(telling, rng),
        inflated_count(telling, held_before, inflate_pct) if inflate_pct > 0 else None,
        await added_motive(session, telling, rng),
    ]
    fresh = [draft for draft in drafts if draft is not None and target_of(draft) not in known]
    return rng.pick(fresh) if fresh else None


def carried(held_before: Sequence[RumourDistortionRow], rumour_id: int, epoch: int) -> list[RumourDistortionRow]:
    return [
        RumourDistortionRow(
            rumour_id=rumour_id,
            position=position,
            distortion=row.distortion,
            role=row.role,
            fact_key=row.fact_key,
            step_id=row.step_id,
            told_node_id=row.told_node_id,
            told_number=row.told_number,
            told_enum_value=row.told_enum_value,
            told_year=row.told_year,
            told_incident_id=row.told_incident_id,
            told_action=row.told_action,
            told_outcome=row.told_outcome,
            epoch=row.epoch if row.epoch else epoch,
            locked=[],
        )
        for position, row in enumerate(held_before)
    ]


@dataclass(frozen=True)
class ToldPart:
    node_id: int
    role: IncidentRole
    position: int


@dataclass(frozen=True)
class ToldFact:
    key: str
    position: int
    node_id: int | None
    number: float | None
    enum_name: str | None
    enum_value: str | None
    name: str | None


@dataclass(frozen=True)
class ToldStep:
    step_id: int | None
    position: int
    action: str
    actor_node_id: int | None
    target_node_id: int | None
    instrument_key: str | None
    instrument_node_id: int | None
    outcome: StepOutcome | None


@dataclass(frozen=True)
class Told:
    incident_id: int
    kind: str
    place_id: int | None
    year: int | None
    cause_incident_id: int | None
    parts: tuple[ToldPart, ...]
    facts: tuple[ToldFact, ...]
    steps: tuple[ToldStep, ...]


def as_told(telling: Telling) -> Told:
    incident = telling.incident
    return Told(
        incident_id=incident.id,
        kind=incident.kind,
        place_id=incident.place_entity_id,
        year=incident.year,
        cause_incident_id=incident.cause_incident_id,
        parts=tuple(ToldPart(row.node_id, row.role, row.position) for row in telling.roles if row.role not in {IncidentRole.WITNESS, IncidentRole.TELLER}),
        facts=tuple(ToldFact(row.key, row.position, row.node_id, row.number, row.enum_name, row.enum_value, row.name) for row in telling.facts),
        steps=tuple(
            ToldStep(
                step.id, step.position, step.action.value, step.actor_node_id, step.target_node_id, step.instrument_key, step.instrument_node_id, step.outcome
            )
            for step in telling.steps
        ),
    )


def swap_part(told: Told, row: RumourDistortionRow) -> Told:
    if row.told_node_id is None or row.role is None:
        return told
    first = next((part for part in told.parts if part.role is row.role), None)
    if first is None:
        return told
    return replace(told, parts=tuple(replace(part, node_id=row.told_node_id) if part == first else part for part in told.parts))


def change_fact(told: Told, row: RumourDistortionRow) -> Told:
    facts = tuple(
        replace(fact, number=row.told_number if row.told_number is not None else fact.number, enum_value=row.told_enum_value or fact.enum_value)
        if fact.key == row.fact_key and fact.position == 0
        else fact
        for fact in told.facts
    )
    return replace(told, facts=facts)


def change_step(told: Told, row: RumourDistortionRow) -> Told:
    steps = []
    for step in told.steps:
        if step.step_id != row.step_id:
            steps.append(step)
            continue
        if row.distortion is RumourDistortion.STEP_DROPPED:
            continue
        if row.distortion is RumourDistortion.STEP_ADDED:
            steps.append(step)
            steps.append(replace(step, step_id=None, action=row.told_action.value if row.told_action is not None else step.action))
            continue
        if row.distortion is RumourDistortion.OUTCOME_CHANGED:
            steps.append(replace(step, outcome=row.told_outcome or step.outcome))
            continue
        steps.append(replace(step, instrument_key=row.told_enum_value or step.instrument_key, instrument_node_id=row.told_node_id or step.instrument_node_id))
    return replace(told, steps=tuple(steps))


def apply_distortion(told: Told, row: RumourDistortionRow) -> Told:
    by_step = row.step_id is not None
    plain: dict[RumourDistortion, Callable[[Told, RumourDistortionRow], Told]] = {
        RumourDistortion.DOER_SWAPPED: swap_part,
        RumourDistortion.TARGET_SWAPPED: swap_part,
        RumourDistortion.ROLE_CHANGED: change_step if by_step else swap_part,
        RumourDistortion.AMOUNT_CHANGED: change_fact,
        RumourDistortion.OUTCOME_CHANGED: change_step if by_step else change_fact,
        RumourDistortion.CAUSE_CHANGED: lambda told, row: replace(told, cause_incident_id=row.told_incident_id),
        RumourDistortion.PLACE_CHANGED: lambda told, row: replace(told, place_id=row.told_node_id),
        RumourDistortion.MOMENT_CHANGED: lambda told, row: replace(told, year=row.told_year),
        RumourDistortion.STEP_ADDED: change_step,
        RumourDistortion.STEP_DROPPED: change_step,
        RumourDistortion.COUNT_INFLATED: change_fact,
        RumourDistortion.MOTIVE_ADDED: lambda told, row: replace(told, cause_incident_id=row.told_incident_id),
    }
    return plain[row.distortion](told, row)


def told_version(telling: Telling, distortions: Sequence[RumourDistortionRow]) -> Told:
    told = as_told(telling)
    for row in distortions:
        told = apply_distortion(told, row)
    return told


async def telling_of(session: AsyncSession, incident_id: int) -> Telling | None:
    return (await tellings_of(session, [incident_id])).get(incident_id)


HELD_DISTORTIONS = "distortions"
HELD_FIDELITY = "fidelity"
HELD_TRUST = "information_trust"


async def trust_row(ctx: TickContext, holder_id: int) -> InformationTrustRow:
    row = await ctx.session.get(InformationTrustRow, holder_id)
    if row is None:
        row = InformationTrustRow(holder_entity_id=holder_id, information_trust=60, shared_account_pct=100, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def heard_again(
    ctx: TickContext, arriving: RumourRow, holder: RumourRow, arriving_told: Sequence[RumourDistortionRow], holder_told: list[RumourDistortionRow]
) -> str | None:
    ahead = {target_of(row) for row in arriving_told}
    known = {target_of(row) for row in holder_told}
    if ahead == known or held(holder.carrier_entity_id):
        return None
    teller = arriving.carrier_entity_id
    if ahead < known and arriving.fidelity >= holder.fidelity and HELD_DISTORTIONS not in holder.locked:
        dropped = [row for row in holder_told if target_of(row) not in ahead]
        for row in dropped:
            holder_told.remove(row)
            await ctx.session.delete(row)
        if HELD_FIDELITY not in holder.locked:
            holder.fidelity = max(holder.fidelity, arriving.fidelity)
        await record(
            ctx,
            "rumour.corrected",
            roles={IncidentRole.SUBJECT: holder.carrier_entity_id, IncidentRole.TELLER: teller},
            facts={"dropped": len(dropped), "fidelity": holder.fidelity},
            cause=holder.incident_id,
        )
        return CORRECTED
    trust = await trust_row(ctx, holder.carrier_entity_id)
    loss = ctx.rules.rumours.contradiction_trust_loss
    with explaining():
        term("rules.rumours.contradiction_trust_loss", -loss, source_node_id=teller, source_incident_id=holder.incident_id)
        if HELD_TRUST not in trust.locked:
            trust.information_trust = clamp_int(trust.information_trust - loss, 0, PERCENT)
            trust.updated_epoch = ctx.epoch
        await record(
            ctx,
            "information.contradicted",
            roles={IncidentRole.SUBJECT: holder.carrier_entity_id, IncidentRole.TELLER: teller},
            facts={"happening": await happening_label(ctx.session, holder.incident_id), "differences": len(ahead ^ known), "trust_lost": loss},
            cause=holder.incident_id,
        )
    return CONTRADICTED


async def happening_label(session: AsyncSession, incident_id: int | None) -> str:
    if incident_id is None:
        return "an earlier happening"
    collection = await session.scalar(
        select(CollectionRow.name)
        .join(CollectionIncidentRow, CollectionIncidentRow.collection_id == CollectionRow.id)
        .where(CollectionIncidentRow.incident_id == incident_id)
        .order_by(CollectionRow.id)
        .limit(1)
    )
    if collection is not None:
        return f"the {collection}"
    incident = await session.get(IncidentRow, incident_id)
    return f"what happened in year {incident.year}" if incident is not None and incident.year is not None else "an earlier happening"


async def node_names(session: AsyncSession, ids: Iterable[int | None]) -> dict[int, str]:
    wanted = sorted({value for value in ids if value is not None})
    found: dict[int, str] = {}
    for start in range(0, len(wanted), LOAD_CHUNK):
        rows = await session.execute(select(NodeRow.id, NodeRow.name).where(NodeRow.id.in_(wanted[start : start + LOAD_CHUNK])))
        found.update({node: name for node, name in rows})
    return found


def told_facts(spec: IncidentKindSpec, told: Told, names: Mapping[int, str]) -> dict[str, object]:
    values: dict[str, list[object]] = defaultdict(list)
    for fact in sorted(told.facts, key=lambda item: (item.key, item.position)):
        if fact.node_id is not None:
            values[fact.key].append(names.get(fact.node_id, "someone"))
        elif fact.number is not None:
            values[fact.key].append(fact.number)
        elif fact.enum_value is not None:
            values[fact.key].append(fact_word(fact.enum_name, fact.enum_value))
        elif fact.name is not None:
            values[fact.key].append(fact.name)
    found: dict[str, object] = {}
    for key, items in values.items():
        declared = spec.fact(key)
        found[key] = items if declared is not None and declared.many else items[0]
    return found


async def told_text(session: AsyncSession, telling: Telling, distortions: Sequence[RumourDistortionRow]) -> str | None:
    spec = INCIDENT_KINDS.get(telling.incident.kind)
    if spec is None or not spec.told or not spec.template or telling.incident.tier is IncidentTier.LINE:
        return None
    told = told_version(telling, distortions)
    names = await node_names(session, [*(part.node_id for part in told.parts), *(fact.node_id for fact in told.facts)])
    roles: dict[IncidentRole, list[str]] = defaultdict(list)
    for part in sorted(told.parts, key=lambda item: item.position):
        roles[part.role].append(names.get(part.node_id, "someone"))
    try:
        return render_incident(spec, roles, told_facts(spec, told, names))
    except ValidationFailedError:
        return None
