from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from aerona.db.repositories.cosmos import CosmosRepository

RETUNED: Mapping[tuple[str, str], tuple[float, float]] = {
    ("demography", "endemic_baseline"): (45.0, 30.0),
    ("apocalypse", "restless_cap"): (6.0, 5.0),
    ("survey", "colony_level"): (3.0, 4.0),
    ("survey", "conquest_level"): (4.0, 5.0),
}


async def move_retuned_rules(session: AsyncSession) -> int:
    cosmos = await CosmosRepository(session).get()
    if cosmos is None or not cosmos.rules_snapshot:
        return 0
    moved = 0
    for (namespace, name), (before, after) in RETUNED.items():
        values = cosmos.rules_snapshot.get(namespace)
        if values is not None and name in values and float(values[name]) == before:
            values[name] = after
            moved += 1
    if moved:
        flag_modified(cosmos, "rules_snapshot")
        await session.flush()
    return moved
