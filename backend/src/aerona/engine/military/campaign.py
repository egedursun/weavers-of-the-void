from collections.abc import Sequence

from sqlalchemy import select

from aerona.catalog.life_traits import COMMANDER_TRAIT_TRAITS, having
from aerona.catalog.mind_split import BOLD_FACETS
from aerona.catalog.movement import FOOT, best_passage
from aerona.catalog.units import UNITS
from aerona.catalog.war_w52 import FALLEN_STATES
from aerona.catalog.weather import has_trait
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.military import ArmyOfficerRow, ArmyProfileRow, ArmyUnitRow, OccupationRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.environment import MovementMode, RiverClass, ScarKind, WeatherKind, WeatherTrait
from aerona.domain.enums.folkways import BiasedDecision
from aerona.domain.enums.life_traits import CommanderTraitTrait
from aerona.domain.enums.military import ArmyRole, CommanderTrait, MutinyOutcome, Stance, UnitFamily
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind, OfficeKind
from aerona.domain.enums.records import StepAction
from aerona.engine.agrarian.book import fell_plantings
from aerona.engine.body.hits import Harm
from aerona.engine.body.variants import fear_of, fear_of_id
from aerona.engine.context import TickContext
from aerona.engine.environment.book import add_scar
from aerona.engine.folkways.biases import lean
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.military.clash import traits_of
from aerona.engine.military.raids import escorted_take
from aerona.engine.military.support import reluctance, support_of
from aerona.engine.military.units import stacks_of, sync, take
from aerona.engine.mind.book import values_for
from aerona.engine.mind.split import facet_weight, facets_for
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import StepDraft, record
from aerona.rules.registry import Rules

MOUNTED = frozenset({UnitFamily.MOUNTED, UnitFamily.BEAST})
AGGRESSIVE = having(COMMANDER_TRAIT_TRAITS, CommanderTraitTrait.AGGRESSIVE)
CAREFUL = having(COMMANDER_TRAIT_TRAITS, CommanderTraitTrait.CAREFUL)
RUTHLESS = frozenset({CommanderTrait.BRUTAL})


def bridged(rules: Rules, region: RegionEnvironmentRow | None) -> bool:
    return region is not None and region.built >= rules.campaign_depth.bridge_built and region.scars.get(ScarKind.BRIDGE_DOWN.value, 0) <= 0


def step_cost(
    rules: Rules, region: RegionEnvironmentRow | None, season: WorldSeasonRow | None, *, pontoon: bool = False, modes: frozenset[MovementMode] = FOOT
) -> int:
    table = rules.campaign_depth
    if region is None:
        return PERCENT
    passability = max(rules.logistics.passability_floor, best_passage(region.passability, modes, PERCENT))
    cost = PERCENT * max(1.0, table.passability_full / passability)
    if region.river_class in {RiverClass.RIVER, RiverClass.GREAT_RIVER}:
        if not bridged(rules, region) and not pontoon:
            cost = cost * PERCENT / max(1, table.ford_march_pct)
        if season is not None and season.growth >= table.flood_growth:
            cost = cost * PERCENT / max(1, table.flood_march_pct)
    return round_half_up(cost)


def march_budget(
    rules: Rules,
    base_regions: int,
    *,
    weather: WeatherKind | None,
    season: WorldSeasonRow | None,
    road: bool,
    baggage: int,
    hardy: float = 0.0,
    inverted: bool = False,
    heavy: bool = False,
) -> int:
    table = rules.campaign_depth
    regions = base_regions + (table.road_regions if road else 0) - baggage // max(1, table.baggage_slow)
    budget = max(0, regions) * PERCENT
    if has_trait(weather, WeatherTrait.SLOWING):
        budget = budget * table.weather_slow_pct // PERCENT
    campaign = (PERCENT - season.campaign if inverted else season.campaign) if season is not None else PERCENT
    if campaign < PERCENT // 2:
        winter = table.winter_march_pct + (PERCENT - table.winter_march_pct) * min(1.0, hardy)
        budget = round_half_up(budget * winter / PERCENT)
    if heavy:
        budget = round_half_up(budget * rules.natural_laws.heavy_march_pct / PERCENT)
    return budget


def on_road(region: RegionEnvironmentRow | None, rules: Rules) -> bool:
    if region is None:
        return False
    return region.built >= rules.campaign_depth.bridge_built or region.scars.get(ScarKind.MILITARY_ROAD.value, 0) >= rules.army_depth.road_at


def feed_mounts(rules: Rules, profile: ArmyProfileRow, rows: Sequence[ArmyUnitRow], foraged: bool) -> bool:
    table = rules.campaign_depth
    mounted = sum(row.count for row in rows if UNITS[row.kind].family in MOUNTED)
    if mounted <= 0:
        return True
    share = mounted / max(1, sum(row.count for row in rows))
    eaten = max(1, round_half_up(rules.logistics.season_days * share * table.fodder_per_mount / PERCENT))
    if "fodder_days" not in profile.locked:
        profile.fodder_days = max(0, profile.fodder_days - eaten)
    if foraged:
        profile.fodder_days = min(table.fodder_days, profile.fodder_days + rules.logistics.forage_days)
    if profile.fodder_days > 0:
        return True
    for row in rows:
        if UNITS[row.kind].family in MOUNTED:
            row.fatigue = clamp_int(row.fatigue + (PERCENT - table.unfed_mount_pct), 0, PERCENT)
            row.condition = clamp_int(row.condition - (PERCENT - table.unfed_mount_pct) // 4, 0, PERCENT)
    return False


async def babel(ctx: TickContext, profile: ArmyProfileRow, rows: Sequence[ArmyUnitRow]) -> int:
    origins = sorted({row.origin_entity_id for row in rows if row.count > 0 and row.origin_entity_id is not None})
    if len(origins) < 2 or "cohesion" in profile.locked:
        return 0
    bonds = BondRepository(ctx.session)
    tongues: set[int] = set()
    for origin in origins:
        tongues.update(bond.target_node_id for bond in await bonds.outgoing(origin, BondKind.SPEAKS))
    loss = ctx.rules.campaign_depth.babel_cohesion * max(0, len(tongues) - 1)
    if loss > 0:
        profile.cohesion = clamp_int(profile.cohesion - loss, 0, PERCENT)
    return loss


async def class_desertion(ctx: TickContext, owner: EntityRow, profile: ArmyProfileRow, rows: Sequence[ArmyUnitRow]) -> int:
    table = ctx.rules.campaign_depth
    society = await ctx.session.get(CommunitySocietyRow, owner.id)
    hold = 1 - profile.cohesion / PERCENT * table.cohesion_desertion_pct / PERCENT
    army = await ctx.session.get(ArmyRow, profile.army_entity_id)
    hold *= 1 + reluctance(
        ctx.rules.war_conduct.low_support_desertion_pct,
        await support_of(ctx, army.war_id if army is not None else None, owner.id),
        ctx.rules.war_conduct.support_neutral,
    )
    leaving = 0
    for row in rows:
        if row.count <= 0 or row.social_class is None or society is None:
            continue
        satisfaction = society.satisfaction(row.social_class)
        if satisfaction >= table.bitter_satisfaction:
            continue
        bitterness = (table.bitter_satisfaction - satisfaction) / max(1, table.bitter_satisfaction)
        part = min(row.count, round_half_up(row.count * table.satisfaction_desertion_pct / PERCENT * (0.5 + bitterness) * hold))
        row.count -= part
        leaving += part
    return leaving


def plunder(rules: Rules, region: RegionEnvironmentRow | None) -> int:
    if region is None:
        return 0
    table = rules.campaign_depth
    add_scar(region, ScarKind.PLUNDERED, table.plunder_depth)
    depth = region.scars.get(ScarKind.PLUNDERED.value, 0)
    region.harvest_pct = clamp_int(region.harvest_pct - round_half_up(depth * table.plunder_harvest_pct / PERCENT / 4), 0, PERCENT)
    return depth


def plundered_share(region: RegionEnvironmentRow | None) -> float:
    if region is None:
        return 0.0
    return min(PERCENT, region.scars.get(ScarKind.PLUNDERED.value, 0)) / PERCENT


async def sanitation_of(ctx: TickContext, owner: EntityRow) -> int:
    town = await ctx.session.get(SettlementProfileRow, owner.id) or await ctx.session.get(SettlementProfileRow, owner.location_id or 0)
    surgeon = await ctx.session.scalar(select(ArmyOfficerRow.id).where(ArmyOfficerRow.role == ArmyRole.SURGEON, ArmyOfficerRow.until_epoch.is_(None)).limit(1))
    base = town.sanitation if town is not None else PERCENT // 4
    return clamp_int(base + (PERCENT // 4 if surgeon is not None else 0), 0, PERCENT)


def summer(season: WorldSeasonRow | None, seasons: Sequence[WorldSeasonRow]) -> bool:
    return season is not None and bool(seasons) and season.temperature_shift >= max(item.temperature_shift for item in seasons) and season.temperature_shift > 0


def mutiny_pressure(rules: Rules, profile: ArmyProfileRow, *, hungry: bool, unpaid: bool) -> int:
    table = rules.campaign_depth
    if "mutiny" in profile.locked:
        return profile.mutiny
    gain = table.mutiny_gain * (int(hungry) + int(unpaid))
    if profile.cohesion < table.mutiny_cohesion:
        gain += table.mutiny_gain // 2
    if not gain:
        gain = -table.mutiny_decay
    profile.mutiny = clamp_int(profile.mutiny + gain, 0, PERCENT)
    return profile.mutiny


def mutiny_outcome(rules: Rules, roll: int, pressure: int, enemy: bool) -> MutinyOutcome:
    excess = pressure - rules.campaign_depth.mutiny_threshold
    score = roll + excess
    if score >= 90 and enemy:
        return MutinyOutcome.TURNCOAT
    if score >= 75:
        return MutinyOutcome.BANDITRY
    if score >= 55:
        return MutinyOutcome.DEPOSED
    if score >= 30:
        return MutinyOutcome.REFUSAL
    return MutinyOutcome.GRUMBLING


async def mutiny(ctx: TickContext, army: EntityRow, row: ArmyRow, profile: ArmyProfileRow, *, enemy_id: int | None) -> MutinyOutcome | None:
    if profile.mutiny < ctx.rules.campaign_depth.mutiny_threshold:
        return None
    outcome = mutiny_outcome(ctx.rules, ctx.rng(f"mutiny.{army.id}.{ctx.epoch}").below(PERCENT), profile.mutiny, enemy_id is not None)
    owner = await living_entity(ctx.session, row.owner_entity_id)
    rows = await stacks_of(ctx.session, army.id)
    steps: tuple[StepDraft, ...] = ()
    if outcome is MutinyOutcome.GRUMBLING:
        for stack in rows:
            stack.morale = clamp_int(stack.morale - round_half_up(ctx.rules.campaign_depth.mutiny_gain // 2 * await fear_of(ctx.session, army)), 0, PERCENT)
    elif outcome is MutinyOutcome.REFUSAL:
        profile.stance = Stance.ENTRENCH
    elif outcome is MutinyOutcome.DEPOSED:
        steps = (StepDraft(StepAction.DEPOSE, actor=army.id, target=row.commander_entity_id),)
        for officer in await ctx.session.scalars(select(ArmyOfficerRow).where(ArmyOfficerRow.army_entity_id == army.id, ArmyOfficerRow.until_epoch.is_(None))):
            if officer.role is ArmyRole.COMMANDER:
                officer.until_epoch = ctx.epoch
        row.commander_entity_id = None
    elif outcome is MutinyOutcome.BANDITRY and owner is not None:
        shift_stat(owner, "prosperity", -ctx.rules.campaign_depth.plunder_depth)
        profile.loot += ctx.rules.campaign_depth.plunder_depth
    elif outcome is MutinyOutcome.TURNCOAT and enemy_id is not None:
        row.owner_entity_id = enemy_id
        for stack in rows:
            stack.origin_entity_id = stack.origin_entity_id or (owner.id if owner is not None else None)
    profile.mutiny = clamp_int(profile.mutiny - ctx.rules.campaign_depth.mutiny_threshold // 2, 0, PERCENT)
    sync(army, rows, ctx.rules)
    roles = {IncidentRole.SUBJECT: army.id, **({IncidentRole.OWNER: owner.id} if owner is not None else {})}
    await record(
        ctx, f"war.mutiny.{outcome.value}", roles=roles, facts={"outcome": outcome, "mutiny": profile.mutiny}, place=profile.region_entity_id, steps=steps
    )
    ctx.count(f"mutiny_{outcome.value}")
    return outcome


async def drill(ctx: TickContext, owner: EntityRow, profile: ArmyProfileRow, rows: Sequence[ArmyUnitRow]) -> bool:
    if await law_param(ctx.session, owner.id, LawKind.STANDING_ARMY, "share") is None:
        return False
    table = ctx.rules.campaign_depth
    if "drill" not in profile.locked:
        profile.drill = clamp_int(profile.drill + table.drill_gain, 0, PERCENT)
    if "cohesion" not in profile.locked:
        profile.cohesion = clamp_int(profile.cohesion + table.drill_cohesion, 0, PERCENT)
    for row in rows:
        if "experience" not in (row.locked or []):
            row.experience = clamp_int(row.experience + round_half_up(table.drill_experience * profile.drill / PERCENT), 0, PERCENT)
        if "discipline" not in (row.locked or []) and row.discipline < profile.drill:
            row.discipline = min(profile.drill, row.discipline + ctx.rules.army_depth.drill_discipline)
    await spar(ctx, profile.army_entity_id)
    return True


async def spar(ctx: TickContext, army_id: int) -> int:
    officers = select(ArmyOfficerRow.mortal_entity_id).where(ArmyOfficerRow.army_entity_id == army_id, ArmyOfficerRow.until_epoch.is_(None))
    commander = await ctx.session.scalar(select(ArmyRow.commander_entity_id).where(ArmyRow.entity_id == army_id))
    hurt = 0
    for mortal_id in sorted({*await ctx.session.scalars(officers), *([commander] if commander is not None else [])}):
        mortal = await living_entity(ctx.session, mortal_id)
        if mortal is None or held(mortal_id):
            continue
        if not ctx.rng(f"sparring.{army_id}.{mortal_id}.{ctx.epoch}").chance(ctx.rules.army_depth.sparring_injury_pct):
            continue
        harm = Harm(ctx.rules.army_depth.sparring_hp, HarmCause.ACCIDENT, "hurt sparring at drill", damage_type=DamageType.BLUNT)
        if (await apply_hits(ctx, mortal, harm, lethal=False)).outcome is not None:
            hurt += 1
    return hurt


async def kin_of(ctx: TickContext, community_id: int) -> set[int]:
    realms = list(await ctx.session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id)))
    if not realms:
        return set()
    return set(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id.in_(realms))))


async def stricken_homes(ctx: TickContext, atlas: RegionAtlas) -> set[int]:
    homes: set[int] = set()
    for siege in await ctx.session.scalars(select(SiegeRow).where(SiegeRow.status.in_(list(FALLEN_STATES)), SiegeRow.ended_epoch >= ctx.epoch - 1)):
        homes.add(siege.besieged_entity_id)
    for occupation in await ctx.session.scalars(select(OccupationRow)):
        homes.update(atlas.communities_in(occupation.region_entity_id))
    return homes


async def home_news(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.campaign_depth
    stricken = await stricken_homes(ctx, atlas)
    if not stricken:
        return 0
    kin: dict[int, set[int]] = {}
    shaken = 0
    for row in await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.count > 0, ArmyUnitRow.origin_entity_id.is_not(None))):
        origin = row.origin_entity_id or 0
        if origin not in kin:
            kin[origin] = await kin_of(ctx, origin)
        weight = 1.0 if origin in stricken else 0.5 if kin[origin] & stricken else 0.0
        if weight <= 0 or "morale" in (row.locked or []):
            continue
        weight *= 1 + (await values_for(ctx.session, origin)).get(ValueAxis.KINSHIP, 0) / PERCENT
        fear = await fear_of_id(ctx.session, row.army_entity_id)
        row.morale = clamp_int(row.morale - round_half_up(table.home_news_morale * weight * table.home_news_pct / PERCENT * fear), 0, PERCENT)
        shaken += 1
    return shaken


async def strategist(ctx: TickContext, owner: EntityRow, army_row: ArmyRow) -> set[CommanderTrait]:
    traits = await traits_of(ctx, army_row.commander_entity_id)
    marshal = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id)
        .join(PolityMemberRow, PolityMemberRow.polity_entity_id == OfficeRow.polity_entity_id)
        .where(PolityMemberRow.member_entity_id == owner.id, OfficeRow.kind == OfficeKind.MARSHAL)
        .limit(1)
    )
    traits |= await traits_of(ctx, marshal)
    ruler = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id)
        .join(PolityMemberRow, PolityMemberRow.polity_entity_id == OfficeRow.polity_entity_id)
        .where(PolityMemberRow.member_entity_id == owner.id, OfficeRow.kind == OfficeKind.RULER)
        .limit(1)
    )
    return traits | await traits_of(ctx, ruler)


async def aggression(ctx: TickContext, owner: EntityRow, army_row: ArmyRow) -> int:
    traits = await strategist(ctx, owner, army_row)
    values = await values_for(ctx.session, owner.id)
    score = PERCENT // 2 + values.get(ValueAxis.MARTIAL, 0) // 4
    score += 15 * len(traits & AGGRESSIVE) - 15 * len(traits & CAREFUL)
    score += round(facet_weight(await facets_for(ctx.session, army_row.commander_entity_id), BOLD_FACETS) * ctx.rules.mind_split.bold_facet_pct)
    return clamp_int(score, 0, PERCENT)


async def choose_stance(
    ctx: TickContext, owner: EntityRow, army_row: ArmyRow, profile: ArmyProfileRow, *, attacking: bool, at_goal: bool, outnumbered: bool
) -> Stance:
    table = ctx.rules.campaign_depth
    bold = round(await aggression(ctx, owner, army_row) / max(0.1, await lean(ctx, army_row.commander_entity_id, BiasedDecision.RETREAT)))
    if profile.supply_days <= 0 or (outnumbered and bold < table.cautious_strategy):
        return Stance.RETREAT
    if attacking:
        if at_goal:
            return Stance.BESIEGE if bold >= table.aggressive_strategy or not outnumbered else Stance.RAID
        return Stance.RAID if bold < table.cautious_strategy else Stance.MARCH
    if bold >= table.aggressive_strategy and not outnumbered:
        return Stance.RAID
    return Stance.ENTRENCH if bold < table.aggressive_strategy else Stance.GARRISON


async def scorch(ctx: TickContext, owner: EntityRow, army_row: ArmyRow, region: RegionEnvironmentRow | None) -> bool:
    if region is None:
        return False
    traits = await strategist(ctx, owner, army_row)
    mercy = (await values_for(ctx.session, owner.id)).get(ValueAxis.MERCY, 0)
    if not (traits & RUTHLESS or mercy < -PERCENT // 4):
        return False
    if not ctx.rng(f"scorch.{owner.id}.{ctx.epoch}.{region.entity_id}").chance(ctx.rules.campaign_depth.scorched_chance):
        return False
    region.harvest_pct = clamp_int(region.harvest_pct - ctx.rules.campaign_depth.scorched_harvest_pct, 0, PERCENT)
    add_scar(region, ScarKind.BURNED, ctx.rules.campaign_depth.plunder_depth)
    land = await ctx.session.get(EntityRow, region.entity_id)
    if land is not None:
        await fell_plantings(ctx, land, ctx.rules.perennials.felling_pct)
    return True


def raid_supply(rules: Rules, raider: ArmyProfileRow, victim: ArmyProfileRow) -> int:
    if raider.stance is not Stance.RAID or "supply_days" in victim.locked:
        return 0
    taken = min(victim.supply_days, rules.campaign_depth.raid_supply_days)
    taken = escorted_take(rules, victim, taken)
    victim.supply_days -= taken
    raider.supply_days += taken // 2
    return taken


def retreat(rules: Rules, atlas: RegionAtlas, owner: EntityRow, profile: ArmyProfileRow) -> int:
    home = atlas.top_region(owner.id)
    if profile.stance is not Stance.RETREAT or home is None or profile.region_entity_id is None or profile.region_entity_id == home:
        return 0
    path = atlas.region_path(profile.region_entity_id, home) or []
    if len(path) > 1 and "region_id" not in profile.locked:
        profile.region_entity_id = path[1]
    profile.supply_days = min(rules.logistics.supply_days, profile.supply_days + rules.campaign_depth.retreat_supply_days)
    profile.entrenchment = 0
    return 1


async def quartermaster(ctx: TickContext, army_id: int) -> int:
    found = await ctx.session.scalar(
        select(ArmyOfficerRow.id).where(
            ArmyOfficerRow.army_entity_id == army_id, ArmyOfficerRow.role == ArmyRole.QUARTERMASTER, ArmyOfficerRow.until_epoch.is_(None)
        )
    )
    return ctx.rules.campaign_depth.quartermaster_days if found is not None else 0


async def loot_wages(ctx: TickContext, owner: EntityRow, profile: ArmyProfileRow, cost: int, rows: Sequence[ArmyUnitRow]) -> int:
    table = ctx.rules.campaign_depth
    usable = min(profile.loot, round_half_up(cost * table.loot_wage_share_pct / PERCENT))
    profile.loot -= usable
    greed = (await values_for(ctx.session, owner.id)).get(ValueAxis.WEALTH, 0)
    if profile.loot > 0 and greed > 0:
        for row in rows:
            row.morale = clamp_int(row.morale + table.loot_greed_morale, 0, PERCENT)
    return usable


async def bring_home_loot(ctx: TickContext, owner: EntityRow | None, profile: ArmyProfileRow) -> int:
    if owner is None or profile.loot <= 0:
        return 0
    brought = profile.loot
    await shift_standing(ctx.session, owner, "wealth", brought, ctx.epoch)
    profile.loot = 0
    return brought


def straggle(rules: Rules, rows: Sequence[ArmyUnitRow], profile: ArmyProfileRow) -> int:
    if profile.cohesion >= rules.campaign_depth.mutiny_cohesion:
        return 0
    return take(rows, round_half_up(sum(row.count for row in rows) * (rules.campaign_depth.mutiny_cohesion - profile.cohesion) / PERCENT / 10))


def carry(rules: Rules, profile: ArmyProfileRow, size: int) -> None:
    if "baggage" not in profile.locked:
        profile.baggage = round_half_up(size * rules.campaign_depth.baggage_per_100 / PERCENT) + profile.loot


def size_of(army: EntityRow) -> int:
    return stat(army, "size") or 0
