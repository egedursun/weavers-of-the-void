from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.unions import PartnerScope, UnionArrangement, UnionDescent, UnionDissolution, UnionExchange, UnionForm, UnionResidence
from aerona.engine.body.customs import people_of
from aerona.engine.cycles.lineage import caste_of, kinship_of, line_of, moiety, union_of
from aerona.engine.polity.laws import law_param

TERM_FORMS = frozenset({UnionForm.CONTRACT, UnionForm.SERIAL})
DIVORCE_RULE: Mapping[UnionDissolution, str] = total(
    UnionDissolution,
    {UnionDissolution.NONE: "forbidden", UnionDissolution.BY_EITHER: "free", UnionDissolution.BY_COURT: "for_cause", UnionDissolution.BY_CUSTOM: "for_cause"},
)
PAYS_FIRST: Mapping[UnionExchange, bool | None] = total(
    UnionExchange,
    {
        UnionExchange.TO_ONE_FAMILY: True,
        UnionExchange.FROM_ONE_FAMILY: False,
        UnionExchange.MUTUAL: None,
        UnionExchange.SERVICE: None,
        UnionExchange.NONE: None,
    },
)


async def house_id_of(session: AsyncSession, mortal_id: int) -> int | None:
    return await session.scalar(
        select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal_id, HouseMemberRow.by_marriage.is_(False)).limit(1)
    )


async def faith_of(session: AsyncSession, mortal_id: int) -> int | None:
    return await session.scalar(
        select(BondRow.target_node_id)
        .where(BondRow.source_node_id == mortal_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.id)
        .limit(1)
    )


async def people_key(session: AsyncSession, mortal: EntityRow) -> object:
    people = await people_of(session, mortal)
    return people.id if people is not None else None


async def class_key(session: AsyncSession, mortal: EntityRow) -> object:
    return mortal.social_class


async def caste_key(session: AsyncSession, mortal: EntityRow) -> object:
    return await caste_of(session, mortal.id)


async def faith_key(session: AsyncSession, mortal: EntityRow) -> object:
    return await faith_of(session, mortal.id)


async def house_key(session: AsyncSession, mortal: EntityRow) -> object:
    return await house_id_of(session, mortal.id)


async def line_key(session: AsyncSession, mortal: EntityRow) -> object:
    system = await kinship_of(session, mortal)
    return await line_of(session, mortal.id, system.descent_group) if system is not None else await line_of(session, mortal.id)


async def moiety_key(session: AsyncSession, mortal: EntityRow) -> object:
    line = await line_key(session, mortal)
    return moiety(line) if isinstance(line, int) else None


async def no_key(session: AsyncSession, mortal: EntityRow) -> object:
    return None


SCOPE_KEYS: Mapping[PartnerScope, Callable[[AsyncSession, EntityRow], Awaitable[object]]] = total(
    PartnerScope,
    {
        PartnerScope.NONE: no_key,
        PartnerScope.PEOPLE: people_key,
        PartnerScope.CLASS: class_key,
        PartnerScope.CASTE: caste_key,
        PartnerScope.FAITH: faith_key,
        PartnerScope.HOUSE: house_key,
        PartnerScope.LINE: line_key,
        PartnerScope.MOIETY: moiety_key,
    },
)


async def scope_key(session: AsyncSession, mortal: EntityRow, scope: PartnerScope) -> object:
    return await SCOPE_KEYS[scope](session, mortal)


async def partners_allowed(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    custom = await union_of(session, first)
    if custom is None:
        return True
    if custom.form is UnionForm.NONE:
        return False
    if custom.endogamy is not PartnerScope.NONE and await scope_key(session, first, custom.endogamy) != await scope_key(session, second, custom.endogamy):
        return False
    return custom.exogamy is PartnerScope.NONE or await scope_key(session, first, custom.exogamy) != await scope_key(session, second, custom.exogamy)


async def divorce_rule(session: AsyncSession, mortal: EntityRow) -> str:
    found = await law_param(session, mortal.location_id, LawKind.MARRIAGE_LAW, "divorce") if mortal.location_id is not None else None
    if found is not None:
        return str(found)
    custom = await union_of(session, mortal)
    return DIVORCE_RULE[custom.dissolution] if custom is not None else "for_cause"


STAYING_SIDE: Mapping[UnionResidence, int | None] = total(
    UnionResidence,
    {UnionResidence.WITH_FIRST_FAMILY: 0, UnionResidence.WITH_SECOND_FAMILY: 1, UnionResidence.NEW_HOUSEHOLD: None, UnionResidence.SEPARATE: None},
)
CONSENTS_NEEDED: Mapping[UnionArrangement, int] = total(
    UnionArrangement,
    {UnionArrangement.ARRANGED: 0, UnionArrangement.CHOSEN: 1, UnionArrangement.BOTH_CONSENT: 2},
)


def sides(custom: UnionCustomRow, first: EntityRow, second: EntityRow) -> tuple[EntityRow, EntityRow] | None:
    staying = STAYING_SIDE[custom.residence]
    if staying is None:
        return None
    return (second, first) if staying == 0 else (first, second)


def payer(custom: UnionCustomRow, first: EntityRow, second: EntityRow) -> tuple[EntityRow, EntityRow] | None:
    pays_first = PAYS_FIRST[custom.exchange]
    if pays_first is None:
        return None
    return (first, second) if pays_first else (second, first)


async def kept_past_death(session: AsyncSession, survivor_id: int) -> bool:
    custom = await union_of(session, await session.get(EntityRow, survivor_id))
    return custom is not None and custom.form is UnionForm.POSTHUMOUS


async def line_house(session: AsyncSession, marriage: MarriageRow, prestige: Mapping[int, int], seed: int) -> int | None:
    first, second = await house_id_of(session, marriage.first_id), await house_id_of(session, marriage.second_id)
    custom = await union_of(session, await session.get(EntityRow, marriage.first_id))
    if custom is None or first is None or second is None or first == second:
        return None
    rule = custom.descent
    if rule is UnionDescent.THROUGH_FIRST:
        return first
    if rule is UnionDescent.THROUGH_SECOND:
        return second
    if rule is UnionDescent.CHOSEN:
        return first if seed % 2 == 0 else second
    if rule is UnionDescent.BY_HOUSE_RULE:
        return first if prestige.get(first, 0) >= prestige.get(second, 0) else second
    return min(first, second)
