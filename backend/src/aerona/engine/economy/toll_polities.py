from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow, PolityTerritoryRow, PolityTreasuryRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.engine.context import TickContext
from aerona.rules.registry import Rules


@dataclass
class Realms:
    polities: set[int] = field(default_factory=set)
    member_of: dict[int, int] = field(default_factory=dict)
    territory: dict[int, tuple[int, int]] = field(default_factory=dict)
    free: set[int] = field(default_factory=set)

    @classmethod
    async def load(cls, session: AsyncSession) -> "Realms":
        living = select(EntityRow.id).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON)
        polities = set(await session.scalars(select(PolityProfileRow.polity_entity_id).where(PolityProfileRow.polity_entity_id.in_(living))))
        member_of: dict[int, int] = {}
        for member in await session.scalars(select(PolityMemberRow).order_by(PolityMemberRow.polity_entity_id)):
            if member.polity_entity_id in polities:
                member_of.setdefault(member.member_entity_id, member.polity_entity_id)
        territory: dict[int, tuple[int, int]] = {}
        for row in await session.scalars(select(PolityTerritoryRow).order_by(PolityTerritoryRow.polity_entity_id)):
            if row.polity_entity_id not in polities:
                continue
            best = territory.get(row.region_entity_id)
            if best is None or row.control > best[1]:
                territory[row.region_entity_id] = (row.polity_entity_id, row.control)
        free = set(await session.scalars(select(SettlementProfileRow.settlement_entity_id).where(SettlementProfileRow.free_city.is_(True))))
        return cls(polities, member_of, territory, free)

    def polity_of(self, entity_id: int | None) -> int | None:
        if entity_id is None:
            return None
        return entity_id if entity_id in self.polities else self.member_of.get(entity_id)

    def treasury_of(self, controller_id: int | None) -> int | None:
        if controller_id is None or controller_id in self.free:
            return None
        return self.polity_of(controller_id)

    def masters(self, rules: Rules) -> dict[int, int]:
        floor = rules.tolls.territory_control_pct
        return {region: polity for region, (polity, control) in sorted(self.territory.items()) if control >= floor}


async def fund_polity(ctx: TickContext, polity_id: int, amount: int, label: str) -> int:
    profile = await ctx.session.get(PolityProfileRow, polity_id)
    if profile is None or amount <= 0:
        return 0
    profile.treasury += amount
    ctx.session.add(
        PolityTreasuryRow(polity_entity_id=polity_id, epoch=ctx.epoch, entry=TreasuryEntry.TOLLS, amount=amount, balance=profile.treasury, note=label)
    )
    return amount
