from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.domestication import UNBOUND_BIOCHEMISTRY
from aerona.catalog.life.limit_ways import LIMIT_WAYS
from aerona.catalog.life_traits import BODY_SYSTEM_TRAITS, having
from aerona.catalog.nature_kinds50 import BODY_SYSTEMS, SENSITIVITIES
from aerona.constants.units import PERCENT
from aerona.db.tables.arcana import RiteGrammarRow
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.body_systems import BodySystemRow, SensitivityRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.kind_crafts import GarmentKindRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.made import AugmentRow
from aerona.db.tables.powers import PowerRow
from aerona.db.tables.space_weather import WorldFieldRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.body_systems import BodySystem, LimitWay
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.kind_crafts import GarmentCategory
from aerona.domain.enums.kinds import KindConcept
from aerona.domain.enums.life_traits import BodySystemTrait
from aerona.domain.enums.made import AugmentSlot
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepState
from aerona.engine.body.customs import people_of
from aerona.engine.body.hits import Harm
from aerona.engine.body.tolerance import Ground, excess, ground_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_views import light_pct, view_of
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import folk_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.recording.terms import explaining_alone, term
from aerona.rules.registry import Rules

BLOODLESS = having(BODY_SYSTEM_TRAITS, BodySystemTrait.BLOODLESS)
SYSTEMS = tuple(system for system in BodySystem if system is not BodySystem.NONE)
TENTHS = 10


@dataclass
class BodySystemTally:
    seeded: int = 0
    strained: int = 0
    failed: int = 0
    recovered: int = 0
    adapted: int = 0
    reactions: int = 0


def adapt(rules: Rules, row: BodySystemRow, ground: Ground) -> bool:
    step = rules.body_systems.adaptation_per_epoch
    moved = False
    for column, target, upward in (
        ("gravity_max", ground.gravity, True),
        ("heat_max", ground.warmth, True),
        ("toxin_tolerance", ground.toxins, True),
        ("radiation_max", ground.radiation, True),
        ("light_min", ground.light, False),
        ("cold_min", ground.warmth, False),
        ("air_need", ground.air, False),
    ):
        value = getattr(row, column)
        behind = value < target if upward else value > target
        if column in row.locked or not behind:
            continue
        setattr(row, column, clamp_int(value + (step if upward else -step), 0, PERCENT))
        moved = True
    return moved


async def seed(ctx: TickContext, holder: EntityRow, biology: BiologyRow, tally: BodySystemTally) -> list[BodySystemRow]:
    rows = list(await ctx.session.scalars(select(BodySystemRow).where(BodySystemRow.holder_entity_id == holder.id).order_by(BodySystemRow.id)))
    if rows:
        return rows
    world = await ctx.session.get(WorldRow, holder.world_id) if holder.world_id is not None else None
    if world is None:
        return []
    margin = ctx.rules.body_systems.margin
    ground = ground_of(world, None)
    profile = await ctx.session.get(SpeciesProfileRow, holder.id)
    unbound = profile is not None and profile.biochemistry in UNBOUND_BIOCHEMISTRY
    for system in SYSTEMS:
        present = not (system is BodySystem.BREATH and not biology.breathes) and not (unbound and system in BLOODLESS)
        row = BodySystemRow(
            holder_entity_id=holder.id,
            system=system,
            present=present,
            air_need=clamp_int(ground.air - margin, 0, PERCENT),
            gravity_max=clamp_int(ground.gravity + margin, 0, PERCENT),
            cold_min=clamp_int(ground.warmth - margin * 2, 0, PERCENT),
            heat_max=clamp_int(ground.warmth + margin * 2, 0, PERCENT),
            sleep_need=PERCENT * 3 // TENTHS if biology.sleeps else 0,
            toxin_tolerance=clamp_int(ground.toxins + margin, 0, PERCENT),
            radiation_max=clamp_int(ground.radiation + margin, 0, PERCENT),
            light_min=clamp_int(ground.light - margin * 2, 0, PERCENT),
            humidity_range=clamp_int(abs(ground.humidity - PERCENT // 2) * 2 + margin * 2, 0, PERCENT),
            locked=[],
        )
        ctx.session.add(row)
        rows.append(row)
    tally.seeded += 1
    return rows


async def ways_past(ctx: TickContext, people_id: int) -> list[LimitWay]:
    among = await folk_among(ctx.session, [people_id])
    folk = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, among)
    found: list[LimitWay] = []
    suits = await ctx.session.scalar(
        select(KindHoldingRow.id)
        .join(GarmentKindRow, GarmentKindRow.id == KindHoldingRow.kind_id)
        .where(
            KindHoldingRow.concept == KindConcept.GARMENT,
            KindHoldingRow.holder_node_id == people_id,
            GarmentKindRow.category == GarmentCategory.ENVIRONMENT_SUIT,
        )
        .limit(1)
    )
    if suits is not None:
        found.append(LimitWay.EQUIPMENT)
    augments = set(await ctx.session.scalars(select(AugmentRow.slot).where(AugmentRow.bearer_node_id.in_(folk))))
    if augments - {AugmentSlot.BLOOD, AugmentSlot.WHOLE_BODY}:
        found.append(LimitWay.AUGMENT)
    if augments & {AugmentSlot.BLOOD, AugmentSlot.WHOLE_BODY}:
        found.append(LimitWay.GROWN_ORGAN)
    if await ctx.session.scalar(select(PowerRow.id).where(PowerRow.holder_node_id.in_(folk)).limit(1)) is not None:
        found.append(LimitWay.POWER)
    rites = select(RiteGrammarRow.rite_entity_id).join(EntityRow, EntityRow.id == RiteGrammarRow.rite_entity_id).where(among)
    if await ctx.session.scalar(rites.limit(1)) is not None:
        found.append(LimitWay.RITE)
    return found


async def eased(ctx: TickContext, people: EntityRow, town: EntityRow, worst: int) -> int:
    if worst <= 0:
        return worst
    ways = await ways_past(ctx, people.id)
    if not ways:
        return worst
    ease = min(PERCENT, sum(LIMIT_WAYS[way].ease(ctx.rules) for way in ways))
    cost = sum(LIMIT_WAYS[way].cost(ctx.rules) for way in ways)
    if not held(town.id):
        with explaining_alone():
            term("body_systems.limit_way_cost", -cost, source_node_id=people.id)
            shift_stat(town, "prosperity", -cost, low=0, high=PERCENT)
    return worst * (PERCENT - ease) // PERCENT


async def strain(ctx: TickContext, folk: tuple[EntityRow, list[BodySystemRow]], town: EntityRow, ground: Ground, tally: BodySystemTally) -> None:
    people, rows = folk
    table = ctx.rules.body_systems
    worst = await eased(ctx, people, town, max((excess(row, ground) for row in rows if BODY_SYSTEMS[row.system].worn), default=0))
    structure = next((row for row in rows if row.system is BodySystem.STRUCTURE and row.present), None)
    light = structure is not None and ground.gravity < structure.gravity_max - table.margin * 2
    if (worst > 0 or light) and not held(town.id):
        loss = worst // TENTHS * table.tolerance_harm_per_point + (table.low_gravity_wear if light else 0)
        if loss > 0:
            with explaining_alone():
                term("body_systems.strain", -loss, source_node_id=people.id)
                shift_stat(town, "prosperity", -loss, low=0, high=PERCENT)
    for row in rows:
        if not BODY_SYSTEMS[row.system].worn or held(people.id):
            continue
        over = excess(row, ground)
        roles = {IncidentRole.SUBJECT: people.id, IncidentRole.PLACE: town.id}
        if over > 0 and not row.strained:
            row.strained = True
            tally.strained += 1
            await record(ctx, "body.tolerance_exceeded", roles=roles, facts={"system": row.system, "excess": over}, place=town.id)
        if over >= table.system_loss_capacity_pct and not row.failed:
            row.failed = True
            tally.failed += 1
            await record(ctx, "body.system_failed", roles=roles, facts={"system": row.system, "excess": over}, place=town.id)
        if over == 0 and row.strained:
            row.strained = False
            key = "body.system_recovered" if row.failed else "body.adapted"
            row.failed = False
            tally.recovered += 1
            await record(ctx, key, roles=roles, facts={"system": row.system, "excess": over}, place=town.id)
        if people.world_id == town.world_id and adapt(ctx.rules, row, ground):
            tally.adapted += 1


async def react(ctx: TickContext, tally: BodySystemTally) -> None:
    table = ctx.rules.body_systems
    for row in list(await ctx.session.scalars(select(SensitivityRow).where(SensitivityRow.trigger_commodity.is_not(None)).order_by(SensitivityRow.id))):
        if not SENSITIVITIES[row.kind].by_goods:
            continue
        being = await ctx.session.get(EntityRow, row.holder_entity_id)
        if being is None or being.status is not EntityStatus.CANON or held(being.id) or being.location_id is None:
            continue
        stock = await ctx.session.scalar(
            select(CommunityStockRow.id)
            .where(
                CommunityStockRow.community_entity_id == being.location_id, CommunityStockRow.commodity == row.trigger_commodity, CommunityStockRow.quantity > 0
            )
            .limit(1)
        )
        if stock is None or not ctx.rng(seed_of("sensitivity", row.id, ctx.epoch)).chance(table.sensitivity_reaction_pct):
            continue
        tally.reactions += 1
        await apply_hits(ctx, being, Harm(max(1, row.severity // TENTHS), HarmCause.POISON, "struck down by what its body cannot bear"), lethal=False)
        await record(
            ctx,
            "body.sensitivity_reaction",
            roles={IncidentRole.SUBJECT: being.id},
            facts={"sensitivity": row.kind, "severity": row.severity},
            steps=(StepDraft(StepAction.FALL_ILL, actor=being.id, states=((being.id, StepState.POISONED),)),),
        )


async def keep_body_systems(ctx: TickContext, tally: BodySystemTally) -> None:
    holders: dict[int, list[BodySystemRow]] = {}
    for biology in list(await ctx.session.scalars(select(BiologyRow).order_by(BiologyRow.holder_entity_id))):
        holder = await ctx.session.get(EntityRow, biology.holder_entity_id)
        if holder is None or holder.status is not EntityStatus.CANON or held(holder.id):
            continue
        holders[holder.id] = await seed(ctx, holder, biology, tally)
    atlas = await RegionAtlas.load(ctx.session)
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        people = await people_of(ctx.session, town)
        rows = holders.get(people.id, []) if people is not None else []
        world = await ctx.session.get(WorldRow, town.world_id) if town.world_id is not None else None
        if people is None or not rows or world is None:
            continue
        region = atlas.top_region(town.id)
        land = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
        field = await ctx.session.get(WorldFieldRow, world.id)
        light = light_pct(ctx.rules, (await view_of(ctx.session, ctx.rules, world.id)).light)
        await strain(ctx, (people, rows), town, ground_of(world, land, radiation=field.surface_dose if field is not None else 0, light=light), tally)
    await react(ctx, tally)
    await ctx.session.flush()
