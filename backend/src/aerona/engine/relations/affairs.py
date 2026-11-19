from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.ethics import HONOUR_MODELS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.write_guard import held, write_blocked
from aerona.domain.enums.mind import ActKind, Emotion, MemoryKind, ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import MarriageEnd
from aerona.domain.enums.polity import OathBreach, OathKind
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.relations import RelationType
from aerona.engine.context import TickContext
from aerona.engine.intimacy.norms import outside_union_weight
from aerona.engine.intrigue.talk import affair_secret
from aerona.engine.military.feuds import house_feud
from aerona.engine.mind.ethics import culture_of, honour_of
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.kin import partners_of
from aerona.engine.mortal.kinship import end_marriage, marriage_between
from aerona.engine.polity.oaths import break_on
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.relations.book import RELATIONS_KEY, ensure_relation, relation, shift
from aerona.engine.relations.passions import betrayed
from aerona.engine.unions.customs import divorce_rule


@dataclass
class AffairTally:
    begun: int = 0
    discovered: int = 0
    divorces: int = 0
    challenges: int = 0
    feuds: int = 0


async def flag_lovers(ctx: TickContext, row: RelationshipRow) -> bool:
    if RelationType.LOVER.value not in row.kinds or row.affair or "affair" in row.locked:
        return False
    if RelationType.SPOUSE.value in row.kinds:
        return False
    married = set(await partners_of(ctx.session, row.holder_node_id)) | set(await partners_of(ctx.session, row.subject_node_id))
    if not married - {row.holder_node_id, row.subject_node_id}:
        return False
    row.affair = True
    back = await relation(ctx.session, row.subject_node_id, row.holder_node_id)
    if back is not None and "affair" not in back.locked and not write_blocked(back.holder_node_id, RELATIONS_KEY):
        back.affair = True
    await affair_secret(ctx, row.holder_node_id, row.subject_node_id)
    return True


async def divorce_allowed(ctx: TickContext, spouse: EntityRow) -> str:
    return await divorce_rule(ctx.session, spouse)


async def consequences(ctx: TickContext, cheat: EntityRow, lover: EntityRow, spouse: EntityRow, tally: AffairTally) -> list[StepDraft]:
    table = ctx.rules.social
    rng = ctx.rng(seed_of("affair_end", cheat.id, spouse.id, ctx.epoch))
    told: list[StepDraft] = []
    model = await honour_of(ctx.session, (await culture_of(ctx.session, spouse.id) or spouse).id)
    if HONOUR_MODELS[model].affairs_end_in_duels and rng.chance(table.affair_duel_pct):
        await remember(
            ctx.session, ctx.rules, holder_id=spouse.id, subject_id=lover.id, kind=MemoryKind.HUMILIATED_ME, magnitude=table.affair_memory, epoch=ctx.epoch
        )
        tally.challenges += 1
        told.append(StepDraft(StepAction.THREATEN, actor=spouse.id, target=lover.id))
    await break_on(ctx, [cheat.id], OathKind.FIDELITY, OathBreach.LOVER_TAKEN)
    custom = await divorce_allowed(ctx, spouse)
    marriage = await marriage_between(ctx.session, cheat.id, spouse.id)
    weight = await outside_union_weight(ctx.session, spouse)
    odds = table.affair_divorce_pct * (2 if custom == "free" else 1) * weight
    if marriage is not None and custom != "forbidden" and rng.chance(min(PERCENT, odds)):
        await end_marriage(ctx.session, marriage, ctx.epoch, MarriageEnd.DIVORCE)
        tally.divorces += 1
        told.append(StepDraft(StepAction.SEPARATE, actor=spouse.id, target=cheat.id))
    if rng.chance(table.affair_feud_pct * weight) and await house_feud(ctx, lover.id, spouse.id, "an affair") is not None:
        tally.feuds += 1
        told.append(StepDraft(StepAction.FEUD, actor=spouse.id, target=lover.id))
    return told


async def discover(ctx: TickContext, cheat: EntityRow, lover: EntityRow, spouse: EntityRow, tally: AffairTally) -> None:
    for holder, subject in ((cheat.id, lover.id), (lover.id, cheat.id)):
        row = await relation(ctx.session, holder, subject)
        if row is not None and not write_blocked(holder, RELATIONS_KEY):
            row.affair_known = True
    await think(ctx.session, ctx.rules, spouse.id, ThoughtKind.JEALOUS, ctx.epoch, subject_id=cheat.id, emotion=Emotion.ANGER)
    await betrayed(ctx, spouse.id, cheat.id)
    await remember(
        ctx.session, ctx.rules, holder_id=spouse.id, subject_id=cheat.id, kind=MemoryKind.BETRAYED_ME, magnitude=ctx.rules.social.affair_memory, epoch=ctx.epoch
    )
    view = await ensure_relation(ctx.session, spouse.id, cheat.id, ctx.epoch)
    if view is not None:
        shift(ctx.rules, view, ctx.epoch, friendship=ctx.rules.social.affair_memory, romance=ctx.rules.social.affair_memory // 2)
    await judged(ctx, cheat.id, spouse.id, ActKind.ADULTERY, note=f"love outside a marriage with {lover.name}")
    told = await consequences(ctx, cheat, lover, spouse, tally)
    await record(
        ctx,
        "affair.discovered",
        roles={IncidentRole.SPOUSE: spouse.id, IncidentRole.ACCUSED: cheat.id, IncidentRole.CO_ACTOR: lover.id},
        steps=(StepDraft(StepAction.DISCOVER, actor=spouse.id, target=cheat.id), *told),
    )
    tally.discovered += 1


async def tend_affairs(ctx: TickContext, tally: AffairTally) -> None:
    rows = list(
        await ctx.session.scalars(
            select(RelationshipRow).where(RelationshipRow.affair.is_(True), RelationshipRow.affair_known.is_(False)).order_by(RelationshipRow.id)
        )
    )
    for row in rows:
        if held(row.holder_node_id) or row.affair_known:
            continue
        cheat, lover = await living_entity(ctx.session, row.holder_node_id), await living_entity(ctx.session, row.subject_node_id)
        if cheat is None or lover is None:
            continue
        for spouse_id in await partners_of(ctx.session, cheat.id):
            spouse = await living_entity(ctx.session, spouse_id)
            if spouse is None or spouse.id == lover.id or held(spouse.id) or spouse.location_id != cheat.location_id:
                continue
            if ctx.rng(seed_of("affair", cheat.id, spouse.id, ctx.epoch)).chance(ctx.rules.social.affair_discovery_pct):
                await discover(ctx, cheat, lover, spouse, tally)
                break
