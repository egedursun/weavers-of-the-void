from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.power_costs import POWER_COSTS
from aerona.catalog.life.powers import RENEWAL_KINDS
from aerona.catalog.life_traits import SOURCE_LOCUS_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.powers import (
    PowerRow,
    PowerSourceCostRow,
    PowerSourceHazardRow,
    PowerSourceInteractionRow,
    PowerSourceKnowledgeRow,
    PowerSourceResistanceRow,
    PowerSourceRow,
    SourceDensityRow,
    SourceLawRow,
    SourceTideRow,
)
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.life_traits import SourceLocusTrait
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.powers import (
    PowerCost,
    PowerHazard,
    ResistanceKind,
    SourceLawLevel,
    SourceRelation,
)
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.dominion.book import DominionBook
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.faith.book import patron_node
from aerona.engine.fortune.profiles import shift_fortune
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.standing import add_infamy, add_renown
from aerona.engine.polity.laws import law_param
from aerona.engine.powers.kinds import locus_factor, tide_wave
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record

LAND_LOCI = having(SOURCE_LOCUS_TRAITS, SourceLocusTrait.LAND_LOCI)


async def costs_of(session: AsyncSession, source_id: int) -> list[PowerSourceCostRow]:
    return list(await session.scalars(select(PowerSourceCostRow).where(PowerSourceCostRow.source_id == source_id).order_by(PowerSourceCostRow.id)))


async def resistances_of(session: AsyncSession, source_id: int) -> list[ResistanceKind]:
    rows = await session.scalars(select(PowerSourceResistanceRow.resistance).where(PowerSourceResistanceRow.source_id == source_id))
    return list(rows)


async def density_row(ctx: TickContext, source: PowerSourceRow, region_id: int) -> SourceDensityRow:
    row = await ctx.session.scalar(select(SourceDensityRow).where(SourceDensityRow.region_entity_id == region_id, SourceDensityRow.source_id == source.id))
    if row is not None:
        return row
    start = ctx.rules.power_sources.start_density
    row = SourceDensityRow(region_entity_id=region_id, source_id=source.id, density=start, base_density=start, renewal_pct=10, depleted=False, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def tide_factor(ctx: TickContext, source_id: int) -> float:
    factor = 1.0
    for tide in await ctx.session.scalars(select(SourceTideRow).where(SourceTideRow.source_id == source_id)):
        wave = tide_wave(ctx.epoch, tide, ctx.rules.power_sources.sky_days)
        factor *= 1 + wave * tide.amplitude / PERCENT * ctx.rules.power_sources.tide_pct / PERCENT
    return max(0.0, factor)


async def interaction_factor(ctx: TickContext, source_id: int, region_id: int | None) -> float:
    if region_id is None:
        return 1.0
    drawn_here = select(SourceDensityRow.source_id).where(SourceDensityRow.region_entity_id == region_id, SourceDensityRow.last_drawn_epoch == ctx.epoch)
    factor = 1.0
    rows = await ctx.session.scalars(
        select(PowerSourceInteractionRow).where(
            PowerSourceInteractionRow.second_source_id == source_id, PowerSourceInteractionRow.first_source_id.in_(drawn_here)
        )
    )
    for row in rows:
        share = row.strength / PERCENT * ctx.rules.power_sources.interaction_pct / PERCENT
        if row.relation is SourceRelation.AMPLIFIES:
            factor *= 1 + share
        elif row.relation is SourceRelation.CONVERTS_INTO:
            await convert(ctx, row.first_source_id, source_id, region_id, row.strength)
        elif row.relation in {SourceRelation.SUPPRESSES, SourceRelation.CONFLICTS}:
            factor *= max(0.0, 1 - share)
    return factor


async def convert(ctx: TickContext, first_id: int, second_id: int, region_id: int, strength: int) -> None:
    taken = await ctx.session.scalar(select(SourceDensityRow).where(SourceDensityRow.source_id == first_id, SourceDensityRow.region_entity_id == region_id))
    given = await ctx.session.scalar(select(SourceDensityRow).where(SourceDensityRow.source_id == second_id, SourceDensityRow.region_entity_id == region_id))
    if taken is None or given is None or held(region_id) or "density" in taken.locked or "density" in given.locked:
        return
    moved = min(taken.density, strength * ctx.rules.power_sources.interaction_pct // PERCENT // 4 + 1)
    taken.density -= moved
    given.density = clamp_int(given.density + moved, 0, max(given.base_density, given.density + moved))


async def source_level(session: AsyncSession, holder_id: int, community_id: int | None, polity_id: int | None, source_id: int) -> SourceLawLevel:
    if polity_id is not None:
        named = await session.scalar(select(SourceLawRow.level).where(SourceLawRow.polity_entity_id == polity_id, SourceLawRow.source_id == source_id))
        if named is not None:
            return named
    place = community_id if community_id is not None else holder_id
    level = await law_param(session, place, LawKind.SOURCE_LAW, "level")
    return SourceLawLevel(str(level)) if level is not None and str(level) in SourceLawLevel else SourceLawLevel.FREE


async def polity_of(session: AsyncSession, town_id: int | None) -> int | None:
    if town_id is None:
        return None
    found: int | None = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).limit(1))
    return found


async def pay_costs(ctx: TickContext, user: EntityRow, source_id: int, strength: int) -> None:
    for cost in await costs_of(ctx.session, source_id):
        amount = max(1, strength * cost.weight // PERCENT)
        spec = POWER_COSTS[cost.cost]
        if spec.mortals_only and user.entity_type is not EntityType.MORTAL:
            continue
        await take_cost(ctx, user, spec.draws, amount)


async def take_cost(ctx: TickContext, user: EntityRow, draws: str, amount: int) -> None:
    if draws in PROFILE_DRAWS:
        await burden(ctx, user, draws, amount * PROFILE_DRAWS[draws])
    elif draws == "age":
        shift_stat(user, "age", amount // 2 or 1, 0)
    elif draws == "wealth":
        if await points_of(ctx.session, user) > 0:
            await shift_points(ctx.session, user, -amount)
    elif draws in STANDING_DRAWS:
        await STANDING_DRAWS[draws](ctx.session, user.id, -amount if draws == "renown" else amount, ctx.epoch, rules=ctx.rules)
    elif draws == "mutation" and not held(user.id):
        await add_flag(ctx.session, user.id, EntityFlag.MUTATED, ctx.epoch)
    elif draws == "fortune" and not held(user.id):
        await shift_fortune(ctx, user.id, -amount)
    elif draws == "patron":
        await patron_pays(ctx, user, amount)
    elif draws == "souls":
        await draw_souls(ctx, user, amount)
    elif draws == "surroundings" and user.location_id is not None:
        town = await ctx.session.get(EntityRow, user.location_id)
        if town is not None and town.entity_type is EntityType.SETTLEMENT and not held(town.id):
            shift_stat(town, "prosperity", -amount, 0)


async def burden(ctx: TickContext, user: EntityRow, column: str, delta: int) -> None:
    profile = await ctx.session.get(MortalProfileRow, user.id)
    if profile is not None and column not in (profile.locked or []):
        setattr(profile, column, clamp_percent(getattr(profile, column) + delta))


PROFILE_DRAWS = {"stress": 1, "fertility": -1}
STANDING_DRAWS = {"renown": add_renown, "regard": add_infamy}


async def patron_of_user(ctx: TickContext, user: EntityRow) -> int | None:
    found = await patron_node(ctx.session, user.id)
    if found is None and user.location_id is not None:
        found = await patron_node(ctx.session, user.location_id)
    return found


async def patron_purse(ctx: TickContext, user: EntityRow) -> tuple[SonRow | None, ForeignGodRow | None]:
    patron = await patron_of_user(ctx, user)
    if patron is None:
        return None, None
    return await ctx.session.get(SonRow, patron), await ctx.session.get(ForeignGodRow, patron)


async def patron_can_pay(ctx: TickContext, user: EntityRow, amount: int) -> bool:
    son, god = await patron_purse(ctx, user)
    return (son is not None and son.essence >= amount) or (god is not None and god.faith >= amount)


async def patron_pays(ctx: TickContext, user: EntityRow, amount: int) -> bool:
    son, god = await patron_purse(ctx, user)
    if son is not None and son.essence >= amount and not held(son.id):
        son.essence -= amount
        return True
    if god is not None and god.faith >= amount and not held(god.id):
        god.faith -= amount
        return True
    return False


async def patron_short(ctx: TickContext, user: EntityRow, source_id: int, strength: int) -> str | None:
    for cost in await costs_of(ctx.session, source_id):
        if POWER_COSTS[cost.cost].draws == "patron" and not await patron_can_pay(ctx, user, max(1, strength * cost.weight // PERCENT)):
            return "no god stands behind this working with power enough to pay for it"
    return None


async def draw_souls(ctx: TickContext, user: EntityRow, amount: int) -> int:
    if user.location_id is None:
        return 0
    table = ctx.rules.power_sources
    drawn = list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(await present_among(ctx.session, [user.location_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.id != user.id)
            .order_by(EntityRow.id)
            .limit(table.soul_draw_beings)
        )
    )
    beings = [being for being in drawn if not held(being.id)]
    if not beings:
        return 0
    share = max(1, amount * table.soul_draw_pct // PERCENT // len(beings))
    for being in beings:
        reason = f"had life drawn out of them by the working of {user.name}"
        await apply_hits(ctx, being, Harm(share, HarmCause.POWER, reason, damage_type=DamageType.MAGIC), lethal=False)
    return len(beings)


async def drawn_from_land(ctx: TickContext, user: EntityRow, source: PowerSourceRow, strength: int) -> float:
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(user.id)
    factor = await tide_factor(ctx, source.id) * await interaction_factor(ctx, source.id, region) * await locus_factor(ctx, user, source.drawn_from)
    if region is None or source.drawn_from not in LAND_LOCI:
        return factor
    row = await density_row(ctx, source, region)
    factor *= row.density / max(1, row.base_density) if row.base_density else 0.0
    if not held(region) and "density" not in row.locked:
        row.density = clamp_percent(row.density - strength * ctx.rules.power_sources.draw_per_strength)
        row.last_drawn_epoch = ctx.epoch
    return factor


async def rite_draw(ctx: TickContext, caster: EntityRow, source: MagicSource, power: int) -> float:
    row = await ctx.session.scalar(select(PowerSourceRow).where(PowerSourceRow.built_in == source).limit(1))
    return await drawn_from_land(ctx, caster, row, power) if row is not None else 1.0


async def draw(ctx: TickContext, user: EntityRow, source: PowerSourceRow, strength: int) -> float:
    factor = await drawn_from_land(ctx, user, source, strength)
    await pay_costs(ctx, user, source.id, strength)
    return factor


async def hazard_of(ctx: TickContext, user: EntityRow, source: PowerSourceRow) -> PowerHazard | None:
    rng = ctx.rng(f"source.hazard.{source.id}.{user.id}.{ctx.epoch}")
    for hazard in await ctx.session.scalars(select(PowerSourceHazardRow).where(PowerSourceHazardRow.source_id == source.id).order_by(PowerSourceHazardRow.id)):
        if rng.chance(hazard.weight * ctx.rules.power_sources.hazard_scale_pct / PERCENT):
            return hazard.hazard
    return None


async def renew(ctx: TickContext, row: SourceDensityRow, source: PowerSourceRow) -> None:
    table = ctx.rules.power_sources
    kind = RENEWAL_KINDS.get(source.renewal)
    if kind is None or "density" in row.locked:
        return
    if kind == "rest":
        gain = table.rest_renewal
    elif kind == "season":
        gain = round(table.season_renewal * await tide_factor(ctx, source.id))
    elif kind == "taking":
        users = await ctx.session.scalar(
            select(func.count()).select_from(PowerRow).where(PowerRow.source_id == source.id, PowerRow.last_used_epoch == ctx.epoch)
        )
        gain = table.taking_renewal * int(users or 0)
    elif kind == "offering":
        shrines = await ctx.session.scalar(
            select(func.count())
            .select_from(EntityRow)
            .where(EntityRow.location_id == row.region_entity_id, EntityRow.engine_kind == EngineKind.TEMPLE, EntityRow.status == EntityStatus.CANON)
        )
        gain = table.offering_renewal * int(shrines or 0)
    else:
        dominion = max(0, (await DominionBook.load(ctx.session)).scale_at(ctx.rules, row.region_entity_id, DivineScale.MAGIC))
        cults = await ctx.session.scalar(
            select(func.count()).select_from(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.location_id == row.region_entity_id)
        )
        gain = table.worship_renewal * (int(cults or 0) + dominion)
    row.density = clamp_int(row.density + gain, 0, row.base_density)


async def deplete(ctx: TickContext, row: SourceDensityRow, source: PowerSourceRow) -> None:
    table = ctx.rules.power_sources
    was = row.depleted
    row.depleted = row.density < table.density_floor
    if not row.depleted:
        return
    if not was:
        await record(ctx, "source.depleted", roles={IncidentRole.SUBJECT: row.region_entity_id}, facts={"source": source.name})
    if not await surroundings_cost(ctx, source.id):
        return
    towns = await ctx.session.scalars(
        select(EntityRow).where(
            EntityRow.location_id == row.region_entity_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON
        )
    )
    for town in list(towns):
        if not held(town.id):
            shift_stat(town, "prosperity", -table.depletion_prosperity, 0)


async def drawers_in(ctx: TickContext, source_id: int, region_id: int) -> list[int]:
    here = select(EntityRow.id).where(
        or_(EntityRow.location_id == region_id, EntityRow.location_id.in_(select(EntityRow.id).where(EntityRow.location_id == region_id)))
    )
    users = select(PowerRow.holder_node_id).where(PowerRow.source_id == source_id, PowerRow.last_used_epoch >= ctx.epoch - 1, PowerRow.holder_node_id.in_(here))
    return sorted(set(await ctx.session.scalars(users)))


async def contend(ctx: TickContext, row: SourceDensityRow, source: PowerSourceRow) -> int:
    table = ctx.rules.power_sources
    if not row.depleted or "density" in row.locked:
        return 0
    drawers = [holder for holder in await drawers_in(ctx, source.id, row.region_entity_id) if not held(holder)]
    if len(drawers) < 2:
        return 0
    row.density = clamp_int(row.density - table.contention_draw * (len(drawers) - 1), 0, row.base_density)
    pairs = [(first, second) for index, first in enumerate(drawers) for second in drawers[index + 1 :]][: table.contention_rivals]
    for first, second in pairs:
        for holder, other in ((first, second), (second, first)):
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=holder,
                subject_id=other,
                kind=MemoryKind.ENVIED,
                magnitude=-table.contention_draw,
                epoch=ctx.epoch,
                note=f"drew on {source.name} where it ran thin",
            )
    return len(pairs)


async def surroundings_cost(ctx: TickContext, source_id: int) -> bool:
    found = await ctx.session.scalar(
        select(PowerSourceCostRow.id).where(PowerSourceCostRow.source_id == source_id, PowerSourceCostRow.cost == PowerCost.SURROUNDINGS)
    )
    return found is not None


async def keep_density(ctx: TickContext) -> int:
    kept = 0
    sources = {row.id: row for row in await ctx.session.scalars(select(PowerSourceRow))}
    for row in list(await ctx.session.scalars(select(SourceDensityRow).order_by(SourceDensityRow.id))):
        source = sources.get(row.source_id)
        if source is None or held(row.region_entity_id):
            continue
        await renew(ctx, row, source)
        await deplete(ctx, row, source)
        ctx.count("source_rivalries", await contend(ctx, row, source))
        kept += 1
    return kept


async def know(ctx: TickContext, source_id: int, holder_id: int, gain: int) -> PowerSourceKnowledgeRow:
    row = await ctx.session.scalar(
        select(PowerSourceKnowledgeRow).where(PowerSourceKnowledgeRow.source_id == source_id, PowerSourceKnowledgeRow.holder_node_id == holder_id)
    )
    if row is None:
        row = PowerSourceKnowledgeRow(source_id=source_id, holder_node_id=holder_id, level=0, learned_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if "level" not in row.locked:
        row.level = clamp_percent(row.level + gain)
    await ctx.session.flush()
    return row


async def knows_source(session: AsyncSession, holder_ids: list[int], source: PowerSourceRow) -> bool:
    if source.built_in is not None:
        return True
    found = await session.scalar(
        select(PowerSourceKnowledgeRow.id).where(
            PowerSourceKnowledgeRow.source_id == source.id, PowerSourceKnowledgeRow.holder_node_id.in_(holder_ids), PowerSourceKnowledgeRow.level > 0
        )
    )
    return found is not None


async def keep_knowledge(ctx: TickContext) -> int:
    table = ctx.rules.power_sources
    changed = 0
    users = set(await ctx.session.scalars(select(PowerRow.source_id).where(PowerRow.source_id.is_not(None))))
    for row in list(await ctx.session.scalars(select(PowerSourceKnowledgeRow).order_by(PowerSourceKnowledgeRow.id))):
        if held(row.holder_node_id) or "level" in row.locked:
            continue
        if row.source_id not in users:
            row.level = clamp_percent(row.level - table.knowledge_loss)
            changed += 1
    dense = await ctx.session.execute(
        select(SourceDensityRow.source_id, EntityRow.id)
        .join(EntityRow, EntityRow.location_id == SourceDensityRow.region_entity_id)
        .where(
            SourceDensityRow.density >= PERCENT - table.density_floor, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON
        )
        .order_by(SourceDensityRow.id, EntityRow.id)
    )
    for source_id, town_id in dense.all():
        if held(town_id) or not ctx.rng(f"source.discover.{source_id}.{town_id}.{ctx.epoch}").chance(table.discovery_chance):
            continue
        await know(ctx, source_id, town_id, table.teaching_gain)
        changed += 1
    return changed
