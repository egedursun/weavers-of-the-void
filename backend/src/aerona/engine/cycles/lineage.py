from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cycles import KinshipSystemRow, MortalCasteRow, PeopleReproductionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.domain.enums.cycles import CousinTerms, DescentGroup, KinshipDescent, MarriagePreference, ReproductiveCaste, ReproductiveSystem
from aerona.domain.enums.demography import InheritanceCustom
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mortal import MortalSex
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.body.customs import people_of
from aerona.engine.mortal.kin import children_of, parents_of
from aerona.rules.registry import Rules

FIXED_SEXES = frozenset({ReproductiveSystem.TWO_SEX, ReproductiveSystem.SEQUENTIAL})
PARALLEL = "parallel"
CROSS = "cross"
MOIETIES = 2


async def kinship_of(session: AsyncSession, mortal: EntityRow) -> KinshipSystemRow | None:
    people = mortal if mortal.entity_type is EntityType.PEOPLE else await people_of(session, mortal)
    return await session.get(KinshipSystemRow, people.id) if people is not None else None


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
    if system.cousin_terms is CousinTerms.ALL_AS_SIBLINGS and cousins is not None:
        return True
    if system.cousin_terms is CousinTerms.PARALLEL_AS_SIBLINGS and cousins == PARALLEL:
        return True
    lines = (await line_of(session, first.id, system.descent_group), await line_of(session, second.id, system.descent_group))
    if system.preference is MarriagePreference.CLAN_EXOGAMY and lines[0] is not None and lines[0] == lines[1]:
        return True
    if system.preference is MarriagePreference.MOIETY_EXOGAMY or system.descent_group is DescentGroup.MOIETY:
        return None not in lines and moiety(lines[0]) == moiety(lines[1])
    return False


def moiety(line_id: int | None) -> int:
    return (line_id or 0) % MOIETIES


async def preference_bonus(session: AsyncSession, rules: Rules, first: EntityRow, second: EntityRow) -> int:
    system = await kinship_of(session, first)
    if system is None or system.preference is MarriagePreference.NONE:
        return 0
    table = rules.marriage_alliance
    if system.preference is MarriagePreference.CROSS_COUSIN:
        return table.cross_cousin_bonus if await cousin_kind(session, first.id, second.id) == CROSS else 0
    return table.exogamy_bonus


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
    if system.descent is KinshipDescent.MATRILINEAL:
        return InheritanceCustom.MATRILINEAL
    if system.descent is KinshipDescent.PATRILINEAL and custom is InheritanceCustom.MATRILINEAL:
        return InheritanceCustom.PRIMOGENITURE
    return custom


async def sisters_children(session: AsyncSession, mortal: EntityRow) -> list[int]:
    found: list[int] = []
    for parent in await parents_of(session, mortal.id):
        for sibling_id in await children_of(session, parent):
            if sibling_id == mortal.id:
                continue
            sibling = await session.get(EntityRow, sibling_id)
            if sex_value(sibling) == MortalSex.FEMALE.value:
                found.extend(await children_of(session, sibling_id))
    return list(dict.fromkeys(found))


async def descent_heirs(session: AsyncSession, mortal: EntityRow, heirs: list[EntityRow]) -> list[EntityRow]:
    system = await kinship_of(session, mortal)
    if system is None or system.descent is not KinshipDescent.MATRILINEAL or sex_value(mortal) == MortalSex.FEMALE.value:
        return heirs
    found: list[EntityRow] = []
    for child_id in await sisters_children(session, mortal):
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
