from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.engagement import ENGINE_ARMS, LIFTED, MISSILE_ARMS, RAM_ARMS, RITE_ARMS, WATERBORNE, WEATHERED, WIND_ARMS
from aerona.catalog.vehicles import FRAMES, SEA_LADDER, FrameSpec
from aerona.catalog.weather import has_trait
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.vehicles import DesignMountRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind, WeatherTrait
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepOutcome
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import TravelMethod, VehicleKind
from aerona.domain.enums.vehicles import VehicleDomain, VehicleFrame
from aerona.domain.models.entity_stats import LegendStats
from aerona.engine.collective.designs import DesignTally, arm_mounts, design_power, fit_design, mend, wear_leg
from aerona.engine.context import TickContext
from aerona.engine.crafts.cover import insured_loss
from aerona.engine.economy.purse import give_coin
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.means.navigation import accuracy_of
from aerona.engine.mind.book import skill_level
from aerona.engine.mortal.standing import add_renown
from aerona.engine.operations.crews import backfill_crews, crew_power, fitted_stations, lives_saved, storm_care
from aerona.engine.operations.engagement import SAILED, Engagement, Weapon, domain_of, engage, weapons_of
from aerona.engine.operations.sail import SailTally, crews_of, set_sail, ship_state, take_prize
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining
from aerona.engine.services.war import current_war
from aerona.engine.vehicles.sections import mend_vessel_sections
from aerona.engine.vehicles.wrecks import battered, wreck_crew
from aerona.rules.registry import Rules

EXOTIC_METHODS = frozenset({TravelMethod.DREAM_JOURNEY, TravelMethod.DEATH_CURRENT})
AFLOAT = frozenset({VesselStatus.AFLOAT, VesselStatus.DAMAGED})
BACKFILL_FIXUP = "military.vessel_profiles"
MOUNTS_FIXUP = "military.vessel_mounts"


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
    prize_money: int = 0
    crews_added: int = 0
    sail: SailTally = field(default_factory=SailTally)


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
        for column in ("frame", "seaworthiness", "cargo_capacity", "home_port_entity_id", "crew_community_entity_id"):
            setattr(row, column, getattr(base, column))
        row.crew = stat_or(vessel, "crew", base.crew)
        row.condition = clamp_int(stat_or(vessel, "armor", PERCENT), 0, PERCENT)
        row.status = VesselStatus.DOCKED if vessel.status is EntityStatus.CANON else VesselStatus.WRECKED
        row.locked = []
        made += 1
    ctx.session.add(AppliedFixupRow(key=BACKFILL_FIXUP, result={"vessels": made}))
    await ctx.session.flush()
    return made


async def arm_unarmed(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, MOUNTS_FIXUP) is not None:
        return 0
    knowledge = await KnowledgeMap.load(ctx.session)
    armed = waiting = 0
    designs = select(VesselProfileRow.design_id).where(VesselProfileRow.design_id.is_not(None)).distinct().order_by(VesselProfileRow.design_id)
    for design_id in list(await ctx.session.scalars(designs)):
        design = await ctx.session.get(DesignRow, design_id)
        mounted = await ctx.session.scalar(select(DesignMountRow.id).where(DesignMountRow.design_id == design_id).limit(1))
        if design is None or mounted is not None or "mounts" in (design.locked or []):
            continue
        if design.owner_entity_id is not None and held(design.owner_entity_id):
            waiting += 1
            continue
        owner = await living_entity(ctx.session, design.owner_entity_id) if design.owner_entity_id is not None else None
        await arm_mounts(ctx, design, owner, knowledge)
        armed += 1
    if not waiting:
        ctx.session.add(AppliedFixupRow(key=MOUNTS_FIXUP, result={"designs": armed}))
    await ctx.session.flush()
    return armed


async def seamanship_of(ctx: TickContext, row: VesselProfileRow, knowledge: KnowledgeMap) -> int:
    captain = await skill_level(ctx.session, row.captain_entity_id, SkillKind.SAILING) if row.captain_entity_id is not None else 0
    crew = knowledge.level(row.crew_community_entity_id or 0, KnowledgeBranch.SEAFARING) * PERCENT // 3
    return clamp_int(max(captain, crew), 0, PERCENT)


def storm_damage(rules: Rules, row: VesselProfileRow) -> int:
    table = rules.seafaring
    shield = (1 - row.seaworthiness / PERCENT * table.seaworthiness_pct / PERCENT) * (1 - row.seamanship / PERCENT * table.seamanship_pct / PERCENT)
    return round_half_up(table.storm_damage * shield)


async def haunt(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, tally: SeaTally, *, cause: int | None) -> bool:
    table = ctx.rules.seafaring
    strange = (stat(vessel, "strangeness") or 0) >= table.strange_route
    if not strange or not ctx.rng(f"ghost_ship.{vessel.id}.{ctx.epoch}").chance(table.ghost_chance):
        return False
    row.status = VesselStatus.GHOST
    vessel.engine_kind = EngineKind.GHOST_SHIP
    tally.ghosts += 1
    await record(ctx, "seafaring.ghost_ship", roles={IncidentRole.SUBJECT: vessel.id}, place=row.region_entity_id, cause=cause)
    return True


async def sink(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, reason: str, tally: SeaTally, *, cause: int | None) -> None:
    if await haunt(ctx, vessel, row, tally, cause=cause):
        return
    row.status = VesselStatus.WRECKED
    tally.wrecks += 1
    await retire_in(ctx, vessel, reason, close_bonds=False)


async def wreck(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, weather: WeatherKind, tally: SeaTally) -> None:
    if await haunt(ctx, vessel, row, tally, cause=None):
        return
    row.status = VesselStatus.WRECKED
    tally.wrecks += 1
    await retire_in(ctx, vessel, f"wrecked by the {spoken(weather)}", close_bonds=False)
    await record(ctx, "seafaring.wreck", roles={IncidentRole.SUBJECT: vessel.id}, facts={"weather": weather}, place=row.region_entity_id)
    await insured_loss(ctx, row.home_port_entity_id, InsuranceCover.VESSEL, ctx.rules.insurance.vessel_payout)


def icing(rules: Rules, damage: int, *, stormy: bool, icy: bool) -> int:
    share = rules.weather.icing_hull_pct
    if not icy:
        return damage
    return damage * (PERCENT + share) // PERCENT if stormy else damage * share // PERCENT


async def weather_leg(ctx: TickContext, vessel: EntityRow, row: VesselProfileRow, weather: WeatherKind | None, tally: SeaTally) -> None:
    table = ctx.rules.seafaring
    stormy, icy = has_trait(weather, WeatherTrait.STORM), has_trait(weather, WeatherTrait.ICY)
    if weather is None or not (stormy or icy) or domain_of(row) not in WEATHERED:
        return
    tally.storms += 1
    crews, fitted = await crews_of(ctx, vessel.id, row), await fitted_stations(ctx.session, vessel.id, row)
    accuracy = await accuracy_of(ctx, row.home_port_entity_id) if row.home_port_entity_id is not None else 0
    with explaining() as found:
        care = 1 - storm_care(ctx.rules, row, crews, fitted, accuracy)
        damage = round_half_up(icing(ctx.rules, storm_damage(ctx.rules, row), stormy=stormy, icy=icy) * care)
    terms = found.snapshot()
    if "condition" not in row.locked:
        row.condition = clamp_int(row.condition - damage, 0, PERCENT)
    await battered(ctx, vessel, row, max(0, damage // ctx.rules.vehicles.section_hit), "storm")
    spared = 1 - lives_saved(ctx.rules, row, crews, fitted)
    lost = round_half_up(row.crew * table.storm_crew_pct / PERCENT * (1 - row.seaworthiness / PERCENT) * spared)
    if "crew" not in row.locked:
        row.crew = max(0, row.crew - lost)
    if row.condition <= table.wreck_condition:
        await wreck(ctx, vessel, row, weather, tally)
        return
    row.status = VesselStatus.DAMAGED if row.condition < PERCENT // 2 else VesselStatus.AFLOAT
    if "renown" not in row.locked:
        row.renown += table.renown_per_storm
    await record(
        ctx,
        "seafaring.storm",
        roles={IncidentRole.SUBJECT: vessel.id},
        facts={"weather": weather, "damage": damage, "lost": lost},
        terms=terms,
        place=row.region_entity_id,
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
    feat = "travelled a hidden route" if (stat(vessel, "strangeness") or 0) >= table.strange_route else "outlived every storm"
    legend = await create_record(
        ctx,
        RecordSpec(
            name=f"The Vessel That {feat.split(' ', 1)[0].title()} {feat.split(' ', 1)[1].title()}",
            entity_type=EntityType.LEGEND,
            stats=LegendStats(spread=min(PERCENT, row.renown)),
            body=f"Crews tell of {vessel.name}, the vessel that {feat}.",
            power=clamp_int(row.renown // 10, 1, 10),
            world_id=vessel.world_id,
            location_id=row.home_port_entity_id,
            subtype="vessel legend",
        ),
    )
    await BondRepository(ctx.session).connect(BondDraft(legend.id, vessel.id, BondKind.TELLS_OF, ctx.epoch, "the vessel of the tale"))
    row.legend_entity_id = legend.id
    tally.legends += 1
    return legend


def arms_weight(rules: Rules, weapons: Sequence[Weapon], weather: WeatherKind | None) -> float:
    table = rules.seafaring
    weights = ((RAM_ARMS, table.ram_pct), (MISSILE_ARMS, table.missile_pct), (ENGINE_ARMS, table.engine_pct), (RITE_ARMS, table.rite_pct))
    total = 0.0
    for weapon in weapons:
        family = weapon.family
        weight = float(next((pct for arms, pct in weights if family in arms), table.boarding_pct) if family is not None else table.boarding_pct)
        if has_trait(weather, WeatherTrait.WINDY) and family in WIND_ARMS:
            weight = weight * table.fire_wind_pct / PERCENT
        total += weight * weapon.count
    return total / PERCENT


def vessel_power(rules: Rules, row: VesselProfileRow, weather: WeatherKind | None, weapons: Sequence[Weapon]) -> float:
    table = rules.seafaring
    crew = row.crew * table.boarding_pct / PERCENT / max(1, FRAMES[row.frame].crew)
    return (1 + arms_weight(rules, weapons, weather) + crew) * (0.5 + row.condition / (2 * PERCENT)) * (1 + row.seamanship / PERCENT)


def fight_key(fight: Engagement) -> str:
    if fight.end is StepOutcome.DESTROYED:
        if fight.crashed:
            return "seafaring.downed"
        return "seafaring.blew_up" if fight.exploded else "seafaring.foundered"
    if fight.end is StepOutcome.ESCAPED:
        return "seafaring.escaped"
    if fight.end is StepOutcome.YIELDED:
        return "seafaring.struck"
    if fight.end is StepOutcome.CAPTURED:
        return "seafaring.boarded"
    return "seafaring.sea_fight"


async def sea_fight(
    ctx: TickContext, first: tuple[EntityRow, VesselProfileRow], second: tuple[EntityRow, VesselProfileRow], weather: WeatherKind | None, tally: SeaTally
) -> EntityRow:
    rng = ctx.rng(f"vessel_fight.{first[0].id}.{second[0].id}.{ctx.epoch}")
    with explaining() as found:
        powers = []
        for vessel, row in (first, second):
            weapons = await weapons_of(ctx, row)
            manning = crew_power(ctx.rules, row, await crews_of(ctx, vessel.id, row), await fitted_stations(ctx.session, vessel.id, row))
            powers.append(vessel_power(ctx.rules, row, weather, weapons) * await design_power(ctx.session, row) * manning * (0.8 + rng.below(40) / PERCENT))
    terms = found.snapshot()
    fight = await engage(ctx, first, second, (powers[0], powers[1]), tally.sail)
    winner, loser = (first, second) if fight.winner.id == first[0].id else (second, first)
    mine, theirs = (powers[0], powers[1]) if winner is first else (powers[1], powers[0])
    table = ctx.rules.seafaring
    if fight.end in {StepOutcome.DAMAGED, StepOutcome.ESCAPED}:
        if "condition" not in loser[1].locked:
            loser[1].condition = clamp_int(loser[1].condition - table.combat_damage, 0, PERCENT)
        await battered(ctx, loser[0], loser[1], max(1, table.combat_damage // ctx.rules.vehicles.section_hit), f"sea_fight.{winner[0].id}")
    if "renown" not in winner[1].locked:
        winner[1].renown += table.renown_per_victory
    tally.fights += 1
    written = await record(
        ctx,
        fight_key(fight),
        roles={IncidentRole.ACTOR: winner[0].id, IncidentRole.OPPONENT: loser[0].id},
        facts={
            "domain": fight.domain,
            "rounds": fight.rounds,
            "hits_given": fight.hits.get(loser[0].id, 0),
            "hits_taken": fight.hits.get(winner[0].id, 0),
            "power": round(mine, 2),
            "foe_power": round(theirs, 2),
        },
        steps=fight.steps,
        terms=terms,
        place=winner[1].region_entity_id or loser[1].region_entity_id,
    )
    if fight.sunk:
        reason = "lost when it blew up" if fight.exploded else ("lost when it fell" if fight.crashed else "lost under fire")
        await sink(ctx, loser[0], loser[1], f"{reason} in its fight with {winner[0].name}", tally, cause=written.incident_id)
    elif fight.struck:
        await prize(ctx, winner, loser, tally, cause=written.incident_id)
    elif loser[1].condition <= table.wreck_condition:
        await sink(ctx, loser[0], loser[1], f"lost to {winner[0].name}", tally, cause=written.incident_id)
    return winner[0]


async def prize(
    ctx: TickContext, winner: tuple[EntityRow, VesselProfileRow], loser: tuple[EntityRow, VesselProfileRow], tally: SeaTally, *, cause: int | None
) -> None:
    captor = await owner_of(ctx, winner[0].id)
    with explaining() as found:
        money = await take_prize(ctx, winner[1], loser[0], loser[1], captor)
    terms = found.snapshot()
    if captor is not None and not held(loser[0].id):
        bonds = BondRepository(ctx.session)
        for bond in await bonds.incoming(loser[0].id, BondKind.OWNS):
            await bonds.deactivate(bond, ctx.epoch, f"yielded to {winner[0].name}")
        await bonds.connect(BondDraft(captor.id, loser[0].id, BondKind.OWNS, ctx.epoch, f"taken as a prize by {winner[0].name}"))
    captain = await living_entity(ctx.session, winner[1].captain_entity_id) if winner[1].captain_entity_id is not None else None
    paid = captain or captor
    if paid is not None:
        await give_coin(ctx.session, ctx.rules, paid, money)
        await add_renown(ctx.session, paid.id, ctx.rules.seafaring.renown_per_victory, ctx.epoch, rules=ctx.rules)
    tally.sail.prizes += 1
    tally.prize_money += money
    roles: dict[IncidentRole, int] = {IncidentRole.ACTOR: winner[0].id, IncidentRole.TARGET: loser[0].id}
    if captor is not None:
        roles[IncidentRole.OWNER] = captor.id
    if paid is not None and paid is not captor:
        roles[IncidentRole.RECEIVER] = paid.id
    state = await ship_state(ctx, loser[0].id)
    await record(
        ctx,
        "seafaring.prize_taken",
        roles=roles,
        facts={"prize_money": money, "prize_crew": state.prize_crew},
        terms=terms,
        place=winner[1].region_entity_id,
        cause=cause,
    )


async def seas(ctx: TickContext) -> SeaTally:
    tally = SeaTally()
    designs = DesignTally()
    await backfill_vessels(ctx)
    await arm_unarmed(ctx)
    tally.crews_added = await backfill_crews(ctx.session)
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
        if row.status in AFLOAT and domain_of(row) in SAILED:
            await set_sail(ctx, vessel, row, row.region_entity_id, tally.sail)
        if row.status in AFLOAT:
            for hazard in await wear_leg(ctx, vessel, row, stormy=has_trait(weather, WeatherTrait.STORM), tally=designs):
                await wreck_crew(ctx, vessel, row, hazard)
        if row.status in AFLOAT:
            row.renown += ctx.rules.seafaring.renown_per_voyage if "renown" not in row.locked else 0
            await strange_waters(ctx, vessel, row, tally)
            await legend_of(ctx, vessel, row, tally)
            afloat.append((vessel, row, owner))
        row.updated_epoch = ctx.epoch
    await skirmishes(ctx, afloat, tally)
    tally.worn, tally.failures, tally.mended = designs.worn, designs.failures, designs.mended
    return tally


def domain_group(row: VesselProfileRow) -> frozenset[VehicleDomain]:
    domain = domain_of(row)
    if domain in WATERBORNE:
        return WATERBORNE
    if domain in LIFTED:
        return LIFTED
    return frozenset({domain})


def can_meet(first: VesselProfileRow, second: VesselProfileRow) -> bool:
    return domain_of(second) in domain_group(first)


async def skirmishes(ctx: TickContext, afloat: list[tuple[EntityRow, VesselProfileRow, EntityRow | None]], tally: SeaTally) -> None:
    seen: set[int] = set()
    for index, (vessel, row, owner) in enumerate(afloat):
        if owner is None or vessel.id in seen:
            continue
        for other, other_row, other_owner in afloat[index + 1 :]:
            if other_owner is None or other.id in seen or other_row.region_entity_id != row.region_entity_id or not can_meet(row, other_row):
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
            await sink(ctx, vessel, row, "lost in a sea battle", tally, cause=None)
            if row.status is VesselStatus.WRECKED:
                await record(ctx, "seafaring.lost_in_battle", roles={IncidentRole.SUBJECT: vessel.id}, facts={"fleet": army_id}, place=row.region_entity_id)
    return damaged


async def fleet_bonus(ctx: TickContext, army_id: int, weather: WeatherKind | None) -> float:
    return sum([vessel_power(ctx.rules, row, weather, await weapons_of(ctx, row)) for _, row in await fleet_of(ctx, army_id)])


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
