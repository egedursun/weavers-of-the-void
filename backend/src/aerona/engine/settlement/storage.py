from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import WorkshopDesignRow, WorkshopRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.society import Commodity
from aerona.engine.economy.workshop_designs import workshop_store_units
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class StorageParts:
    districts: int
    workshops: int
    other: int = 0

    @property
    def total(self) -> int:
        return self.districts + self.workshops + self.other


def store_kind(aggregate: Commodity) -> WorkshopKind:
    return WorkshopKind.GRANARY if aggregate is Commodity.FOOD else WorkshopKind.WAREHOUSE


def workshop_store(rules: Rules, store: WorkshopRow | None, aggregate: Commodity, design: WorkshopDesignRow | None = None) -> int:
    table = rules.districts
    return workshop_store_units(store, design, table.granary_workshop_store if aggregate is Commodity.FOOD else table.warehouse_workshop_store)


def settlement_store(
    rules: Rules, district_units: int, store: WorkshopRow | None, aggregate: Commodity, *, other: int = 0, design: WorkshopDesignRow | None = None
) -> StorageParts:
    return StorageParts(district_units, workshop_store(rules, store, aggregate, design), other)


def held_capacity(infrastructure: SettlementInfrastructureRow, aggregate: Commodity) -> int:
    return infrastructure.granary_capacity if aggregate is Commodity.FOOD else infrastructure.warehouse_capacity


def capacity_of(
    rules: Rules, infrastructure: SettlementInfrastructureRow | None, store: WorkshopRow | None, aggregate: Commodity, design: WorkshopDesignRow | None = None
) -> int:
    if infrastructure is not None:
        return held_capacity(infrastructure, aggregate)
    return workshop_store(rules, store, aggregate, design)


def storage_index(rules: Rules, capacity: int, need: int) -> int:
    return rules.economy.storage_base_index + round_half_up(capacity * rules.economy.supply_index_epoch / max(1, need))


def storage_room(rules: Rules, capacity: int, need: int) -> int:
    return round_half_up(rules.economy.storage_base_index * max(1, need) / rules.economy.supply_index_epoch) + capacity


async def community_capacity(session: AsyncSession, rules: Rules, community_id: int, aggregate: Commodity) -> int:
    infrastructure = await session.get(SettlementInfrastructureRow, community_id)
    store = await session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == community_id, WorkshopRow.kind == store_kind(aggregate)))
    design = await design_for(session, store)
    return capacity_of(rules, infrastructure, store, aggregate, design)


async def design_for(session: AsyncSession, store: WorkshopRow | None) -> WorkshopDesignRow | None:
    return await session.get(WorkshopDesignRow, store.design_id) if store is not None and store.design_id is not None else None
