from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import AppealRow, PrecedentRow, PrisonerRow
from aerona.db.write_guard import held
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of, take_coin
from aerona.engine.law.systems import advocacy, court_above, courts_of
from aerona.engine.loops.delay import lagged
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import StepDraft, record

REVERSED = "reversed"


@dataclass
class AppealTally:
    filed: int = 0
    heard: int = 0
    reversed: int = 0


async def appeal_fee(ctx: TickContext, case: CrimeCaseRow) -> int:
    chain = await courts_of(ctx.session, case.polity_entity_id)
    step = chain.index(case.court) if case.court in chain else 0
    return ctx.rules.appeals.fee + step * ctx.rules.appeals.fee_step


async def file_appeal(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> AppealRow | None:
    if case.verdict is not Verdict.GUILTY or held(accused.id) or await ctx.session.get(AppealRow, case.id) is not None:
        return None
    above = await court_above(ctx.session, case)
    fee = await appeal_fee(ctx, case)
    if above is None or await coin_of(ctx.session, ctx.rules, accused) < fee or not await take_coin(ctx.session, ctx.rules, accused, fee):
        return None
    row = AppealRow(case_id=case.id, from_court=case.court, to_court=above, fee=fee, filed_epoch=ctx.epoch, reversed=False, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


def upheld_chance(ctx: TickContext, case: CrimeCaseRow, advocate_bonus: int) -> int:
    table = ctx.rules.appeals
    return clamp_int(table.reversal_pct + advocate_bonus - round_half_up(case.evidence * table.evidence_pct / PERCENT), 0, PERCENT)


async def overturn(ctx: TickContext, case: CrimeCaseRow) -> None:
    case.verdict = Verdict.ACQUITTED
    await ctx.session.execute(delete(PrisonerRow).where(PrisonerRow.case_id == case.id))
    for precedent in await ctx.session.scalars(select(PrecedentRow).where(PrecedentRow.case_id == case.id)):
        if "overturned" not in precedent.locked:
            precedent.overturned = True


async def hear_appeal(ctx: TickContext, row: AppealRow, tally: AppealTally) -> None:
    case = await ctx.session.get(CrimeCaseRow, row.case_id)
    if case is None:
        return
    chance = upheld_chance(ctx, case, await advocacy(ctx.session, case.advocate_entity_id, ctx.rules.appeals.advocate_pct))
    chance = await lagged(ctx, BalanceLoop.PRECEDENT_DRIFT, case.polity_entity_id or case.settlement_entity_id, chance)
    upheld = row.reversed if REVERSED in row.locked else ctx.rng(f"law.appeal.{row.case_id}").chance(chance)
    row.decided_epoch, row.reversed = ctx.epoch, upheld
    if "court" not in case.locked:
        case.court = row.to_court
    tally.heard += 1
    accused = await living_entity(ctx.session, case.accused_entity_id) if case.accused_entity_id is not None else None
    if upheld and "verdict" not in case.locked:
        await overturn(ctx, case)
        tally.reversed += 1
    if accused is not None:
        await record(
            ctx,
            f"law.appeal_upheld_{row.to_court.value}" if upheld else f"law.appeal_denied_{row.to_court.value}",
            roles={IncidentRole.ACCUSED: accused.id, IncidentRole.ADVOCATE: case.advocate_entity_id},
            facts={"chance": chance, "fee": row.fee, "from_court": row.from_court},
            steps=(
                StepDraft(StepAction.APPEAL, actor=accused.id, amount=row.fee, unit=FactUnit.COIN),
                StepDraft(StepAction.JUDGE, target=accused.id, outcome=StepOutcome.REVERSED if upheld else StepOutcome.REFUSED),
            ),
            place=case.settlement_entity_id,
        )


async def hear_appeals(ctx: TickContext, tally: AppealTally) -> None:
    due = ctx.epoch - ctx.rules.appeals.delay
    rows = await ctx.session.scalars(
        select(AppealRow).where(AppealRow.decided_epoch.is_(None), AppealRow.filed_epoch <= due, AppealRow.filed_epoch < ctx.epoch).order_by(AppealRow.case_id)
    )
    for row in list(rows):
        case = await ctx.session.get(CrimeCaseRow, row.case_id)
        nodes = [node for node in (case.accused_entity_id, case.polity_entity_id, case.settlement_entity_id) if node is not None] if case else []
        if "decided_epoch" in row.locked or held(*nodes):
            continue
        await hear_appeal(ctx, row, tally)
    await ctx.session.flush()
