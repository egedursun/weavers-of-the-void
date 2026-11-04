from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.military import ArmourType, HullClass, PeaceTermKind, ShieldType, SpyCover, UnitKind, VesselArmament, WarAimKind
from aerona.domain.enums.war import WarCause
from aerona.engine.military.orders import build_peace, create_vessel, declare_with_cause, raise_standing_army, start_siege
from aerona.engine.military.records import create_record
from aerona.engine.military.shipyard import Commission
from aerona.engine.military.spycraft import recruit
from aerona.engine.phases.espionage import network_for
from aerona.engine.phases.warfare import disband_army
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, label_of, require_canon
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

PERCENT = 100
NAME_MAX = 120
Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
Percent = Annotated[int, Field(ge=0, le=PERCENT)]


class WageWarInput(ToolInput):
    attacker_id: int
    defender_id: int
    cause: WarCause
    aims: list[WarAimKind] = Field(default_factory=list)
    reason: Reason


class RaiseHostInput(ToolInput):
    community_id: int
    soldiers: Annotated[int, Field(ge=1)]
    commander_id: int | None = None
    war_id: int | None = None


class DisbandHostInput(ToolInput):
    army_id: int
    reason: Reason


class LaySiegeInput(ToolInput):
    war_id: int
    army_id: int
    settlement_id: int


class OfferPeaceInput(ToolInput):
    war_id: int
    victor_id: int | None = None
    terms: list[PeaceTermKind] = Field(default_factory=list)


class CommissionVesselInput(ToolInput):
    owner_id: int
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX)]
    hull: HullClass = HullClass.BOAT
    armament: list[VesselArmament] = Field(default_factory=list)
    captain_id: int | None = None


class DesignUnitInput(ToolInput):
    owner_id: int
    name: Annotated[str, Field(min_length=1, max_length=NAME_MAX)]
    base_kind: UnitKind
    melee: Percent = 40
    missile: Percent = 0
    defence: Percent = 40
    armour: ArmourType = ArmourType.NONE
    shield: ShieldType = ShieldType.NONE
    terror: Percent = 0


class PlantSpiesInput(ToolInput):
    owner_id: int
    target_id: int
    cover: SpyCover = SpyCover.MERCHANT


async def community(call: SonCall, entity_id: int) -> EntityRow:
    entity = await require_canon(call.session, entity_id)
    if entity.entity_type not in COMMUNITY_TYPES:
        fail(SonResult.MILITARY_TARGETS, id=entity.id, name=entity.name)
    await ensure_in_reach(call, entity)
    return entity


def pay(call: SonCall, cost: int, target: int) -> None:
    require_essence(call, cost)
    call.spend_essence(cost)
    call.target(target)


async def wage_war(call: SonCall, args: WageWarInput) -> str:
    attacker = await community(call, args.attacker_id)
    defender = await community(call, args.defender_id)
    require_essence(call, call.rules.son_military.wage_war_cost)
    aims = list(dict.fromkeys(args.aims))[: call.rules.son_military.max_aims]
    war = await declare_with_cause(call.tick, attacker.id, defender.id, args.cause, reason=args.reason, aims=[(aim, {}) for aim in aims])
    pay(call, call.rules.son_military.wage_war_cost, attacker.id)
    await call.chronicle(
        ChronicleKind.WAR,
        lines.WAGE_WAR,
        entity_ids=[attacker.id, defender.id],
        son=call.son.name,
        attacker=attacker.name,
        defender=defender.name,
        reason=args.reason,
    )
    return result(
        SonResult.WAR_WAGED,
        attacker=attacker.name,
        defender=defender.name,
        id=war.id,
        cause=label_of(args.cause),
        aims=", ".join(label_of(aim) for aim in aims),
    )


async def raise_host(call: SonCall, args: RaiseHostInput) -> str:
    raiser = await community(call, args.community_id)
    require_essence(call, call.rules.son_military.raise_host_cost)
    soldiers = min(args.soldiers, call.rules.son_military.raise_host_max)
    army = await raise_standing_army(call.tick, raiser.id, soldiers, commander_id=args.commander_id, war_id=args.war_id)
    pay(call, call.rules.son_military.raise_host_cost, army.id)
    await call.chronicle(ChronicleKind.WAR, lines.RAISE_HOST, entity_ids=[raiser.id, army.id], son=call.son.name, community=raiser.name, army=army.name)
    return result(SonResult.HOST_RAISED, community=raiser.name, army=army.name, id=army.id, soldiers=soldiers)


async def standing_army(call: SonCall, army_id: int) -> EntityRow:
    army = await require_canon(call.session, army_id)
    if army.entity_type is not EntityType.ARMY or await call.session.get(ArmyRow, army.id) is None:
        fail(SonResult.NOT_AN_ARMY, id=army_id)
    await ensure_in_reach(call, army)
    return army


async def disband_host(call: SonCall, args: DisbandHostInput) -> str:
    army = await standing_army(call, args.army_id)
    require_essence(call, call.rules.son_military.disband_cost)
    await disband_army(call.tick, army.id)
    pay(call, call.rules.son_military.disband_cost, army.id)
    await call.chronicle(ChronicleKind.WAR, lines.DISBAND_HOST, entity_ids=[army.id], son=call.son.name, army=army.name, reason=args.reason)
    return result(SonResult.HOST_DISBANDED, army=army.name)


async def lay_siege(call: SonCall, args: LaySiegeInput) -> str:
    army = await standing_army(call, args.army_id)
    city = await require_canon(call.session, args.settlement_id)
    await ensure_in_reach(call, city)
    require_essence(call, call.rules.son_military.siege_cost)
    siege = await start_siege(call.tick, args.war_id, army.id, city.id)
    pay(call, call.rules.son_military.siege_cost, city.id)
    await call.chronicle(ChronicleKind.WAR, lines.LAY_SIEGE, entity_ids=[army.id, city.id], son=call.son.name, army=army.name, city=city.name)
    return result(SonResult.SIEGE_LAID, army=army.name, city=city.name, id=siege.id)


async def offer_peace(call: SonCall, args: OfferPeaceInput) -> str:
    require_essence(call, call.rules.son_military.peace_cost)
    settlement = await build_peace(call.tick, args.war_id, args.victor_id, [(term, {}) for term in dict.fromkeys(args.terms)])
    sides = [side for side in (settlement.victor_id, settlement.loser_id) if side is not None]
    pay(call, call.rules.son_military.peace_cost, sides[0] if sides else args.war_id)
    named = [await living_entity(call.session, side) for side in sides]
    names = [entity.name for entity in named if entity is not None] or ["both sides", "the other"]
    await call.chronicle(ChronicleKind.WAR, lines.OFFER_PEACE, entity_ids=sides, son=call.son.name, first=names[0], second=names[-1])
    return result(SonResult.PEACE_MADE, outcome="; ".join([label_of(settlement.ending), *settlement.notes]))


async def commission_vessel(call: SonCall, args: CommissionVesselInput) -> str:
    owner = await require_canon(call.session, args.owner_id)
    await ensure_in_reach(call, owner)
    require_essence(call, call.rules.son_military.vessel_cost)
    order = Commission(hull=args.hull, armament=list(dict.fromkeys(args.armament)) or None, captain_id=args.captain_id)
    vessel = await create_vessel(call.tick, owner.id, args.name, order)
    pay(call, call.rules.son_military.vessel_cost, vessel.id)
    hull = label_of(args.hull)
    await call.chronicle(
        ChronicleKind.WAR, lines.COMMISSION_VESSEL, entity_ids=[owner.id, vessel.id], son=call.son.name, owner=owner.name, hull=hull, name=vessel.name
    )
    return result(SonResult.VESSEL_LAID, owner=owner.name, name=vessel.name, id=vessel.id, hull=hull)


async def design_unit(call: SonCall, args: DesignUnitInput) -> str:
    owner = await community(call, args.owner_id)
    require_essence(call, call.rules.son_military.design_cost)
    values = {
        "name": args.name,
        "base_kind": args.base_kind.value,
        "melee": args.melee,
        "missile": args.missile,
        "defence": args.defence,
        "armour": args.armour.value,
        "shield": args.shield.value,
        "terror": args.terror,
        "owner_entity_id": owner.id,
    }
    design = await create_record(call.tick, "unit_design", values)
    pay(call, call.rules.son_military.design_cost, owner.id)
    await call.chronicle(ChronicleKind.WAR, lines.DESIGN_UNIT, entity_ids=[owner.id], son=call.son.name, owner=owner.name, name=args.name)
    return result(SonResult.UNIT_DESIGNED, owner=owner.name, name=args.name, id=design.id, base=label_of(args.base_kind))


async def plant_spies(call: SonCall, args: PlantSpiesInput) -> str:
    owner = await community(call, args.owner_id)
    target = await community(call, args.target_id)
    require_essence(call, call.rules.son_military.spies_cost)
    network = await network_for(call.tick, owner, target, None)
    network.cover = args.cover
    await call.session.flush()
    await recruit(call.tick, network)
    pay(call, call.rules.son_military.spies_cost, target.id)
    await call.chronicle(ChronicleKind.INTRIGUE, lines.PLANT_SPIES, entity_ids=[owner.id, target.id], son=call.son.name, owner=owner.name, target=target.name)
    return result(SonResult.SPIES_PLANTED, owner=owner.name, target=target.name, id=network.id, cover=label_of(args.cover))


def cost(field: str) -> Any:
    return lambda rules: getattr(rules.son_military, field)


def meta(kind: ActionKind, field: str) -> ToolMeta:
    return ToolMeta(kind, son_standard_action, essence_cost=cost(field))


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(SonToolId.WAGE_WAR, son, WageWarInput, meta(ActionKind.DECLARE_WAR, "wage_war_cost"), wage_war),
        ToolSpec(SonToolId.RAISE_HOST, son, RaiseHostInput, meta(ActionKind.RAISE_ARMY, "raise_host_cost"), raise_host),
        ToolSpec(SonToolId.DISBAND_HOST, son, DisbandHostInput, meta(ActionKind.DISBAND_ARMY, "disband_cost"), disband_host),
        ToolSpec(SonToolId.LAY_SIEGE, son, LaySiegeInput, meta(ActionKind.LAY_SIEGE, "siege_cost"), lay_siege),
        ToolSpec(SonToolId.OFFER_PEACE, son, OfferPeaceInput, meta(ActionKind.OFFER_PEACE, "peace_cost"), offer_peace),
        ToolSpec(SonToolId.COMMISSION_VESSEL, son, CommissionVesselInput, meta(ActionKind.BUILD_SHIP, "vessel_cost"), commission_vessel),
        ToolSpec(SonToolId.DESIGN_UNIT, son, DesignUnitInput, meta(ActionKind.DESIGN_UNIT, "design_cost"), design_unit),
        ToolSpec(SonToolId.PLANT_SPIES, son, PlantSpiesInput, meta(ActionKind.BUILD_SPY_NETWORK, "spies_cost"), plant_spies),
    ]
