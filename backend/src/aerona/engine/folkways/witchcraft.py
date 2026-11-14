from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.culture import CastingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import AccusationRow, MishapRow, WitchHuntRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folkways import AccusationOutcome, MishapResponse
from aerona.domain.enums.justice import CaseStage, Verdict
from aerona.domain.enums.mind import MemoryKind, PressureKind
from aerona.domain.enums.mortal import CrimeKind, PunishmentKind
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import pressures_of
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.notes import note
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.trials import judge_for, trial_for
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up

GRIEVANCES = frozenset({MemoryKind.BETRAYED_ME, MemoryKind.ILL_WILL, MemoryKind.KILLED_KIN})
PENALTY_OUTCOMES = {PunishmentKind.DEATH.value: AccusationOutcome.KILLED, PunishmentKind.EXILE.value: AccusationOutcome.EXILED}


@dataclass
class WitchTally:
    accused: int = 0
    true: int = 0
    hunts: int = 0
    killed: int = 0
    cleared: int = 0


async def cast_on(ctx: TickContext, caster_id: int, victim_id: int | None) -> bool:
    query = select(CastingRow.id).where(CastingRow.caster_entity_id == caster_id)
    if victim_id is not None:
        query = query.where(CastingRow.target_entity_id == victim_id)
    return await ctx.session.scalar(query.limit(1)) is not None


async def suspicion(ctx: TickContext, accuser: EntityRow | None, suspect: EntityRow, town_people: int | None, mishap: MishapRow | None) -> float:
    table = ctx.rules.witchcraft
    score = 1.0
    mine = await ctx.session.get(MortalProfileRow, suspect.id)
    theirs = await ctx.session.get(MortalProfileRow, accuser.id) if accuser is not None else None
    if mine is not None and theirs is not None and mine.wealth > theirs.wealth:
        score += table.envy_weight
    folk = await people_of(ctx.session, suspect)
    if town_people is not None and (folk is None or folk.id != town_people):
        score += table.outsider_weight
    if not await close_kin_of(ctx.session, suspect.id):
        score += table.isolation_weight
    if accuser is not None:
        grudge = await ctx.session.scalar(
            select(MemoryRow.id)
            .where(MemoryRow.holder_node_id == accuser.id, MemoryRow.subject_node_id == suspect.id, MemoryRow.kind.in_(list(GRIEVANCES)))
            .limit(1)
        )
        if grudge is not None:
            score += table.grievance_weight
    if await ctx.session.scalar(select(AccusationRow.id).where(AccusationRow.accused_node_id == suspect.id).limit(1)) is not None:
        score += table.repeat_weight
    if mishap is not None and (mishap.cause_node_id == suspect.id or await cast_on(ctx, suspect.id, mishap.victim_node_id)):
        score += table.caster_weight
    return score


async def townsfolk(ctx: TickContext, town: EntityRow, besides: set[int]) -> list[EntityRow]:
    here = await present_in(ctx.session, town)
    rows = await ctx.session.scalars(
        select(EntityRow).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return [row for row in rows if row.id not in besides and not held(row.id) and row.location_id is not None]


async def open_case(ctx: TickContext, town: EntityRow, accused: EntityRow, guilty: bool, true_caster: int | None) -> CrimeCaseRow:
    laws = await LawBook.load(ctx.session)
    place = accused.location_id or town.id
    polity = laws.member_of.get(place)
    judge = await judge_for(ctx, polity, place)
    case = CrimeCaseRow(
        settlement_entity_id=place,
        polity_entity_id=polity,
        crime=CrimeKind.WITCHCRAFT,
        culprit_entity_id=accused.id if guilty else true_caster,
        accused_entity_id=accused.id,
        judge_entity_id=judge.id if judge is not None else None,
        stage=CaseStage.TRIAL,
        trial=await trial_for(ctx, place),
        evidence=ctx.rules.witchcraft.caster_weight if guilty else 0,
        opened_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(case)
    await ctx.session.flush()
    return case


async def accuse(
    ctx: TickContext,
    town: EntityRow,
    accuser: EntityRow | None,
    tally: WitchTally,
    *,
    mishap: MishapRow | None = None,
    hunt: WitchHuntRow | None = None,
    named: EntityRow | None = None,
) -> AccusationRow | None:
    besides = {node for node in (accuser.id if accuser else None, mishap.victim_node_id if mishap else None) if node is not None}
    suspects = [named] if named is not None else await townsfolk(ctx, town, besides)
    if not suspects:
        return None
    folk = await people_of(ctx.session, town)
    scores = [await suspicion(ctx, accuser, suspect, folk.id if folk is not None else None, mishap) for suspect in suspects]
    rng = ctx.rng(seed_of("witch.accuse", town.id, mishap.id if mishap else 0, hunt.id if hunt else 0, ctx.epoch))
    accused = rng.weighted(suspects, scores)
    victim = mishap.victim_node_id if mishap is not None else None
    guilty = (mishap is not None and mishap.cause_node_id == accused.id) or await cast_on(ctx, accused.id, victim)
    case = await open_case(ctx, town, accused, guilty, mishap.cause_node_id if mishap is not None else None)
    row = AccusationRow(
        settlement_entity_id=town.id,
        mishap_id=mishap.id if mishap else None,
        hunt_id=hunt.id if hunt else None,
        accuser_node_id=accuser.id if accuser else None,
        accused_node_id=accused.id,
        case_id=case.id,
        guilty_in_truth=guilty,
        opened_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    tally.accused += 1
    tally.true += guilty
    if hunt is not None and "accused" not in hunt.locked:
        hunt.accused += 1
    await note(ctx, f"{accused.name} of {town.name} was accused of witchcraft.", key="witchcraft.accused", ids=[accused.id, town.id])
    return row


async def accuser_for(ctx: TickContext, mishap: MishapRow) -> EntityRow | None:
    victim = await ctx.session.get(EntityRow, mishap.victim_node_id) if mishap.victim_node_id is not None else None
    if victim is not None and victim.entity_type is EntityType.MORTAL and victim.status is EntityStatus.CANON:
        return victim
    candidates = [*await close_kin_of(ctx.session, victim.id)] if victim is not None and victim.entity_type is EntityType.MORTAL else []
    for kin in candidates:
        found = await ctx.session.get(EntityRow, kin)
        if found is not None and found.status is EntityStatus.CANON:
            return found
    return None


async def answer_mishaps(ctx: TickContext, tally: WitchTally) -> None:
    accused = select(AccusationRow.mishap_id).where(AccusationRow.mishap_id.is_not(None))
    rows = await ctx.session.scalars(
        select(MishapRow)
        .where(MishapRow.response == MishapResponse.ACCUSATION, MishapRow.epoch >= ctx.epoch - 1, MishapRow.id.not_in(accused))
        .order_by(MishapRow.id)
    )
    for mishap in list(rows):
        town = await ctx.session.get(EntityRow, mishap.settlement_entity_id)
        if town is None or held(town.id) or not ctx.rng(seed_of("witch.answer", mishap.id)).chance(ctx.rules.witchcraft.accuse_chance):
            continue
        await accuse(ctx, town, await accuser_for(ctx, mishap), tally, mishap=mishap)


async def stir_hunts(ctx: TickContext, tally: WitchTally) -> None:
    table = ctx.rules.witchcraft
    since = ctx.epoch - table.hunt_memory
    counts = await ctx.session.execute(
        select(AccusationRow.settlement_entity_id, func.count(AccusationRow.id))
        .where(AccusationRow.opened_epoch >= since, AccusationRow.settlement_entity_id.is_not(None))
        .group_by(AccusationRow.settlement_entity_id)
    )
    burning = set(await ctx.session.scalars(select(WitchHuntRow.settlement_entity_id).where(WitchHuntRow.ended_epoch.is_(None))))
    for town_id, count in counts.all():
        if town_id is None or town_id in burning or held(town_id) or count < table.hunt_from:
            continue
        pressures = await pressures_of(ctx.session, town_id)
        if max(pressures.get(PressureKind.HUNGER, 0), pressures.get(PressureKind.INSECURITY, 0)) < table.hunt_stress:
            continue
        town = await ctx.session.get(EntityRow, town_id)
        if town is None:
            continue
        ctx.session.add(WitchHuntRow(settlement_entity_id=town_id, fervour=table.hunt_fervour, started_epoch=ctx.epoch, locked=[]))
        tally.hunts += 1
        await note(ctx, f"A witch hunt took hold of {town.name}.", key="witchcraft.hunt", ids=[town_id])
    await ctx.session.flush()


async def run_hunts(ctx: TickContext, tally: WitchTally) -> None:
    table = ctx.rules.witchcraft
    for hunt in list(await ctx.session.scalars(select(WitchHuntRow).where(WitchHuntRow.ended_epoch.is_(None)).order_by(WitchHuntRow.id))):
        town = await ctx.session.get(EntityRow, hunt.settlement_entity_id)
        if town is None or held(town.id):
            continue
        for _ in range(round_half_up(table.hunt_accusations * hunt.fervour / PERCENT)):
            await accuse(ctx, town, None, tally, hunt=hunt)
        if "fervour" not in hunt.locked:
            hunt.fervour = clamp_int(hunt.fervour - table.hunt_fade, 0, PERCENT)
        if hunt.fervour <= 0 and "ended_epoch" not in hunt.locked:
            hunt.ended_epoch = ctx.epoch
            await note(ctx, f"The witch hunt in {town.name} burned out.", key="witchcraft.hunt_over", ids=[town.id])


async def settle(ctx: TickContext, tally: WitchTally) -> None:
    pending = await ctx.session.scalars(select(AccusationRow).where(AccusationRow.outcome == AccusationOutcome.PENDING).order_by(AccusationRow.id))
    for row in list(pending):
        case = await ctx.session.get(CrimeCaseRow, row.case_id) if row.case_id is not None else None
        if held(row.accused_node_id) or "outcome" in row.locked or case is None or case.verdict is None:
            continue
        if case.verdict is Verdict.GUILTY:
            row.outcome = PENALTY_OUTCOMES.get(case.penalty or "", AccusationOutcome.PUNISHED)
        else:
            row.outcome = AccusationOutcome.EXILED if case.verdict is Verdict.FLED else AccusationOutcome.CLEARED
        row.closed_epoch = ctx.epoch
        tally.killed += row.outcome is AccusationOutcome.KILLED
        tally.cleared += row.outcome is AccusationOutcome.CLEARED
        hunt = await ctx.session.get(WitchHuntRow, row.hunt_id) if row.hunt_id is not None else None
        if hunt is not None and row.outcome is AccusationOutcome.KILLED and "killed" not in hunt.locked:
            hunt.killed += 1


async def keep_witchcraft(ctx: TickContext, tally: WitchTally) -> None:
    await settle(ctx, tally)
    await answer_mishaps(ctx, tally)
    await stir_hunts(ctx, tally)
    await run_hunts(ctx, tally)
    await ctx.session.flush()
