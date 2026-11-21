from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.concealment import BreachRow, HiddenTruthRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionRow
from aerona.db.tables.reckoning import ReckoningCaseRow, ReckoningMeasureRow, ReckoningRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import AccountKind, AccountMedium
from aerona.domain.enums.concealment import BreachCause
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.made import Authenticity
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.reckoning import CaseOutcome, ReckoningMeasure
from aerona.engine.concealment.truths import knowledge
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.reckoning.book import ReckoningTally, acts_of, case_of, realm_of, servants
from aerona.engine.recording.record import record

RESTITUTION_CONTENT = 5
CONFESSION_SHARE = 2


async def vacate(ctx: TickContext, row: ReckoningRow, accused: EntityRow) -> None:
    for holder, office in await servants(ctx.session, row):
        if holder.id == accused.id and office is not None and "holder_entity_id" not in (office.locked or []):
            office.holder_entity_id, office.since_epoch = None, ctx.epoch


async def try_case(
    ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, case: ReckoningCaseRow, *, accused: EntityRow, tally: ReckoningTally
) -> None:
    if case.outcome is not CaseOutcome.PENDING or "outcome" in (case.locked or []):
        return
    tally.trials += 1
    await record(
        ctx, "reckoning.trial", roles={IncidentRole.ACCUSED: accused.id, IncidentRole.JUDGE: row.polity_entity_id}, facts={"acts": len(case.incident_ids or [])}
    )
    chance = ctx.rules.reckoning.convict_pct * measure.strength // PERCENT if case.incident_ids else 0
    if ctx.rng(f"reckoning.verdict.{case.id}").chance(chance):
        case.outcome = CaseOutcome.CONVICTED
        tally.convicted += 1
        await vacate(ctx, row, accused)
    else:
        case.outcome = CaseOutcome.ACQUITTED
        tally.acquitted += 1
    case.epoch = ctx.epoch
    await record(ctx, "reckoning.verdict", roles={IncidentRole.ACCUSED: accused.id, IncidentRole.JUDGE: row.polity_entity_id}, facts={"outcome": case.outcome})


async def open_case(ctx: TickContext, row: ReckoningRow, accused: EntityRow, measure: ReckoningMeasure) -> ReckoningCaseRow:
    found = await case_of(ctx.session, row.id, accused.id)
    if found is not None:
        return found
    case = ReckoningCaseRow(
        reckoning_id=row.id,
        accused_node_id=accused.id,
        incident_ids=await acts_of(ctx.session, accused.id, row.fallen_epoch),
        measure=measure,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(case)
    await ctx.session.flush()
    return case


async def tribunal(ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, tally: ReckoningTally) -> None:
    for holder, _office in await servants(ctx.session, row):
        if held(holder.id):
            continue
        case = await open_case(ctx, row, holder, ReckoningMeasure.TRIBUNAL)
        await try_case(ctx, row, measure, case, accused=holder, tally=tally)


async def office_bar(ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, tally: ReckoningTally) -> None:
    realm = await realm_of(ctx.session, row)
    if realm is not None and not measure.admin_taken and "administration" not in (realm.locked or []):
        taken = round_half_up(realm.administration * ctx.rules.reckoning.office_bar_admin_loss_pct / PERCENT)
        realm.administration -= taken
        measure.admin_taken = taken
    for holder, _office in await servants(ctx.session, row):
        if held(holder.id):
            continue
        case = await open_case(ctx, row, holder, ReckoningMeasure.OFFICE_BAR)
        if case.outcome is CaseOutcome.PENDING and "outcome" not in (case.locked or []):
            case.outcome = CaseOutcome.BARRED
            tally.barred += 1
            await vacate(ctx, row, holder)


async def victims_grieve(ctx: TickContext, row: ReckoningRow, amount: int) -> None:
    realm = await realm_of(ctx.session, row)
    town = await ctx.session.get(SettlementProfileRow, realm.capital_entity_id) if realm is not None and realm.capital_entity_id is not None else None
    if town is not None and "unrest" not in (town.locked or []):
        town.unrest = clamp_int(town.unrest + amount, 0, PERCENT)


async def amnesty(ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, tally: ReckoningTally) -> None:
    shift = ctx.rules.reckoning.amnesty_grievance_shift
    for holder, _office in await servants(ctx.session, row):
        case = await open_case(ctx, row, holder, ReckoningMeasure.AMNESTY)
        if case.outcome is CaseOutcome.PENDING and "outcome" not in (case.locked or []):
            case.outcome = CaseOutcome.PARDONED
            tally.pardoned += 1
    if "resistance" not in (row.locked or []):
        row.resistance = clamp_int(row.resistance - shift, 0, PERCENT)
    if "victims_pressure" not in (row.locked or []):
        row.victims_pressure = clamp_int(row.victims_pressure + shift, 0, PERCENT)
    await victims_grieve(ctx, row, shift // 2)
    await record(ctx, "reckoning.amnesty", roles={IncidentRole.ACTOR: row.polity_entity_id}, facts={"measure": measure.measure, "shift": shift})


async def confession(ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, tally: ReckoningTally) -> None:
    shift = ctx.rules.reckoning.amnesty_grievance_shift // CONFESSION_SHARE
    for holder, _office in await servants(ctx.session, row):
        case = await open_case(ctx, row, holder, ReckoningMeasure.AMNESTY_FOR_CONFESSION)
        if case.outcome is CaseOutcome.PENDING and case.incident_ids and "outcome" not in (case.locked or []):
            case.outcome = CaseOutcome.CONFESSED
            tally.pardoned += 1
            await testify(ctx, row, holder.id, AccountKind.TESTIMONY, measure.strength)
    if "resistance" not in (row.locked or []):
        row.resistance = clamp_int(row.resistance - shift, 0, PERCENT)
    await record(ctx, "reckoning.amnesty", roles={IncidentRole.ACTOR: row.polity_entity_id}, facts={"measure": measure.measure, "shift": shift})


async def testify(ctx: TickContext, row: ReckoningRow, author: int | None, kind: AccountKind, strength: int) -> AccountRow:
    account = AccountRow(
        holder_entity_id=row.polity_entity_id,
        author_node_id=author,
        kind=kind,
        medium=AccountMedium.BOOK,
        subject_node_id=row.fallen_node_id,
        fidelity=clamp_int(ctx.rules.reckoning.inquiry_fidelity * strength // PERCENT, 0, PERCENT),
        credence=clamp_int(strength, 0, PERCENT),
        epoch=ctx.epoch,
        authenticity=Authenticity.GENUINE,
        locked=[],
    )
    ctx.session.add(account)
    await ctx.session.flush()
    return account


async def inquiry(ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, tally: ReckoningTally) -> None:
    if measure.started_epoch != ctx.epoch:
        return
    account = await testify(ctx, row, row.opened_by_node_id, AccountKind.RECORD, measure.strength)
    tally.inquiries += 1
    await record(
        ctx,
        "reckoning.inquiry_report",
        roles={IncidentRole.ACTOR: row.polity_entity_id, IncidentRole.SUBJECT: row.fallen_node_id},
        facts={"fidelity": account.fidelity},
    )


async def restitution(ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, tally: ReckoningTally) -> None:
    realm = await realm_of(ctx.session, row)
    if measure.started_epoch != ctx.epoch or realm is None or "treasury" in (realm.locked or []):
        return
    cost = round_half_up(realm.treasury * ctx.rules.reckoning.restitution_cost_pct * measure.strength // PERCENT / PERCENT)
    realm.treasury -= cost
    society = await ctx.session.get(CommunitySocietyRow, realm.capital_entity_id) if realm.capital_entity_id is not None else None
    if society is not None:
        society.satisfaction_farmer = clamp_int(society.satisfaction_farmer + RESTITUTION_CONTENT, 0, PERCENT)
    tally.restitutions += 1
    await record(ctx, "reckoning.restitution", roles={IncidentRole.ACTOR: row.polity_entity_id}, facts={"cost": cost})


async def victims_of(ctx: TickContext, row: ReckoningRow) -> list[EntityRow]:
    purges = (
        select(CollectionRow.id)
        .join(CollectionMemberRow, CollectionMemberRow.collection_id == CollectionRow.id)
        .where(CollectionRow.kind == CollectionKind.PURGE, CollectionMemberRow.node_id == row.polity_entity_id)
    )
    victims = select(CollectionMemberRow.node_id).where(CollectionMemberRow.collection_id.in_(purges), CollectionMemberRow.role == CollectionRole.VICTIM)
    found = [await living_entity(ctx.session, node) for node in sorted(set(await ctx.session.scalars(victims)))]
    return [victim for victim in found if victim is not None]


async def reparation(ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, tally: ReckoningTally) -> None:
    if measure.started_epoch != ctx.epoch:
        return
    for victim in await victims_of(ctx, row):
        if not held(victim.id):
            await give_coin(ctx.session, ctx.rules, victim, ctx.rules.reckoning.reparation_coin)
            tally.reparations += 1
    if "victims_pressure" not in (row.locked or []):
        row.victims_pressure = clamp_int(row.victims_pressure - ctx.rules.reckoning.amnesty_grievance_shift, 0, PERCENT)


async def memorial(ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, tally: ReckoningTally) -> None:
    realm = await realm_of(ctx.session, row)
    if measure.started_epoch != ctx.epoch or realm is None or "legitimacy" in (realm.locked or []):
        return
    realm.legitimacy = clamp_int(realm.legitimacy + ctx.rules.reckoning.memorial_legitimacy, 0, PERCENT)
    if "victims_pressure" not in (row.locked or []):
        row.victims_pressure = clamp_int(row.victims_pressure - ctx.rules.reckoning.memorial_legitimacy, 0, PERCENT)


async def open_records(ctx: TickContext, row: ReckoningRow, measure: ReckoningMeasureRow, tally: ReckoningTally) -> None:
    realm = await realm_of(ctx.session, row)
    capital = realm.capital_entity_id if realm is not None else None
    if measure.started_epoch != ctx.epoch or capital is None or row.fallen_node_id is None:
        return
    for truth in await ctx.session.scalars(select(HiddenTruthRow).where(HiddenTruthRow.subject_node_id == row.fallen_node_id).order_by(HiddenTruthRow.id)):
        known = await knowledge(ctx, truth.id, capital)
        known.know_pct = known.believe_pct = clamp_int(measure.strength, 0, PERCENT)
        known.revealed_epoch = ctx.epoch
        ctx.session.add(
            BreachRow(
                truth_id=truth.id,
                epoch=ctx.epoch,
                cause=BreachCause.RECORD_LEAK,
                witnesses=0,
                witness_node_ids=[],
                place_node_id=capital,
                spread=measure.strength,
            )
        )


Apply = Callable[[TickContext, ReckoningRow, ReckoningMeasureRow, ReckoningTally], Awaitable[None]]
APPLY: Mapping[ReckoningMeasure, Apply] = total(
    ReckoningMeasure,
    {
        ReckoningMeasure.TRIBUNAL: tribunal,
        ReckoningMeasure.TRUTH_INQUIRY: inquiry,
        ReckoningMeasure.OFFICE_BAR: office_bar,
        ReckoningMeasure.AMNESTY: amnesty,
        ReckoningMeasure.AMNESTY_FOR_CONFESSION: confession,
        ReckoningMeasure.RESTITUTION: restitution,
        ReckoningMeasure.REPARATION_TO_VICTIMS: reparation,
        ReckoningMeasure.MEMORIAL: memorial,
        ReckoningMeasure.RECORD_OPENING: open_records,
    },
)
