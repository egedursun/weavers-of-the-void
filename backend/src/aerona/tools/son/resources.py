from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EngineKind, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.son import PowerEffect
from aerona.engine.cosmos.resources import DepositSpec, create_cosmic_deposit, travel_resource
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, no_cost
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

ABUNDANCE = "abundance"
LAND = frozenset({EntityType.REGION, EntityType.PLACE})
PERCENT = 100


class HarvestInput(ToolInput):
    resource_id: int


class CosmicBedInput(ToolInput):
    region_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def _may_harvest(call: SonCall, resource: EntityRow) -> bool:
    if resource.creator_son_id == call.son.id or resource.domain in call.son.domains:
        return True
    bonds = BondRepository(call.session)
    for owner in await bonds.incoming(resource.id, BondKind.OWNS):
        if await bonds.patron(owner.source_node_id) == call.son.id:
            return True
    return False


async def harvestable(call: SonCall) -> str:
    statement = select(EntityRow).where(EntityRow.entity_type == EntityType.RESOURCE, EntityRow.status == EntityStatus.CANON)
    if call.world_id is not None:
        statement = statement.where(EntityRow.world_id == call.world_id)
    found = [
        f"#{resource.id} {resource.name}"
        for resource in await call.session.scalars(statement.order_by(EntityRow.id))
        if resource.id not in call.turn.context.harvested_resource_ids and await _may_harvest(call, resource)
    ]
    return ", ".join(found[: call.rules.son_tools.choice_hints * 3]) or "none yet: create a resource or win worshippers who own one"


async def harvest_resource(call: SonCall, args: HarvestInput) -> str:
    tools = call.rules.son_tools
    resource = require_type(await require_canon(call.session, args.resource_id), {EntityType.RESOURCE}, SonResult.NOT_A_RESOURCE)
    await ensure_in_reach(call, resource)
    if resource.id in call.turn.context.harvested_resource_ids:
        fail(SonResult.ALREADY_HARVESTED)
    if not await _may_harvest(call, resource):
        fail(SonResult.NO_RIGHT, choices=await harvestable(call))
    abundance = stat_or(resource, ABUNDANCE, 0)
    if abundance < tools.harvest_depleted_threshold:
        fail(SonResult.EXHAUSTED)
    son = call.son
    gain = round(abundance / tools.harvest_abundance_divisor + son.wisdom / tools.harvest_wisdom_divisor + son.might / tools.harvest_might_divisor)
    if await call.has_power(PowerEffect.HARVESTER):
        gain *= tools.harvest_power_mult
    left = max(0, min(PERCENT, abundance - tools.harvest_abundance_loss))
    set_stats(resource, abundance=left)
    gained = call.gain_essence(gain)
    call.turn.remember_harvest(resource.id)
    call.target(resource.id)
    await call.bump(TurnCounter.HARVESTS)
    await call.chronicle(ChronicleKind.RESOURCE, lines.HARVEST, entity_ids=[resource.id], son=son.name, gain=gained, resource=resource.name, abundance=left)
    return result(SonResult.HARVESTED, gain=gained, name=resource.name, abundance=left)


async def open_cosmic_bed(call: SonCall, args: CosmicBedInput) -> str:
    tools = call.rules.son_tools
    region = require_type(await require_canon(call.session, args.region_id), LAND, SonResult.BED_LAND_ONLY)
    await ensure_in_reach(call, region)
    resource = await travel_resource(call.session)
    if resource is None:
        fail(SonResult.NO_TRAVEL_RESOURCE)
    existing = await call.session.scalar(
        select(EntityRow.id).where(
            EntityRow.location_id == region.id,
            EntityRow.engine_kind == EngineKind.COSMIC_TRAVEL_RESOURCE,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    if existing is not None:
        fail(SonResult.BED_EXISTS, name=region.name)
    require_essence(call, tools.open_deposit_cost)
    hand = call.rules.god_hand
    spec = DepositSpec(
        region=region,
        abundance=hand.deposit_abundance,
        value=hand.deposit_value,
        might=hand.deposit_might,
        power_level=hand.deposit_power,
        origin=EntityOrigin.SON,
        creator_son_id=call.son.id,
    )
    bed = await create_cosmic_deposit(call.session, call.epoch, resource, spec)
    call.spend_essence(tools.open_deposit_cost)
    call.remember_creation(bed.id)
    call.target(bed.id)
    await call.chronicle(
        ChronicleKind.COSMIC, lines.COSMIC_BED, entity_ids=[bed.id, region.id], son=call.son.name, bed=bed.name, region=region.name, reason=args.reason
    )
    return result(SonResult.BED_OPENED, id=bed.id, name=bed.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(SonToolId.HARVEST_RESOURCE, son, HarvestInput, ToolMeta(ActionKind.HARVEST_RESOURCE, no_cost), harvest_resource),
        ToolSpec(
            SonToolId.OPEN_COSMIC_BED,
            son,
            CosmicBedInput,
            ToolMeta(
                ActionKind.OPEN_COSMIC_BED,
                lambda rules: rules.son_tools.open_deposit_ap,
                essence_cost=lambda rules: rules.son_tools.open_deposit_cost,
                rarity_gate=gate(Gate.OPEN_COSMIC_BED),
            ),
            open_cosmic_bed,
        ),
    ]
