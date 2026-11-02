from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import FolkBeliefRow
from aerona.db.tables.sons import SonRow
from aerona.engine.primitives.folk_names import clashes, folk_god_name, guarded_names
from aerona.engine.primitives.naming import Namer
from aerona.engine.primitives.renames import name_in_text
from aerona.rules.registry import Rules


async def god_guard(session: AsyncSession, god_id: int) -> list[str] | None:
    son = await session.get(SonRow, god_id)
    if son is not None:
        return guarded_names(son.name, son.title)
    creator = await session.get(CreatorRow, god_id)
    return guarded_names(creator.name, creator.title) if creator is not None else None


async def rename_belief(session: AsyncSession, rules: Rules, belief: FolkBeliefRow, namer: Namer, *, fresh: bool) -> str | None:
    people = await session.get(EntityRow, belief.people_entity_id)
    guarded = await god_guard(session, belief.god_node_id)
    if people is None or guarded is None:
        return None
    current = belief.local_name or ""
    avoided = [*guarded, current] if fresh and current else guarded
    name = await folk_god_name(namer, rules, people, belief.god_node_id, avoided, salt=current if fresh else "")
    if name is None or name == current:
        return None
    if current:
        belief.account = name_in_text(belief.account, current, name)
        belief.misconception = name_in_text(belief.misconception, current, name) if belief.misconception else belief.misconception
    belief.local_name = name
    return name


async def repair_belief_names(session: AsyncSession, rules: Rules) -> int:
    namer = Namer(session, rules)
    repaired = 0
    for belief in list(await session.scalars(select(FolkBeliefRow).where(FolkBeliefRow.local_name.is_not(None)))):
        guarded = await god_guard(session, belief.god_node_id)
        if guarded is None or not clashes(belief.local_name or "", guarded):
            continue
        if await rename_belief(session, rules, belief, namer, fresh=False) is not None:
            repaired += 1
    await session.flush()
    return repaired
