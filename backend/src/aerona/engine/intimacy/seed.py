from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.intimacy import ACT_CONTEXTS
from aerona.db.tables.cycles import PeopleReproductionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intimacy import IntimacyNormRow, LegitimacyRuleRow, ReproductiveCourseRow
from aerona.db.write_guard import held
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intimacy import (
    BirthAttendant,
    ChildLegitimacy,
    KinScope,
    LegitimacyPath,
    NormEnforcer,
    NormSanction,
    NormStance,
    ParentUnion,
    PostnatalCustom,
    RelationContext,
)
from aerona.domain.enums.mind import EthicalStance, ValueAxis, ValueHolder
from aerona.engine.context import TickContext
from aerona.engine.cycles.lineage import sexes_fixed
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.ethics import ethics_of

LEANING = 60
RECOGNITION_COST = 10
ETHIC_STANCES = {EthicalStance.UNTHINKABLE: (NormStance.FORBIDDEN, NormEnforcer.LAW), EthicalStance.SHAMEFUL: (NormStance.DISCOURAGED, NormEnforcer.KIN)}


@dataclass
class IntimacySeedTally:
    norms: int = 0
    courses: int = 0
    legitimacy: int = 0


async def peoples(ctx: TickContext) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return [row for row in rows if not held(row.id)]


async def seed_norms(ctx: TickContext, folk: EntityRow, tally: IntimacySeedTally) -> None:
    if await ctx.session.scalar(select(IntimacyNormRow.context).where(IntimacyNormRow.people_entity_id == folk.id).limit(1)) is not None:
        return
    reproduction = await ctx.session.get(PeopleReproductionRow, folk.id)
    sexed = sexes_fixed(reproduction.system if reproduction is not None else ReproductiveSystem.TWO_SEX)
    ethics = await ethics_of(ctx.session, folk.id)
    banned = {context: ETHIC_STANCES[ethics[act].stance] for act, context in ACT_CONTEXTS.items() if act in ethics and ethics[act].stance in ETHIC_STANCES}
    for context in RelationContext:
        if context is RelationContext.BETWEEN_ANY_SEXES and not sexed:
            continue
        stance, enforcer = banned.get(context, (NormStance.TOLERATED, NormEnforcer.NONE))
        ctx.session.add(
            IntimacyNormRow(
                people_entity_id=folk.id,
                context=context,
                stance=stance,
                enforcer=enforcer,
                sanction=NormSanction.SHAMING if context in banned else NormSanction.NONE,
                kin_scope=KinScope.CLOSE if context is RelationContext.WITH_KIN else None,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.norms += 1


async def seed_course(ctx: TickContext, folk: EntityRow, values: dict[ValueAxis, int], tally: IntimacySeedTally) -> None:
    if await ctx.session.get(ReproductiveCourseRow, folk.id) is not None:
        return
    ctx.session.add(
        ReproductiveCourseRow(
            people_entity_id=folk.id,
            attendant=BirthAttendant.SPECIALIST if values.get(ValueAxis.KNOWLEDGE, 0) >= LEANING else BirthAttendant.KIN,
            postnatal=PostnatalCustom.KIN_CARE if values.get(ValueAxis.FAMILY, 0) >= LEANING else PostnatalCustom.NONE,
            locked=[],
        )
    )
    tally.courses += 1


async def seed_legitimacy(ctx: TickContext, folk: EntityRow, values: dict[ValueAxis, int], tally: IntimacySeedTally) -> None:
    if await ctx.session.scalar(select(LegitimacyRuleRow.parent_union).where(LegitimacyRuleRow.people_entity_id == folk.id).limit(1)) is not None:
        return
    strict = values.get(ValueAxis.TRADITION, 0) >= LEANING
    for union in ParentUnion:
        partial = strict and union in {ParentUnion.OUTSIDE_UNION, ParentUnion.UNKNOWN}
        ctx.session.add(
            LegitimacyRuleRow(
                people_entity_id=folk.id,
                parent_union=union,
                standing=ChildLegitimacy.PARTIAL if partial else ChildLegitimacy.FULL,
                path=(LegitimacyPath.RECOGNITION if union is ParentUnion.OUTSIDE_UNION else LegitimacyPath.ADOPTION) if partial else LegitimacyPath.NONE,
                cost=RECOGNITION_COST if partial else 0,
                locked=[],
            )
        )
        tally.legitimacy += 1


async def seed_intimacy(ctx: TickContext) -> IntimacySeedTally:
    tally = IntimacySeedTally()
    for folk in await peoples(ctx):
        values = dict(await stored_values(ctx.session, ValueHolder.CULTURE, folk.id))
        await seed_norms(ctx, folk, tally)
        await seed_course(ctx, folk, values, tally)
        await seed_legitimacy(ctx, folk, values, tally)
    await ctx.session.flush()
    return tally
