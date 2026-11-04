from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.society import Commodity
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


def workshop_store(rules: Rules, store: WorkshopRow | None, aggregate: Commodity) -> int:
    if store is None:
        return 0
    table = rules.districts
    return store.level * (table.granary_workshop_store if aggregate is Commodity.FOOD else table.warehouse_workshop_store)


def settlement_store(rules: Rules, district_units: int, store: WorkshopRow | None, aggregate: Commodity, other: int = 0) -> StorageParts:
    return StorageParts(district_units, workshop_store(rules, store, aggregate), other)


def held_capacity(infrastructure: SettlementInfrastructureRow, aggregate: Commodity) -> int:
    return infrastructure.granary_capacity if aggregate is Commodity.FOOD else infrastructure.warehouse_capacity


def capacity_of(rules: Rules, infrastructure: SettlementInfrastructureRow | None, store: WorkshopRow | None, aggregate: Commodity) -> int:
    if infrastructure is not None:
        return held_capacity(infrastructure, aggregate)
    return workshop_store(rules, store, aggregate)


def storage_index(rules: Rules, capacity: int, need: int) -> int:
    return rules.economy.storage_base_index + round_half_up(capacity * rules.economy.supply_index_epoch / max(1, need))


def storage_room(rules: Rules, capacity: int, need: int) -> int:
    return round_half_up(rules.economy.storage_base_index * max(1, need) / rules.economy.supply_index_epoch) + capacity


async def community_capacity(session: AsyncSession, rules: Rules, community_id: int, aggregate: Commodity) -> int:
    infrastructure = await session.get(SettlementInfrastructureRow, community_id)
    store = await session.scalar(select(WorkshopRow).where(WorkshopRow.community_entity_id == community_id, WorkshopRow.kind == store_kind(aggregate)))
    return capacity_of(rules, infrastructure, store, aggregate)
