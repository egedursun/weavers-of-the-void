from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.catalog.law_depth import COURT_TEXT
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import AppealRow, PrecedentRow, PrisonerRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.justice import Verdict
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of, take_coin
from aerona.engine.law.systems import advocacy, court_above, courts_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity

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
        outcome = "overturned the conviction of" if upheld else "upheld the conviction of"
        await note(
            ctx,
            f"On appeal, {COURT_TEXT[row.to_court]} {outcome} {accused.name}.",
            key="law.appeal_upheld" if upheld else "law.appeal_denied",
            ids=[accused.id],
            kind=ChronicleKind.CIVILIZATION,
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
