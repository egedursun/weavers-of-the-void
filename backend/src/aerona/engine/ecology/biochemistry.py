from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.domestication import UNBOUND_BIOCHEMISTRY
from aerona.catalog.flora import world_life
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.flora import WorldBiochemistryRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import Biochemistry

LIFE_FIXUP = "flora.world_life"
ORDER = tuple(Biochemistry)


async def tolerated(session: AsyncSession, world_id: int | None) -> tuple[Biochemistry, ...]:
    if world_id is None:
        return ()
    statement = select(WorldBiochemistryRow.biochemistry).where(WorldBiochemistryRow.world_id == world_id)
    found = tuple(sorted(await session.scalars(statement), key=ORDER.index))
    if found or await session.get(AppliedFixupRow, f"{LIFE_FIXUP}.{world_id}") is not None:
        return found
    world = await session.get(WorldRow, world_id)
    return world_life(world.world_type, world.atmosphere) if world is not None else ()


def bearable(biochemistry: Biochemistry, allowed: tuple[Biochemistry, ...]) -> bool:
    return biochemistry in UNBOUND_BIOCHEMISTRY or biochemistry in allowed


async def can_live_on(session: AsyncSession, species_id: int, world_id: int | None) -> bool:
    profile = await session.get(SpeciesProfileRow, species_id)
    if profile is None or world_id is None or await session.get(WorldRow, world_id) is None:
        return True
    return bearable(profile.biochemistry, await tolerated(session, world_id))


async def seed_world_life(session: AsyncSession) -> int:
    done = set(await session.scalars(select(AppliedFixupRow.key).where(AppliedFixupRow.key.like(f"{LIFE_FIXUP}.%"))))
    seeded = set(await session.scalars(select(WorldBiochemistryRow.world_id).distinct()))
    added = 0
    for world in list(await session.scalars(select(WorldRow).order_by(WorldRow.id))):
        key = f"{LIFE_FIXUP}.{world.id}"
        if key in done or held(world.id):
            continue
        kinds = () if world.id in seeded else world_life(world.world_type, world.atmosphere)
        for biochemistry in kinds:
            session.add(WorldBiochemistryRow(world_id=world.id, biochemistry=biochemistry))
        session.add(AppliedFixupRow(key=key, result={"biochemistries": len(kinds)}))
        added += len(kinds)
    await session.flush()
    return added
