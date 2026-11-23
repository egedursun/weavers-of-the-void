from collections import Counter

from sqlalchemy import func, select

from aerona.catalog.beast_tempers import ACTIVE_TEMPERS, AVENGING, HELD_TEMPERS, TEMPERS
from aerona.catalog.goods_tables import TROPHY_CLASSES
from aerona.catalog.goods_traits import commodities_with
from aerona.catalog.life_traits import SIZE_CLASS_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProductRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import HouseMemberRow, TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.warfare import WarSideRow
from aerona.db.write_guard import held, unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CurseKind, ItemClass, ItemDeed
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.ecology import SIZE_ORDER, BeastTemper, SizeClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, MaterialSlot
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.goods_traits import CommodityTrait
from aerona.domain.enums.life_traits import SizeClassTrait
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyBreach, TreatyKind, TreatyStatus
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.enums.transform import TransformKind
from aerona.domain.models.entity_stats import BeastStats, ItemStats, LegendStats, PlaceStats
from aerona.engine.arcana.vis import harvest_vis
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.couplings.beast_memory import knowledge_dies, memory_dies
from aerona.engine.ecology.anatomy import anatomy_of, harm_factor, plan_limbs, repelled
from aerona.engine.ecology.beast_acts import attacks_of, bite_someone, carry_off, free_captives, is_abductor, sight_scale, strike, triggered, void_trophy
from aerona.engine.ecology.beast_ways import gathers, grudge_town, guard_land, habitat_ways, keep_grudges, richest
from aerona.engine.ecology.foodweb import raid_herds
from aerona.engine.ecology.lineages import pass_to_beast
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.economy.materials import set_node_material
from aerona.engine.economy.money import inject_hoard
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.gods.queries import community_of
from aerona.engine.lore.history import record
from aerona.engine.mind.hooks import committed
from aerona.engine.mind.memories import remember
from aerona.engine.polity.accords import Clause, end_treaty, sign
from aerona.engine.polity.treaties import breach
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, close, connect, has_flag, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, shift_stat, stat, stat_or
from aerona.engine.recording.record import FactInput, RoleValue
from aerona.engine.recording.record import record as record_happening
from aerona.engine.renown.deeds import acclaim_deed
from aerona.engine.transform.creatures import colossal_remains
from aerona.engine.transform.record import blocked, record_transformation
from aerona.rules.registry import Rules

ACTIVE = ACTIVE_TEMPERS
LAIRBOUND = frozenset(temper for temper, spec in TEMPERS.items() if spec.lairbound)
COMMODITY_KEYS = frozenset(item.value for item in CommodityKind)
HELD = HELD_TEMPERS
HOARD_GOODS = commodities_with(CommodityTrait.HOARD)
GREAT = SIZE_ORDER.index(SizeClass.HUGE)
RIDEABLE = having(SIZE_CLASS_TRAITS, SizeClassTrait.RIDEABLE)
TRIBUTE_PARAMS = {"hoard": True}


def stash(row: BeastProfileRow, key: str, amount: int) -> None:
    if "hoard" in row.locked:
        return
    row.hoard = {**row.hoard, key: max(0, row.hoard.get(key, 0) + amount)}


def size_factor(rules: Rules, row: BeastProfileRow) -> float:
    return 1 + max(0, SIZE_ORDER.index(row.size_class) - GREAT) * rules.beasts.size_raid_pct / PERCENT


def reach_of(rules: Rules, row: BeastProfileRow) -> int:
    return rules.beasts.raid_reach + row.endurance // rules.beasts.endurance_reach


def wound_harm(rules: Rules, row: BeastProfileRow | None) -> int:
    table = rules.beasts
    if row is None:
        return table.wound_damage
    return round_half_up(table.wound_damage * (1 - row.endurance / PERCENT * table.endurance_harm_pct / PERCENT))


def tame_chance(rules: Rules, row: BeastProfileRow) -> int:
    return clamp_int(PERCENT - row.willpower * rules.beasts.willpower_tame_pct / PERCENT, 0, PERCENT)


def wake_chance(rules: Rules, row: BeastProfileRow) -> int:
    table = rules.beasts
    return clamp_int(table.disturb_chance * (1 + row.perception / PERCENT * table.perception_wake_pct / PERCENT), 0, PERCENT)


def rest_chance(rules: Rules, row: BeastProfileRow) -> int:
    table = rules.beasts
    return clamp_int(table.sleep_chance * (1 - row.willpower / PERCENT * table.willpower_sleep_pct / PERCENT), 0, PERCENT)


async def living_beasts(ctx: TickContext) -> list[tuple[EntityRow, BeastProfileRow]]:
    found = []
    for beast in await canon(ctx.session, [EntityType.BEAST]):
        row = await ctx.session.get(BeastProfileRow, beast.id)
        if row is None:
            row = await profile_beast(ctx, beast, None)
        found.append((beast, row))
    return found


async def lair_in(ctx: TickContext, region_id: int | None) -> int | None:
    if region_id is None:
        return None
    place = await ctx.session.scalar(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.PLACE, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == region_id)
        .limit(1)
    )
    return place if place is not None else region_id


async def profile_beast(ctx: TickContext, beast: EntityRow, species: EntityRow | None, size: SizeClass | None = None) -> BeastProfileRow:
    kind = await profile_of(ctx, species) if species is not None else None
    region = (await RegionAtlas.load(ctx.session)).top_region(beast.id)
    grown = kind.size_class if kind is not None and SIZE_ORDER.index(kind.size_class) >= GREAT else SizeClass.HUGE
    row = BeastProfileRow(
        beast_entity_id=beast.id,
        species_entity_id=species.id if species is not None else None,
        endurance=clamp_int((stat_or(beast, "hp", PERCENT)) // 4, 0, PERCENT),
        perception=clamp_int(stat_or(beast, "cunning", PERCENT // 2), 0, PERCENT),
        willpower=clamp_int(stat_or(beast, "danger", PERCENT // 2), 0, PERCENT),
        intelligence=clamp_int(stat_or(species, "intelligence", stat_or(beast, "cunning", 20)), 0, PERCENT) if species is not None else 20,
        age=0,
        lifespan=max(1, (kind.lifespan_years if kind is not None else 100) * 3),
        size_class=size or grown,
        lair_place_id=await lair_in(ctx, region),
        temper=BeastTemper.SLEEPING,
        bound_to_node_id=None,
        hoard={},
        raids=0,
        woke_epoch=None,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await pass_to_beast(ctx, beast, row.species_entity_id)
    return row


async def champions(ctx: TickContext) -> int:
    table = ctx.rules.beasts
    risen = 0
    by_world: Counter[int | None] = Counter()
    profiled = set(await ctx.session.scalars(select(BeastProfileRow.species_entity_id).where(BeastProfileRow.species_entity_id.is_not(None))))
    for species in ctx.rng("champion.order").shuffled(unheld(await canon(ctx.session, [EntityType.SPECIES]))):
        if by_world[species.world_id] >= table.promotion_cap or species.id in profiled:
            continue
        kind = await ctx.session.get(SpeciesProfileRow, species.id)
        huge = kind is not None and SIZE_ORDER.index(kind.size_class) >= GREAT
        mighty = await has_flag(ctx.session, species.id, EntityFlag.MEGAFAUNA) or (huge and (stat(species, "danger") or 0) >= table.promotion_danger)
        if not mighty or not ctx.rng(f"champion.{species.id}.{ctx.epoch}").chance(table.promotion_chance):
            continue
        if await blocked(ctx, TransformKind.BEAST_PROMOTION, species.id):
            continue
        home = await ctx.session.scalar(
            select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == species.id).order_by(SpeciesRangeRow.abundance.desc()).limit(1)
        )
        region = await living_entity(ctx.session, home) if home is not None else None
        if region is not None and held(region.id):
            continue
        beast = await create_record(
            ctx,
            RecordSpec(
                name=f"The Great {species.name}" if region is None else f"The {species.name} of {region.name}",
                entity_type=EntityType.BEAST,
                stats=BeastStats(
                    hp=(stat_or(species, "hp", PERCENT)) * 2,
                    danger=clamp_int((stat(species, "danger") or 0) + PERCENT // 10, 0, PERCENT),
                    strength=clamp_int((stat_or(species, "strength", PERCENT // 2)) + PERCENT // 5, 0, PERCENT),
                    agility=stat(species, "agility"),
                    cunning=stat(species, "intelligence"),
                    renown=PERCENT // 5,
                    terror=PERCENT // 10,
                ),
                body=f"The greatest of its kind in {region.name if region is not None else 'its lands'}.",
                power=max(species.power_level, 3),
                world_id=species.world_id,
                location_id=region.id if region is not None else species.location_id,
            ),
        )
        await profile_beast(ctx, beast, species)
        await connect(ctx.session, beast.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, description="the greatest of its kind")
        await record_transformation(ctx, TransformKind.BEAST_PROMOTION, species.id, beast.id)
        facts: dict[str, FactInput] = {"species": species.id, "hp": stat_or(beast, "hp", 0), "danger": stat_or(beast, "danger", 0)}
        await record_happening(ctx, "beasts.risen", roles={IncidentRole.SUBJECT: beast.id}, facts=facts, place=region.id if region is not None else None)
        risen += 1
        by_world[species.world_id] += 1
    return risen


async def disturbed(ctx: TickContext, beast: EntityRow, region: int | None) -> bool:
    if region is None:
        return False
    land = await ctx.session.get(RegionEnvironmentRow, region)
    mined = land is not None and land.mined > 0
    wars = await ctx.session.scalar(
        select(func.count(WarSideRow.war_id)).where(
            WarSideRow.left_epoch.is_(None), WarSideRow.entity_id.in_(select(EntityRow.id).where(EntityRow.location_id == region))
        )
    )
    robbed = await ctx.session.scalar(
        select(MemoryRow.id).where(MemoryRow.holder_node_id == beast.id, MemoryRow.kind == MemoryKind.CHEATED_US, MemoryRow.epoch >= ctx.epoch - 1).limit(1)
    )
    return mined or bool(wars) or robbed is not None


async def avenger_target(ctx: TickContext, beast: EntityRow, near: list[EntityRow]) -> EntityRow | None:
    if not ctx.rng(f"vengeance.{beast.id}.{ctx.epoch}").chance(ctx.rules.beasts.vengeance_chance):
        return None
    wounders = await ctx.session.scalars(
        select(MemoryRow.subject_node_id).where(MemoryRow.holder_node_id == beast.id, MemoryRow.kind == MemoryKind.HARMED_ME).order_by(MemoryRow.id.desc())
    )
    for wounder in list(wounders):
        house = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == wounder).limit(1))
        kin = select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == house) if house is not None else None
        homes = set(await ctx.session.scalars(select(EntityRow.location_id).where(EntityRow.id.in_(kin)))) if kin is not None else set()
        mortal = await ctx.session.get(EntityRow, wounder)
        if mortal is not None and mortal.location_id is not None:
            homes.add(mortal.location_id)
        target = next((town for town in near if town.id in homes), None)
        if target is not None:
            return target
    return None


async def towns_near(ctx: TickContext, atlas: RegionAtlas, row: BeastProfileRow) -> list[EntityRow]:
    reach = reach_of(ctx.rules, row)
    lair = row.lair_place_id
    return [town for town in await canon(ctx.session, [EntityType.SETTLEMENT]) if lair is not None and atlas.distance(lair, town.id) <= reach]


async def slayer_towns(ctx: TickContext) -> set[int]:
    slain = select(EntityRow.id).where(EntityRow.entity_type == EntityType.BEAST)
    slayers = select(BondRow.source_node_id).where(BondRow.kind == BondKind.KILLED, BondRow.target_node_id.in_(slain))
    homes = await ctx.session.scalars(
        select(EntityRow.location_id).where(EntityRow.id.in_(slayers), EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
    )
    return {home for home in homes if home is not None}


async def owned_items(ctx: TickContext, owner_ids: list[int]) -> list[int]:
    if not owner_ids:
        return []
    items = select(EntityRow.id).where(EntityRow.entity_type == EntityType.ITEM, EntityRow.status == EntityStatus.CANON)
    rows = await ctx.session.scalars(
        select(BondRow.target_node_id)
        .where(BondRow.source_node_id.in_(owner_ids), BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(items))
        .order_by(BondRow.target_node_id)
    )
    return list(dict.fromkeys(rows))


async def hand_over(ctx: TickContext, item_id: int, receiver_id: int, deed: ItemDeed, text: str) -> None:
    for bond in list(
        await ctx.session.scalars(select(BondRow).where(BondRow.target_node_id == item_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE))
    ):
        await close(ctx.session, bond, ctx.epoch, text)
    await connect(ctx.session, receiver_id, item_id, BondKind.OWNS, ctx.epoch, description=text)
    record(ctx, item_id, deed, receiver_id, text)


async def seize_treasure(ctx: TickContext, beast: EntityRow, town: EntityRow) -> int | None:
    if not ctx.rng(f"hoard_item.{beast.id}.{town.id}.{ctx.epoch}").chance(ctx.rules.beasts.hoard_item_chance):
        return None
    dwellers = list(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.location_id == town.id, EntityRow.status == EntityStatus.CANON)))
    items = await owned_items(ctx, [town.id, *dwellers])
    if not items:
        return None
    chosen = ctx.rng(f"hoard_pick.{beast.id}.{ctx.epoch}").pick(items)
    await hand_over(ctx, chosen, beast.id, ItemDeed.THEFT, f"carried off to the hoard of {beast.name}")
    return chosen


async def raid(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, town: EntityRow) -> None:
    table = ctx.rules.beasts
    anatomy = await anatomy_of(ctx.session, beast.id)
    attacks = await attacks_of(ctx, beast.id)
    scale = size_factor(ctx.rules, row) * harm_factor(ctx.rules, anatomy, await plan_limbs(ctx.session, beast.id), len(attacks))
    if row.temper is BeastTemper.WOUNDED:
        scale *= 1 + ctx.rules.beast_tempers.wounded_fury_pct / PERCENT
    scale *= await sight_scale(ctx, beast, town, attacks)
    herds = await raid_herds(ctx, beast, town)
    lost = round_half_up((stat(town, "population") or 0) * table.raid_population_pct * scale / PERCENT)
    if stat(town, "population") is not None:
        shift_stat(town, "population", -lost)
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    if anatomy is not None and anatomy.hoards is not None:
        taken = await ledger.take_units(town.id, CommodityKind.LUXURIES, ctx.rules.creature_anatomy.hoard_take, GoodsFlow.LOOT)
        if taken:
            stash(row, anatomy.hoards.value, taken)
    for commodity in HOARD_GOODS:
        taken = await ledger.take_units(town.id, commodity, round_half_up(table.raid_hoard * scale), GoodsFlow.LOOT)
        if taken:
            stash(row, commodity.value, taken)
            break
    if anatomy is not None and anatomy.bite is not None:
        await bite_someone(ctx, beast, town, anatomy.bite)
    for attack in attacks:
        await strike(ctx, beast, row, town, attack)
    treasure = await seize_treasure(ctx, beast, town)
    row.raids += 1
    set_stats(
        beast,
        terror=clamp_int((stat(beast, "terror") or 0) + table.terror_gain, 0, PERCENT),
        renown=clamp_int((stat(beast, "renown") or 0) + table.renown_gain, 0, PERCENT),
    )
    await connect(ctx.session, beast.id, town.id, BondKind.HUNTS, ctx.epoch, description="raids")
    roles: dict[IncidentRole, RoleValue] = {IncidentRole.ACTOR: beast.id, IncidentRole.VICTIM: town.id}
    facts: dict[str, FactInput] = {"population_lost": lost, "head": herds, "attacks": len(attacks), "scale": round_half_up(scale * PERCENT)}
    if treasure is not None:
        facts["treasure"] = treasure
    await record_happening(ctx, "beasts.raid_treasure" if treasure is not None else "beasts.raid", roles=roles, facts=facts, place=town.id)


async def tribute_clauses(ctx: TickContext, beast_id: int) -> list[tuple[TreatyProfileRow, TreatyClauseRow]]:
    rows = await ctx.session.execute(
        select(TreatyProfileRow, TreatyClauseRow)
        .join(TreatyClauseRow, TreatyClauseRow.treaty_entity_id == TreatyProfileRow.treaty_entity_id)
        .where(TreatyProfileRow.status == TreatyStatus.IN_FORCE, TreatyClauseRow.kind == ClauseKind.TRIBUTE, TreatyClauseRow.beneficiary_node_id == beast_id)
        .order_by(TreatyClauseRow.id)
    )
    return [(profile, clause) for profile, clause in rows]


async def swear_tribute(ctx: TickContext, beast: EntityRow, town: EntityRow) -> EntityRow:
    table = ctx.rules.beasts
    clause = Clause(ClauseKind.TRIBUTE, town.id, beast.id, {**TRIBUTE_PARAMS, "commodity": CommodityKind.LUXURIES.value, "units": table.tribute_hoard})
    return await sign(
        ctx,
        TreatyKind.TRIBUTE,
        [(town.id, PartyRole.VASSAL), (beast.id, PartyRole.OVERLORD)],
        clauses=[clause],
        until=ctx.epoch + table.tribute_epochs,
        witnessed=False,
    )


async def tribute(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, near: list[EntityRow]) -> tuple[int, EntityRow | None]:
    table = ctx.rules.beasts
    cowed = (stat(beast, "terror") or 0) >= table.cowed_terror
    sworn = await tribute_clauses(ctx, beast.id)
    if not cowed:
        for profile, _ in sworn:
            await end_treaty(ctx, profile, TreatyStatus.EXPIRED, f"the fear of {beast.name} ended")
        return 0, None
    paying = {clause.obligor_node_id for _, clause in sworn}
    for town in near:
        if town.id not in paying and (stat(town, "defense") or 0) < (stat(beast, "strength") or 0):
            await swear_tribute(ctx, beast, town)
    paid = 0
    payers: list[int] = []
    units = 0
    defiant: EntityRow | None = None
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    for profile, clause in await tribute_clauses(ctx, beast.id):
        payer = await living_entity(ctx.session, clause.obligor_node_id)
        if payer is None:
            await end_treaty(ctx, profile, TreatyStatus.EXPIRED, "the tributary is gone")
            continue
        commodity = CommodityKind(str(clause.params.get("commodity", CommodityKind.LUXURIES.value)))
        due = int(clause.params.get("units", table.tribute_hoard))
        taken = await ledger.take_units(payer.id, commodity, due, GoodsFlow.TRIBUTE)
        if taken:
            stash(row, commodity.value, taken)
            clause.last_kept_epoch = ctx.epoch
            paid += 1
            payers.append(payer.id)
            units += taken
        elif due > 0:
            await breach(ctx, profile, payer.id, clause=clause, reason=TreatyBreach.BEAST_TRIBUTE_UNPAID, occasion=beast.id)
            defiant = defiant or payer
    if payers:
        await record_happening(
            ctx, "beasts.tribute", roles={IncidentRole.RECEIVER: beast.id, IncidentRole.GIVER: payers}, facts={"towns": paid, "units": units}
        )
    return paid, defiant


async def dread(ctx: TickContext, beast: EntityRow, near: list[EntityRow], *, quiet: bool) -> None:
    table = ctx.rules.beasts
    terror = stat(beast, "terror") or 0
    for town in near:
        if stat(town, "prosperity") is not None:
            shift_stat(town, "prosperity", -round_half_up(table.terror_prosperity * terror / PERCENT))
        fear = round_half_up(terror * table.terror_insecurity_pct / PERCENT)
        if fear > 0:
            await remember(
                ctx.session, ctx.rules, holder_id=town.id, subject_id=beast.id, kind=MemoryKind.HARMED_ME, magnitude=-fear, epoch=ctx.epoch, note="dread"
            )
    if quiet:
        set_stats(beast, terror=clamp_int(terror - table.terror_decay, 0, PERCENT))


async def guard(ctx: TickContext, row: BeastProfileRow) -> None:
    ward = await living_entity(ctx.session, row.bound_to_node_id)
    if ward is not None and stat(ward, "defense") is not None:
        set_stats(ward, defense=clamp_int((stat(ward, "defense") or 0) + ctx.rules.beasts.guard_defence, 0, PERCENT))


async def pick_prey(ctx: TickContext, beast: EntityRow, near: list[EntityRow], defiant: EntityRow | None) -> EntityRow | None:
    rng = ctx.rng(f"lair.prey.{beast.id}.{ctx.epoch}")
    if defiant is not None:
        return defiant
    shunned = await slayer_towns(ctx) if rng.chance(ctx.rules.beasts.slayer_shun_pct) else set()
    anatomy = await anatomy_of(ctx.session, beast.id)
    atlas = await RegionAtlas.load(ctx.session)
    bold = [town for town in near if town.id not in shunned and not await repelled(ctx, atlas, town, anatomy.hates if anatomy else None)]
    if near and not bold and anatomy is not None and anatomy.hates is not None:
        await cow(ctx, beast, near[0].id)
        await record_happening(
            ctx, "beast.driven_off", roles={IncidentRole.SUBJECT: beast.id, IncidentRole.ACTOR: near[0].id}, facts={"aversion": anatomy.hates}
        )
    return rng.pick(bold) if bold else None


async def woken(
    ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: BeastProfileRow, *, anatomy: CreatureAnatomyRow | None, region: int | None
) -> bool:
    if anatomy is not None and anatomy.awakening is not None:
        return await triggered(ctx, atlas, anatomy, region)
    rng = ctx.rng(f"lair.wake.{beast.id}.{ctx.epoch}")
    return rng.chance(ctx.rules.beasts.wake_chance) or (await disturbed(ctx, beast, region) and rng.chance(wake_chance(ctx.rules, row)))


async def shift_temper(ctx: TickContext, beast: EntityRow, row: BeastProfileRow) -> bool:
    table = ctx.rules.beast_tempers
    if "temper" in row.locked:
        return row.temper in LAIRBOUND
    full = max(1, row.endurance * 4)
    hp = stat_or(beast, "hp", full)
    if row.temper is BeastTemper.COWED:
        if row.temper_epoch is not None and ctx.epoch - row.temper_epoch < table.epochs(table.cowed_years):
            return True
        row.temper, row.temper_epoch = BeastTemper.HUNGRY, ctx.epoch
        return False
    if hp * PERCENT < table.wounded_hp_pct * full:
        if row.temper is not BeastTemper.WOUNDED:
            row.temper, row.temper_epoch = BeastTemper.WOUNDED, ctx.epoch
            await record_happening(ctx, "beast.wounded", roles={IncidentRole.SUBJECT: beast.id}, facts={"hp": hp, "full": full})
        shift_stat(beast, "hp", max(1, row.endurance // 4), 0)
        return not await strikes_back(ctx, beast.id)
    if row.temper is BeastTemper.WOUNDED:
        row.temper, row.temper_epoch = BeastTemper.HUNGRY, ctx.epoch
    young = await fresh_young(ctx, beast.id)
    if young and row.temper is not BeastTemper.BROODING:
        row.temper, row.temper_epoch = BeastTemper.BROODING, ctx.epoch
        await record_happening(ctx, "beast.brooding", roles={IncidentRole.SUBJECT: beast.id, IncidentRole.PRODUCT: young})
    elif not young and row.temper is BeastTemper.BROODING:
        row.temper, row.temper_epoch = BeastTemper.TERRITORIAL, ctx.epoch
    return row.temper is BeastTemper.BROODING


async def strikes_back(ctx: TickContext, beast_id: int) -> bool:
    anatomy = await anatomy_of(ctx.session, beast_id)
    return anatomy is not None and anatomy.temperament in AVENGING


async def fresh_young(ctx: TickContext, beast_id: int) -> list[int]:
    statement = (
        select(BondRow.source_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.target_node_id == beast_id, BondRow.kind == BondKind.DESCENDS_FROM, EntityRow.birth_epoch >= ctx.epoch - 1)
        .order_by(BondRow.source_node_id)
    )
    return list(await ctx.session.scalars(statement))


async def cow(ctx: TickContext, beast: EntityRow, by_node_id: int) -> None:
    row = await ctx.session.get(BeastProfileRow, beast.id)
    if row is None or "temper" in row.locked or held(beast.id) or row.temper in HELD:
        return
    row.temper, row.temper_epoch = BeastTemper.COWED, ctx.epoch
    await record_happening(
        ctx,
        "beast.cowed",
        roles={IncidentRole.SUBJECT: beast.id, IncidentRole.ACTOR: by_node_id},
        facts={"epochs": ctx.rules.beast_tempers.epochs(ctx.rules.beast_tempers.cowed_years)},
    )


async def beast_ways(
    ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: BeastProfileRow, *, anatomy: CreatureAnatomyRow | None, near: list[EntityRow]
) -> bool:
    await guard_land(ctx, atlas, beast, row, anatomy)
    grudges = await keep_grudges(ctx, beast, anatomy)
    found = await grudge_town(ctx, atlas, row, grudges) if grudges else None
    if found is not None:
        town, grudge = found
        await raid(ctx, beast, row, town)
        await record_happening(
            ctx,
            "beast.vengeance",
            roles={IncidentRole.ACTOR: beast.id, IncidentRole.TARGET: grudge.target_node_id, IncidentRole.VICTIM: town.id},
            facts={"strength": grudge.strength},
            place=town.id,
        )
        return True
    if (
        near
        and gathers(anatomy)
        and ctx.rng(f"lair.gather.{beast.id}.{ctx.epoch}").chance(ctx.rules.beast_acts.acquisitive_raid_pct * PERCENT // (PERCENT + sum(row.hoard.values())))
    ):
        target = await richest(ctx, near)
        if target is not None:
            await raid(ctx, beast, row, target)
            await record_happening(
                ctx,
                "beast.hoard_raid",
                roles={IncidentRole.ACTOR: beast.id, IncidentRole.VICTIM: target.id},
                facts={"hoard": sum(row.hoard.values())},
                place=target.id,
            )
            return True
    return False


async def lair_cycle(ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: BeastProfileRow) -> bool:
    table = ctx.rules.beasts
    rng = ctx.rng(f"lair.{beast.id}.{ctx.epoch}")
    if "age" not in row.locked:
        row.age += table.age_years
    if row.age > row.lifespan:
        return True
    row.updated_epoch = ctx.epoch
    tamer = await bonded_state(ctx, beast.id)
    if tamer is not None and row.temper not in HELD and "temper" not in row.locked and rng.chance(tame_chance(ctx.rules, row)):
        row.temper, row.bound_to_node_id = BeastTemper.TAMED, tamer.source_node_id
    if row.temper in HELD:
        await guard(ctx, row)
    if row.temper in HELD or await shift_temper(ctx, beast, row):
        return False
    await prowl(ctx, atlas, beast, row)
    return False


async def prowl(ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: BeastProfileRow) -> None:
    rng = ctx.rng(f"lair.{beast.id}.{ctx.epoch}")
    near = await towns_near(ctx, atlas, row)
    region = atlas.top_region(row.lair_place_id) if row.lair_place_id is not None else atlas.top_region(beast.id)
    anatomy = await anatomy_of(ctx.session, beast.id)
    surfaced = await habitat_ways(ctx, beast, row, anatomy, region)
    if row.temper is BeastTemper.SLEEPING and "temper" not in row.locked and (surfaced or await woken(ctx, atlas, beast, row, anatomy=anatomy, region=region)):
        row.temper, row.woke_epoch = BeastTemper.HUNGRY, ctx.epoch
    if await beast_ways(ctx, atlas, beast, row, anatomy=anatomy, near=near):
        return
    _, defiant = await tribute(ctx, beast, row, near)
    if defiant is not None and "temper" not in row.locked:
        row.temper = BeastTemper.ENRAGED
    if row.temper not in ACTIVE or not near:
        await dread(ctx, beast, near, quiet=True)
        return
    if is_abductor(anatomy):
        taken = await carry_off(ctx, beast, row, near)
        await dread(ctx, beast, near, quiet=taken is None)
        return
    target = await avenger_target(ctx, beast, near)
    if target is not None and "temper" not in row.locked:
        row.temper = BeastTemper.ENRAGED
    prey = target or await pick_prey(ctx, beast, near, defiant)
    if prey is None:
        await dread(ctx, beast, near, quiet=False)
        await record_happening(ctx, "beasts.shunned", roles={IncidentRole.ACTOR: beast.id, IncidentRole.TARGET: [town.id for town in near]})
        return
    await raid(ctx, beast, row, prey)
    await dread(ctx, beast, near, quiet=False)
    if row.temper is not BeastTemper.ENRAGED and "temper" not in row.locked and rng.chance(rest_chance(ctx.rules, row)):
        row.temper = BeastTemper.SLEEPING


async def slayer_of(ctx: TickContext, beast_id: int) -> EntityRow | None:
    killer = await ctx.session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == beast_id, BondRow.kind.in_([BondKind.KILLED, BondKind.DESTROYED]))
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    return await ctx.session.get(EntityRow, killer) if killer is not None else None


async def trophy(ctx: TickContext, beast: EntityRow, slayer: EntityRow, item: SpeciesProductRow, material: MaterialKind) -> EntityRow:
    amount = ctx.rules.beasts.corpse_yield * item.rate
    made = await create_record(
        ctx,
        RecordSpec(
            name=f"The {item.product.title()} of {beast.name}",
            entity_type=EntityType.ITEM,
            stats=ItemStats(might=clamp_int(amount, 0, PERCENT)),
            body=f"Taken by {slayer.name} from the body of {beast.name}.",
            power=max(1, beast.power_level - 1),
            world_id=beast.world_id,
            location_id=slayer.location_id,
            subtype=material.value,
            maker_entity_id=slayer.id,
        ),
    )
    ctx.session.add(
        ItemProfileRow(
            item_entity_id=made.id,
            item_class=TROPHY_CLASSES.get(material, ItemClass.JEWEL),
            quality=clamp_int(PERCENT // 2 + amount, 0, PERCENT),
            condition=PERCENT,
            curse=CurseKind.NONE,
            value=amount,
            renown=clamp_int(stat(beast, "renown") or 0, 0, PERCENT),
            maker_entity_id=slayer.id,
            symbol=False,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    await set_node_material(ctx.session, made.id, MaterialSlot.BODY, material, None, force=True)
    await connect(ctx.session, slayer.id, made.id, BondKind.OWNS, ctx.epoch, description=f"slew {beast.name}")
    record(ctx, made.id, ItemDeed.KILL, slayer.id, f"cut from {beast.name} by {slayer.name}")
    return made


async def corpse(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, slayer: EntityRow) -> int:
    if row.species_entity_id is None:
        return 0
    given = 0
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    for item in list(await ctx.session.scalars(select(SpeciesProductRow).where(SpeciesProductRow.species_entity_id == row.species_entity_id))):
        if item.commodity is None or item.material is None:
            continue
        if slayer.entity_type in COMMUNITY_TYPES:
            amount = ctx.rules.beasts.corpse_yield * item.rate
            given += await ledger.add(slayer.id, item.commodity, amount, GoodsFlow.EXTRACTION, material=item.material, world_material_id=item.world_material_id)
        else:
            await trophy(ctx, beast, slayer, item, item.material)
            given += 1
    return given


async def loot(ctx: TickContext, row: BeastProfileRow, slayer: EntityRow) -> int:
    home = slayer if slayer.entity_type in COMMUNITY_TYPES else await community_of(ctx.session, slayer)
    if home is None:
        return 0
    share = ctx.rules.beasts.hoard_wealth_pct / PERCENT
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    carried = 0
    for key, value in sorted(row.hoard.items()):
        taken = round_half_up(value * share)
        if taken <= 0 or key not in COMMODITY_KEYS:
            continue
        stash(row, key, -taken)
        if key == CommodityKind.LUXURIES.value:
            carried += await inject_hoard(ctx, home, taken, MaterialKind.GOLD)
        else:
            carried += await ledger.add(home.id, CommodityKind(key), taken, GoodsFlow.LOOT)
    return carried


async def recover_wilds(ctx: TickContext, beast: EntityRow, row: BeastProfileRow) -> int:
    table = ctx.rules.beasts
    atlas = await RegionAtlas.load(ctx.session)
    region_id = atlas.top_region(row.lair_place_id) if row.lair_place_id is not None else atlas.top_region(beast.id)
    if region_id is None:
        return 0
    region = await living_entity(ctx.session, region_id)
    if region is not None and stat(region, "danger") is not None:
        set_stats(region, danger=clamp_int((stat(region, "danger") or 0) - table.recovery_danger, 0, PERCENT))
    grown = 0
    for wild in list(await ctx.session.scalars(select(SpeciesRangeRow).where(SpeciesRangeRow.region_entity_id == region_id, SpeciesRangeRow.abundance > 0))):
        if "abundance" in wild.locked or wild.species_entity_id == row.species_entity_id:
            continue
        wild.abundance = clamp_int(wild.abundance + table.recovery_abundance, 0, PERCENT)
        grown += 1
    return grown


async def honour_slayer(ctx: TickContext, beast: EntityRow, slayer: EntityRow) -> None:
    table = ctx.rules.beasts
    slayer.importance = (slayer.importance or 0) + table.slayer_renown
    if slayer.entity_type is EntityType.MORTAL and not slayer.title:
        slayer.title = f"Slayer of {beast.name}"
    legend = await create_record(
        ctx,
        RecordSpec(
            name=f"The Slaying of {beast.name}",
            entity_type=EntityType.LEGEND,
            stats=LegendStats(spread=PERCENT // 4),
            body=f"How {slayer.name} slew {beast.name}.",
            power=3,
            world_id=beast.world_id,
            location_id=slayer.location_id,
        ),
    )
    await connect(ctx.session, legend.id, beast.id, BondKind.TELLS_OF, ctx.epoch, description="the slaying")
    await connect(ctx.session, legend.id, slayer.id, BondKind.TELLS_OF, ctx.epoch, description="the slayer")


async def fall(ctx: TickContext, beast: EntityRow, row: BeastProfileRow) -> str:
    row.locked = []
    slayer = await slayer_of(ctx, beast.id)
    await colossal_remains(ctx, beast, row)
    await memory_dies(ctx, beast)
    await knowledge_dies(ctx, beast)
    for profile, _ in await tribute_clauses(ctx, beast.id):
        await end_treaty(ctx, profile, TreatyStatus.FULFILLED, f"{beast.name} is dead")
    ctx.count("captives_rescued", await free_captives(ctx, beast))
    if slayer is not None:
        await corpse(ctx, beast, row, slayer)
        await loot(ctx, row, slayer)
        await void_trophy(ctx, beast, slayer)
        await harvest_vis(ctx, beast, slayer)
        await acclaim_deed(ctx, slayer.id, ReputationAxis.HEROISM, ctx.rules.local_renown.act_magnitude * 2, place_id=slayer.location_id, token=True)
        kind_traits = await traits_of(ctx.session, row.species_entity_id) if row.species_entity_id is not None else set()
        if CreatureTrait.SACRED_ANIMAL in kind_traits | await traits_of(ctx.session, beast.id):
            await committed(ctx, slayer.id, ActKind.KILLING_SACRED_ANIMAL, beast.id)
    treasures = await owned_items(ctx, [beast.id])
    if any(value > 0 for value in row.hoard.values()) or treasures:
        place = await create_record(
            ctx,
            RecordSpec(
                name=f"The Hoard of {beast.name}",
                entity_type=EntityType.PLACE,
                stats=PlaceStats(danger=PERCENT // 10, mystery=PERCENT // 2),
                body=f"What {beast.name} had taken and kept: {', '.join(f'{value} {key}' for key, value in sorted(row.hoard.items()) if value > 0)}.",
                power=2,
                world_id=beast.world_id,
                location_id=beast.location_id,
            ),
        )
        await connect(ctx.session, place.id, beast.id, BondKind.SOURCE_OF, ctx.epoch, description="its hoard")
        for item_id in treasures:
            receiver = slayer.id if slayer is not None else place.id
            await hand_over(ctx, item_id, receiver, ItemDeed.OWNED, f"taken from the hoard of {beast.name}")
    if slayer is not None:
        await honour_slayer(ctx, beast, slayer)
    ctx.count("wilds_recovered", await recover_wilds(ctx, beast, row))
    hoarded = sum(value for value in row.hoard.values() if value > 0)
    row.hoard, row.lair_place_id = {}, None
    roles: dict[IncidentRole, RoleValue] = {IncidentRole.VICTIM: beast.id, IncidentRole.ACTOR: slayer.id if slayer is not None else None}
    written = await record_happening(
        ctx, "beasts.fallen_by" if slayer is not None else "beasts.fallen", roles=roles, facts={"hoard": hoarded, "treasures": len(treasures)}
    )
    return written.text


async def fallen(ctx: TickContext) -> list[str]:
    told = []
    rows = await ctx.session.scalars(select(BeastProfileRow).where(BeastProfileRow.lair_place_id.is_not(None)))
    for row in list(rows):
        beast = await ctx.session.get(EntityRow, row.beast_entity_id)
        if beast is not None and beast.status is not EntityStatus.CANON:
            told.append(await fall(ctx, beast, row))
    return told


async def bonded_state(ctx: TickContext, beast_id: int) -> BondRow | None:
    return await ctx.session.scalar(
        select(BondRow).where(BondRow.target_node_id == beast_id, BondRow.kind == BondKind.TAMED, BondRow.state == BondState.ACTIVE).limit(1)
    )


async def mount_of(ctx: TickContext, rider_id: int | None) -> EntityRow | None:
    if rider_id is None:
        return None
    rows = await ctx.session.scalars(
        select(BeastProfileRow.beast_entity_id)
        .where(BeastProfileRow.bound_to_node_id == rider_id, BeastProfileRow.temper == BeastTemper.TAMED, BeastProfileRow.size_class.in_([*RIDEABLE]))
        .order_by(BeastProfileRow.beast_entity_id)
    )
    for beast_id in list(rows):
        found = await living_entity(ctx.session, beast_id)
        if found is not None:
            return found
    return None


async def mounted_power(ctx: TickContext, rider_id: int) -> float:
    mount = await mount_of(ctx, rider_id)
    return 1 + ctx.rules.beasts.mount_power_pct / PERCENT * (stat(mount, "strength") or 0) / PERCENT if mount is not None else 1.0


async def mounted_edge(ctx: TickContext, rider_id: int | None) -> float:
    mount = await mount_of(ctx, rider_id)
    return 1 + ctx.rules.beasts.mount_edge_pct / PERCENT * (stat(mount, "strength") or 0) / PERCENT if mount is not None else 1.0


async def bound_to(ctx: TickContext, owner_id: int) -> list[tuple[EntityRow, BeastProfileRow]]:
    rows = await ctx.session.scalars(
        select(BeastProfileRow)
        .where(BeastProfileRow.bound_to_node_id == owner_id, BeastProfileRow.temper == BeastTemper.BOUND)
        .order_by(BeastProfileRow.beast_entity_id)
    )
    found = [(await living_entity(ctx.session, row.beast_entity_id), row) for row in list(rows)]
    return [(beast, row) for beast, row in found if beast is not None]


async def beast_dread(ctx: TickContext, foe_id: int) -> int:
    return sum(round_half_up(ctx.rules.beasts.army_terror * size_factor(ctx.rules, row)) for _, row in await bound_to(ctx, foe_id))


TERRORS = {
    "fire_breathing": Domain.FIRE,
    "cold_breathing": Domain.ICE,
    "flying": Domain.SKY,
    "aquatic": Domain.SEA,
    "venomous": Domain.BLOOD,
    "soul_eater": Domain.DEATH,
}


async def deified(ctx: TickContext, beast_id: int) -> bool:
    found = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == beast_id, BondRow.kind == BondKind.SOURCE_OF, BondRow.description == "worshipped as a god").limit(1)
    )
    return found is not None


async def deify(ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: BeastProfileRow) -> bool:
    table = ctx.rules.beasts
    if (stat(beast, "renown") or 0) < table.deify_renown or (stat(beast, "terror") or 0) < table.deify_terror or beast.world_id is None:
        return False
    if await deified(ctx, beast.id) or not ctx.rng(f"deify.{beast.id}.{ctx.epoch}").chance(table.deify_chance):
        return False
    marks = await traits_of(ctx.session, row.species_entity_id) if row.species_entity_id is not None else set()
    second = next((domain for trait, domain in TERRORS.items() if trait in {item.value for item in marks}), None)
    god = await add_foreign_god(
        ctx.session,
        ctx.rules,
        ctx.rng(f"beast_god.{beast.id}"),
        ctx.epoch,
        NewForeignGod(
            name=beast.name,
            world_id=beast.world_id,
            domains=(Domain.HUNT, second),
            title="the Beast Worshipped",
            description=f"{beast.name}, feared until it was prayed to.",
        ),
    )
    await connect(ctx.session, beast.id, god.id, BondKind.SOURCE_OF, ctx.epoch, description="worshipped as a god")
    praying = await towns_near(ctx, atlas, row)
    for town in praying:
        await connect(ctx.session, town.id, god.id, BondKind.WORSHIPS, ctx.epoch, description=f"in dread of {beast.name}")
    roles: dict[IncidentRole, RoleValue] = {IncidentRole.SUBJECT: beast.id, IncidentRole.PRODUCT: god.id, IncidentRole.MEMBER: [town.id for town in praying]}
    facts: dict[str, FactInput] = {"renown": stat_or(beast, "renown", 0), "terror": stat_or(beast, "terror", 0)}
    await record_happening(ctx, "beasts.worshipped", roles=roles, facts=facts)
    return True


async def rob_hoard(ctx: TickContext, beast: EntityRow, thief: EntityRow) -> int:
    row = await ctx.session.get(BeastProfileRow, beast.id)
    home = await living_entity(ctx.session, thief.location_id)
    if row is None or home is None:
        return 0
    table = ctx.rules.beasts
    share = table.theft_pct / PERCENT * (1 - row.perception / PERCENT * table.perception_theft_pct / PERCENT)
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    carried = 0
    for key, value in sorted(row.hoard.items()):
        taken = round_half_up(value * share)
        if taken <= 0 or key not in COMMODITY_KEYS:
            continue
        stash(row, key, -taken)
        if key == CommodityKind.LUXURIES.value and home.entity_type in COMMUNITY_TYPES:
            carried += await inject_hoard(ctx, home, taken, MaterialKind.GOLD)
        else:
            carried += await ledger.add(home.id, CommodityKind(key), taken, GoodsFlow.LOOT)
    treasures = await owned_items(ctx, [beast.id])
    if treasures and ctx.rng(f"rob_item.{beast.id}.{thief.id}.{ctx.epoch}").chance(clamp_int(share * PERCENT, 0, PERCENT)):
        await hand_over(ctx, treasures[0], thief.id, ItemDeed.THEFT, f"stolen from the hoard of {beast.name}")
        carried += 1
    if carried:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=beast.id,
            subject_id=thief.id,
            kind=MemoryKind.CHEATED_US,
            magnitude=-PERCENT // 4,
            epoch=ctx.epoch,
            note="robbed its hoard",
        )
    return carried
