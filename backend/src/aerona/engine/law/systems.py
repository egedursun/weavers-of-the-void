from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.law_depth import CODE_TECHNIQUES, COURT_OFFICES, SECULAR_COURTS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import LegalSystemRow, PrecedentRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.justice import TrialKind, Verdict
from aerona.domain.enums.law_depth import CourtLevel, LegalSystem
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of, give_coin, take_coin
from aerona.engine.lore.civics import holders_know
from aerona.engine.mind.book import best_skill, values_for
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat_or
from aerona.engine.relations.book import relation

SYSTEM = "system"
ADVOCATE = "advocate"
DIVINE_TRIALS = frozenset({TrialKind.COMBAT, TrialKind.ORDEAL})


@dataclass
class SystemTally:
    adopted: int = 0
    faded: int = 0
    set_aside: int = 0


async def system_of(session: AsyncSession, holder_id: int | None) -> LegalSystem | None:
    row = await session.get(LegalSystemRow, holder_id) if holder_id is not None else None
    return row.system if row is not None else None


def court_of_case(case: CrimeCaseRow) -> int | None:
    return case.polity_entity_id if case.polity_entity_id is not None else case.settlement_entity_id


async def courts_of(session: AsyncSession, polity_id: int | None) -> list[CourtLevel]:
    if polity_id is None:
        return [CourtLevel.LOCAL]
    kinds = set(await session.scalars(select(OfficeRow.kind).where(OfficeRow.polity_entity_id == polity_id, OfficeRow.holder_entity_id.is_not(None))))
    return [court for court in SECULAR_COURTS if court not in COURT_OFFICES or COURT_OFFICES[court] in kinds]


async def court_above(session: AsyncSession, case: CrimeCaseRow) -> CourtLevel | None:
    chain = await courts_of(session, case.polity_entity_id)
    if case.court not in chain:
        return None
    index = chain.index(case.court)
    return chain[index + 1] if index + 1 < len(chain) else None


async def favoured(session: AsyncSession, polity: EntityRow) -> LegalSystem:
    profile = await session.get(PolityProfileRow, polity.id)
    members = [polity.id, *([profile.capital_entity_id] if profile is not None and profile.capital_entity_id is not None else [])]
    written = await written_code(session, members)
    churched = profile is not None and profile.state_religion_id is not None
    if written and churched:
        return LegalSystem.MIXED
    if churched:
        return LegalSystem.RELIGIOUS
    if written:
        return LegalSystem.CODIFIED
    return LegalSystem.CUSTOMARY


async def adopt_systems(ctx: TickContext, tally: SystemTally) -> None:
    table = ctx.rules.legal_systems
    realms = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for realm in list(realms):
        if held(realm.id):
            continue
        row = await ctx.session.get(LegalSystemRow, realm.id)
        wanted = await favoured(ctx.session, realm)
        if row is None:
            ctx.session.add(LegalSystemRow(holder_entity_id=realm.id, system=wanted, since_epoch=ctx.epoch, locked=[]))
            tally.adopted += 1
            continue
        if SYSTEM in row.locked or row.system in (wanted, LegalSystem.PRECEDENT, LegalSystem.ORACLE):
            continue
        if ctx.rng(f"law.system.{realm.id}").chance(table.adopt_pct):
            row.system, row.since_epoch = wanted, ctx.epoch
            tally.adopted += 1
    await ctx.session.flush()


async def compurgators(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> int:
    if case.settlement_entity_id is None:
        return 0
    folk = await ctx.session.scalars(
        select(EntityRow.id).where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.id != accused.id,
            await present_among(ctx.session, [case.settlement_entity_id]),
        )
    )
    sworn = 0
    for mortal_id in list(folk):
        view = await relation(ctx.session, mortal_id, accused.id)
        if view is not None and view.friendship >= ctx.rules.trials.friend_at:
            sworn += 1
    return sworn


async def customary(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    table = ctx.rules.legal_systems
    judge = await ctx.session.get(EntityRow, case.judge_entity_id) if case.judge_entity_id is not None else None
    memory = round_half_up(stat_or(judge, "intellect", 0) * table.lawspeaker_pct / PERCENT) if judge is not None else 0
    score = case.evidence + memory - await compurgators(ctx, case, accused) * table.compurgator_weight
    return score >= ctx.rules.trials.standard


async def religious(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    table = ctx.rules.legal_systems
    piety = (await values_for(ctx.session, accused.id)).get(ValueAxis.PIETY, 0)
    sacred = table.clergy_bonus if case.crime is CrimeKind.BLASPHEMY else 0
    return case.evidence + sacred - round_half_up(max(0, piety) * table.piety_pct / PERCENT) >= ctx.rules.trials.standard


def codified(ctx: TickContext, case: CrimeCaseRow) -> bool:
    return case.evidence + ctx.rules.legal_systems.code_bonus >= ctx.rules.trials.standard


async def leading_precedent(session: AsyncSession, holder_id: int | None, crime: CrimeKind) -> PrecedentRow | None:
    if holder_id is None:
        return None
    rows = await session.scalars(
        select(PrecedentRow)
        .where(PrecedentRow.holder_entity_id == holder_id, PrecedentRow.crime == crime, PrecedentRow.overturned.is_(False))
        .order_by(PrecedentRow.authority.desc(), PrecedentRow.id.desc())
        .limit(1)
    )
    return rows.first()


async def by_precedent(ctx: TickContext, case: CrimeCaseRow, guilty: bool) -> tuple[bool, bool]:
    leading = await leading_precedent(ctx.session, court_of_case(case), case.crime)
    if leading is None or not ctx.rng(f"law.follow.{case.id}").chance(ctx.rules.legal_systems.follow_pct * leading.authority / PERCENT):
        return guilty, False
    if "authority" not in leading.locked and not held(leading.holder_entity_id):
        leading.authority = clamp_int(leading.authority + ctx.rules.precedents.follow_gain, 0, PERCENT)
    return leading.verdict is Verdict.GUILTY, True


def by_oracle(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    if case.oracle_answer is not None:
        return case.oracle_answer is Verdict.GUILTY
    truth = case.culprit_entity_id == accused.id
    return truth if ctx.rng(f"law.oracle.{case.id}").chance(ctx.rules.legal_systems.oracle_truth_pct) else not truth


async def record_precedent(ctx: TickContext, case: CrimeCaseRow, verdict: Verdict) -> PrecedentRow | None:
    holder = court_of_case(case)
    if holder is None or held(holder):
        return None
    chain = await courts_of(ctx.session, case.polity_entity_id)
    step = chain.index(case.court) if case.court in chain else 0
    row = PrecedentRow(
        holder_entity_id=holder,
        crime=case.crime,
        verdict=verdict,
        court=case.court,
        case_id=case.id,
        authority=clamp_int(ctx.rules.precedents.authority + step * ctx.rules.precedents.court_step, 0, PERCENT),
        overturned=False,
        epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def by_system(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow, guilty: bool) -> bool:
    system = await system_of(ctx.session, court_of_case(case))
    trial = case.trial or TrialKind.JUDGE
    if system is LegalSystem.ORACLE:
        return by_oracle(ctx, case, accused)
    if system is None or trial in DIVINE_TRIALS:
        return guilty
    if system is LegalSystem.MIXED:
        system = LegalSystem.RELIGIOUS if case.crime is CrimeKind.BLASPHEMY else LegalSystem.CODIFIED
    if system is LegalSystem.CUSTOMARY:
        return await customary(ctx, case, accused)
    if system is LegalSystem.RELIGIOUS:
        return await religious(ctx, case, accused)
    if system is LegalSystem.CODIFIED:
        return codified(ctx, case)
    ruled, followed = await by_precedent(ctx, case, guilty)
    if not followed:
        await record_precedent(ctx, case, Verdict.GUILTY if ruled else Verdict.ACQUITTED)
    return ruled


async def hire_advocate(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> EntityRow | None:
    table = ctx.rules.appeals
    if case.settlement_entity_id is None or held(accused.id) or ADVOCATE in case.locked:
        return await ctx.session.get(EntityRow, case.advocate_entity_id) if case.advocate_entity_id is not None else None
    chosen = await ctx.session.get(EntityRow, case.advocate_entity_id) if case.advocate_entity_id is not None else None
    if chosen is None:
        if await coin_of(ctx.session, ctx.rules, accused) < table.advocate_fee:
            return None
        folk = await ctx.session.scalars(
            select(EntityRow)
            .where(
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                EntityRow.id != accused.id,
                await present_among(ctx.session, [case.settlement_entity_id]),
            )
            .order_by(EntityRow.id)
        )
        best: tuple[int, EntityRow] | None = None
        for mortal in list(folk):
            skill = await best_skill(ctx.session, mortal.id, (SkillKind.LAW,))
            if skill > 0 and not held(mortal.id) and (best is None or skill > best[0]):
                best = (skill, mortal)
        if best is None or not await take_coin(ctx.session, ctx.rules, accused, table.advocate_fee):
            return None
        chosen = best[1]
        await give_coin(ctx.session, ctx.rules, chosen, table.advocate_fee)
        case.advocate_entity_id = chosen.id
    return chosen


async def advocacy(session: AsyncSession, advocate_id: int | None, pct: int) -> int:
    if advocate_id is None:
        return 0
    law = await best_skill(session, advocate_id, (SkillKind.LAW,))
    oratory = await best_skill(session, advocate_id, (SkillKind.ORATORY,))
    return round_half_up((law + oratory) / 2 * pct / PERCENT)


async def plead(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> None:
    advocate = await hire_advocate(ctx, case, accused)
    if advocate is not None and "evidence" not in case.locked:
        case.evidence = clamp_int(case.evidence - await advocacy(ctx.session, advocate.id, ctx.rules.appeals.advocate_pct), 0, PERCENT)


async def drift_precedents(ctx: TickContext, tally: SystemTally) -> None:
    table = ctx.rules.precedents
    rows = await ctx.session.scalars(select(PrecedentRow).where(PrecedentRow.overturned.is_(False)).order_by(PrecedentRow.id))
    for row in list(rows):
        if held(row.holder_entity_id):
            continue
        if "authority" not in row.locked:
            row.authority = clamp_int(row.authority - table.decay, 0, PERCENT)
        if "overturned" in row.locked:
            continue
        if row.authority <= 0:
            row.overturned = True
            tally.faded += 1
            continue
        if await judge_opposes(ctx, row) and ctx.rng(f"law.drift.{row.id}").chance(table.drift_pct):
            row.overturned = True
            tally.set_aside += 1
    await ctx.session.flush()


async def judge_opposes(ctx: TickContext, row: PrecedentRow) -> bool:
    judge = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id).where(
            OfficeRow.polity_entity_id == row.holder_entity_id, OfficeRow.kind == OfficeKind.HIGH_JUDGE, OfficeRow.holder_entity_id.is_not(None)
        )
    )
    if judge is None:
        return False
    mercy = (await values_for(ctx.session, judge)).get(ValueAxis.MERCY, 0)
    return (mercy > 0) == (row.verdict is Verdict.GUILTY) and mercy != 0


async def written_code(session: AsyncSession, holder_ids: list[int]) -> bool:
    for technique in CODE_TECHNIQUES:
        if await holders_know(session, holder_ids, technique):
            return True
    return False
