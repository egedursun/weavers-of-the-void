from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cycles import KinshipSystemRow, MortalCasteRow, PeopleReproductionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.domain.enums.cycles import DescentGroup, KinshipDescent, KinTermSystem, ReproductiveCaste, ReproductiveSystem
from aerona.domain.enums.demography import InheritanceCustom
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.unions import KinMatch, PartnerScope
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.sides import second_sex
from aerona.engine.death_work.handling import death_match
from aerona.engine.mortal.kin import children_of, parents_of
from aerona.rules.registry import Rules

FIXED_SEXES = frozenset({ReproductiveSystem.TWO_SEX, ReproductiveSystem.SEQUENTIAL})
PARALLEL = "parallel"
CROSS = "cross"
MOIETIES = 2

PARALLEL_AS_SIBLINGS = frozenset({KinTermSystem.BIFURCATE_MERGING, KinTermSystem.CROSS_PARALLEL})


async def kinship_of(session: AsyncSession, mortal: EntityRow) -> KinshipSystemRow | None:
    people = mortal if mortal.entity_type is EntityType.PEOPLE else await people_of(session, mortal)
    return await session.get(KinshipSystemRow, people.id) if people is not None else None


async def union_of(session: AsyncSession, mortal: EntityRow | None) -> UnionCustomRow | None:
    if mortal is None:
        return None
    people = mortal if mortal.entity_type is EntityType.PEOPLE else await people_of(session, mortal)
    return await session.get(UnionCustomRow, people.id) if people is not None else None


async def reproduction_of(session: AsyncSession, mortal: EntityRow) -> PeopleReproductionRow | None:
    people = mortal if mortal.entity_type is EntityType.PEOPLE else await people_of(session, mortal)
    return await session.get(PeopleReproductionRow, people.id) if people is not None else None


async def system_of(session: AsyncSession, mortal: EntityRow) -> ReproductiveSystem:
    row = await reproduction_of(session, mortal)
    return row.system if row is not None else ReproductiveSystem.TWO_SEX


async def caste_of(session: AsyncSession, mortal_id: int) -> ReproductiveCaste | None:
    row = await session.get(MortalCasteRow, mortal_id)
    return row.caste if row is not None else None


def sex_value(mortal: EntityRow | None) -> str | None:
    if mortal is None or not isinstance(mortal.stats, MortalStats):
        return None
    return mortal.stats.sex


async def root_house(session: AsyncSession, house_id: int) -> int:
    seen = {house_id}
    current = house_id
    while (profile := await session.get(HouseProfileRow, current)) is not None and profile.parent_house_id is not None:
        if profile.parent_house_id in seen:
            break
        seen.add(profile.parent_house_id)
        current = profile.parent_house_id
    return current


async def line_of(session: AsyncSession, mortal_id: int, group: DescentGroup = DescentGroup.HOUSE) -> int | None:
    house: int | None = await session.scalar(
        select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal_id).order_by(HouseMemberRow.house_entity_id).limit(1)
    )
    if house is None or group in {DescentGroup.HOUSE, DescentGroup.LINEAGE}:
        return house
    return await root_house(session, house)


async def cousin_kind(session: AsyncSession, first_id: int, second_id: int) -> str | None:
    mine = set(await parents_of(session, first_id))
    theirs = set(await parents_of(session, second_id))
    if mine & theirs:
        return None
    for parent_id in sorted(mine):
        grand = set(await parents_of(session, parent_id))
        if not grand:
            continue
        for other_id in sorted(theirs):
            if not grand & set(await parents_of(session, other_id)):
                continue
            parent = await session.get(EntityRow, parent_id)
            other = await session.get(EntityRow, other_id)
            return PARALLEL if sex_value(parent) == sex_value(other) else CROSS
    return None


async def kin_bars(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    system = await kinship_of(session, first)
    if system is None:
        return False
    cousins = await cousin_kind(session, first.id, second.id)
    if system.kin_terms is KinTermSystem.GENERATIONAL and cousins is not None:
        return True
    if system.kin_terms in PARALLEL_AS_SIBLINGS and cousins == PARALLEL:
        return True
    lines = (await line_of(session, first.id, system.descent_group), await line_of(session, second.id, system.descent_group))
    union = await union_of(session, first)
    exogamy = union.exogamy if union is not None else PartnerScope.NONE
    if exogamy is PartnerScope.LINE and lines[0] is not None and lines[0] == lines[1]:
        return True
    if exogamy is PartnerScope.MOIETY or system.descent_group is DescentGroup.MOIETY:
        return None not in lines and moiety(lines[0]) == moiety(lines[1])
    return False


def moiety(line_id: int | None) -> int:
    return (line_id or 0) % MOIETIES


COUSIN_SOUGHT = {KinMatch.CROSS_COUSIN: CROSS, KinMatch.PARALLEL_COUSIN: PARALLEL}
SOUGHT_OUTSIDE = frozenset({PartnerScope.LINE, PartnerScope.MOIETY})


async def preference_bonus(session: AsyncSession, rules: Rules, first: EntityRow, second: EntityRow) -> int:
    return await custom_bonus(session, rules, first, second) + await death_match(session, rules, second)


async def custom_bonus(session: AsyncSession, rules: Rules, first: EntityRow, second: EntityRow) -> int:
    union = await union_of(session, first)
    if union is None:
        return 0
    table = rules.marriage_alliance
    sought = COUSIN_SOUGHT.get(union.kin_match)
    if sought is not None:
        return table.cross_cousin_bonus if await cousin_kind(session, first.id, second.id) == sought else 0
    return table.exogamy_bonus if union.exogamy in SOUGHT_OUTSIDE else 0


async def breeds(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    system = await system_of(session, first)
    if system is ReproductiveSystem.ASEXUAL:
        return False
    if system is ReproductiveSystem.CASTE:
        return ReproductiveCaste.BREEDER in {await caste_of(session, first.id), await caste_of(session, second.id)}
    return True


async def descent_custom(session: AsyncSession, mortal: EntityRow, custom: InheritanceCustom) -> InheritanceCustom:
    system = await kinship_of(session, mortal)
    if system is None:
        return custom
    if system.descent is KinshipDescent.THROUGH_SECOND_LINE:
        return InheritanceCustom.THROUGH_SECOND_LINE
    if system.descent is KinshipDescent.THROUGH_FIRST_LINE and custom is InheritanceCustom.THROUGH_SECOND_LINE:
        return InheritanceCustom.PRIMOGENITURE
    return custom


async def second_side_siblings_children(session: AsyncSession, mortal: EntityRow, second: str) -> list[int]:
    found: list[int] = []
    for parent in await parents_of(session, mortal.id):
        for sibling_id in await children_of(session, parent):
            if sibling_id == mortal.id:
                continue
            sibling = await session.get(EntityRow, sibling_id)
            if sex_value(sibling) == second:
                found.extend(await children_of(session, sibling_id))
    return list(dict.fromkeys(found))


async def descent_heirs(session: AsyncSession, mortal: EntityRow, heirs: list[EntityRow]) -> list[EntityRow]:
    system = await kinship_of(session, mortal)
    if system is None or system.descent is not KinshipDescent.THROUGH_SECOND_LINE or sex_value(mortal) == second_sex(system):
        return heirs
    found: list[EntityRow] = []
    for child_id in await second_side_siblings_children(session, mortal, second_sex(system)):
        child = await session.get(EntityRow, child_id)
        if child is not None and child.status is EntityStatus.CANON:
            found.append(child)
    return found or heirs


async def breeds_or_weds(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    if await system_of(session, first) is not ReproductiveSystem.CASTE:
        return True
    castes = {await caste_of(session, first.id), await caste_of(session, second.id)}
    return castes <= {ReproductiveCaste.BREEDER, None}


def sexes_fixed(system: ReproductiveSystem) -> bool:
    return system in FIXED_SEXES
