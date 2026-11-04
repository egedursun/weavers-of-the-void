from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProfileRow, SpeciesRangeRow, SpeciesYieldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.ecology import SIZE_ORDER, BeastTemper, SizeClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.models.entity_stats import BeastStats, LegendStats, PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.ecology.foodweb import raid_herds
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.economy.money import gain
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, connect, has_flag, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, shift_stat, stat

ACTIVE = frozenset({BeastTemper.HUNGRY, BeastTemper.TERRITORIAL, BeastTemper.ENRAGED})
COMMODITY_KEYS = frozenset(item.value for item in CommodityKind)
HELD = frozenset({BeastTemper.BOUND, BeastTemper.TAMED})
COWED = 60
HOARD_GOODS = (CommodityKind.LUXURIES, CommodityKind.LIVESTOCK, CommodityKind.GRAIN)
GREAT = SIZE_ORDER.index(SizeClass.HUGE)


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


async def profile_beast(ctx: TickContext, beast: EntityRow, species: EntityRow | None) -> BeastProfileRow:
    kind = await profile_of(ctx, species) if species is not None else None
    region = (await RegionAtlas.load(ctx.session)).top_region(beast.id)
    row = BeastProfileRow(
        beast_entity_id=beast.id,
        species_entity_id=species.id if species is not None else None,
        endurance=clamp_int((stat(beast, "hp") or PERCENT) // 4, 0, PERCENT),
        perception=clamp_int(stat(beast, "cunning") or PERCENT // 2, 0, PERCENT),
        willpower=clamp_int(stat(beast, "danger") or PERCENT // 2, 0, PERCENT),
        intelligence=clamp_int(stat(species, "intelligence") or stat(beast, "cunning") or 20, 0, PERCENT) if species is not None else 20,
        age=0,
        lifespan=max(1, (kind.lifespan_years if kind is not None else 100) * 3),
        size_class=kind.size_class if kind is not None and SIZE_ORDER.index(kind.size_class) >= GREAT else SizeClass.HUGE,
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


async def disturbed(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, region: int | None) -> bool:
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
    reach = ctx.rules.beasts.raid_reach
    lair = row.lair_place_id
    return [town for town in await canon(ctx.session, [EntityType.SETTLEMENT]) if lair is not None and atlas.distance(lair, town.id) <= reach]


async def raid(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, town: EntityRow) -> str:
    table = ctx.rules.beasts
    herds = await raid_herds(ctx, beast, town)
    if stat(town, "population") is not None:
        shift_stat(town, "population", -round_half_up((stat(town, "population") or 0) * table.raid_population_pct / PERCENT))
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    for commodity in HOARD_GOODS:
        taken = await ledger.take_units(town.id, commodity, table.raid_hoard, GoodsFlow.LOOT)
        if taken:
            row.hoard[commodity.value] = row.hoard.get(commodity.value, 0) + taken
            break
    row.raids += 1
    set_stats(
        beast,
        terror=clamp_int((stat(beast, "terror") or 0) + table.terror_gain, 0, PERCENT),
        renown=clamp_int((stat(beast, "renown") or 0) + table.renown_gain, 0, PERCENT),
    )
    await connect(ctx.session, beast.id, town.id, BondKind.HUNTS, ctx.epoch, description="raids")
    return f"{beast.name} fell on {town.name}" + (f" and carried off {herds} head of its herds" if herds else "")


async def tribute(ctx: TickContext, beast: EntityRow, row: BeastProfileRow, near: list[EntityRow]) -> int:
    if (stat(beast, "terror") or 0) < COWED:
        return 0
    paid = 0
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    for town in near:
        if (stat(town, "defense") or 0) >= (stat(beast, "strength") or 0):
            continue
        taken = await ledger.take_units(town.id, CommodityKind.LUXURIES, ctx.rules.beasts.tribute_hoard, GoodsFlow.TRIBUTE)
        if taken:
            row.hoard[CommodityKind.LUXURIES.value] = row.hoard.get(CommodityKind.LUXURIES.value, 0) + taken
            paid += 1
    return paid


async def dread(ctx: TickContext, beast: EntityRow, near: list[EntityRow], *, quiet: bool) -> None:
    table = ctx.rules.beasts
    terror = stat(beast, "terror") or 0
    for town in near:
        if stat(town, "prosperity") is not None:
            shift_stat(town, "prosperity", -round_half_up(table.terror_prosperity * terror / PERCENT))
    if quiet:
        set_stats(beast, terror=clamp_int(terror - table.terror_decay, 0, PERCENT))


async def guard(ctx: TickContext, row: BeastProfileRow) -> None:
    ward = await living_entity(ctx.session, row.bound_to_node_id)
    if ward is not None and stat(ward, "defense") is not None:
        set_stats(ward, defense=clamp_int((stat(ward, "defense") or 0) + ctx.rules.beasts.guard_defence, 0, PERCENT))


async def lair_cycle(ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: BeastProfileRow) -> str | None:
    table = ctx.rules.beasts
    rng = ctx.rng(f"lair.{beast.id}.{ctx.epoch}")
    if "age" not in row.locked:
        row.age += table.age_years
    if row.age > row.lifespan:
        return "old age"
    row.updated_epoch = ctx.epoch
    tamer = await bonded_state(ctx, beast.id)
    if tamer is not None and row.temper not in HELD and "temper" not in row.locked:
        row.temper, row.bound_to_node_id = BeastTemper.TAMED, tamer.source_node_id
    if row.temper in HELD:
        await guard(ctx, row)
        return None
    near = await towns_near(ctx, atlas, row)
    region = atlas.top_region(row.lair_place_id) if row.lair_place_id is not None else atlas.top_region(beast.id)
    if row.temper is BeastTemper.SLEEPING and "temper" not in row.locked:
        woke = rng.chance(table.wake_chance) or (await disturbed(ctx, beast, row, region) and rng.chance(table.disturb_chance))
        if woke:
            row.temper, row.woke_epoch = BeastTemper.HUNGRY, ctx.epoch
    paid = await tribute(ctx, beast, row, near)
    if row.temper not in ACTIVE or not near:
        await dread(ctx, beast, near, quiet=True)
        return f"tribute from {paid} towns" if paid else None
    target = await avenger_target(ctx, beast, near)
    if target is not None and "temper" not in row.locked:
        row.temper = BeastTemper.ENRAGED
    text = await raid(ctx, beast, row, target or rng.pick(near))
    await dread(ctx, beast, near, quiet=False)
    if row.temper is not BeastTemper.ENRAGED and "temper" not in row.locked and rng.chance(table.sleep_chance):
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


async def fall(ctx: TickContext, beast: EntityRow, row: BeastProfileRow) -> str:
    table = ctx.rules.beasts
    slayer = await slayer_of(ctx, beast.id)
    home = await living_entity(ctx.session, slayer.location_id) if slayer is not None else None
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    if home is not None and row.species_entity_id is not None:
        for item in await ctx.session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == row.species_entity_id)):
            if item.commodity is not None and item.material is not None:
                await ledger.add(home.id, item.commodity, table.corpse_yield * item.rate, GoodsFlow.EXTRACTION, material=item.material)
    hoard_value = sum(row.hoard.values())
    if hoard_value and home is not None:
        gain(home, round_half_up(hoard_value * table.hoard_wealth_pct / PERCENT))
    if hoard_value:
        treasure = await create_record(
            ctx,
            RecordSpec(
                name=f"The Hoard of {beast.name}",
                entity_type=EntityType.PLACE,
                stats=PlaceStats(danger=PERCENT // 10, mystery=PERCENT // 2),
                body=f"Where {beast.name} slept on what it had taken: {', '.join(f'{value} {key}' for key, value in sorted(row.hoard.items()))}.",
                power=2,
                world_id=beast.world_id,
                location_id=beast.location_id,
            ),
        )
        await connect(ctx.session, treasure.id, beast.id, BondKind.SOURCE_OF, ctx.epoch, description="its hoard")
    if slayer is not None:
        slayer.importance = (slayer.importance or 0) + table.slayer_renown
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


async def mount_of(ctx: TickContext, rider_id: int) -> EntityRow | None:
    beast_id = await ctx.session.scalar(
        select(BeastProfileRow.beast_entity_id).where(BeastProfileRow.bound_to_node_id == rider_id, BeastProfileRow.temper == BeastTemper.TAMED).limit(1)
    )
    return await living_entity(ctx.session, beast_id)


async def mounted_power(ctx: TickContext, rider_id: int) -> float:
    mount = await mount_of(ctx, rider_id)
    return 1 + ctx.rules.beasts.mount_power_pct / PERCENT * (stat(mount, "strength") or 0) / PERCENT if mount is not None else 1.0


async def bound_to(ctx: TickContext, owner_id: int) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(BeastProfileRow.beast_entity_id).where(BeastProfileRow.bound_to_node_id == owner_id, BeastProfileRow.temper == BeastTemper.BOUND)
    )
    found = [await living_entity(ctx.session, beast_id) for beast_id in list(rows)]
    return [beast for beast in found if beast is not None]


async def beast_dread(ctx: TickContext, foe_id: int) -> int:
    return ctx.rules.beasts.army_terror * len(await bound_to(ctx, foe_id))


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
    if row is None or home is None or not row.hoard:
        return 0
    share = ctx.rules.beasts.theft_pct / PERCENT
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    carried = 0
    for key, value in sorted(row.hoard.items()):
        taken = round_half_up(value * share)
        if taken <= 0 or key not in COMMODITY_KEYS:
            continue
        row.hoard[key] = value - taken
        carried += await ledger.add(home.id, CommodityKind(key), taken, GoodsFlow.LOOT)
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
