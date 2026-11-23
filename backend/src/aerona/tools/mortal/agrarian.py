from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.agrarian import CommonsRow, GameReserveRow, PreparednessRow, ReconstructionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.agrarian import AidKind, CommonsRule, PerennialKind, PreparednessKind, RebuildPlan
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.engine.agrarian import control
from aerona.engine.agrarian.resilience import most_level, per_thousand
from aerona.engine.collective.book import shift
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.mind.hooks import judged
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.trials import report_crime
from aerona.engine.primitives.queries import living_entity, top_region
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import StepDraft
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.cycles import ruled_realm

WORK_COST = 200
CATCH_COIN = 15
CATCH_POACHING = 10
DEFAULT_STRICTNESS = 60
STRICT_RESERVE = 50


class EncloseCommonsInput(ToolInput):
    commons_id: int


class RuleCommonsInput(ToolInput):
    commons_id: int


class SetCommonsRuleInput(ToolInput):
    commons_id: int
    rule: CommonsRule
    quota: Annotated[int, Field(ge=0, le=200)] = 60
    licence_price: Annotated[int, Field(ge=0, le=1000)] = 0


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
        fail(refused, why="the land is held")
    return row


async def enclose_commons(call: MortalCall, args: EncloseCommonsInput) -> str:
    row = await common_here(call, args.commons_id, MortalResult.ENCLOSURE_REFUSED)
    if row.rule is CommonsRule.ENCLOSED:
        fail(MortalResult.ENCLOSURE_REFUSED, why="it is already enclosed")
    await control.enclose_common(call.tick, row.id, call.me.id)
    call.target(row.region_entity_id)
    await call.record(
        "tools.mortal.enclose_commons",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: row.region_entity_id},
        facts={"commons": row.kind, "driven": row.dispossessed},
        place=row.region_entity_id,
    )
    return result(MortalResult.COMMONS_ENCLOSED, kind=spoken(row.kind), driven=row.dispossessed)


async def rule_commons(call: MortalCall, args: RuleCommonsInput) -> str:
    row = await common_here(call, args.commons_id, MortalResult.COUNCIL_REFUSED)
    if row.rule in (CommonsRule.ENCLOSED, CommonsRule.COUNCIL):
        fail(MortalResult.COUNCIL_REFUSED, why=f"it is already {spoken(row.rule)}")
    await control.edit_record(call.tick, "commons", row.id, {"rule": CommonsRule.COUNCIL.value}, [])
    call.target(row.region_entity_id)
    await call.record(
        "tools.mortal.rule_commons",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: row.region_entity_id},
        facts={"commons": row.kind, "condition": row.condition},
        place=row.region_entity_id,
        steps=(
            StepDraft(
                StepAction.APPOINT,
                actor=call.me.id,
                target=row.region_entity_id,
                record_table="commons",
                record_key=str(row.id),
                outcome=StepOutcome.SUCCESS,
            ),
        ),
    )
    return result(MortalResult.COMMONS_RULED, kind=spoken(row.kind), condition=row.condition)


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
    await call.record(
        "tools.mortal.reserve_game",
        roles={IncidentRole.OWNER: call.me.id, IncidentRole.PLACE: land.id, IncidentRole.SUBJECT: args.species_id},
        facts={"strictness": args.strictness},
        place=land.id,
    )
    return result(MortalResult.GAME_RESERVED, land=land.name, id=row.id)


async def poach_game(call: MortalCall, args: PoachGameInput) -> str:
    row = await call.session.get(GameReserveRow, args.reserve_id)
    land = await home_land(call)
    if row is None or land is None or row.region_entity_id != land.id:
        fail(MortalResult.POACH_REFUSED, why="there is no such reserve in your land")
    if row.holder_node_id == call.me.id:
        fail(MortalResult.POACH_REFUSED, why="the game is yours to hunt")
    if held(land.id):
        fail(MortalResult.POACH_REFUSED, why="the land is held")
    shift(row, "poaching", CATCH_POACHING)
    await give_coin(call.session, call.tick.rules, call.me, CATCH_COIN)
    if row.holder_node_id is not None:
        await judged(call.tick, call.me.id, row.holder_node_id, ActKind.POACHING, note=f"poached the game of {land.name}")
    town = await home_town(call)
    if town is not None and row.strictness >= STRICT_RESERVE:
        await report_crime(call.tick, town.id, call.me.id, CrimeKind.THEFT)
    call.target(land.id)
    await call.record(
        "tools.mortal.poach_game",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: land.id, IncidentRole.VICTIM: row.holder_node_id},
        facts={"coin": CATCH_COIN, "poaching": row.poaching},
        place=land.id,
    )
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
    await call.record(
        "tools.mortal.plant_perennial",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: land.id},
        facts={"perennial": args.kind, "epochs": row.mature_epochs},
        place=land.id,
    )
    return result(MortalResult.PERENNIAL_PLANTED, kind=spoken(args.kind), epochs=row.mature_epochs)


async def send_aid(call: MortalCall, args: SendAidInput) -> str:
    realm = await ruled_realm(call)
    if realm is None or held(realm.id):
        fail(MortalResult.AID_REFUSED, why="you rule no realm")
    town = await living_entity(call.session, args.settlement_id)
    if town is None or town.entity_type is not EntityType.SETTLEMENT or held(town.id):
        fail(MortalResult.AID_REFUSED, why="there is no such town")
    try:
        row = await control.send_aid(call.tick, realm.id, town.id, args.kind, per_thousand(call.tick.rules.relief.cap, town))
    except ValidationFailedError as error:
        fail(MortalResult.AID_REFUSED, why=str(error).rstrip("."))
    call.target(town.id)
    await call.record(
        "tools.mortal.send_aid",
        roles={IncidentRole.GIVER: realm.id, IncidentRole.RECEIVER: town.id, IncidentRole.ACTOR: call.me.id},
        facts={"aid": args.kind, "refused": int(row.refused)},
        place=town.id,
    )
    return result(MortalResult.AID_TURNED_AWAY if row.refused else MortalResult.AID_SENT, kind=spoken(args.kind), town=town.name)


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
    await call.record(
        "tools.mortal.plan_rebuilding", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id}, facts={"progress": row.progress}, place=town.id
    )
    return result(MortalResult.REBUILDING_PLANNED, town=town.name, progress=row.progress)


async def prepare_town(call: MortalCall, args: PrepareTownInput) -> str:
    town = await home_town(call)
    if town is None or held(town.id):
        fail(MortalResult.PREPARE_REFUSED, why="you live in no town")
    work = await call.session.get(PreparednessRow, (town.id, args.kind))
    level = (work.level if work is not None else 0) + 1
    if level > most_level(call.tick.rules, stat_or(town, "population", 0)):
        fail(MortalResult.PREPARE_REFUSED, why="that work stands as high as it can")
    if not await take_coin(call.session, call.tick.rules, call.me, WORK_COST * level):
        fail(MortalResult.PREPARE_REFUSED, why=f"it costs {WORK_COST * level} coin")
    await control.build_work(call.tick, town.id, args.kind, level)
    call.target(town.id)
    await call.record(
        "tools.mortal.prepare_town",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PLACE: town.id},
        facts={"work": args.kind, "level": level, "cost": WORK_COST * level},
        place=town.id,
    )
    return result(MortalResult.TOWN_PREPARED, kind=spoken(args.kind), level=level)


async def set_commons_rule(call: MortalCall, args: SetCommonsRuleInput) -> str:
    row = await call.session.get(CommonsRow, args.commons_id)
    if row is None or row.steward_entity_id is None:
        fail(MortalResult.COMMONS_RULE_REFUSED, why="there is no such common")
    book = await RealmBook.load(call.session)
    realm_id = book.member_of.get(row.steward_entity_id)
    realm = book.realms.get(realm_id) if realm_id is not None else None
    if realm is None or realm.ruler_id != call.me.id:
        fail(MortalResult.COMMONS_RULE_REFUSED, why="only the ruler of the realm that holds the common sets its rule")
    if held(row.region_entity_id):
        fail(MortalResult.COMMONS_RULE_REFUSED, why="the land is held")
    values = {"rule": args.rule.value, "quota": args.quota, "licence_price": args.licence_price}
    if args.rule is CommonsRule.STATE:
        values["officials"] = call.rules.commons.state_enforcement
    before = row.rule
    await control.edit_record(call.tick, "commons", row.id, values, [])
    call.target(row.region_entity_id)
    await call.record(
        "commons.rule_changed",
        roles={IncidentRole.SUBJECT: row.steward_entity_id},
        facts={"common": row.kind, "rule": args.rule, "before": before},
        place=row.steward_entity_id,
    )
    return result(MortalResult.COMMONS_RULE_SET, kind=spoken(row.kind), rule=spoken(args.rule))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.ENCLOSE_COMMONS, mortal, EncloseCommonsInput, meta, enclose_commons),
        ToolSpec(MortalToolId.RULE_COMMONS, mortal, RuleCommonsInput, meta, rule_commons),
        ToolSpec(MortalToolId.SET_COMMONS_RULE, mortal, SetCommonsRuleInput, meta, set_commons_rule),
        ToolSpec(MortalToolId.RESERVE_GAME, mortal, ReserveGameInput, meta, reserve_game),
        ToolSpec(MortalToolId.POACH_GAME, mortal, PoachGameInput, meta, poach_game),
        ToolSpec(MortalToolId.PLANT_PERENNIAL, mortal, PlantPerennialInput, meta, plant_perennial),
        ToolSpec(MortalToolId.SEND_AID, mortal, SendAidInput, meta, send_aid),
        ToolSpec(MortalToolId.PLAN_REBUILDING, mortal, PlanRebuildingInput, meta, plan_rebuilding),
        ToolSpec(MortalToolId.PREPARE_TOWN, mortal, PrepareTownInput, meta, prepare_town),
    ]
