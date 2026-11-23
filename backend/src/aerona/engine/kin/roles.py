from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.total import total
from aerona.domain.enums.kin import KinRole
from aerona.engine.mortal.kin import children_of, fosterers_of, fosterlings_of, godparents_of, parents_of, siblings_of, spouses_of, sworn_kin_of

type Lookup = Callable[[AsyncSession, int], Awaitable[list[int]]]

FIRST = 0
SECOND = 1


async def of_each(session: AsyncSession, ids: list[int], lookup: Lookup) -> list[int]:
    found: set[int] = set()
    for node_id in ids:
        found.update(await lookup(session, node_id))
    return sorted(found)


async def line_parent(session: AsyncSession, mortal_id: int, line: int) -> list[int]:
    parents = sorted(await parents_of(session, mortal_id))
    return [parents[line]] if len(parents) > line else []


async def grandparents(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await parents_of(session, mortal_id), parents_of)


async def grandchildren(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await children_of(session, mortal_id), children_of)


async def first_line_kin(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await line_parent(session, mortal_id, FIRST), siblings_of)


async def second_line_kin(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await line_parent(session, mortal_id, SECOND), siblings_of)


async def sibling_children(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await siblings_of(session, mortal_id), children_of)


async def parallel_cousins(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await first_line_kin(session, mortal_id), children_of)


async def cross_cousins(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await second_line_kin(session, mortal_id), children_of)


async def parents_in_law(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await spouses_of(session, mortal_id), parents_of)


async def children_in_law(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await children_of(session, mortal_id), spouses_of)


async def siblings_in_law(session: AsyncSession, mortal_id: int) -> list[int]:
    by_spouse = await of_each(session, await spouses_of(session, mortal_id), siblings_of)
    by_sibling = await of_each(session, await siblings_of(session, mortal_id), spouses_of)
    return sorted(set(by_spouse) | set(by_sibling))


async def co_spouses(session: AsyncSession, mortal_id: int) -> list[int]:
    return await of_each(session, await spouses_of(session, mortal_id), spouses_of)


async def foster_kin(session: AsyncSession, mortal_id: int) -> list[int]:
    return sorted(set(await fosterers_of(session, mortal_id)) | set(await fosterlings_of(session, mortal_id)))


async def chosen_kin(session: AsyncSession, mortal_id: int) -> list[int]:
    return sorted(set(await foster_kin(session, mortal_id)) | set(await godparents_of(session, mortal_id)))


RESOLVERS: Mapping[KinRole, Lookup] = total(
    KinRole,
    {
        KinRole.PARENT: parents_of,
        KinRole.CHILD: children_of,
        KinRole.SIBLING: siblings_of,
        KinRole.GRANDPARENT: grandparents,
        KinRole.GRANDCHILD: grandchildren,
        KinRole.PARENT_SIBLING_FIRST_LINE: first_line_kin,
        KinRole.PARENT_SIBLING_SECOND_LINE: second_line_kin,
        KinRole.SIBLING_CHILD: sibling_children,
        KinRole.COUSIN_PARALLEL: parallel_cousins,
        KinRole.COUSIN_CROSS: cross_cousins,
        KinRole.PARENT_IN_LAW: parents_in_law,
        KinRole.CHILD_IN_LAW: children_in_law,
        KinRole.SIBLING_IN_LAW: siblings_in_law,
        KinRole.CO_SPOUSE: co_spouses,
        KinRole.CHOSEN_KIN: chosen_kin,
        KinRole.GODPARENT: godparents_of,
        KinRole.SWORN_KIN: sworn_kin_of,
        KinRole.FOSTER_KIN: foster_kin,
    },
)


async def kin_by_role(session: AsyncSession, mortal_id: int, role: KinRole) -> list[int]:
    return sorted(set(await RESOLVERS[role](session, mortal_id)) - {mortal_id})
