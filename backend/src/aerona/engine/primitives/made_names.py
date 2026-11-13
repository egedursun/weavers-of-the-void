from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.collective import DesignRow
from aerona.db.tables.cuisine import DishRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.equipment import EquipmentModelRow
from aerona.db.tables.military import UnitDesignRow
from aerona.db.tables.structures import StructureDesignRow
from aerona.engine.body.customs import people_of
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.language.generator import NameKind
from aerona.rules.registry import Rules

MADE_TABLES = (DesignRow, UnitDesignRow, EquipmentModelRow, DishRow, StructureDesignRow)
TRIES = 6


async def made_names_of(session: AsyncSession, world_id: int | None) -> set[str]:
    found: set[str] = set()
    for table in MADE_TABLES:
        found.update(await session.scalars(select(table.name).where(table.world_id == world_id)))
    return found


async def coin(session: AsyncSession, namer: Namer, origin: EntityRow, key: str) -> str | None:
    people = await people_of(session, origin)
    for speaker in dict.fromkeys(item for item in (origin.id, people.id if people is not None else None) if item is not None):
        coined = await namer.from_speaker(speaker, key, NameKind.GENERAL)
        if coined:
            return coined
    return await namer.person([origin], key, origin.world_id)


async def made_name(session: AsyncSession, rules: Rules, origin: EntityRow | None, label: str, *seed: object) -> str:
    if origin is None:
        return label
    namer = Namer(session, rules)
    taken = await made_names_of(session, origin.world_id)
    fallback = f"{origin.name} {label.lower()}"
    for attempt in range(TRIES):
        coined = await coin(session, namer, origin, seed_of("made", origin.id, label, attempt, *seed))
        name = f"{coined} {label.lower()}" if coined else fallback
        if name not in taken:
            return name
    return fallback if fallback not in taken else f"{fallback} {len(taken) + 1}"
