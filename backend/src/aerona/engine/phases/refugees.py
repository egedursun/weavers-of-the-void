from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several, spoken
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction
from aerona.domain.enums.travel import RefugeeCause
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.drives import closeness
from aerona.engine.phase import Phase
from aerona.engine.phases.settlements import resettle_ruin
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import BondIndex, canon, connect, living_entity, spoken_language
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat
from aerona.engine.recording.record import StepDraft, record

SHELTER_TYPES = (EntityType.SETTLEMENT, EntityType.PEOPLE)
WAR_EVENT_KINDS = frozenset({EngineKind.WAR, EngineKind.BATTLE, EngineKind.SIEGE})
DISASTER_EVENT_KINDS = frozenset({EngineKind.EARTHQUAKE, EngineKind.FLOOD, EngineKind.PLAGUE, EngineKind.DROUGHT, EngineKind.STORM, EngineKind.FAMINE})


@dataclass(frozen=True)
class Exodus:
    origin: EntityRow
    refugees: int
    shelter: EntityRow | None
    rebuilt_ruin: bool


async def defeated_this_epoch(ctx: TickContext) -> set[int]:
    statement = (
        select(BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.role == BondRole.LOSER, BondRow.epoch == ctx.epoch, EntityRow.engine_kind.in_(list(WAR_EVENT_KINDS)))
    )
    return set(await ctx.session.scalars(statement))


async def disaster_sites(ctx: TickContext) -> set[int]:
    flagged = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.DISASTER)
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.EVENT,
        EntityRow.birth_epoch == ctx.epoch,
        (EntityRow.engine_kind.in_(list(DISASTER_EVENT_KINDS))) | (EntityRow.id.in_(flagged)),
    )
    sites: set[int] = set()
    for event in await ctx.session.scalars(statement):
        if (stat(event, "severity") or 0) < ctx.rules.deep_life.refugee_disaster_min_severity:
            continue
        bonds = await ctx.session.scalars(
            select(BondRow.target_node_id).where(BondRow.source_node_id == event.id, BondRow.kind == BondKind.CAUSED, BondRow.state == BondState.ACTIVE)
        )
        sites.update(bonds)
    return sites


async def shelter_score(ctx: TickContext, bonds: BondIndex, atlas: RegionAtlas, origin: EntityRow, host: EntityRow) -> float:
    life = ctx.rules.deep_life
    score = 0.0
    if bonds.between(origin.id, host.id, BondKind.ALLY):
        score += life.refugee_weight_ally
    origin_language = await spoken_language(ctx.session, origin.id)
    host_language = await spoken_language(ctx.session, host.id)
    if origin_language is not None and host_language is not None and origin_language.id == host_language.id:
        score += life.refugee_weight_language
    origin_god = await patron_node(ctx.session, origin)
    if origin_god is not None and origin_god == await patron_node(ctx.session, host):
        score += life.refugee_weight_god
    if not atlas.same_region(origin.id, host.id):
        score += life.refugee_weight_other_region
    score += await closeness(ctx.session, origin.id, host.id) * ctx.rules.culture_drift.refugee_kinship_weight
    return score


async def shelters(ctx: TickContext, atlas: RegionAtlas, bonds: BondIndex, origin: EntityRow, excluded: set[int]) -> list[EntityRow]:
    scored: list[tuple[float, int, EntityRow]] = []
    for host in await canon(ctx.session, SHELTER_TYPES, origin.world_id):
        if host.id == origin.id or host.id in excluded or bonds.between(origin.id, host.id, BondKind.ENEMY):
            continue
        if not atlas.adjacent(origin.id, host.id):
            continue
        scored.append((-await shelter_score(ctx, bonds, atlas, origin, host), host.id, host))
    return [host for _, _, host in sorted(scored, key=lambda item: (item[0], item[1]))]


async def flee(
    ctx: TickContext, atlas: RegionAtlas, origin: EntityRow, refugees: int, *, cause: RefugeeCause, destination: EntityRow | None, excluded: set[int]
) -> Exodus | None:
    bonds = await BondIndex.load(ctx.session, [BondKind.ALLY, BondKind.ENEMY])
    floor, cap = headcount_bounds(ctx.rules, origin)
    population = stat(origin, "population") or 0
    hosts = [destination] if destination is not None else await shelters(ctx, atlas, bonds, origin, excluded)
    if hosts:
        host = hosts[0]
        set_stats(origin, population=max(floor, population - refugees))
        host_floor, host_cap = headcount_bounds(ctx.rules, host)
        set_stats(host, population=min(host_cap, max(host_floor, (stat(host, "population") or 0) + refugees)))
        await connect(
            ctx.session, origin.id, host.id, BondKind.MIGRATED_TO, ctx.epoch, description=f"refugees ({spoken(cause)}): {several(refugees, 'person', 'people')}"
        )
        await record(
            ctx,
            "refugees.sheltered",
            roles={IncidentRole.ORIGIN: origin.id, IncidentRole.HOST: host.id},
            facts={"refugees": refugees, "cause_kind": cause},
            steps=(
                StepDraft(StepAction.LEAVE, actor=origin.id, amount=refugees, unit=FactUnit.PEOPLE),
                StepDraft(StepAction.ARRIVE, target=host.id, amount=refugees, unit=FactUnit.PEOPLE),
            ),
            place=host.id,
        )
        return Exodus(origin, refugees, host, False)
    region_id = atlas.top_region(origin.id)
    for neighbour_id in atlas.neighbour_regions(region_id) if region_id is not None else []:
        region = await living_entity(ctx.session, neighbour_id)
        if region is None:
            continue
        ruin = await resettle_ruin(ctx, region, origin, refugees, f"refugees fleeing {spoken(cause)} from {origin.name}", atlas=atlas)
        if ruin is None:
            continue
        set_stats(origin, population=max(floor, min(cap, population - refugees)))
        await connect(
            ctx.session, origin.id, ruin.id, BondKind.MIGRATED_TO, ctx.epoch, description=f"refugees ({spoken(cause)}): {several(refugees, 'person', 'people')}"
        )
        await record(
            ctx,
            "refugees.ruin",
            roles={IncidentRole.ORIGIN: origin.id, IncidentRole.PRODUCT: ruin.id},
            facts={"refugees": refugees, "cause_kind": cause},
            steps=(
                StepDraft(StepAction.LEAVE, actor=origin.id, amount=refugees, unit=FactUnit.PEOPLE),
                StepDraft(StepAction.ARRIVE, target=ruin.id),
                StepDraft(StepAction.SETTLE, target=ruin.id, amount=refugees, unit=FactUnit.PEOPLE),
            ),
            place=ruin.id,
        )
        return Exodus(origin, refugees, ruin, True)
    return None


@reads(
    "event.severity",
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.creator",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.incident_participants",
    "table.incidents",
    "table.node_births",
    "table.nodes",
    "table.sons",
    "table.stars",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
)
async def refugees(ctx: TickContext) -> None:
    rules = ctx.rules
    life = rules.deep_life
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    defeated = await defeated_this_epoch(ctx)
    sites = await disaster_sites(ctx)
    for community in await canon(ctx.session, SHELTER_TYPES):
        population = stat(community, "population") or 0
        if community.status is not EntityStatus.CANON or population < life.refugee_min_population:
            continue
        struck = {community.id, community.location_id, atlas.top_region(community.id)} & sites
        cause = RefugeeCause.WAR if community.id in defeated else RefugeeCause.DISASTER if struck else None
        if cause is None or not rng.chance(rules.deep_world.refugee_chance):
            continue
        count = round_half_up(population * rules.deep_world.refugee_share_pct / PERCENT)
        if count < life.refugee_min_people:
            continue
        await flee(ctx, atlas, community, count, cause=cause, destination=None, excluded=defeated)


async def order_exodus(ctx: TickContext, origin_id: int, share_pct: int, destination_id: int | None = None) -> Exodus:
    origin = await living_entity(ctx.session, origin_id)
    if origin is None or origin.entity_type not in SHELTER_TYPES:
        raise ValidationFailedError("Only a living people or settlement can be sent into exodus.")
    if not 0 < share_pct <= PERCENT:
        raise ValidationFailedError(f"The exodus share must be between 1 and {PERCENT} percent.")
    destination = await living_entity(ctx.session, destination_id) if destination_id is not None else None
    if destination_id is not None and (destination is None or destination.entity_type not in SHELTER_TYPES or destination.id == origin.id):
        raise ValidationFailedError("Refugees can only shelter in another living people or settlement.")
    count = round_half_up((stat(origin, "population") or 0) * share_pct / PERCENT)
    if count <= 0:
        raise ValidationFailedError("No one is left to leave.")
    exodus = await flee(ctx, await RegionAtlas.load(ctx.session), origin, count, cause=RefugeeCause.DECREE, destination=destination, excluded=set())
    if exodus is None:
        raise ValidationFailedError(f"{origin.name} has nowhere to flee.")
    return exodus


PHASES = (Phase("refugees", refugees),)
