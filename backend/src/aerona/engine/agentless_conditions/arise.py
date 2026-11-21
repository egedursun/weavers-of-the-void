from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.agentless_conditions import AgentlessConditionRow
from aerona.db.tables.body import SEVERITY_MAX, ConditionRow, InjuryRow
from aerona.db.tables.body_systems import BodySystemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.agentless_conditions import ConditionCause
from aerona.domain.enums.body_systems import BodySystem
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ThoughtKind
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.agentless_conditions.catalogue import SOURCES, SYSTEMS
from aerona.engine.body.conditions import CONDITION_KEY
from aerona.engine.body.customs import people_of
from aerona.engine.body.state import refresh
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import blocked
from aerona.engine.mind.thoughts import think
from aerona.engine.nature.seasons import region_of
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record

C = ConditionCause
FOULING_PARTS = 3


@dataclass
class ConditionTally:
    arose: int = 0
    worsened: int = 0
    eased: int = 0
    seeded: int = 0


@dataclass
class Ground:
    kinds: list[AgentlessConditionRow]
    borne: dict[int, set[int]]
    parents: dict[int, list[int]]
    stress: dict[int, int]
    wounded: set[int]
    systems: dict[int, frozenset[BodySystem]] = field(default_factory=dict)
    fouling: dict[int | None, int] = field(default_factory=dict)


async def ground_of(ctx: TickContext) -> Ground:
    session = ctx.session
    kinds = list(await session.scalars(select(AgentlessConditionRow).order_by(AgentlessConditionRow.id)))
    borne: dict[int, set[int]] = defaultdict(set)
    for bearer, kind in await session.execute(
        select(ConditionRow.bearer_node_id, ConditionRow.kind_id).where(ConditionRow.ended_epoch.is_(None), ConditionRow.kind_id.is_not(None))
    ):
        if kind is not None:
            borne[bearer].add(kind)
    parents: dict[int, list[int]] = defaultdict(list)
    for bond in await active_bonds(session, [BondKind.PARENT_OF]):
        parents[bond.target_node_id].append(bond.source_node_id)
    stress = {row.entity_id: row.stress for row in await session.scalars(select(MortalProfileRow))}
    floor = ctx.rules.agentless_conditions.aftermath_severity
    healed = select(InjuryRow.bearer_node_id).where(InjuryRow.healed_epoch == ctx.epoch, InjuryRow.severity >= floor)
    return Ground(kinds, borne, parents, stress, set(await session.scalars(healed)))


async def systems_of(ctx: TickContext, ground: Ground, being: EntityRow) -> frozenset[BodySystem]:
    people = await people_of(ctx.session, being)
    key = people.id if people is not None else 0
    if key not in ground.systems:
        rows = list(await ctx.session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == key))) if people is not None else []
        ground.systems[key] = frozenset(row.system for row in rows if row.present) if rows else frozenset(SYSTEMS)
    return ground.systems[key]


async def fouling_at(ctx: TickContext, ground: Ground, place_id: int | None) -> int:
    region = await region_of(ctx.session, place_id)
    if region not in ground.fouling:
        row = await ctx.session.get(RegionPollutionRow, region) if region is not None else None
        ground.fouling[region] = (row.air + row.water + row.soil) // FOULING_PARTS if row is not None else 0
    return ground.fouling[region]


async def want_at(ctx: TickContext, place_id: int | None) -> float:
    place = await ctx.session.get(EntityRow, place_id) if place_id is not None else None
    return (PERCENT - stat_or(place, "prosperity", PERCENT // 2)) / PERCENT if place is not None else 0.5


async def chances(ctx: TickContext, ground: Ground, being: EntityRow) -> dict[ConditionCause, float]:
    table = ctx.rules.agentless_conditions
    age, span = stat_or(being, "age", 0), max(1, stat_or(being, "lifespan", 70))
    heritable = {kind.id for kind in ground.kinds if kind.cause is C.HEREDITY}
    inherited = sum(1 for parent in ground.parents.get(being.id, []) if heritable & ground.borne.get(parent, set()))
    strain = max(0, ground.stress.get(being.id, 0) - table.strain_floor) / max(1, PERCENT - table.strain_floor)
    return {
        C.AGE: table.age_rate_pct * min(1.0, age / span),
        C.DIET: table.diet_rate_pct * await want_at(ctx, being.location_id),
        C.EXPOSURE: table.exposure_rate_pct * await fouling_at(ctx, ground, being.location_id) / PERCENT,
        C.HEREDITY: table.heredity_weight_pct * inherited,
        C.INJURY_AFTERMATH: table.aftermath_rate_pct if being.id in ground.wounded else 0,
        C.STRAIN: table.strain_rate_pct * strain,
        C.UNKNOWN: table.unknown_rate_pct,
    }


def eligible(ground: Ground, being: EntityRow, cause: ConditionCause, systems: frozenset[BodySystem]) -> list[AgentlessConditionRow]:
    age, span = stat_or(being, "age", 0), max(1, stat_or(being, "lifespan", 70))
    world = being.world_id
    borne = ground.borne.get(being.id, set())
    if cause is C.HEREDITY:
        lines = {kind for parent in ground.parents.get(being.id, []) for kind in ground.borne.get(parent, set())}
        pool = [kind for kind in ground.kinds if kind.id in lines and kind.cause is C.HEREDITY]
    else:
        causes = {cause, C.HEREDITY} if cause is C.UNKNOWN else {cause}
        pool = [kind for kind in ground.kinds if kind.cause in causes]
    return [kind for kind in pool if kind.system in systems and kind.world_id == world and kind.id not in borne and age * PERCENT >= kind.onset_pct * span]


async def arise(ctx: TickContext, being: EntityRow, kind: AgentlessConditionRow, tally: ConditionTally, *, cause: ConditionCause | None = None) -> ConditionRow:
    row = ConditionRow(
        bearer_node_id=being.id,
        kind=kind.manifests,
        severity=min(SEVERITY_MAX, kind.severity),
        source=SOURCES[cause or kind.cause],
        since_epoch=ctx.epoch,
        visible=False,
        cause=cause or kind.cause,
        kind_id=kind.id,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await refresh(ctx.session, ctx.rules, being, ctx.epoch)
    await think(ctx.session, ctx.rules, being.id, ThoughtKind.FELL_ILL, ctx.epoch)
    await record(
        ctx,
        "body.condition_arose",
        roles={IncidentRole.SUBJECT: being.id},
        facts={"condition": kind.name, "cause": row.cause, "system": kind.system, "severity": row.severity},
        place=being.location_id,
    )
    tally.arose += 1
    return row


async def bodies(ctx: TickContext) -> list[EntityRow]:
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    made = set(await ctx.session.scalars(select(MindProfileRow.node_id).where(MindProfileRow.origin == MindOrigin.MADE)))
    return [being for being in await ctx.session.scalars(query) if being.id not in made and not held(being.id) and not blocked(being.id, CONDITION_KEY)]


async def roll_conditions(ctx: TickContext, tally: ConditionTally) -> None:
    ground = await ground_of(ctx)
    if not ground.kinds:
        return
    for being in await bodies(ctx):
        systems = await systems_of(ctx, ground, being)
        if not systems:
            continue
        rng = ctx.rng(f"agentless.{being.id}.{ctx.epoch}")
        for cause, chance in (await chances(ctx, ground, being)).items():
            if chance <= 0 or not rng.chance(chance):
                continue
            pool = eligible(ground, being, cause, systems)
            if pool:
                kind = rng.weighted_by(pool, lambda option: option.weight)
                await arise(ctx, being, kind, tally, cause=cause if cause is not C.UNKNOWN else kind.cause if kind.cause is C.HEREDITY else C.UNKNOWN)
                ground.borne[being.id].add(kind.id)
