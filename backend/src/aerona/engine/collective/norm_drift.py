from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import EthicalStance, ValueAxis, ValueHolder
from aerona.engine.collective.norms import STRICT, NormTally, norms_of, stance_in, step_toward, write_norm
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values

STEADFAST_AT = 50


async def contact_drift(ctx: TickContext, tally: NormTally) -> None:
    pairs = await ctx.session.execute(select(CommunityRelationRow.entity_a_id, CommunityRelationRow.entity_b_id).where(CommunityRelationRow.value > 0))
    for first, second in list(pairs):
        for holder, other in ((first, second), (second, first)):
            people = await ctx.session.get(EntityRow, holder)
            if people is None or people.entity_type is not EntityType.PEOPLE or held(holder):
                continue
            if not ctx.rng(f"norm_contact.{holder}.{other}.{ctx.epoch}").chance(ctx.rules.norm_depth.contact_drift):
                continue
            own, theirs = await norms_of(ctx.session, holder), await norms_of(ctx.session, other)
            differing = sorted(key for key, stance in theirs.items() if stance_in(own, *key) is not stance)
            if differing:
                key = differing[0]
                if await write_norm(ctx, holder, *key, step_toward(stance_in(own, *key), theirs[key]), cause="contact") is not None:
                    tally.drifted += 1


async def generation_drift(ctx: TickContext, tally: NormTally) -> None:
    peoples = await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE).order_by(EntityRow.id))
    for people in list(peoples):
        if held(people.id) or not ctx.rng(f"norm_generation.{people.id}.{ctx.epoch}").chance(ctx.rules.norm_depth.generation_drift):
            continue
        if (await stored_values(ctx.session, ValueHolder.CULTURE, people.id)).get(ValueAxis.TRADITION, 0) > STEADFAST_AT:
            continue
        own = await norms_of(ctx.session, people.id)
        strict = sorted(key for key, stance in own.items() if stance in STRICT)
        if not strict:
            continue
        loosened = step_toward(stance_in(own, *strict[0]), EthicalStance.ACCEPTABLE)
        if await write_norm(ctx, people.id, *strict[0], loosened, cause="generation") is not None:
            tally.drifted += 1


async def keep_norm_drift(ctx: TickContext, tally: NormTally) -> None:
    await contact_drift(ctx, tally)
    await generation_drift(ctx, tally)
