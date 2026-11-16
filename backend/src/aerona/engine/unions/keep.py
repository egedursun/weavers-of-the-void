from collections.abc import Mapping

from sqlalchemy import select

from aerona.core.total import total
from aerona.db.tables.cycles import KinshipSystemRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import KinshipDescent, MarriagePayment, ResidenceRule
from aerona.domain.enums.demography import MarriageCustom
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mortal import MarriageEnd, MarriageKind
from aerona.domain.enums.unions import PartnerScope, UnionDescent, UnionExchange, UnionForm, UnionPurpose, UnionResidence
from aerona.engine.context import TickContext
from aerona.engine.mortal.kinship import end_marriage
from aerona.engine.notes import note
from aerona.engine.unions.customs import TERM_FORMS, union_of

FORM_OF: Mapping[MarriageCustom, UnionForm] = total(
    MarriageCustom,
    {
        MarriageCustom.MONOGAMY: UnionForm.PAIR,
        MarriageCustom.POLYGYNY: UnionForm.PLURAL,
        MarriageCustom.POLYANDRY: UnionForm.PLURAL,
        MarriageCustom.GROUP: UnionForm.GROUP,
    },
)
RESIDENCE_OF: Mapping[ResidenceRule, UnionResidence] = total(
    ResidenceRule,
    {
        ResidenceRule.PATRILOCAL: UnionResidence.WITH_FIRST_FAMILY,
        ResidenceRule.MATRILOCAL: UnionResidence.WITH_SECOND_FAMILY,
        ResidenceRule.NEOLOCAL: UnionResidence.NEW_HOUSEHOLD,
        ResidenceRule.AVUNCULOCAL: UnionResidence.WITH_SECOND_FAMILY,
    },
)
DESCENT_OF: Mapping[KinshipDescent, UnionDescent] = total(
    KinshipDescent,
    {
        KinshipDescent.PATRILINEAL: UnionDescent.THROUGH_FIRST,
        KinshipDescent.MATRILINEAL: UnionDescent.THROUGH_SECOND,
        KinshipDescent.BILATERAL: UnionDescent.THROUGH_BOTH,
        KinshipDescent.DOUBLE: UnionDescent.THROUGH_BOTH,
        KinshipDescent.AMBILINEAL: UnionDescent.CHOSEN,
    },
)
EXCHANGE_OF: Mapping[MarriagePayment, UnionExchange] = total(
    MarriagePayment,
    {
        MarriagePayment.NONE: UnionExchange.NONE,
        MarriagePayment.BRIDE_PRICE: UnionExchange.TO_ONE_FAMILY,
        MarriagePayment.DOWRY: UnionExchange.FROM_ONE_FAMILY,
        MarriagePayment.BRIDE_SERVICE: UnionExchange.TO_ONE_FAMILY,
    },
)
PURPOSE_OF: Mapping[MarriageKind, UnionPurpose] = total(
    MarriageKind,
    {MarriageKind.MONOGAMOUS: UnionPurpose.KINSHIP, MarriageKind.PLURAL: UnionPurpose.KINSHIP, MarriageKind.POLITICAL: UnionPurpose.ALLIANCE},
)


def legacy_custom(people_id: int, culture: PeopleCultureRow | None, kinship: KinshipSystemRow | None, political: bool) -> UnionCustomRow:
    return UnionCustomRow(
        people_entity_id=people_id,
        form=FORM_OF[culture.marriage] if culture is not None else UnionForm.PAIR,
        purpose=PURPOSE_OF[MarriageKind.POLITICAL if political else MarriageKind.MONOGAMOUS],
        residence=RESIDENCE_OF[kinship.residence] if kinship is not None else UnionResidence.NEW_HOUSEHOLD,
        descent=DESCENT_OF[kinship.descent] if kinship is not None else UnionDescent.THROUGH_BOTH,
        exchange=EXCHANGE_OF[kinship.payment] if kinship is not None else UnionExchange.NONE,
        endogamy=PartnerScope.PEOPLE if culture is not None and culture.endogamous else PartnerScope.NONE,
        exogamy=PartnerScope.HOUSE if kinship is not None and kinship.preference.value.endswith("exogamy") else PartnerScope.NONE,
        locked=[],
    )


async def seed_unions(ctx: TickContext) -> int:
    peoples = list(
        await ctx.session.scalars(
            select(EntityRow.id).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    seeded = 0
    for people in peoples:
        if held(people) or await ctx.session.get(UnionCustomRow, people) is not None:
            continue
        culture = await ctx.session.get(PeopleCultureRow, people)
        kinship = await ctx.session.get(KinshipSystemRow, people)
        ctx.session.add(legacy_custom(people, culture, kinship, political=False))
        seeded += 1
    return seeded


async def end_terms(ctx: TickContext) -> int:
    ended = 0
    for marriage in list(await ctx.session.scalars(select(MarriageRow).where(MarriageRow.end_epoch.is_(None)).order_by(MarriageRow.id))):
        if held(marriage.first_id, marriage.second_id):
            continue
        first = await ctx.session.get(EntityRow, marriage.first_id)
        custom = await union_of(ctx.session, first)
        if custom is None or custom.form not in TERM_FORMS or ctx.epoch - marriage.start_epoch < custom.term_epochs:
            continue
        await end_marriage(ctx.session, marriage, ctx.epoch, MarriageEnd.TERM)
        second = await ctx.session.get(EntityRow, marriage.second_id)
        names = " and ".join(row.name for row in (first, second) if row is not None)
        await note(ctx, f"The term of the union of {names} came to its end by custom.", key="union.term", ids=[marriage.first_id, marriage.second_id])
        ended += 1
    return ended


async def keep_unions(ctx: TickContext) -> None:
    ctx.count("union_customs_seeded", await seed_unions(ctx))
    ctx.count("unions_ended_by_term", await end_terms(ctx))
