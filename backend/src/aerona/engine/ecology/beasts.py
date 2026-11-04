from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import HouseMemberRow, TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CurseKind, ItemClass, ItemDeed
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.ecology import SIZE_ORDER, BeastTemper, SizeClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind, TreatyStatus
from aerona.domain.models.entity_stats import BeastStats, ItemStats, LegendStats, PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.ecology.foodweb import raid_herds
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.economy.money import inject_hoard
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.gods.queries import community_of
from aerona.engine.lore.history import record
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.polity.accords import Clause, end_treaty, sign
from aerona.engine.polity.treaties import breach
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, close, connect, has_flag, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, shift_stat, stat
from aerona.rules.registry import Rules

ACTIVE = frozenset({BeastTemper.HUNGRY, BeastTemper.TERRITORIAL, BeastTemper.ENRAGED})
COMMODITY_KEYS = frozenset(item.value for item in CommodityKind)
HELD = frozenset({BeastTemper.BOUND, BeastTemper.TAMED})
HOARD_GOODS = (CommodityKind.LUXURIES, CommodityKind.LIVESTOCK, CommodityKind.GRAIN)
GREAT = SIZE_ORDER.index(SizeClass.HUGE)
RIDEABLE = frozenset({SizeClass.LARGE, SizeClass.HUGE, SizeClass.COLOSSAL})
TROPHY_CLASSES = {
    MaterialKind.DRAGONBONE: ItemClass.BLADE,
    MaterialKind.IVORY: ItemClass.JEWEL,
    MaterialKind.CHITIN: ItemClass.ARMOUR,
    MaterialKind.HIDE: ItemClass.ARMOUR,
    MaterialKind.BONE: ItemClass.TOOL,
}
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
        endurance=clamp_int((stat(beast, "hp") or PERCENT) // 4, 0, PERCENT),
        perception=clamp_int(stat(beast, "cunning") or PERCENT // 2, 0, PERCENT),
        willpower=clamp_int(stat(beast, "danger") or PERCENT // 2, 0, PERCENT),
        intelligence=clamp_int(stat(species, "intelligence") or stat(beast, "cunning") or 20, 0, PERCENT) if species is not None else 20,
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
    return row


async def champions(ctx: TickContext) -> int:
    table = ctx.rules.beasts
    risen = 0
    held = set(await ctx.session.scalars(select(BeastProfileRow.species_entity_id).where(BeastProfileRow.species_entity_id.is_not(None))))
    for species in await canon(ctx.session, [EntityType.SPECIES]):
        if risen >= table.promotion_cap or species.id in held:
            continue
        kind = await ctx.session.get(SpeciesProfileRow, species.id)
        huge = kind is not None and SIZE_ORDER.index(kind.size_class) >= GREAT
        mighty = await has_flag(ctx.session, species.id, EntityFlag.MEGAFAUNA) or (huge and (stat(species, "danger") or 0) >= table.promotion_danger)
        if not mighty or not ctx.rng(f"champion.{species.id}.{ctx.epoch}").chance(table.promotion_chance):
            continue
        home = await ctx.session.scalar(
            select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == species.id).order_by(SpeciesRangeRow.abundance.desc()).limit(1)
        )
        region = await living_entity(ctx.session, home) if home is not None else None
        beast = await create_record(
            ctx,
            RecordSpec(
                name=f"The Great {species.name}" if region is None else f"The {species.name} of {region.name}",
                entity_type=EntityType.BEAST,
                stats=BeastStats(
                    hp=(stat(species, "hp") or PERCENT) * 2,
                    danger=clamp_int((stat(species, "danger") or 0) + PERCENT // 10, 0, PERCENT),
                    strength=clamp_int((stat(species, "strength") or PERCENT // 2) + PERCENT // 5, 0, PERCENT),
                    agility=stat(species, "agility"),
                    cunning=stat(species, "intelligence"),
                    renown=PERCENT // 5,
                    terror=PERCENT // 10,
                ),
                body=f"The greatest of its kind, the terror or the guardian of {region.name if region is not None else 'its lands'}.",
                power=max(species.power_level, 3),
                world_id=species.world_id,
                location_id=region.id if region is not None else species.location_id,
            ),
        )
        await profile_beast(ctx, beast, species)
        await connect(ctx.session, beast.id, species.id, BondKind.DESCENDS_FROM, ctx.epoch, description="the greatest of its kind")
        await note(ctx, f"{beast.name} rose among the {species.name}, and the land learned its name.", key="beasts.risen", ids=[beast.id, species.id])
        risen += 1
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


async def raid(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, town: EntityRow) -> str:
    table = ctx.rules.beasts
    scale = size_factor(ctx.rules, row)
    herds = await raid_herds(ctx, beast, town)
    if stat(town, "population") is not None:
        shift_stat(town, "population", -round_half_up((stat(town, "population") or 0) * table.raid_population_pct * scale / PERCENT))
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    for commodity in HOARD_GOODS:
        taken = await ledger.take_units(town.id, commodity, round_half_up(table.raid_hoard * scale), GoodsFlow.LOOT)
        if taken:
            stash(row, commodity.value, taken)
            break
    treasure = await seize_treasure(ctx, beast, town)
    row.raids += 1
    set_stats(
        beast,
        terror=clamp_int((stat(beast, "terror") or 0) + table.terror_gain, 0, PERCENT),
        renown=clamp_int((stat(beast, "renown") or 0) + table.renown_gain, 0, PERCENT),
    )
    await connect(ctx.session, beast.id, town.id, BondKind.HUNTS, ctx.epoch, description="raids")
    item = await ctx.session.get(EntityRow, treasure) if treasure is not None else None
    taken_text = f" and carried off {herds} head of its herds" if herds else ""
    return f"{beast.name} fell on {town.name}{taken_text}" + (f", bearing {item.name} to its hoard" if item is not None else "")


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
            await end_treaty(ctx, profile, TreatyStatus.EXPIRED, f"the dread of {beast.name} faded")
        return 0, None
    paying = {clause.obligor_node_id for _, clause in sworn}
    for town in near:
        if town.id not in paying and (stat(town, "defense") or 0) < (stat(beast, "strength") or 0):
            await swear_tribute(ctx, beast, town)
    paid = 0
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
        elif due > 0:
            await breach(ctx, profile, payer.id, clause=clause, reason=f"it could not pay {beast.name} its tribute")
            defiant = defiant or payer
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
    bold = [town for town in near if town.id not in shunned]
    return rng.pick(bold) if bold else None


async def lair_cycle(ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: BeastProfileRow) -> str | None:
    table = ctx.rules.beasts
    rng = ctx.rng(f"lair.{beast.id}.{ctx.epoch}")
    if "age" not in row.locked:
        row.age += table.age_years
    if row.age > row.lifespan:
        return "old age"
    row.updated_epoch = ctx.epoch
    tamer = await bonded_state(ctx, beast.id)
    if tamer is not None and row.temper not in HELD and "temper" not in row.locked and rng.chance(tame_chance(ctx.rules, row)):
        row.temper, row.bound_to_node_id = BeastTemper.TAMED, tamer.source_node_id
    if row.temper in HELD:
        await guard(ctx, row)
        return None
    near = await towns_near(ctx, atlas, row)
    region = atlas.top_region(row.lair_place_id) if row.lair_place_id is not None else atlas.top_region(beast.id)
    if row.temper is BeastTemper.SLEEPING and "temper" not in row.locked:
        woke = rng.chance(table.wake_chance) or (await disturbed(ctx, beast, region) and rng.chance(wake_chance(ctx.rules, row)))
        if woke:
            row.temper, row.woke_epoch = BeastTemper.HUNGRY, ctx.epoch
    paid, defiant = await tribute(ctx, beast, row, near)
    if defiant is not None and "temper" not in row.locked:
        row.temper = BeastTemper.ENRAGED
    if row.temper not in ACTIVE or not near:
        await dread(ctx, beast, near, quiet=True)
        return f"tribute from {paid} towns" if paid else None
    target = await avenger_target(ctx, beast, near)
    if target is not None and "temper" not in row.locked:
        row.temper = BeastTemper.ENRAGED
    prey = target or await pick_prey(ctx, beast, near, defiant)
    if prey is None:
        await dread(ctx, beast, near, quiet=False)
        return f"{beast.name} prowled but shunned the towns of the beast slayers"
    text = await raid(ctx, beast, row, prey)
    await dread(ctx, beast, near, quiet=False)
    if row.temper is not BeastTemper.ENRAGED and "temper" not in row.locked and rng.chance(rest_chance(ctx.rules, row)):
        row.temper = BeastTemper.SLEEPING
    return text


async def slayer_of(ctx: TickContext, beast_id: int) -> EntityRow | None:
    killer = await ctx.session.scalar(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == beast_id, BondRow.kind.in_([BondKind.KILLED, BondKind.DESTROYED]))
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    return await ctx.session.get(EntityRow, killer) if killer is not None else None


async def trophy(ctx: TickContext, beast: EntityRow, slayer: EntityRow, item: SpeciesYieldRow, material: MaterialKind) -> EntityRow:
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
            material=material.value,
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
    await connect(ctx.session, slayer.id, made.id, BondKind.OWNS, ctx.epoch, description=f"slew {beast.name}")
    record(ctx, made.id, ItemDeed.KILL, slayer.id, f"cut from {beast.name} by {slayer.name}")
    return made


async def corpse(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, slayer: EntityRow) -> int:
    if row.species_entity_id is None:
        return 0
    given = 0
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    for item in list(await ctx.session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == row.species_entity_id))):
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
    for profile, _ in await tribute_clauses(ctx, beast.id):
        await end_treaty(ctx, profile, TreatyStatus.FULFILLED, f"{beast.name} is dead")
    if slayer is not None:
        await corpse(ctx, beast, row, slayer)
        await loot(ctx, row, slayer)
    treasures = await owned_items(ctx, [beast.id])
    if any(value > 0 for value in row.hoard.values()) or treasures:
        place = await create_record(
            ctx,
            RecordSpec(
                name=f"The Hoard of {beast.name}",
                entity_type=EntityType.PLACE,
                stats=PlaceStats(danger=PERCENT // 10, mystery=PERCENT // 2),
                body=f"Where {beast.name} slept on what it had taken: {', '.join(f'{value} {key}' for key, value in sorted(row.hoard.items()) if value > 0)}.",
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
    row.hoard, row.lair_place_id = {}, None
    return f"{beast.name} is dead" + (f" by the hand of {slayer.name}" if slayer is not None else "")


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


async def deify(ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: BeastProfileRow) -> str | None:
    table = ctx.rules.beasts
    if (stat(beast, "renown") or 0) < table.deify_renown or (stat(beast, "terror") or 0) < table.deify_terror or beast.world_id is None:
        return None
    if await deified(ctx, beast.id) or not ctx.rng(f"deify.{beast.id}.{ctx.epoch}").chance(table.deify_chance):
        return None
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
    for town in await towns_near(ctx, atlas, row):
        await connect(ctx.session, town.id, god.id, BondKind.WORSHIPS, ctx.epoch, description=f"in dread of {beast.name}")
    return f"the towns near its lair began to pray to {beast.name}"


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
