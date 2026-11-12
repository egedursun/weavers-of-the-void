from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.agrarian import CommonsRow, GameReserveRow, PreparednessRow, ReconstructionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.agrarian import AidKind, CommonsRule, PerennialKind, PreparednessKind, RebuildPlan
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind
from aerona.engine.agrarian import control
from aerona.engine.collective.book import shift
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.mind.hooks import judged
from aerona.engine.primitives.queries import living_entity, top_region
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.cycles import ruled_realm

WORK_COST = 200
CATCH_COIN = 15
CATCH_POACHING = 10
DEFAULT_STRICTNESS = 60
MOST_LEVEL = 5


class EncloseCommonsInput(ToolInput):
    commons_id: int


class RuleCommonsInput(ToolInput):
    commons_id: int


class ReserveGameInput(ToolInput):
    species_id: int | None = None
    strictness: int = Field(default=DEFAULT_STRICTNESS, ge=0, le=PERCENT)


class PoachGameInput(ToolInput):
    reserve_id: int


class PlantPerennialInput(ToolInput):
    kind: PerennialKind
    species_id: int | None = None


class SendAidInput(ToolInput):
    settlement_id: int
    kind: AidKind


class PlanRebuildingInput(ToolInput):
    pass


class PrepareTownInput(ToolInput):
    kind: PreparednessKind


async def home_town(call: MortalCall) -> EntityRow | None:
    place = await living_entity(call.session, call.me.location_id) if call.me.location_id is not None else None
    return place if place is not None and place.entity_type is EntityType.SETTLEMENT else None


async def home_land(call: MortalCall) -> EntityRow | None:
    return await top_region(call.session, call.me)


async def common_here(call: MortalCall, commons_id: int, refused: MortalResult) -> CommonsRow:
    row = await call.session.get(CommonsRow, commons_id)
    land = await home_land(call)
    if row is None or land is None or row.region_entity_id != land.id:
        fail(refused, why="there is no such common in your land")
    if held(row.region_entity_id):
        fail(refused, why="a stronger hand holds the land")
    return row


async def enclose_commons(call: MortalCall, args: EncloseCommonsInput) -> str:
    row = await common_here(call, args.commons_id, MortalResult.ENCLOSURE_REFUSED)
    if row.rule is CommonsRule.ENCLOSED:
        fail(MortalResult.ENCLOSURE_REFUSED, why="it is already enclosed")
    await control.enclose_common(call.tick, row.id, call.me.id)
    call.target(row.region_entity_id)
    await call.chronicle(ChronicleKind.WORLD, lines.ENCLOSE_COMMONS, entity_ids=[call.me.id, row.region_entity_id], me=call.me.name, kind=row.kind.value)
    return result(MortalResult.COMMONS_ENCLOSED, kind=row.kind.value, driven=row.dispossessed)


async def rule_commons(call: MortalCall, args: RuleCommonsInput) -> str:
    row = await common_here(call, args.commons_id, MortalResult.COUNCIL_REFUSED)
    if row.rule in (CommonsRule.ENCLOSED, CommonsRule.COUNCIL):
        fail(MortalResult.COUNCIL_REFUSED, why=f"it is already {row.rule.value}")
    await control.edit_record(call.tick, "commons", row.id, {"rule": CommonsRule.COUNCIL.value}, [])
    call.target(row.region_entity_id)
    await call.chronicle(ChronicleKind.WORLD, lines.RULE_COMMONS, entity_ids=[call.me.id, row.region_entity_id], me=call.me.name, kind=row.kind.value)
    return result(MortalResult.COMMONS_RULED, kind=row.kind.value, condition=row.condition)


async def reserve_game(call: MortalCall, args: ReserveGameInput) -> str:
    land = await home_land(call)
    if land is None or held(land.id):
        fail(MortalResult.RESERVE_REFUSED, why="you stand on no land you could reserve")
    if await call.session.scalar(select(GameReserveRow.id).where(GameReserveRow.region_entity_id == land.id).limit(1)) is not None:
        fail(MortalResult.RESERVE_REFUSED, why="its game is already reserved")
    try:
        row = await control.declare_reserve(call.tick, land.id, call.me.id, args.species_id, args.strictness)
    except ValidationFailedError as error:
        fail(MortalResult.RESERVE_REFUSED, why=str(error).rstrip("."))
    call.target(land.id)
    await call.chronicle(ChronicleKind.WORLD, lines.RESERVE_GAME, entity_ids=[call.me.id, land.id], me=call.me.name, land=land.name)
    return result(MortalResult.GAME_RESERVED, land=land.name, id=row.id)


async def poach_game(call: MortalCall, args: PoachGameInput) -> str:
    row = await call.session.get(GameReserveRow, args.reserve_id)
    land = await home_land(call)
    if row is None or land is None or row.region_entity_id != land.id:
        fail(MortalResult.POACH_REFUSED, why="there is no such reserve in your land")
    if row.holder_node_id == call.me.id:
        fail(MortalResult.POACH_REFUSED, why="the game is yours to hunt")
    if held(land.id):
        fail(MortalResult.POACH_REFUSED, why="a stronger hand holds the land")
    shift(row, "poaching", CATCH_POACHING)
    await give_coin(call.session, call.tick.rules, call.me, CATCH_COIN)
    if row.holder_node_id is not None:
        await judged(call.tick, call.me.id, row.holder_node_id, ActKind.POACHING, note=f"poached the game of {land.name}")
    call.target(land.id)
    await call.chronicle(ChronicleKind.WORLD, lines.POACH_GAME, entity_ids=[call.me.id, land.id], me=call.me.name, land=land.name)
    return result(MortalResult.GAME_POACHED, land=land.name, coin=CATCH_COIN)


async def plant_perennial(call: MortalCall, args: PlantPerennialInput) -> str:
    land = await home_land(call)
    if land is None or held(land.id):
        fail(MortalResult.PLANTING_REFUSED, why="you stand on no land you could plant")
    try:
        row = await control.plant(call.tick, land.id, args.kind, species_id=args.species_id, owner_id=call.me.id, area=call.tick.rules.perennials.area)
    except ValidationFailedError as error:
        fail(MortalResult.PLANTING_REFUSED, why=str(error).rstrip("."))
    call.target(land.id)
    await call.chronicle(ChronicleKind.WORLD, lines.PLANT_PERENNIAL, entity_ids=[call.me.id, land.id], me=call.me.name, kind=args.kind.value, land=land.name)
    return result(MortalResult.PERENNIAL_PLANTED, kind=args.kind.value, epochs=row.mature_epochs)


async def send_aid(call: MortalCall, args: SendAidInput) -> str:
    realm = await ruled_realm(call)
    if realm is None or held(realm.id):
        fail(MortalResult.AID_REFUSED, why="you rule no realm")
    town = await living_entity(call.session, args.settlement_id)
    if town is None or town.entity_type is not EntityType.SETTLEMENT or held(town.id):
        fail(MortalResult.AID_REFUSED, why="there is no such town")
    try:
        row = await control.send_aid(call.tick, realm.id, town.id, args.kind, call.tick.rules.relief.cap)
    except ValidationFailedError as error:
        fail(MortalResult.AID_REFUSED, why=str(error).rstrip("."))
    call.target(town.id)
    await call.chronicle(ChronicleKind.WORLD, lines.SEND_AID, entity_ids=[call.me.id, realm.id, town.id], me=call.me.name, kind=args.kind.value, town=town.name)
    return result(MortalResult.AID_TURNED_AWAY if row.refused else MortalResult.AID_SENT, kind=args.kind.value, town=town.name)


async def plan_rebuilding(call: MortalCall, args: PlanRebuildingInput) -> str:
    town = await home_town(call)
    if town is None or held(town.id):
        fail(MortalResult.REBUILD_REFUSED, why="you live in no town")
    row = await call.session.scalar(
        select(ReconstructionRow).where(ReconstructionRow.settlement_entity_id == town.id, ReconstructionRow.finished_epoch.is_(None)).limit(1)
    )
    if row is None:
        fail(MortalResult.REBUILD_REFUSED, why="nothing there waits to be rebuilt")
    await control.edit_record(call.tick, "reconstruction", row.id, {"plan": RebuildPlan.PLANNED.value, "planner_entity_id": call.me.id}, [])
    call.target(town.id)
    await call.chronicle(ChronicleKind.WORLD, lines.PLAN_REBUILDING, entity_ids=[call.me.id, town.id], me=call.me.name, town=town.name)
    return result(MortalResult.REBUILDING_PLANNED, town=town.name, progress=row.progress)


async def prepare_town(call: MortalCall, args: PrepareTownInput) -> str:
    town = await home_town(call)
    if town is None or held(town.id):
        fail(MortalResult.PREPARE_REFUSED, why="you live in no town")
    work = await call.session.get(PreparednessRow, (town.id, args.kind))
    level = (work.level if work is not None else 0) + 1
    if level > MOST_LEVEL:
        fail(MortalResult.PREPARE_REFUSED, why="that work stands as high as it can")
    if not await take_coin(call.session, call.tick.rules, call.me, WORK_COST * level):
        fail(MortalResult.PREPARE_REFUSED, why=f"it costs {WORK_COST * level} coin")
    await control.build_work(call.tick, town.id, args.kind, level)
    call.target(town.id)
    await call.chronicle(ChronicleKind.WORLD, lines.PREPARE_TOWN, entity_ids=[call.me.id, town.id], me=call.me.name, kind=args.kind.value, town=town.name)
    return result(MortalResult.TOWN_PREPARED, kind=args.kind.value, level=level)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.ENCLOSE_COMMONS, mortal, EncloseCommonsInput, meta, enclose_commons),
        ToolSpec(MortalToolId.RULE_COMMONS, mortal, RuleCommonsInput, meta, rule_commons),
        ToolSpec(MortalToolId.RESERVE_GAME, mortal, ReserveGameInput, meta, reserve_game),
        ToolSpec(MortalToolId.POACH_GAME, mortal, PoachGameInput, meta, poach_game),
        ToolSpec(MortalToolId.PLANT_PERENNIAL, mortal, PlantPerennialInput, meta, plant_perennial),
        ToolSpec(MortalToolId.SEND_AID, mortal, SendAidInput, meta, send_aid),
        ToolSpec(MortalToolId.PLAN_REBUILDING, mortal, PlanRebuildingInput, meta, plan_rebuilding),
        ToolSpec(MortalToolId.PREPARE_TOWN, mortal, PrepareTownInput, meta, prepare_town),
    ]
