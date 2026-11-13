from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.vehicles import FRAMES, SEA_LADDER, FrameSpec
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.military import VesselArmament, VesselStatus
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import TravelMethod, VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.domain.models.entity_stats import LegendStats
from aerona.engine.collective.designs import DesignTally, design_power, fit_design, mend, wear_leg
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.mind.book import skill_level
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.services.war import current_war
from aerona.engine.vehicles.sections import batter_vessel, mend_vessel_sections
from aerona.rules.registry import Rules

STORMS = frozenset({WeatherKind.STORM, WeatherKind.MAGIC_STORM, WeatherKind.BLIZZARD, WeatherKind.SANDSTORM, WeatherKind.HAIL})
WINDY = frozenset({WeatherKind.STORM, WeatherKind.DROUGHT_WIND, WeatherKind.SANDSTORM})
EXOTIC_METHODS = frozenset({TravelMethod.DREAM_JOURNEY, TravelMethod.RIVER_OF_DEAD})
AFLOAT = frozenset({VesselStatus.AFLOAT, VesselStatus.DAMAGED})
BACKFILL_FIXUP = "military.vessel_profiles"


@dataclass
class SeaTally:
    voyages: int = 0
    storms: int = 0
    wrecks: int = 0
    ghosts: int = 0
    repaired: int = 0
    fights: int = 0
    legends: int = 0
    routes: int = 0
    designed: int = 0
    worn: int = 0
    failures: int = 0
    mended: int = 0


def frame_value(rules: Rules, frame: VehicleFrame, key: str) -> int:
    spec = FRAMES[frame]
    found = {"speed": spec.speed, "cargo": spec.cargo, "seaworthiness": spec.endurance}[key]
    return round_half_up(found * rules.seafaring.frame_scale_pct / PERCENT)


def fresh_profile(
    rules: Rules, vessel: EntityRow, frame: VehicleFrame, *, owner_id: int | None, home_port: int | None, kind: VehicleKind = VehicleKind.SHIP
) -> VesselProfileRow:
    spec: FrameSpec = FRAMES[frame]
    return VesselProfileRow(
        entity_id=vessel.id,
        kind=kind,
        frame=frame,
        condition=PERCENT,
        armament=[item.value for item in spec.armament],
        seaworthiness=frame_value(rules, frame, "seaworthiness"),
        cargo_capacity=min(frame_value(rules, frame, "cargo"), spec.crew * rules.seafaring.crew_per_cargo),
        crew=spec.crew,
        seamanship=0,
        home_port_entity_id=home_port,
        crew_community_entity_id=owner_id,
        renown=0,
        status=VesselStatus.DOCKED,
        voyages=0,
        updated_epoch=0,
        locked=[],
    )


def best_hull(knowledge: KnowledgeMap, owner_id: int | None, strangeness: int) -> VehicleFrame:
    if owner_id is None:
        return VehicleFrame.BOAT
    for frame in SEA_LADDER:
        spec = FRAMES[frame]
        if spec.branch is None or knowledge.level(owner_id, spec.branch) >= spec.level:
            return frame
    return VehicleFrame.LIVING_SHIP if strangeness >= FRAMES[VehicleFrame.LIVING_SHIP].strangeness else VehicleFrame.RAFT


async def owner_of(ctx: TickContext, vessel_id: int) -> EntityRow | None:
    bonds = await BondRepository(ctx.session).incoming(vessel_id, BondKind.OWNS)
    owner_id = bonds[0].source_node_id if bonds else None
    return await living_entity(ctx.session, owner_id)


async def backfill_vessels(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, BACKFILL_FIXUP) is not None:
        return 0
    knowledge = await KnowledgeMap.load(ctx.session)
    made = 0
    profiled = select(VesselProfileRow.entity_id)
    bare = await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.VESSEL, EntityRow.id.not_in(profiled)))
    for bare_vessel in list(bare):
        ctx.session.add(VesselProfileRow(entity_id=bare_vessel.id, kind=VehicleKind.SHIP, locked=[]))
    await ctx.session.flush()
    for row in list(await ctx.session.scalars(select(VesselProfileRow).where(VesselProfileRow.kind == VehicleKind.SHIP))):
        vessel = await ctx.session.get(EntityRow, row.entity_id)
        if vessel is None:
            continue
        owner = await owner_of(ctx, vessel.id)
        strangeness = stat(vessel, "strangeness") or 0
        hull = best_hull(knowledge, owner.id if owner is not None else None, strangeness)
        if (stat(vessel, "speed") or 0) >= FRAMES[VehicleFrame.SKYSHIP].speed and knowledge.level(
            owner.id if owner else 0, KnowledgeBranch.SKY_NAVIGATION
        ) >= 1:
            hull = VehicleFrame.SKYSHIP
        base = fresh_profile(ctx.rules, vessel, hull, owner_id=owner.id if owner is not None else None, home_port=vessel.location_id)
        for column in ("frame", "armament", "seaworthiness", "cargo_capacity", "home_port_entity_id", "crew_community_entity_id"):
            setattr(row, column, getattr(base, column))
        row.crew = stat_or(vessel, "crew", base.crew)
        row.condition = clamp_int(stat_or(vessel, "armor", PERCENT), 0, PERCENT)
        row.status = VesselStatus.DOCKED if vessel.status is EntityStatus.CANON else VesselStatus.WRECKED
        row.locked = []
        made += 1
    ctx.session.add(AppliedFixupRow(key=BACKFILL_FIXUP, result={"vessels": made}))
    await ctx.session.flush()
    return made


async def seamanship_of(ctx: TickContext, row: VesselProfileRow, knowledge: KnowledgeMap) -> int:
    captain = await skill_level(ctx.session, row.captain_entity_id, SkillKind.SAILING) if row.captain_entity_id is not None else 0
    crew = knowledge.level(row.crew_community_entity_id or 0, KnowledgeBranch.SEAFARING) * PERCENT // 3
    return clamp_int(max(captain, crew), 0, PERCENT)


def storm_damage(rules: Rules, row: VesselProfileRow) -> int:
    table = rules.seafaring
    shield = (1 - row.seaworthiness / PERCENT * table.seaworthiness_pct / PERCENT) * (1 - row.seamanship / PERCENT * table.seamanship_pct / PERCENT)
    return round_half_up(table.storm_damage * shield)


async def wreck(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, reason: str, tally: SeaTally) -> None:
    table = ctx.rules.seafaring
    strange = (stat(vessel, "strangeness") or 0) >= table.strange_route
    if strange and ctx.rng(f"ghost_ship.{vessel.id}.{ctx.epoch}").chance(table.ghost_chance):
        row.status = VesselStatus.GHOST
        vessel.engine_kind = EngineKind.GHOST_SHIP
        tally.ghosts += 1
        text = f"{vessel.name} went down {reason}, and it is still seen on the routes it sailed, though no living crew sails it."
        await ctx.chronicle(ChronicleKind.WORLD, text, template_key="seafaring.ghost_ship", entity_ids=(vessel.id,), feed_category=FeedCategory.VOYAGE)
        return
    row.status = VesselStatus.WRECKED
    tally.wrecks += 1
    await retire_in(ctx, vessel, f"wrecked {reason}", close_bonds=False)
    await ctx.chronicle(
        ChronicleKind.DISASTER,
        f"{vessel.name} was wrecked {reason}.",
        template_key="seafaring.wreck",
        entity_ids=(vessel.id,),
        feed_category=FeedCategory.VOYAGE,
    )


async def weather_leg(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, weather: WeatherKind | None, tally: SeaTally) -> None:
    table = ctx.rules.seafaring
    if weather not in STORMS:
        return
    tally.storms += 1
    damage = storm_damage(ctx.rules, row)
    if "condition" not in row.locked:
        row.condition = clamp_int(row.condition - damage, 0, PERCENT)
    await batter_vessel(ctx, vessel, row, max(0, damage // ctx.rules.vehicles.section_hit), "storm")
    lost = round_half_up(row.crew * table.storm_crew_pct / PERCENT * (1 - row.seaworthiness / PERCENT))
    if "crew" not in row.locked:
        row.crew = max(0, row.crew - lost)
    if row.condition <= table.wreck_condition:
        await wreck(ctx, vessel, row, "in a storm at sea", tally)
        return
    row.status = VesselStatus.DAMAGED if row.condition < PERCENT // 2 else VesselStatus.AFLOAT
    if "renown" not in row.locked:
        row.renown += table.renown_per_storm
    await ctx.chronicle(
        ChronicleKind.DISASTER,
        f"{vessel.name} rode out a storm; the hull took {damage} damage and {lost} crew were lost.",
        template_key="seafaring.storm",
        entity_ids=(vessel.id,),
        feed_category=FeedCategory.VOYAGE,
    )


async def strange_waters(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, tally: SeaTally) -> None:
    table = ctx.rules.seafaring
    strangeness = stat_or(vessel, "strangeness", FRAMES[row.frame].strangeness)
    if strangeness < table.strange_route:
        return
    hidden = await ctx.session.scalars(
        select(RouteRow).where(
            RouteRow.method.in_(list(EXOTIC_METHODS)),
            RouteRow.known.is_(False),
            (RouteRow.world_a_id == vessel.world_id) | (RouteRow.world_b_id == vessel.world_id),
        )
    )
    for route in hidden:
        route.known = True
        tally.routes += 1
    beings = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == vessel.world_id)
    )
    for being in beings:
        shift_stat(being, "interest", table.outer_attention)


async def repair(ctx: TickContext, row: VesselProfileRow, tally: SeaTally) -> int:
    table = ctx.rules.seafaring
    if (row.status in AFLOAT and row.condition >= PERCENT // 2) or row.condition >= PERCENT or "condition" in row.locked:
        return 0
    port = row.home_port_entity_id
    yard = await ctx.session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == port, WorkshopRow.kind == WorkshopKind.SHIPYARD).limit(1))
    owner = await living_entity(ctx.session, port)
    if yard is None or owner is None:
        return 0
    affordable = (stat(owner, "wealth") or 0) // table.repair_cost if table.repair_cost else PERCENT
    gain = min(PERCENT - row.condition, table.repair_per_epoch * yard.level, affordable)
    if gain <= 0:
        return 0
    await mend_vessel_sections(ctx.session, row.entity_id, gain)
    cost = gain * table.repair_cost
    shift_stat(owner, "wealth", -cost)
    row.condition = clamp_int(row.condition + gain, 0, PERCENT)
    row.status = VesselStatus.DOCKED
    tally.repaired += 1
    return gain


async def legend_of(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, tally: SeaTally) -> EntityRow | None:
    table = ctx.rules.seafaring
    if row.renown < table.legend_renown or row.legend_entity_id is not None:
        return None
    feat = "sailed a hidden route" if (stat(vessel, "strangeness") or 0) >= table.strange_route else "outlived every storm"
    legend = await create_record(
        ctx,
        RecordSpec(
            name=f"The Ship That {feat.split(' ', 1)[0].title()} {feat.split(' ', 1)[1].title()}",
            entity_type=EntityType.LEGEND,
            stats=LegendStats(spread=min(PERCENT, row.renown)),
            body=f"Sailors tell of {vessel.name}, the ship that {feat}.",
            power=clamp_int(row.renown // 10, 1, 10),
            world_id=vessel.world_id,
            location_id=row.home_port_entity_id,
            subtype="ship legend",
        ),
    )
    await BondRepository(ctx.session).connect(BondDraft(legend.id, vessel.id, BondKind.TELLS_OF, ctx.epoch, "the ship of the tale"))
    row.legend_entity_id = legend.id
    tally.legends += 1
    return legend


def vessel_power(rules: Rules, row: VesselProfileRow, weather: WeatherKind | None) -> float:
    table = rules.seafaring
    weights = {
        VesselArmament.RAMS.value: table.ram_pct,
        VesselArmament.MISSILES.value: table.missile_pct,
        VesselArmament.SIEGE_ENGINES.value: table.engine_pct,
        VesselArmament.RITES.value: table.rite_pct,
    }
    arms = sum(weights.get(item, 0) for item in row.armament) / PERCENT
    if weather in WINDY and VesselArmament.RITES.value in row.armament:
        arms *= table.fire_wind_pct / PERCENT
    crew = row.crew * table.boarding_pct / PERCENT / max(1, FRAMES[row.frame].crew)
    return (1 + arms + crew) * (0.5 + row.condition / (2 * PERCENT)) * (1 + row.seamanship / PERCENT)


async def sea_fight(
    ctx: TickContext, first: tuple[EntityRow, VesselProfileRow], second: tuple[EntityRow, VesselProfileRow], weather: WeatherKind | None, tally: SeaTally
) -> EntityRow:
    rng = ctx.rng(f"vessel_fight.{first[0].id}.{second[0].id}.{ctx.epoch}")
    powers = [vessel_power(ctx.rules, row, weather) * await design_power(ctx.session, row) * (0.8 + rng.below(40) / PERCENT) for _, row in (first, second)]
    winner, loser = (first, second) if powers[0] >= powers[1] else (second, first)
    table = ctx.rules.seafaring
    if "condition" not in loser[1].locked:
        loser[1].condition = clamp_int(loser[1].condition - table.combat_damage, 0, PERCENT)
    await batter_vessel(ctx, loser[0], loser[1], max(1, table.combat_damage // ctx.rules.vehicles.section_hit), f"sea_fight.{winner[0].id}")
    if "renown" not in winner[1].locked:
        winner[1].renown += table.renown_per_victory
    tally.fights += 1
    await ctx.chronicle(
        ChronicleKind.WAR,
        f"{winner[0].name} met {loser[0].name} at sea and beat it.",
        template_key="seafaring.sea_fight",
        entity_ids=(winner[0].id, loser[0].id),
        feed_category=FeedCategory.WAR,
    )
    if loser[1].condition <= table.wreck_condition:
        await wreck(ctx, loser[0], loser[1], f"by {winner[0].name}", tally)
    return winner[0]


async def seas(ctx: TickContext) -> SeaTally:
    tally = SeaTally()
    designs = DesignTally()
    await backfill_vessels(ctx)
    ground = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    atlas = await RegionAtlas.load(ctx.session)
    knowledge = await KnowledgeMap.load(ctx.session)
    afloat: list[tuple[EntityRow, VesselProfileRow, EntityRow | None]] = []
    for row in list(await ctx.session.scalars(select(VesselProfileRow).where(VesselProfileRow.kind == VehicleKind.SHIP).order_by(VesselProfileRow.entity_id))):
        vessel = await living_entity(ctx.session, row.entity_id)
        if vessel is None or row.status in {VesselStatus.WRECKED, VesselStatus.GHOST}:
            continue
        if "seamanship" not in row.locked:
            row.seamanship = await seamanship_of(ctx, row, knowledge)
        owner = await owner_of(ctx, vessel.id)
        row.region_entity_id = row.region_entity_id or atlas.top_region(row.home_port_entity_id) or atlas.top_region(vessel.id)
        if row.design_id is None:
            await fit_design(ctx, vessel, row, owner.id if owner is not None else row.home_port_entity_id)
            tally.designed += row.design_id is not None
        if row.status is VesselStatus.DOCKED and row.condition < PERCENT:
            await repair(ctx, row, tally)
        if row.status is VesselStatus.DOCKED:
            await mend(ctx, row, designs)
        sailing = row.status in AFLOAT or (owner is not None and row.crew > 0 and row.condition >= PERCENT // 2)
        if sailing and "status" not in row.locked:
            row.status = VesselStatus.AFLOAT if row.condition >= PERCENT // 2 else VesselStatus.DAMAGED
        if row.status not in AFLOAT:
            continue
        region = ground.regions.get(row.region_entity_id or -1)
        season = ground.season_at(vessel.world_id, ctx.epoch) if region is not None else None
        weather = ground.weather(ctx.environment.world_seed, ctx.epoch, region, season, f"voyage.{vessel.id}").kind if region is not None else None
        row.voyages += 1
        tally.voyages += 1
        await weather_leg(ctx, vessel, row, weather, tally)
        if row.status in AFLOAT:
            await wear_leg(ctx, vessel, row, stormy=weather in STORMS, tally=designs)
        if row.status in AFLOAT:
            row.renown += ctx.rules.seafaring.renown_per_voyage if "renown" not in row.locked else 0
            await strange_waters(ctx, vessel, row, tally)
            await legend_of(ctx, vessel, row, tally)
            afloat.append((vessel, row, owner))
        row.updated_epoch = ctx.epoch
    await skirmishes(ctx, afloat, tally)
    tally.worn, tally.failures, tally.mended = designs.worn, designs.failures, designs.mended
    return tally


async def skirmishes(ctx: TickContext, afloat: list[tuple[EntityRow, VesselProfileRow, EntityRow | None]], tally: SeaTally) -> None:
    seen: set[int] = set()
    for index, (vessel, row, owner) in enumerate(afloat):
        if owner is None or vessel.id in seen:
            continue
        for other, other_row, other_owner in afloat[index + 1 :]:
            if other_owner is None or other.id in seen or other_row.region_entity_id != row.region_entity_id:
                continue
            if await current_war(ctx.session, owner.id, other_owner.id) is None:
                continue
            if not ctx.rng(f"fleet_meet.{vessel.id}.{other.id}.{ctx.epoch}").chance(ctx.rules.seafaring.fleet_chance):
                continue
            await sea_fight(ctx, (vessel, row), (other, other_row), None, tally)
            seen.update({vessel.id, other.id})
            break


async def fleet_of(ctx: TickContext, army_id: int) -> list[tuple[EntityRow, VesselProfileRow]]:
    rows = await ctx.session.scalars(select(VesselProfileRow).where(VesselProfileRow.fleet_army_entity_id == army_id))
    found = []
    for row in rows:
        vessel = await living_entity(ctx.session, row.entity_id)
        if vessel is not None and row.status not in {VesselStatus.WRECKED, VesselStatus.GHOST}:
            found.append((vessel, row))
    return found


async def batter_fleet(ctx: TickContext, army_id: int, share: float, *, region_id: int | None) -> int:
    damaged = 0
    tally = SeaTally()
    for vessel, row in await fleet_of(ctx, army_id):
        row.region_entity_id = region_id or row.region_entity_id
        if "condition" not in row.locked:
            row.condition = clamp_int(row.condition - round_half_up(PERCENT * share), 0, PERCENT)
        damaged += 1
        if row.condition <= ctx.rules.seafaring.wreck_condition:
            await wreck(ctx, vessel, row, "in a sea battle", tally)
    return damaged


async def fleet_bonus(ctx: TickContext, army_id: int, weather: WeatherKind | None) -> float:
    return sum(vessel_power(ctx.rules, row, weather) for _, row in await fleet_of(ctx, army_id))


async def renown_fleet(ctx: TickContext, army_id: int) -> None:
    for _, row in await fleet_of(ctx, army_id):
        if "renown" not in row.locked:
            row.renown += ctx.rules.seafaring.renown_per_victory


async def muster_fleet(ctx: TickContext, army: EntityRow, owner: EntityRow) -> int:
    from_owner = select(VesselProfileRow).where(
        VesselProfileRow.kind == VehicleKind.SHIP, VesselProfileRow.status.in_([VesselStatus.DOCKED, VesselStatus.AFLOAT])
    )
    attached = 0
    for row in await ctx.session.scalars(from_owner.order_by(VesselProfileRow.entity_id)):
        if row.fleet_army_entity_id == army.id or "fleet_army_entity_id" in row.locked:
            continue
        current = await living_entity(ctx.session, row.fleet_army_entity_id)
        if current is not None:
            continue
        holder = await owner_of(ctx, row.entity_id)
        if holder is None or holder.id != owner.id:
            continue
        row.fleet_army_entity_id = army.id
        attached += 1
    return attached
