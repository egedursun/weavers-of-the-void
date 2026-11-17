from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.methods import METHODS
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.tables.living import LivingLineRow, LivingLineTraitRow, LivingProfileRow
from aerona.db.tables.made import AugmentRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.industry import MethodKind
from aerona.domain.enums.living import LineTrait, Metabolism
from aerona.domain.enums.made import AugmentKind, AugmentMake, AugmentSlot
from aerona.domain.enums.minds import MindUpkeep
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.domain.models.entity_stats import ItemStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.living.control import give_life
from aerona.engine.living.kin import line_of
from aerona.engine.living.production import LIVING_METHODS
from aerona.engine.military.orders import create_vessel
from aerona.engine.military.shipyard import Commission
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import record
from aerona.engine.structures.profiles import ensure_profile

GROWN_POWER = 1
WORKS_LIFESPAN = 120
VESSEL_LIFESPAN = 80
GEAR_LIFESPAN = 30
HALF = PERCENT // 2


@dataclass(frozen=True)
class Growing:
    maker: EntityRow
    line_id: int | None
    name: str


async def grown_line(ctx: TickContext, line_id: int | None) -> LivingLineRow | None:
    return await line_of(ctx, line_id) if line_id is not None else None


async def grow_structure(ctx: TickContext, order: Growing, kind: StructureKind = StructureKind.BOTANICAL_GARDEN) -> EntityRow:
    town = order.maker.location_id if order.maker.entity_type is not EntityType.SETTLEMENT else order.maker.id
    if town is None:
        raise ValidationFailedError("A grown work needs a town to grow in.")
    await grown_line(ctx, order.line_id)
    work = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.STRUCTURE,
            name=order.name,
            body=f"Grown by {order.maker.name} in epoch {ctx.epoch}.",
            stats=StructureStats(splendor=HALF, durability=HALF, function=HALF),
            power=GROWN_POWER,
            world_id=order.maker.world_id,
            location_id=town,
        ),
    )
    await ensure_profile(ctx.session, ctx.rules, ctx.epoch, work, kind, builder=order.maker, architect_id=order.maker.id)
    await connect(ctx.session, order.maker.id, work.id, BondKind.BUILT, ctx.epoch, description="grew it")
    await give_life(ctx, work.id, line_id=order.line_id, metabolism=Metabolism.LIGHT, lifespan=WORKS_LIFESPAN, bonded_to=order.maker.id)
    return work


async def grow_vessel(ctx: TickContext, order: Growing) -> EntityRow:
    await grown_line(ctx, order.line_id)
    vessel = await create_vessel(ctx, order.maker.id, order.name, Commission(frame=VehicleFrame.BIOSHIP))
    await give_life(ctx, vessel.id, line_id=order.line_id, metabolism=Metabolism.FEEDING, lifespan=VESSEL_LIFESPAN, bonded_to=order.maker.id)
    return vessel


async def grow_gear(ctx: TickContext, order: Growing) -> EntityRow:
    await grown_line(ctx, order.line_id)
    strength = 0
    if order.line_id is not None:
        rows = await ctx.session.scalars(
            select(LivingLineTraitRow.strength).where(LivingLineTraitRow.line_id == order.line_id, LivingLineTraitRow.trait == LineTrait.STRENGTH)
        )
        strength = sum(rows)
    gear = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.ITEM,
            name=order.name,
            body=f"Grown by {order.maker.name} to be worn, in epoch {ctx.epoch}.",
            stats=ItemStats(damage=clamp_percent(HALF + strength // 2), protection=clamp_percent(HALF + strength // 2)),
            power=GROWN_POWER,
            world_id=order.maker.world_id,
            location_id=order.maker.id,
        ),
    )
    await connect(ctx.session, order.maker.id, gear.id, BondKind.OWNS, ctx.epoch, description="grew it to be worn")
    await give_life(ctx, gear.id, line_id=order.line_id, metabolism=Metabolism.HOST, lifespan=GEAR_LIFESPAN, bonded_to=order.maker.id)
    return gear


async def grow_organ(ctx: TickContext, bearer: EntityRow, slot: AugmentSlot, kind: AugmentKind, grower_id: int) -> AugmentRow:
    row = AugmentRow(
        bearer_node_id=bearer.id,
        slot=slot,
        kind=kind,
        make=AugmentMake.GROWN,
        quality=HALF + HALF // 2,
        upkeep=MindUpkeep.FOOD,
        integration=PERCENT - PERCENT // 10,
        installed_by_node_id=grower_id,
        installed_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(ctx, "living.organ_grown", roles={IncidentRole.PATIENT: bearer.id, IncidentRole.MAKER: grower_id}, facts={"integration": row.integration})
    return row


async def found_living_works(ctx: TickContext, maker: EntityRow, method: MethodKind, name: str) -> EntityRow:
    if method not in LIVING_METHODS:
        raise ValidationFailedError("That is not a way of making by living things.")
    town = maker.location_id if maker.entity_type is not EntityType.SETTLEMENT else maker.id
    if town is None:
        raise ValidationFailedError("Living works need a town.")
    process = METHODS[method].process
    found = await ctx.session.scalar(select(CommunityMethodRow).where(CommunityMethodRow.community_node_id == town, CommunityMethodRow.process == process))
    if found is None:
        ctx.session.add(CommunityMethodRow(community_node_id=town, process=process, method=method, adopted_epoch=ctx.epoch, locked=[]))
    elif "method" in found.locked:
        raise ValidationFailedError("The way this town works is held as it is.")
    else:
        found.method, found.adopted_epoch = method, ctx.epoch
    works = await grow_structure(ctx, Growing(maker, None, name), StructureKind.WORKSHOP)
    profile = await ctx.session.get(LivingProfileRow, works.id)
    if profile is not None:
        profile.metabolism, profile.feed_commodity = Metabolism.FEEDING, CommodityKind.FODDER
        profile.feed_per_season = ctx.rules.living_production.works_feed
    return works


async def raise_sapience(ctx: TickContext, line: LivingLineRow, strength: int) -> LivingLineTraitRow:
    nervous = await ctx.session.scalar(
        select(LivingLineTraitRow).where(LivingLineTraitRow.line_id == line.id, LivingLineTraitRow.trait == LineTrait.NERVOUS_SYSTEM)
    )
    if nervous is None or nervous.strength <= 0:
        raise ValidationFailedError("A line needs a designed nervous system before it can be raised to thought.")
    found = await ctx.session.scalar(select(LivingLineTraitRow).where(LivingLineTraitRow.line_id == line.id, LivingLineTraitRow.trait == LineTrait.SAPIENCE))
    if found is None:
        found = LivingLineTraitRow(line_id=line.id, trait=LineTrait.SAPIENCE, strength=0, side_effect=False, locked=[])
        ctx.session.add(found)
    if "strength" not in found.locked:
        found.strength = clamp_percent(max(found.strength, strength))
    await ctx.session.flush()
    await record(ctx, "living.sapience_shaped", roles={IncidentRole.SUBJECT: line.species_entity_id}, facts={"line": line.name, "strength": found.strength})
    return found


async def license_line(ctx: TickContext, line: LivingLineRow, licensee: EntityRow, fee: int) -> LivingLineRow:
    owner = await ctx.session.get(EntityRow, line.owner_node_id) if line.owner_node_id is not None else None
    if owner is None:
        raise ValidationFailedError("A line with no owner cannot be licensed.")
    if not await take_coin(ctx.session, ctx.rules, licensee, fee):
        raise ValidationFailedError(f"{licensee.name} cannot pay for the licence.")
    await give_coin(ctx.session, ctx.rules, owner, fee)
    line.licensed = True
    await connect(ctx.session, licensee.id, owner.id, BondKind.TRADES_WITH, ctx.epoch, description=f"licensed the line {line.name}")
    await record(ctx, "living.licensed", roles={IncidentRole.BUYER: licensee.id, IncidentRole.SELLER: owner.id}, facts={"line": line.name, "fee": fee})
    return line
