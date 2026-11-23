from collections.abc import Callable, Mapping
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import partial
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import InheritanceCustom
from aerona.domain.enums.unions import PartnerScope, PluralSide, UnionForm
from aerona.engine.body.customs import people_of
from aerona.engine.customs.grades import too_young_to_wed
from aerona.engine.customs.rights import unwed_by_law
from aerona.engine.cycles.lineage import breeds_or_weds, descent_custom, kin_bars
from aerona.engine.cycles.sides import first_sex, second_sex, system_of_people
from aerona.engine.folkways.purity import caste_bars
from aerona.engine.kin.groups import kin_group_bars
from aerona.engine.polity.book import sex_of
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat
from aerona.engine.unions.axes import Spousing, spousing_of
from aerona.engine.unions.customs import partners_allowed
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class Terms:
    people_id: int | None
    spousing: Spousing
    first: str | None = None
    second: str | None = None

    @property
    def endogamous(self) -> bool:
        return self.spousing.endogamy is PartnerScope.PEOPLE


def spouse_limit(rules: Rules, terms: Terms, sex: str) -> int:
    table = rules.customs
    spousing = terms.spousing
    if spousing.form is UnionForm.GROUP:
        return table.group_spouses
    if spousing.form is not UnionForm.PLURAL:
        return 1
    if spousing.side is PluralSide.FIRST:
        return table.plural_first_side_spouses if sex == terms.first else 1
    if spousing.side is PluralSide.SECOND:
        return table.plural_second_side_spouses if sex == terms.second else 1
    return table.plural_first_side_spouses if sex == terms.first else table.plural_second_side_spouses


async def terms_of(session: AsyncSession, mortal: EntityRow) -> Terms:
    people = await people_of(session, mortal)
    people_id = people.id if people is not None else None
    custom = await session.get(UnionCustomRow, people_id) if people_id is not None else None
    if custom is None:
        return Terms(people_id, Spousing())
    system = await system_of_people(session, people_id)
    first, second = (first_sex(system), second_sex(system)) if system is not None else (None, None)
    return Terms(people_id, spousing_of(custom), first=first, second=second)


async def spouses_of(session: AsyncSession, mortal_id: int) -> int:
    bonds = [*await active_bonds(session, [BondKind.LOVES], sources=[mortal_id]), *await active_bonds(session, [BondKind.LOVES], targets=[mortal_id])]
    return len({bond.other_end(mortal_id) for bond in bonds})


def may_wed_terms(rules: Rules, first: tuple[Terms, str, int], second: tuple[Terms, str, int]) -> bool:
    for terms, sex, spouses in (first, second):
        if spouses >= spouse_limit(rules, terms, sex):
            return False
    mine, theirs = first[0], second[0]
    foreign = mine.people_id is not None and theirs.people_id is not None and mine.people_id != theirs.people_id
    return not (foreign and (mine.endogamous or theirs.endogamous))


async def may_wed(session: AsyncSession, rules: Rules, first: EntityRow, second: EntityRow) -> bool:
    one = (await terms_of(session, first), sex_of(first), await spouses_of(session, first.id))
    two = (await terms_of(session, second), sex_of(second), await spouses_of(session, second.id))
    if (
        not may_wed_terms(rules, one, two)
        or await kin_bars(session, first, second)
        or await kin_group_bars(session, rules, first, second)
        or await caste_bars(session, first, second)
        or await too_young_to_wed(session, first, second)
        or await unwed_by_law(session, first, second)
        or not await partners_allowed(session, first, second)
    ):
        return False
    return await breeds_or_weds(session, first, second)


async def has_room(session: AsyncSession, rules: Rules, mortal: EntityRow) -> bool:
    terms = await terms_of(session, mortal)
    return await spouses_of(session, mortal.id) < spouse_limit(rules, terms, sex_of(mortal))


def match_bonus(rules: Rules, mine: Terms, theirs: Terms) -> int:
    foreign = mine.people_id is not None and theirs.people_id is not None and mine.people_id != theirs.people_id
    return rules.customs.exogamy_match_bonus if foreign and not mine.endogamous else 0


def assimilation_factor(rules: Rules, custom: UnionCustomRow | None) -> float:
    if custom is None:
        return 1.0
    pct = rules.customs.endogamy_assimilation_pct if custom.endogamy is PartnerScope.PEOPLE else rules.customs.exogamy_assimilation_pct
    return pct / PERCENT


def merit(mortal: EntityRow) -> int:
    return (stat(mortal, "intellect") or 0) + (stat(mortal, "strength") or 0)


def charisma(mortal: EntityRow) -> int:
    return (stat(mortal, "charisma") or 0) + (mortal.importance or 0)


def eldest_of_second_line(by_age: list[EntityRow], second: str | None) -> EntityRow:
    return next((child for child in by_age if second is not None and sex_of(child) == second), by_age[0])


SOLE_HEIR: Mapping[InheritanceCustom, Callable[[list[EntityRow], str | None], EntityRow]] = partial(
    InheritanceCustom,
    {
        InheritanceCustom.PRIMOGENITURE: lambda by_age, _: by_age[0],
        InheritanceCustom.ULTIMOGENITURE: lambda by_age, _: by_age[-1],
        InheritanceCustom.THROUGH_SECOND_LINE: eldest_of_second_line,
        InheritanceCustom.BY_MERIT: lambda by_age, _: max(by_age, key=lambda child: (merit(child), -child.id)),
        InheritanceCustom.ELECTIVE: lambda by_age, _: max(by_age, key=lambda child: (charisma(child), -child.id)),
        InheritanceCustom.SENIORITY: lambda by_age, _: by_age[0],
        InheritanceCustom.DESIGNATED: lambda by_age, _: by_age[0],
    },
    without={InheritanceCustom.EQUAL_SHARES},
)


def heirs_by_custom(custom: InheritanceCustom, children: list[EntityRow], second: str | None = None) -> list[EntityRow]:
    if not children:
        return []
    by_age = sorted(children, key=lambda child: (-(stat(child, "age") or 0), child.id))
    if custom is InheritanceCustom.EQUAL_SHARES:
        return by_age
    return [SOLE_HEIR[custom](by_age, second)]


async def inheritance_of(session: AsyncSession, mortal: EntityRow) -> InheritanceCustom:
    people = await people_of(session, mortal)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    return await descent_custom(session, mortal, culture.inheritance if culture is not None else InheritanceCustom.PRIMOGENITURE)
