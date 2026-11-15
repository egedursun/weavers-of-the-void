from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.fossils import FossilBedRow
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.lifecycle_ends import LifecycleStateRow
from aerona.db.tables.museums import MuseumCollectionRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.world_ends import WorldEndRow
from aerona.engine.lifecycle.states import GONE


async def son_lifecycle_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    rows = (
        await scope.session.execute(
            select(EntityRow, LifecycleStateRow)
            .join(LifecycleStateRow, LifecycleStateRow.holder_entity_id == EntityRow.id)
            .where(EntityRow.world_id == son.current_world_id, LifecycleStateRow.state.in_(list(GONE)))
            .order_by(EntityRow.id)
        )
    ).all()
    shown = [f"{entity.name} (id {entity.id}, {row.kind.value.replace('_', ' ')}, {row.state.value})" for entity, row in rows]
    return [f"Lore and powers of the world you walk that have come to an end or lie dormant: {', '.join(shown)}."] if shown else []


async def son_world_end_lines(scope: Scope, son: SonRow) -> list[str]:
    del son
    ended = select(WorldRow.name, WorldEndRow.state).join(WorldEndRow, WorldEndRow.world_id == WorldRow.id).order_by(WorldRow.id)
    rows = (await scope.session.execute(ended)).all()
    shown = [f"{name} ({state.value.replace('_', ' ')})" for name, state in rows]
    return [f"Worlds that have come to their end: {', '.join(shown)}."] if shown else []


async def son_fossil_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    hidden = (
        await scope.session.execute(
            select(EntityRow.id, EntityRow.name)
            .join(FossilBedRow, FossilBedRow.region_entity_id == EntityRow.id)
            .where(FossilBedRow.world_id == son.current_world_id, FossilBedRow.found_epoch.is_(None))
            .distinct()
            .order_by(EntityRow.id)
        )
    ).all()
    shown = [f"{name} (id {region_id})" for region_id, name in hidden]
    return [f"Lands of the world you walk where remains lie hidden: {', '.join(shown)}."] if shown else []


async def mortal_grounds_lines(scope: Scope, me: EntityRow) -> list[str]:
    town = await scope.session.get(EntityRow, me.location_id) if me.location_id is not None else None
    if town is None:
        return []
    found: list[str] = []
    kept = select(MuseumCollectionRow).where(MuseumCollectionRow.keeper_entity_id == town.id).order_by(MuseumCollectionRow.id)
    for hoard in await scope.session.scalars(kept):
        found.append(f"{town.name} keeps a collection ({hoard.kind.value.replace('_', ' ')}, prestige {hoard.prestige})")
    for garden in await scope.session.scalars(select(GardenRow).where(GardenRow.settlement_entity_id == town.id).order_by(GardenRow.id)):
        found.append(f"a garden ({garden.kind.value.replace('_', ' ')}, condition {garden.condition})")
    for bed in await scope.session.scalars(select(FossilBedRow).where(FossilBedRow.finder_entity_id == town.id).order_by(FossilBedRow.id)):
        found.append(f"remains found there ({bed.source.value.replace('_', ' ')}, read as {bed.reading.value.replace('_', ' ')})")
    return found
