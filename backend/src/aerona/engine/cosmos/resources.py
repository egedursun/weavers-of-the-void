from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmic_state import ResourceMechanicRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.models.entity_stats import ResourceStats
from aerona.domain.models.profiles import TravelResource
from aerona.engine.economy.resources import set_resource_yield
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

ABUNDANCE_KEY = "abundance"
COSMIC_DEPOSIT_MECHANICS = frozenset({ResourceMechanic.ADDICTIVE, ResourceMechanic.FIXED})


async def set_mechanics(session: AsyncSession, resource: EntityRow, mechanics: Iterable[ResourceMechanic], sacred_son_id: int | None = None) -> None:
    ordered = list(dict.fromkeys(mechanics))
    if resource.entity_type is not EntityType.RESOURCE:
        raise ValidationFailedError("Only a resource can carry resource mechanics.")
    await session.execute(delete(ResourceMechanicRow).where(ResourceMechanicRow.entity_id == resource.id))
    primary = ResourceMechanic.SACRED if ResourceMechanic.SACRED in ordered and sacred_son_id is not None else None
    if primary is None:
        primary = next((item for item in ordered if item is not ResourceMechanic.SACRED), None)
    resource.resource_mechanic = primary
    resource.sacred_to_son_id = sacred_son_id if primary is ResourceMechanic.SACRED else None
    session.add_all(ResourceMechanicRow(entity_id=resource.id, mechanic=item) for item in ordered if item is not primary)
    if await session.get(EntityFlagRow, (resource.id, EntityFlag.MECHANICS_WEIGHED)) is None:
        session.add(EntityFlagRow(entity_id=resource.id, flag=EntityFlag.MECHANICS_WEIGHED, epoch=None))
    await session.flush()


async def owners(session: AsyncSession, resource_id: int) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(BondRow.target_node_id == resource_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, EntityRow.status == EntityStatus.CANON)
        .order_by(BondRow.epoch, BondRow.id)
    )
    return list((await session.scalars(statement)).unique())


async def cosmic_deposits(session: AsyncSession, world_id: int | None = None) -> list[EntityRow]:
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.RESOURCE,
        EntityRow.engine_kind == EngineKind.COSMIC_TRAVEL_RESOURCE,
        EntityRow.status == EntityStatus.CANON,
    )
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    return list(await session.scalars(statement.order_by(EntityRow.id)))


async def has_access(session: AsyncSession, traveller_id: int, deposit: EntityRow) -> bool:
    holders = await owners(session, deposit.id)
    if any(holder.id == traveller_id for holder in holders):
        return True
    bonds = BondRepository(session)
    for holder in holders:
        if await bonds.exists_between(traveller_id, holder.id, BondKind.TRADES_WITH):
            return True
    return False


async def cosmic_access(session: AsyncSession, traveller_id: int, minimum_abundance: int) -> EntityRow | None:
    for deposit in await cosmic_deposits(session):
        if stat_or(deposit, ABUNDANCE_KEY, 0) >= minimum_abundance and await has_access(session, traveller_id, deposit):
            return deposit
    return None


@dataclass(frozen=True)
class DepositSpec:
    region: EntityRow
    abundance: int
    value: int
    might: int
    power_level: int
    name: str | None = None
    origin: EntityOrigin = EntityOrigin.ENGINE
    creator_son_id: int | None = None


async def create_cosmic_deposit(session: AsyncSession, rules: Rules, epoch: int, resource: TravelResource, spec: DepositSpec) -> EntityRow:
    region = spec.region
    deposit = await open_record(
        session,
        epoch,
        RecordSpec(
            name=spec.name or f"{resource.name} Deposit ({region.name})",
            entity_type=EntityType.RESOURCE,
            body=f"A vein of {resource.name} in the soil of {region.name}. {resource.rule}".strip(),
            stats=ResourceStats(abundance=clamp_percent(spec.abundance), value=clamp_percent(spec.value), might=clamp_percent(spec.might)),
            power=spec.power_level,
            world_id=region.world_id,
            location_id=region.id,
            subtype="cosmic travel resource",
            engine_kind=EngineKind.COSMIC_TRAVEL_RESOURCE,
            resource_mechanic=ResourceMechanic.ADDICTIVE,
            origin=spec.origin,
            creator_son_id=spec.creator_son_id,
        ),
    )
    await set_mechanics(session, deposit, COSMIC_DEPOSIT_MECHANICS)
    await set_resource_yield(session, rules, deposit.id, CommodityKind.MAGICAL_REAGENTS)
    return deposit


def economy_deposit(rules: Rules, rng: SeededRandom, region: EntityRow) -> DepositSpec:
    economy = rules.economy
    return DepositSpec(
        region=region,
        abundance=economy.deposit_abundance + rng.die(economy.deposit_abundance_die),
        value=economy.deposit_value,
        might=economy.deposit_might,
        power_level=economy.deposit_power,
    )


async def define_cosmic_resource(session: AsyncSession, resource: TravelResource, replace: bool = False) -> TravelResource:
    cosmos = await CosmosRepository(session).require_cosmos()
    if cosmos.travel_resource is not None and not replace:
        raise ValidationFailedError("The cosmos already has its travel resource.")
    if not resource.name.strip():
        raise ValidationFailedError("The travel resource needs a name.")
    cosmos.travel_resource = resource
    await session.flush()
    return resource


async def travel_resource(session: AsyncSession) -> TravelResource | None:
    cosmos = await CosmosRepository(session).get()
    return cosmos.travel_resource if cosmos is not None else None


async def claim(session: AsyncSession, owner: EntityRow, resource: EntityRow, epoch: int, reason: str) -> BondRow:
    return await BondRepository(session).connect(BondDraft(owner.id, resource.id, BondKind.OWNS, epoch, reason))
