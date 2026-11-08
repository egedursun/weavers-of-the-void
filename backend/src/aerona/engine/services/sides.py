from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.warfare import CaptiveRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.war import CaptiveStatus
from aerona.engine.services.war_geography import Neighbourhood

SIDE_BOND_ORDER = (BondKind.PROTECTS, BondKind.RULES, BondKind.DESCENDS_FROM)


async def held_captives(session: AsyncSession) -> set[int]:
    return set(await session.scalars(select(CaptiveRow.captive_entity_id).where(CaptiveRow.status == CaptiveStatus.HELD)))


class SideIndex:
    def __init__(self, communities: dict[int, EntityRow], mortals: list[EntityRow], sides: dict[int, int | None], captives: set[int]) -> None:
        self._communities = communities
        self._mortals = mortals
        self._sides = sides
        self._captives = captives

    @classmethod
    async def load(cls, session: AsyncSession, neighbourhood: Neighbourhood) -> "SideIndex":
        canon = list(
            await session.scalars(
                select(EntityRow)
                .where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_([*COMMUNITY_TYPES, EntityType.MORTAL]))
                .order_by(EntityRow.id)
            )
        )
        communities = {entity.id: entity for entity in canon if entity.entity_type in COMMUNITY_TYPES}
        mortals = [entity for entity in canon if entity.entity_type is EntityType.MORTAL]
        targets: dict[tuple[int, BondKind], list[int]] = defaultdict(list)
        rows = await session.execute(
            select(BondRow.source_node_id, BondRow.kind, BondRow.target_node_id)
            .where(BondRow.state == BondState.ACTIVE, BondRow.kind.in_(SIDE_BOND_ORDER), BondRow.source_node_id.in_([mortal.id for mortal in mortals]))
            .order_by(BondRow.id)
        )
        for source, kind, target in rows:
            targets[(source, kind)].append(target)
        peoples_by_region: dict[int, int] = {}
        for community in communities.values():
            region = neighbourhood.top_region(community.id)
            if community.entity_type is EntityType.PEOPLE and region is not None:
                peoples_by_region.setdefault(region, community.id)
        sides: dict[int, int | None] = {}
        for mortal in mortals:
            sides[mortal.id] = cls._resolve(mortal, communities, targets, peoples_by_region, neighbourhood)
        return cls(communities, mortals, sides, await held_captives(session))

    @staticmethod
    def _resolve(
        mortal: EntityRow,
        communities: dict[int, EntityRow],
        targets: dict[tuple[int, BondKind], list[int]],
        peoples_by_region: dict[int, int],
        neighbourhood: Neighbourhood,
    ) -> int | None:
        for kind in SIDE_BOND_ORDER:
            for target in targets.get((mortal.id, kind), []):
                if target in communities:
                    return target
        if mortal.location_id is not None and mortal.location_id in communities:
            return mortal.location_id
        region = neighbourhood.top_region(mortal.id)
        return peoples_by_region.get(region) if region is not None else None

    def side_of(self, entity: EntityRow) -> int | None:
        if entity.entity_type in COMMUNITY_TYPES:
            return entity.id
        return self._sides.get(entity.id)

    def heroes_of(self, community_id: int) -> list[EntityRow]:
        community = self._communities.get(community_id)
        if community is None:
            return []
        return [
            mortal
            for mortal in self._mortals
            if mortal.status is EntityStatus.CANON
            and mortal.world_id == community.world_id
            and mortal.id not in self._captives
            and self._sides.get(mortal.id) == community_id
        ]

    def mark_captive(self, mortal_id: int) -> None:
        self._captives.add(mortal_id)


async def heroes_of(session: AsyncSession, community_id: int, neighbourhood: Neighbourhood) -> list[EntityRow]:
    return (await SideIndex.load(session, neighbourhood)).heroes_of(community_id)
