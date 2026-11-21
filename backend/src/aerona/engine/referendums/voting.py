from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.tables.communication import PublicOpinionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import MovementProfileRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import MovementCause
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import DecisionRule, LawKind
from aerona.domain.enums.referendums import ReferendumCaller, ReferendumResult, ReferendumSubject
from aerona.engine.context import TickContext
from aerona.engine.polity.laws import ruling_law
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.engine.referendums.book import SALIENCE_PCT, ReferendumTally, enfranchised_pct, franchise_at, realm_of_holder, realm_profile
from aerona.engine.referendums.outcomes import carry_out

PETITIONS = total(
    MovementCause,
    {
        MovementCause.ABOLITION: None,
        MovementCause.INDEPENDENCE: ReferendumSubject.INDEPENDENCE,
        MovementCause.REVIVAL: ReferendumSubject.FAITH,
        MovementCause.LAND_REFORM: None,
        MovementCause.FRANCHISE: ReferendumSubject.CONSTITUTION,
        MovementCause.PEACE: ReferendumSubject.WAR,
        MovementCause.CONSERVATION: None,
    },
)
ASKING = sorted(cause for cause, subject in PETITIONS.items() if subject is not None)
APPROVAL_SPAN = 100
RC = ReferendumCaller
CALLER_WEIGHT = total(ReferendumCaller, {RC.RULER: 0, RC.ASSEMBLY: 10, RC.PETITION: -10, RC.LEAGUE: 20, RC.GOD: 100})


async def call_vote(
    ctx: TickContext,
    holder: EntityRow,
    subject: ReferendumSubject,
    target: int | None,
    *,
    binding: bool,
    caller: ReferendumCaller,
    called_by: int | None,
    tally: ReferendumTally,
) -> ReferendumRow:
    realm = await realm_of_holder(ctx.session, holder)
    row = ReferendumRow(
        name=f"the vote of {holder.name} on {spoken(subject)}",
        holder_node_id=holder.id,
        subject=subject,
        target_node_id=target,
        caller=caller,
        called_by_node_id=called_by,
        franchise=await franchise_at(ctx.session, realm),
        binding=binding,
        called_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.called += 1
    await record(
        ctx,
        "vote.called",
        roles={IncidentRole.ACTOR: called_by, IncidentRole.SUBJECT: holder.id, IncidentRole.TARGET: target},
        facts={"question": subject, "caller": caller, "franchise": row.franchise, "binding": "binding" if binding else "not binding"},
    )
    return row


async def opinion_lean(ctx: TickContext, row: ReferendumRow, holder: EntityRow) -> int:
    if row.target_node_id is None:
        return 0
    towns = [holder.id]
    if holder.entity_type is EntityType.POLITY:
        towns = list(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == holder.id)))
    query = select(func.avg(PublicOpinionRow.approval)).where(
        PublicOpinionRow.subject_node_id == row.target_node_id, PublicOpinionRow.community_node_id.in_(towns)
    )
    approval = await ctx.session.scalar(query)
    return round_half_up(float(approval or 0) * ctx.rules.referendums.opinion_weight_pct / APPROVAL_SPAN)


def spending_lean(ctx: TickContext, row: ReferendumRow) -> int:
    return round_half_up((row.yes_spending - row.no_spending) * ctx.rules.referendums.campaign_shift_pct / PERCENT)


async def hold(ctx: TickContext, row: ReferendumRow, tally: ReferendumTally) -> None:
    table = ctx.rules.referendums
    holder = await ctx.session.get(EntityRow, row.holder_node_id)
    if holder is None:
        return
    locked = row.locked or []
    if "yes_pct" not in locked:
        row.yes_pct = clamp_int(row.yes_pct + await opinion_lean(ctx, row, holder) + spending_lean(ctx, row), 0, PERCENT)
    if "turnout_pct" not in locked:
        row.turnout_pct = clamp_int(
            await enfranchised_pct(ctx, holder, row.franchise) * SALIENCE_PCT[row.subject] * table.salience_turnout_pct // (PERCENT * PERCENT), 0, PERCENT
        )
    row.held_epoch = ctx.epoch
    tally.held += 1
    await record(ctx, "vote.held", roles={IncidentRole.SUBJECT: holder.id}, facts={"question": row.subject, "turnout": row.turnout_pct, "yes": row.yes_pct})
    if row.fraud and ctx.rng(f"referendums.fraud.{row.id}").chance(row.fraud * table.fraud_detect_pct // PERCENT):
        row.result = ReferendumResult.VOID
        tally.voided += 1
        await record(ctx, "vote.fraud_exposed", roles={IncidentRole.SUBJECT: holder.id}, facts={"question": row.subject, "fraud": row.fraud})
        return
    row.result = ReferendumResult.PASSED if row.yes_pct >= row.threshold_pct else ReferendumResult.FAILED
    tally.passed += 1 if row.result is ReferendumResult.PASSED else 0
    tally.failed += 1 if row.result is ReferendumResult.FAILED else 0
    await record(
        ctx,
        "vote.result",
        roles={IncidentRole.SUBJECT: holder.id, IncidentRole.TARGET: row.target_node_id},
        facts={"question": row.subject, "result": row.result, "yes": row.yes_pct},
    )
    await answer(ctx, row, holder, tally)


async def answer(ctx: TickContext, row: ReferendumRow, holder: EntityRow, tally: ReferendumTally) -> None:
    table = ctx.rules.referendums
    obeyed = clamp_int(table.obey_chance_pct + CALLER_WEIGHT[row.caller], 0, PERCENT)
    if row.binding or row.result is not ReferendumResult.PASSED or ctx.rng(f"referendums.obey.{row.id}").chance(obeyed):
        if await carry_out(ctx, row, holder):
            tally.carried += 1
        return
    row.ignored = True
    tally.ignored += 1
    profile = await realm_profile(ctx.session, await realm_of_holder(ctx.session, holder))
    if profile is not None and "legitimacy" not in (profile.locked or []):
        profile.legitimacy = clamp_int(profile.legitimacy - table.ignore_legitimacy_loss, 0, PERCENT)
    await record(ctx, "vote.ignored", roles={IncidentRole.SUBJECT: holder.id}, facts={"question": row.subject, "legitimacy_lost": table.ignore_legitimacy_loss})


async def assembly_questions(ctx: TickContext, tally: ReferendumTally) -> None:
    query = select(PolityProfileRow).where(PolityProfileRow.decision_rule == DecisionRule.ASSEMBLY).order_by(PolityProfileRow.polity_entity_id)
    for profile in list(await ctx.session.scalars(query)):
        if held(profile.polity_entity_id) or not ctx.rng(f"referendums.assembly.{profile.polity_entity_id}.{ctx.epoch}").chance(
            ctx.rules.referendums.assembly_call_pct
        ):
            continue
        realm = await ctx.session.get(EntityRow, profile.polity_entity_id)
        charter = await ruling_law(ctx.session, profile.polity_entity_id, LawKind.CONSTITUTION)
        if realm is not None and charter is not None and not await asked(ctx, realm.id, ReferendumSubject.CONSTITUTION):
            await call_vote(
                ctx,
                realm,
                ReferendumSubject.CONSTITUTION,
                charter.law_entity_id,
                binding=True,
                caller=ReferendumCaller.ASSEMBLY,
                called_by=realm.id,
                tally=tally,
            )


async def asked(ctx: TickContext, holder_id: int, subject: ReferendumSubject) -> bool:
    query = select(ReferendumRow.id).where(
        ReferendumRow.holder_node_id == holder_id, ReferendumRow.subject == subject, ReferendumRow.result == ReferendumResult.PENDING
    )
    return await ctx.session.scalar(query.limit(1)) is not None


async def petitions(ctx: TickContext, tally: ReferendumTally) -> None:
    floor = ctx.rules.referendums.petition_threshold_pct
    query = select(MovementProfileRow).where(MovementProfileRow.support >= floor, MovementProfileRow.cause.in_(ASKING))
    for movement in list(await ctx.session.scalars(query.order_by(MovementProfileRow.faction_entity_id))):
        realm = await ctx.session.get(EntityRow, movement.polity_entity_id) if movement.polity_entity_id is not None else None
        subject = PETITIONS[movement.cause]
        if subject is None or realm is None or held(realm.id) or movement.target_entity_id is None or await asked(ctx, realm.id, subject):
            continue
        await call_vote(
            ctx, realm, subject, movement.target_entity_id, binding=False, caller=ReferendumCaller.PETITION, called_by=movement.faction_entity_id, tally=tally
        )
