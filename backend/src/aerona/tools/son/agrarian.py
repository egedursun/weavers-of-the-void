from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.db.tables.agrarian import SoilNutrientRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.agrarian import AidKind, KeystoneUse, NutrientKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.agrarian import control
from aerona.engine.agrarian.resilience import per_thousand
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import definite
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
NAME = 200


class DesignateKeystoneInput(ToolInput):
    species_id: int
    region_id: int
    name: str = Field(min_length=1, max_length=NAME)
    use: KeystoneUse
    cult_id: int | None = None
    reason: Reason


class TendSoilStockInput(ToolInput):
    region_id: int
    stock: NutrientKind
    change: int = Field(ge=-100, le=100)
    reason: Reason


class InspireReliefInput(ToolInput):
    giver_id: int
    settlement_id: int
    kind: AidKind
    reason: Reason


async def reached(call: SonCall, entity_id: int, kinds: frozenset[EntityType], refused: SonResult, why: str) -> EntityRow:
    entity = await living_entity(call.session, entity_id)
    if entity is None or entity.entity_type not in kinds:
        fail(refused, why=why)
    await ensure_in_reach(call, entity)
    if held(entity.id):
        fail(refused, why="it is held")
    return entity


async def designate_keystone(call: SonCall, args: DesignateKeystoneInput) -> str:
    species = await reached(call, args.species_id, frozenset({EntityType.SPECIES}), SonResult.KEYSTONE_REFUSED, "there is no such species")
    land = await reached(call, args.region_id, frozenset({EntityType.REGION}), SonResult.KEYSTONE_REFUSED, "there is no such land")
    if args.cult_id is not None:
        await reached(call, args.cult_id, frozenset({EntityType.CULT}), SonResult.KEYSTONE_REFUSED, "there is no such cult")
    if land.world_id is None:
        fail(SonResult.KEYSTONE_REFUSED, why="that land lies in no world")
    try:
        row = await control.designate_keystone(
            call.tick, land.world_id, args.name, use=args.use, producer_id=species.id, source_id=land.id, cult_id=args.cult_id, son_id=call.son.id
        )
    except ValidationFailedError as error:
        fail(SonResult.KEYSTONE_REFUSED, why=str(error).rstrip("."))
    call.target(land.id)
    await call.record(
        "tools.son.designate_keystone",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [species.id, land.id]},
        facts={"name": definite(row.name), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.KEYSTONE_DESIGNATED, name=definite(row.name), land=land.name, use=spoken(row.use))


async def inspire_relief(call: SonCall, args: InspireReliefInput) -> str:
    giver = await reached(call, args.giver_id, frozenset({EntityType.POLITY, EntityType.CULT}), SonResult.RELIEF_REFUSED, "there is no such realm or cult")
    town = await reached(call, args.settlement_id, frozenset({EntityType.SETTLEMENT}), SonResult.RELIEF_REFUSED, "there is no such town")
    try:
        row = await control.send_aid(call.tick, giver.id, town.id, args.kind, per_thousand(call.tick.rules.relief.cap, town))
    except ValidationFailedError as error:
        fail(SonResult.RELIEF_REFUSED, why=str(error).rstrip("."))
    call.target(town.id)
    await call.record(
        "tools.son.inspire_relief",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [giver.id, town.id]},
        facts={"giver_detail": str(giver.name), "town": str(town.name), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.RELIEF_TURNED_AWAY if row.refused else SonResult.RELIEF_INSPIRED, giver=giver.name, town=town.name, kind=spoken(args.kind))


async def tend_soil_stock(call: SonCall, args: TendSoilStockInput) -> str:
    land = await reached(call, args.region_id, frozenset({EntityType.REGION}), SonResult.SOIL_STOCK_REFUSED, "there is no such land")
    if held(land.id):
        fail(SonResult.SOIL_STOCK_REFUSED, why="that land is held")
    try:
        known = await call.session.get(SoilNutrientRow, (land.id, args.stock))
        if known is not None and "stock" in known.locked:
            fail(SonResult.SOIL_STOCK_REFUSED, why="that stock of the soil is held")
        start = known.stock if known is not None else 0
        row = await control.set_nutrient(call.tick, land.id, args.stock, {"stock": clamp_int(start + args.change, 0, PERCENT)})
    except ValidationFailedError as error:
        fail(SonResult.SOIL_STOCK_REFUSED, why=str(error).rstrip("."))
    call.target(land.id)
    await call.record(
        "tools.son.tend_soil_stock",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: land.id},
        facts={"stock": args.stock, "level": row.stock, "reason": args.reason},
        place=land.id,
    )
    return result(SonResult.SOIL_STOCK_TENDED, land=land.name, stock=spoken(args.stock), level=row.stock)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.DESIGNATE_KEYSTONE, son, DesignateKeystoneInput, meta, designate_keystone),
        ToolSpec(SonToolId.INSPIRE_RELIEF, son, InspireReliefInput, meta, inspire_relief),
        ToolSpec(SonToolId.TEND_SOIL_STOCK, son, TendSoilStockInput, meta, tend_soil_stock),
    ]
