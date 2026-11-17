from sqlalchemy import select

from aerona.db.tables.cycles import KinshipSystemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mortal import MarriageEnd
from aerona.engine.context import TickContext
from aerona.engine.cycles.lineage import union_of
from aerona.engine.mortal.kinship import end_marriage
from aerona.engine.notes import note
from aerona.engine.unions.axes import Spousing, fresh_custom
from aerona.engine.unions.customs import TERM_FORMS


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
        kinship = await ctx.session.get(KinshipSystemRow, people)
        ctx.session.add(fresh_custom(people, Spousing(), kinship, ctx.rules.kinship.union_payment))
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
