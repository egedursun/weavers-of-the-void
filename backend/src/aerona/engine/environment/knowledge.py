from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityTerritoryRow
from aerona.db.tables.region import PolityMapKnowledgeRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules


async def polity_of(session: AsyncSession, member_id: int | None) -> int | None:
    if member_id is None:
        return None
    found: int | None = await session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == member_id).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )
    return found


async def knowledge_of(session: AsyncSession, polity_id: int | None, region_id: int | None) -> int | None:
    if polity_id is None or region_id is None:
        return None
    row = await session.get(PolityMapKnowledgeRow, (polity_id, region_id))
    return row.level if row is not None else 0


def reveals(rules: Rules, level: int) -> dict[str, bool]:
    table = rules.terrain
    return {"terrain": level >= table.reveal_terrain_at, "sacred": level >= table.reveal_sacred_at, "minerals": level >= table.reveal_minerals_at}


@dataclass
class Floors:
    levels: dict[int, dict[int, int]] = field(default_factory=lambda: defaultdict(dict))
    owned: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    members: dict[int, int] = field(default_factory=dict)
    homes: dict[int, int | None] = field(default_factory=dict)

    def lift(self, polity_id: int, region_id: int | None, level: int) -> None:
        if region_id is not None:
            self.levels[polity_id][region_id] = max(self.levels[polity_id].get(region_id, 0), level)

    def polity_for(self, entity_id: int) -> int | None:
        return self.members.get(entity_id) or self.members.get(self.homes.get(entity_id) or 0)


async def _territory(session: AsyncSession, rules: Rules, atlas: RegionAtlas, floors: Floors, polities: set[int]) -> None:
    table = rules.terrain
    for polity_id, region_id, control in await session.execute(
        select(PolityTerritoryRow.polity_entity_id, PolityTerritoryRow.region_entity_id, PolityTerritoryRow.control)
    ):
        if polity_id in polities and control > 0:
            floors.owned[polity_id].add(region_id)
            floors.lift(polity_id, region_id, table.knowledge_owned)
    for polity_id, regions in floors.owned.items():
        for region_id in sorted(regions):
            for neighbour in atlas.neighbour_regions(region_id):
                floors.lift(polity_id, neighbour, table.knowledge_neighbour)


async def _maps(session: AsyncSession, rules: Rules, atlas: RegionAtlas, floors: Floors) -> None:
    maps = select(ItemProfileRow.item_entity_id).where(ItemProfileRow.item_class == ItemClass.MAP)
    holders = list(
        await session.scalars(
            select(BondRow.source_node_id).where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(maps))
        )
    )
    if not holders:
        return
    worlds: dict[int, list[int]] = defaultdict(list)
    for region_id in await session.scalars(select(EntityRow.id).where(EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)):
        world = atlas.world_of(region_id)
        if world is not None:
            worlds[world].append(region_id)
    for holder in holders:
        holder_polity = floors.polity_for(holder)
        if holder_polity is None:
            continue
        for region_id in worlds.get(atlas.world_of(holder) or 0, []):
            floors.lift(holder_polity, region_id, rules.terrain.knowledge_map_item)


async def _floors(session: AsyncSession, rules: Rules, atlas: RegionAtlas) -> tuple[dict[int, dict[int, int]], dict[int, set[int]]]:
    floors = Floors()
    polities = set(await session.scalars(select(EntityRow.id).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON)))
    await _territory(session, rules, atlas, floors, polities)
    for polity_id, member_id in await session.execute(
        select(PolityMemberRow.polity_entity_id, PolityMemberRow.member_entity_id).order_by(PolityMemberRow.polity_entity_id)
    ):
        if polity_id in polities:
            floors.members.setdefault(member_id, polity_id)
    floors.homes = {
        row.id: row.location_id
        for row in await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON))
    }
    discoveries = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.DISCOVERED, BondRow.state == BondState.ACTIVE)
    )
    for finder, land in discoveries:
        finder_polity = floors.polity_for(finder)
        if finder_polity is not None:
            floors.lift(finder_polity, atlas.top_region(land), rules.terrain.knowledge_discovered)
    await _maps(session, rules, atlas, floors)
    return floors.levels, floors.owned


async def _frontiers(session: AsyncSession, atlas: RegionAtlas, owned: dict[int, set[int]]) -> dict[int, set[int]]:
    explorers = await session.scalars(
        select(EntityRow.location_id).where(
            EntityRow.entity_type == EntityType.MORTAL, EntityRow.mortal_role == MortalRole.EXPLORER, EntityRow.status == EntityStatus.CANON
        )
    )
    members: dict[int, int] = {}
    for polity_id, member_id in await session.execute(
        select(PolityMemberRow.polity_entity_id, PolityMemberRow.member_entity_id).order_by(PolityMemberRow.polity_entity_id)
    ):
        members.setdefault(member_id, polity_id)
    frontier: dict[int, set[int]] = defaultdict(set)
    for home in explorers:
        explorer_polity = members.get(home or 0)
        if explorer_polity is None:
            continue
        polity_id = explorer_polity
        for region_id in sorted(owned.get(polity_id, set())):
            for neighbour in atlas.neighbour_regions(region_id):
                for beyond in atlas.neighbour_regions(neighbour):
                    if beyond not in owned[polity_id]:
                        frontier[polity_id].add(beyond)
                frontier[polity_id].add(neighbour)
    return frontier


async def chart(session: AsyncSession, rules: Rules, atlas: RegionAtlas, epoch: int) -> int:
    table = rules.terrain
    floors, owned = await _floors(session, rules, atlas)
    frontier = await _frontiers(session, atlas, owned)
    rows = {(row.polity_entity_id, row.region_entity_id): row for row in await session.scalars(select(PolityMapKnowledgeRow))}
    pairs = (
        set(rows)
        | {(polity_id, region_id) for polity_id, regions in floors.items() for region_id in regions}
        | {(polity_id, region_id) for polity_id, regions in frontier.items() for region_id in regions}
    )
    changed = 0
    for polity_id, region_id in sorted(pairs):
        row = rows.get((polity_id, region_id))
        if row is not None and row.held:
            continue
        floor = floors.get(polity_id, {}).get(region_id, 0)
        previous = row.level if row is not None else 0
        drift = table.knowledge_explore_gain if region_id in frontier.get(polity_id, set()) else -table.knowledge_decay
        level = clamp_int(max(floor, previous + drift), 0, PERCENT)
        if row is None:
            if level <= 0:
                continue
            session.add(PolityMapKnowledgeRow(polity_entity_id=polity_id, region_entity_id=region_id, level=level, held=False, updated_epoch=epoch))
            changed += 1
        elif level <= 0:
            await session.delete(row)
            changed += 1
        elif level != row.level:
            row.level = level
            row.updated_epoch = epoch
            changed += 1
    await session.flush()
    return changed
