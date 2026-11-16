from collections.abc import Callable, Mapping

from aerona.catalog.crimes import CRIMES
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import LawArea, LawKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.naming import seed_of

Offender = Callable[[EntityRow], bool]
K = CrimeKind
OWN_DETECTION = frozenset(
    {
        K.THEFT,
        K.MURDER,
        K.TREASON,
        K.BLASPHEMY,
        K.DESERTION,
        K.WITCHCRAFT,
        K.MIND_THEFT,
        K.UNLICENSED_COPYING,
        K.FORCED_EDIT,
        K.ERASURE,
        K.MACHINE_SEIZURE,
        K.IMPERSONATION,
        K.MIND_COMPULSION,
    }
)
NAMED_BY_LAW = frozenset(
    {
        K.DUELLING,
        K.VAGRANCY,
        K.UNLAWFUL_ASSEMBLY,
        K.UNION_OFFENCE,
        K.SUMPTUARY_BREACH,
        K.FORBIDDEN_FOOD,
        K.INTOXICATION,
        K.TABOO_BREACH,
        K.PURITY_BREACH,
        K.UNLICENSED_TRADE,
        K.UNLICENSED_POWER,
        K.UNLAWFUL_POLLUTION,
    }
)
WIDE_OFFENCES = tuple(crime for crime in CrimeKind if crime not in OWN_DETECTION)
CLASSES: Mapping[LawArea, frozenset[SocialClass] | None] = total(
    LawArea,
    {
        LawArea.SUCCESSION: frozenset({SocialClass.NOBLE}),
        LawArea.PROPERTY: None,
        LawArea.FISCAL: frozenset({SocialClass.MERCHANT, SocialClass.ARTISAN, SocialClass.PROFESSIONAL, SocialClass.NOBLE}),
        LawArea.PENAL: None,
        LawArea.MILITARY: frozenset({SocialClass.WARRIOR}),
        LawArea.SOCIAL: None,
        LawArea.PUBLIC_HEALTH: frozenset({SocialClass.MERCHANT, SocialClass.ARTISAN, SocialClass.FARMER, SocialClass.WORKER}),
        LawArea.MAGIC: frozenset({SocialClass.PRIEST, SocialClass.MONASTIC, SocialClass.SCRIBE, SocialClass.OUTCAST}),
        LawArea.CONSTITUTIONAL: frozenset({SocialClass.OFFICIAL, SocialClass.NOBLE, SocialClass.SCRIBE, SocialClass.PROFESSIONAL}),
    },
)


def open_to(mortal: EntityRow, crime: CrimeKind) -> bool:
    allowed = CLASSES[CRIMES[crime].area]
    return allowed is None or mortal.social_class in allowed


def chargeable(laws: LawBook, town_id: int, crime: CrimeKind) -> bool:
    if crime not in NAMED_BY_LAW:
        return True
    code = laws.in_force(town_id, LawKind.PENAL_CODE)
    return code is not None and crime.value in code.params


async def wide_offences(ctx: TickContext, town_id: int, laws: LawBook, mortals: list[EntityRow], found: dict[CrimeKind, list[EntityRow]]) -> None:
    town = await ctx.session.get(SettlementProfileRow, town_id)
    if town is None:
        return
    table = ctx.rules.crime
    taken = {row.id for rows in found.values() for row in rows}
    kinds = [crime for crime in WIDE_OFFENCES if chargeable(laws, town_id, crime)]
    for mortal in mortals:
        rng = ctx.rng(seed_of("offence", mortal.id, ctx.epoch))
        if mortal.id in taken or not rng.chance(town.crime * table.offence_pct // PERCENT):
            continue
        open_kinds = [crime for crime in kinds if open_to(mortal, crime)]
        if not open_kinds:
            continue
        crime = rng.weighted(open_kinds, [PERCENT + 1 - CRIMES[crime].severity for crime in open_kinds])
        if rng.chance(CRIMES[crime].detection * (PERCENT + town.public_order) // (2 * PERCENT)):
            found[crime].append(mortal)
