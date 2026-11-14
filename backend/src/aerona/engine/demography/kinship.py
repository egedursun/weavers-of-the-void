from collections.abc import Callable, Mapping
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import partial
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import InheritanceCustom, MarriageCustom
from aerona.domain.enums.polity import SuccessionRule
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.lineage import breeds_or_weds, descent_custom, kin_bars
from aerona.engine.folkways.purity import caste_bars
from aerona.engine.polity.book import sex_of
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

FEMALE = "female"
MALE = "male"
INHERITANCE_RULES: dict[InheritanceCustom, SuccessionRule] = {
    InheritanceCustom.PRIMOGENITURE: SuccessionRule.PRIMOGENITURE,
    InheritanceCustom.GAVELKIND: SuccessionRule.SENIORITY,
    InheritanceCustom.ELECTIVE: SuccessionRule.ELECTIVE,
    InheritanceCustom.BY_MERIT: SuccessionRule.TANISTRY,
    InheritanceCustom.ULTIMOGENITURE: SuccessionRule.ULTIMOGENITURE,
    InheritanceCustom.MATRILINEAL: SuccessionRule.MATRILINEAL,
}


@dataclass(frozen=True)
class Terms:
    people_id: int | None
    marriage: MarriageCustom
    endogamous: bool


def spouse_limit(rules: Rules, custom: MarriageCustom, sex: str) -> int:
    table = rules.customs
    if custom is MarriageCustom.POLYGYNY:
        return table.polygyny_spouses if sex == MALE else 1
    if custom is MarriageCustom.POLYANDRY:
        return table.polyandry_spouses if sex == FEMALE else 1
    if custom is MarriageCustom.GROUP:
        return table.group_spouses
    return 1


async def terms_of(session: AsyncSession, mortal: EntityRow) -> Terms:
    people = await people_of(session, mortal)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    if culture is None:
        return Terms(people.id if people is not None else None, MarriageCustom.MONOGAMY, endogamous=False)
    return Terms(people.id if people is not None else None, culture.marriage, endogamous=culture.endogamous)


async def spouses_of(session: AsyncSession, mortal_id: int) -> int:
    bonds = [*await active_bonds(session, [BondKind.LOVES], sources=[mortal_id]), *await active_bonds(session, [BondKind.LOVES], targets=[mortal_id])]
    return len({bond.other_end(mortal_id) for bond in bonds})


def may_wed_terms(rules: Rules, first: tuple[Terms, str, int], second: tuple[Terms, str, int]) -> bool:
    for terms, sex, spouses in (first, second):
        if spouses >= spouse_limit(rules, terms.marriage, sex):
            return False
    mine, theirs = first[0], second[0]
    foreign = mine.people_id is not None and theirs.people_id is not None and mine.people_id != theirs.people_id
    return not (foreign and (mine.endogamous or theirs.endogamous))


async def may_wed(session: AsyncSession, rules: Rules, first: EntityRow, second: EntityRow) -> bool:
    one = (await terms_of(session, first), sex_of(first), await spouses_of(session, first.id))
    two = (await terms_of(session, second), sex_of(second), await spouses_of(session, second.id))
    if not may_wed_terms(rules, one, two) or await kin_bars(session, first, second) or await caste_bars(session, first, second):
        return False
    return await breeds_or_weds(session, first, second)


async def has_room(session: AsyncSession, rules: Rules, mortal: EntityRow) -> bool:
    terms = await terms_of(session, mortal)
    return await spouses_of(session, mortal.id) < spouse_limit(rules, terms.marriage, sex_of(mortal))


def match_bonus(rules: Rules, mine: Terms, theirs: Terms) -> int:
    foreign = mine.people_id is not None and theirs.people_id is not None and mine.people_id != theirs.people_id
    return rules.customs.exogamy_match_bonus if foreign and not mine.endogamous else 0


def assimilation_factor(rules: Rules, culture: PeopleCultureRow | None) -> float:
    if culture is None:
        return 1.0
    pct = rules.customs.endogamy_assimilation_pct if culture.endogamous else rules.customs.exogamy_assimilation_pct
    return pct / PERCENT


def merit(mortal: EntityRow) -> int:
    return (stat(mortal, "intellect") or 0) + (stat(mortal, "strength") or 0)


def charisma(mortal: EntityRow) -> int:
    return (stat(mortal, "charisma") or 0) + (mortal.importance or 0)


def eldest_daughter(by_age: list[EntityRow]) -> EntityRow:
    return next((child for child in by_age if sex_of(child) == FEMALE), by_age[0])


SOLE_HEIR: Mapping[InheritanceCustom, Callable[[list[EntityRow]], EntityRow]] = partial(
    InheritanceCustom,
    {
        InheritanceCustom.PRIMOGENITURE: lambda by_age: by_age[0],
        InheritanceCustom.ULTIMOGENITURE: lambda by_age: by_age[-1],
        InheritanceCustom.MATRILINEAL: eldest_daughter,
        InheritanceCustom.BY_MERIT: lambda by_age: max(by_age, key=lambda child: (merit(child), -child.id)),
        InheritanceCustom.ELECTIVE: lambda by_age: max(by_age, key=lambda child: (charisma(child), -child.id)),
    },
    without={InheritanceCustom.GAVELKIND},
)


def heirs_by_custom(custom: InheritanceCustom, children: list[EntityRow]) -> list[EntityRow]:
    if not children:
        return []
    by_age = sorted(children, key=lambda child: (-(stat(child, "age") or 0), child.id))
    if custom is InheritanceCustom.GAVELKIND:
        return by_age
    return [SOLE_HEIR[custom](by_age)]


async def inheritance_of(session: AsyncSession, mortal: EntityRow) -> InheritanceCustom:
    people = await people_of(session, mortal)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    return await descent_custom(session, mortal, culture.inheritance if culture is not None else InheritanceCustom.PRIMOGENITURE)
