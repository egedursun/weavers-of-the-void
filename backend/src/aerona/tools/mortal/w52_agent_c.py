from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.fugitives import FUGITIVES, SANCTUARIES
from aerona.catalog.life.domain import CRIME_KINDS, UNFINISHED_STATES
from aerona.catalog.rebuilding import REBUILD_PLANS
from aerona.catalog.relief import RELIEF_KINDS
from aerona.core.grammar import spoken
from aerona.db.tables.agrarian import ReconstructionRow
from aerona.db.tables.belonging import FugitiveRow
from aerona.db.tables.customs import PoorReliefRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.structures import ConstructionRow, StructureProfileRow
from aerona.db.tables.urban import CrimeStanceRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.agrarian import RebuildPlan
from aerona.domain.enums.belonging import FugitiveKind, SanctuaryKind
from aerona.domain.enums.customs import ReliefKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import AbandonCause, ConstructionStatus
from aerona.domain.enums.urban import CrimeStance
from aerona.engine.agrarian.rebuilding_ways import safer_site
from aerona.engine.belonging.fugitives_w52 import flee as take_flight
from aerona.engine.belonging.fugitives_w52 import hunt_one
from aerona.engine.belonging.refuge import refuge_of
from aerona.engine.belonging.sanctuary import Fugitive, fugitives, host_for, shelter
from aerona.engine.cycles.book import realm_of
from aerona.engine.economy.purse import take_coin
from aerona.engine.means.security import attempt_theft
from aerona.engine.museums.gardens import lay_out
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import living_entity
from aerona.engine.settlement.control import build_district
from aerona.engine.structures.construction import abandon
from aerona.engine.structures.leftovers import abandon_work, dismantle
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.city_rules import governed_town
from aerona.tools.mortal.monetary import controls

BUDGET_MAX = 100000


class OpenDistrictInput(ToolInput):
    settlement_id: int
    kind: DistrictKind
    material: BuildMaterial = BuildMaterial.TIMBER


class RebuildInput(ToolInput):
    settlement_id: int
    plan: RebuildPlan


class WorkInput(ToolInput):
    structure_id: int


class FoundGardenInput(ToolInput):
    kind: GardenKind


class PickLockInput(ToolInput):
    structure_id: int


class SetCrimeStanceInput(ToolInput):
    faction_id: int
    stance: CrimeStance


class FleeInput(ToolInput):
    sanctuary: SanctuaryKind | None = None


class HuntFugitiveInput(ToolInput):
    fugitive_id: int


class GiveReliefInput(ToolInput):
    kind: ReliefKind
    budget: int = Field(ge=1, le=BUDGET_MAX)


async def open_district(call: MortalCall, args: OpenDistrictInput) -> str:
    town = await governed_town(call, args.settlement_id)
    district = await build_district(call.tick, town.id, args.kind, material=args.material, son_id=None)
    call.target(town.id)
    await call.record(
        "tools.mortal.open_district", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id}, facts={"kind": args.kind}, place=town.id
    )
    return result(MortalResult.DISTRICT_OPENED, kind=spoken(args.kind), town=town.name, level=district.level)


async def rebuild(call: MortalCall, args: RebuildInput) -> str:
    town = await governed_town(call, args.settlement_id)
    row = await call.session.scalar(
        select(ReconstructionRow).where(ReconstructionRow.settlement_entity_id == town.id, ReconstructionRow.finished_epoch.is_(None)).limit(1)
    )
    if row is None:
        fail(MortalResult.REBUILD_REFUSED, why="nothing there waits to be rebuilt")
    if "plan" in row.locked:
        fail(MortalResult.REBUILD_REFUSED, why="how it is rebuilt is held")
    if REBUILD_PLANS[args.plan].moves:
        site = await safer_site(call.tick, town)
        if site is None:
            fail(MortalResult.REBUILD_REFUSED, why="no safer site lies near")
        row.site_entity_id = site
    row.plan = args.plan
    if args.plan is RebuildPlan.PLANNED:
        row.planner_entity_id = call.me.id
    call.target(town.id)
    await call.record("tools.mortal.rebuild", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id}, facts={"plan": args.plan}, place=town.id)
    return result(MortalResult.REBUILD_SET, town=town.name, plan=REBUILD_PLANS[args.plan].label.lower())


async def ruled_work(call: MortalCall, structure_id: int) -> tuple[EntityRow, StructureProfileRow]:
    work = await living_entity(call.session, structure_id)
    profile = await call.session.get(StructureProfileRow, structure_id)
    if work is None or profile is None or profile.host_entity_id is None:
        fail(MortalResult.WORK_REFUSED, why="there is no such work")
    await governed_town(call, profile.host_entity_id)
    if held(work.id) or "construction_state" in profile.locked:
        fail(MortalResult.WORK_REFUSED, why="that work is held")
    return work, profile


async def abandon_work_tool(call: MortalCall, args: WorkInput) -> str:
    work, profile = await ruled_work(call, args.structure_id)
    if profile.construction_state not in UNFINISHED_STATES:
        fail(MortalResult.WORK_REFUSED, why="only a work still being raised can be left unfinished")
    site = await call.session.scalar(
        select(ConstructionRow)
        .where(ConstructionRow.structure_entity_id == work.id, ConstructionRow.status == ConstructionStatus.ACTIVE)
        .order_by(ConstructionRow.id.desc())
        .limit(1)
    )
    if site is not None:
        await abandon(call.tick, site, AbandonCause.CALLED_AWAY, reason=f"{call.me.name} called its builders away")
    else:
        await abandon_work(call.tick, work, profile, by=call.me.id)
    call.target(work.id)
    await call.record("tools.mortal.abandon_work", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: work.id}, facts={"structure": profile.kind})
    return result(MortalResult.WORK_ABANDONED, name=work.name)


async def dismantle_work_tool(call: MortalCall, args: WorkInput) -> str:
    work, profile = await ruled_work(call, args.structure_id)
    gained = await dismantle(call.tick, work, profile, by=call.me.id)
    call.target(work.id)
    await call.record("tools.mortal.dismantle_work", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: work.id}, facts={"gained": gained})
    return result(MortalResult.WORK_DISMANTLED, name=work.name, gained=gained)


async def found_garden(call: MortalCall, args: FoundGardenInput) -> str:
    town = await living_entity(call.session, call.me.location_id) if call.me.location_id is not None else None
    if town is None or town.entity_type is not EntityType.SETTLEMENT or held(town.id):
        fail(MortalResult.GARDEN_REFUSED, why="you live in no town")
    known = await call.session.scalar(select(GardenRow.id).where(GardenRow.settlement_entity_id == town.id, GardenRow.kind == args.kind).limit(1))
    if known is not None:
        fail(MortalResult.GARDEN_REFUSED, why="your town already keeps such a garden")
    if not await take_coin(call.session, call.rules, call.me, call.rules.gardens.upkeep):
        fail(MortalResult.GARDEN_REFUSED, why="you cannot pay to lay it out")
    garden = await lay_out(call.tick, town.id, args.kind, None, await RegionAtlas.load(call.session))
    call.target(town.id)
    await call.record(
        "tools.mortal.found_garden", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id}, facts={"kind": args.kind}, place=town.id
    )
    return result(MortalResult.GARDEN_FOUNDED, kind=spoken(args.kind), town=town.name, kinds=len(garden.species))


async def pick_lock(call: MortalCall, args: PickLockInput) -> str:
    work = await living_entity(call.session, args.structure_id)
    profile = await call.session.get(StructureProfileRow, args.structure_id)
    if work is None or profile is None or profile.host_entity_id is None or profile.host_entity_id != call.me.location_id:
        fail(MortalResult.LOCK_REFUSED, why="that store is not in your town")
    owner = await call.session.get(EntityRow, profile.host_entity_id)
    if owner is None or held(work.id):
        fail(MortalResult.LOCK_REFUSED, why="it is held")
    attempt = await attempt_theft(call.tick, call.me, owner, work)
    call.target(work.id)
    await call.record("tools.mortal.pick_lock", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: work.id}, facts={"held": int(attempt.thwarted)})
    return result(MortalResult.LOCK_HELD if attempt.thwarted else MortalResult.LOCK_BEATEN, name=work.name)


async def set_crime_stance(call: MortalCall, args: SetCrimeStanceInput) -> str:
    realm = await realm_of(call.session, call.me.location_id) if call.me.location_id is not None else None
    if realm is None or not await controls(call, realm):
        fail(MortalResult.CRIME_STANCE_REFUSED, why="only the ruler of a realm sets its stance toward crime")
    faction = await living_entity(call.session, args.faction_id)
    profile = await call.session.get(FactionProfileRow, args.faction_id)
    if faction is None or profile is None or profile.kind not in CRIME_KINDS:
        fail(MortalResult.CRIME_STANCE_REFUSED, why="that is no organisation of crime")
    if held(realm, faction.id):
        fail(MortalResult.CRIME_STANCE_REFUSED, why="they are held")
    row = await call.session.get(CrimeStanceRow, (realm, faction.id))
    if row is None:
        row = CrimeStanceRow(polity_entity_id=realm, faction_entity_id=faction.id, stance=args.stance, strength=50, since_epoch=call.epoch, locked=[])
        call.session.add(row)
    elif "stance" in row.locked:
        fail(MortalResult.CRIME_STANCE_REFUSED, why="that stance is held")
    row.stance = args.stance
    call.target(faction.id)
    await call.record("polity.crime_stance", roles={IncidentRole.AUTHORITY: realm, IncidentRole.TARGET: faction.id}, facts={"stance": args.stance})
    return result(MortalResult.CRIME_STANCE_SET, faction=faction.name, stance=spoken(args.stance))


async def flee_tool(call: MortalCall, args: FleeInput) -> str:
    me = call.me
    if await refuge_of(call.session, me.id) is not None:
        fail(MortalResult.FLIGHT_REFUSED, why="you already have sanctuary")
    hunted = next((item for item in await fugitives(call.tick) if item.mortal.id == me.id), None)
    if hunted is None:
        if me.social_class is not SocialClass.SERF_OR_SLAVE:
            fail(MortalResult.FLIGHT_REFUSED, why="nothing hunts you and no bond holds you")
        realm = await realm_of(call.session, me.location_id) if me.location_id is not None else None
        row = await take_flight(call.tick, me, FugitiveKind.RUNAWAY, realm)
        if row is None:
            fail(MortalResult.FLIGHT_REFUSED, why="you cannot get away")
        hunted = Fugitive(me, FugitiveKind.RUNAWAY, realm)
    found = await host_for(call.tick, hunted, args.sanctuary)
    if found is None:
        fail(MortalResult.FLIGHT_REFUSED, why="no refuge of that kind will take you in here")
    host, kind = found
    await shelter(call.tick, hunted, host, kind)
    call.target(host.id)
    await call.record(
        "sanctuary.sought", roles={IncidentRole.ACTOR: me.id, IncidentRole.HOST: host.id, IncidentRole.OPPONENT: hunted.pursuer}, facts={"kind": kind}
    )
    return result(MortalResult.FLED, host=host.name, refuge=SANCTUARIES[kind].label.lower(), fugitive=FUGITIVES[hunted.kind].label.lower())


async def hunt_fugitive(call: MortalCall, args: HuntFugitiveInput) -> str:
    row = await call.session.get(FugitiveRow, args.fugitive_id)
    if row is None or row.caught_epoch is not None or row.freed_epoch is not None:
        fail(MortalResult.FUGITIVE_HUNT_REFUSED, why="no such fugitive is still at large")
    realm = await realm_of(call.session, call.me.location_id) if call.me.location_id is not None else None
    if row.pursuer_entity_id is None or realm != row.pursuer_entity_id:
        fail(MortalResult.FUGITIVE_HUNT_REFUSED, why="only those of the power that hunts them may take them")
    caught = await hunt_one(call.tick, row, by=call.me.id, certain=call.tick.rng(f"hunt.tool.{row.id}.{call.epoch}").chance(50))
    call.target(row.mortal_entity_id)
    await call.record(
        "tools.mortal.hunt_fugitive", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: row.mortal_entity_id}, facts={"caught": int(caught)}
    )
    return result(MortalResult.FUGITIVE_CAUGHT if caught else MortalResult.FUGITIVE_ESCAPED, kind=FUGITIVES[row.kind].label.lower())


async def give_relief(call: MortalCall, args: GiveReliefInput) -> str:
    realm = await realm_of(call.session, call.me.location_id) if call.me.location_id is not None else None
    if realm is None or held(realm):
        fail(MortalResult.RELIEF_REFUSED, why="your town answers to no realm")
    profile = await call.session.get(PolityProfileRow, realm)
    row = await call.session.get(PoorReliefRow, realm)
    if await controls(call, realm):
        if row is None:
            row = PoorReliefRow(polity_entity_id=realm, kind=args.kind, budget=args.budget, reach=call.rules.poor_relief.adopt_reach, locked=[])
            call.session.add(row)
        elif "kind" in row.locked or "budget" in row.locked:
            fail(MortalResult.RELIEF_REFUSED, why="the realm's relief is held")
        row.kind, row.budget = args.kind, args.budget
    elif row is not None and row.kind is args.kind and profile is not None and await take_coin(call.session, call.rules, call.me, args.budget):
        profile.treasury += args.budget
    else:
        fail(MortalResult.RELIEF_REFUSED, why="only a ruler sets the realm's relief; others may give to it only as it already stands")
    call.target(realm)
    await call.record("relief.funded", roles={IncidentRole.AUTHORITY: realm}, facts={"kind": args.kind, "budget": args.budget})
    return result(MortalResult.RELIEF_SET, kind=RELIEF_KINDS[args.kind].label.lower(), budget=args.budget)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.OPEN_DISTRICT, mortal, OpenDistrictInput, meta, open_district),
        ToolSpec(MortalToolId.REBUILD, mortal, RebuildInput, meta, rebuild),
        ToolSpec(MortalToolId.ABANDON_WORK, mortal, WorkInput, meta, abandon_work_tool),
        ToolSpec(MortalToolId.DISMANTLE_WORK, mortal, WorkInput, meta, dismantle_work_tool),
        ToolSpec(MortalToolId.FOUND_GARDEN, mortal, FoundGardenInput, meta, found_garden),
        ToolSpec(MortalToolId.PICK_LOCK, mortal, PickLockInput, meta, pick_lock),
        ToolSpec(MortalToolId.SET_CRIME_STANCE, mortal, SetCrimeStanceInput, meta, set_crime_stance),
        ToolSpec(MortalToolId.FLEE, mortal, FleeInput, meta, flee_tool),
        ToolSpec(MortalToolId.HUNT_FUGITIVE, mortal, HuntFugitiveInput, meta, hunt_fugitive),
        ToolSpec(MortalToolId.GIVE_RELIEF, mortal, GiveReliefInput, meta, give_relief),
    ]
