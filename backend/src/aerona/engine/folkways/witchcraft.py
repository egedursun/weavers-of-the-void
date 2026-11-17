from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import agree, several
from aerona.db.tables.culture import CastingRow, RumourRow
from aerona.db.tables.cycles import PolityStressRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import AccusationRow, MishapRow, WitchHuntRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.lore import ChronicleEntityRow
from aerona.db.tables.mind import MemoryRow, TraitRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.sacred import DivinationSystemRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import FanaticismKind
from aerona.domain.enums.folkways import AccusationOutcome, MishapResponse
from aerona.domain.enums.justice import CaseStage, Verdict
from aerona.domain.enums.mind import MemoryKind, PressureKind, TraitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind, PunishmentKind
from aerona.domain.enums.sacred import DivinationValidity
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.faith.book import FaithBook
from aerona.engine.mind.book import pressures_of
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.trials import judge_for, trial_for
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.recording.record import RoleValue, record
from aerona.engine.sacred.places import realm_of_town, region_of
from aerona.engine.services.war import ongoing_war_count

GRIEVANCES = frozenset({MemoryKind.BETRAYED_ME, MemoryKind.ILL_WILL, MemoryKind.KILLED_KIN})
PENALTY_OUTCOMES = {PunishmentKind.DEATH.value: AccusationOutcome.KILLED, PunishmentKind.EXILE.value: AccusationOutcome.EXILED}

ECCENTRIC = frozenset({TraitKind.RECLUSIVE, TraitKind.SCATTERBRAINED, TraitKind.LITERAL_MINDED, TraitKind.AWKWARD, TraitKind.BLUNT})
HOSTILE = "hostile"


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
    if not await close_kin_of(ctx.session, suspect.id) or await ctx.session.get(TraitRow, (suspect.id, TraitKind.RECLUSIVE)) is not None:
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
    if suspect.location_id is not None and await rumoured(ctx, suspect.location_id, suspect.id):
        score += table.rumour_weight
    return score + await deeper_suspicion(ctx, accuser, suspect)


async def rumoured(ctx: TickContext, town_id: int, suspect_id: int) -> bool:
    found = await ctx.session.scalar(
        select(RumourRow.id)
        .join(IncidentRow, IncidentRow.id == RumourRow.incident_id)
        .join(ChronicleEntityRow, ChronicleEntityRow.chronicle_id == IncidentRow.chronicle_id)
        .where(RumourRow.carrier_entity_id == town_id, ChronicleEntityRow.entity_id == suspect_id)
        .limit(1)
    )
    return found is not None


async def divined(ctx: TickContext, people_id: int | None, true_caster: int | None) -> EntityRow | None:
    if people_id is None or true_caster is None:
        return None
    systems = await ctx.session.scalars(
        select(DivinationSystemRow).where(DivinationSystemRow.people_entity_id == people_id, DivinationSystemRow.diviners > 0).order_by(DivinationSystemRow.id)
    )
    for system in list(systems):
        rng = ctx.rng(seed_of("witch.divined", system.id, true_caster, ctx.epoch))
        if system.validity is not DivinationValidity.NOISE and rng.chance(ctx.rules.divination.valid_truth):
            return await living_entity(ctx.session, true_caster)
    return None


async def consulted(ctx: TickContext, people_id: int | None) -> bool:
    if people_id is None:
        return False
    found = await ctx.session.scalar(
        select(DivinationSystemRow.id).where(DivinationSystemRow.people_entity_id == people_id, DivinationSystemRow.diviners > 0).limit(1)
    )
    return found is not None


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
    folk_id = folk.id if folk is not None else None
    seen = await divined(ctx, folk_id, mishap.cause_node_id if mishap is not None else None) if named is None else None
    if seen is not None:
        accused = seen
    else:
        scores = [await suspicion(ctx, accuser, suspect, folk_id, mishap) for suspect in suspects]
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
    key = (
        "witchcraft.accused_by_diviners"
        if seen is not None or (named is None and await consulted(ctx, folk_id))
        else "witchcraft.accused_by_rumour"
        if accused.location_id is not None and await rumoured(ctx, accused.location_id, accused.id)
        else "witchcraft.accused"
    )
    roles: dict[IncidentRole, RoleValue] = {
        IncidentRole.ACCUSED: accused.id,
        IncidentRole.PLACE: town.id,
        IncidentRole.ACCUSER: accuser.id if accuser else None,
    }
    await record(ctx, key, roles=roles, facts={"suspects": len(suspects)}, place=town.id)
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
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or await hunt_stress_of(ctx, town) < table.hunt_stress:
            continue
        fervour = clamp_int(table.hunt_fervour + (table.zealous_fervour if await zealous(ctx, town) else 0), 0, PERCENT)
        ctx.session.add(WitchHuntRow(settlement_entity_id=town_id, fervour=fervour, started_epoch=ctx.epoch, locked=[]))
        tally.hunts += 1
        await record(ctx, "witchcraft.hunt", roles={IncidentRole.PLACE: town_id}, facts={"fervour": fervour, "accusations": count}, place=town_id)
    await ctx.session.flush()


async def hunt_stress_of(ctx: TickContext, town: EntityRow) -> int:
    table = ctx.rules.witchcraft
    pressures = await pressures_of(ctx.session, town.id)
    region = await region_of(ctx.session, town)
    plague = (
        await ctx.session.scalar(select(OutbreakRow.id).where(OutbreakRow.region_entity_id == region.id, OutbreakRow.status != OutbreakStatus.ENDED).limit(1))
        if region is not None
        else None
    )
    realm = await realm_of_town(ctx.session, town.id)
    war = realm is not None and await ongoing_war_count(ctx.session, realm) > 0
    stress = await ctx.session.get(PolityStressRow, realm) if realm is not None else None
    return max(
        pressures.get(PressureKind.HUNGER, 0),
        pressures.get(PressureKind.INSECURITY, 0),
        table.plague_stress if plague is not None else 0,
        table.war_stress if war else 0,
        stress.psi if stress is not None else 0,
    )


async def zealous(ctx: TickContext, town: EntityRow) -> bool:
    church = (await FaithBook.load(ctx.session)).church_of(town.id)
    doctrine = church.doctrine if church is not None else None
    return doctrine is not None and doctrine.fanaticism is FanaticismKind.INQUISITION


async def remember_hunt(ctx: TickContext, town: EntityRow, hunt: WitchHuntRow) -> None:
    entry = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.EVENT,
            name=f"The witch hunt of {town.name}",
            body=(
                f"A witch hunt held {town.name} from epoch {hunt.started_epoch} to epoch {ctx.epoch}: "
                f"{several(hunt.accused, 'mortal', 'mortals')} {agree(hunt.accused, 'was', 'were')} accused and "
                f"{several(hunt.killed, 'mortal', 'mortals')} {agree(hunt.killed, 'was', 'were')} put to death."
            ),
            stats=EventStats(),
            power=min(PERCENT, hunt.accused + hunt.killed),
            world_id=town.world_id,
            location_id=town.id,
            subtype="witch hunt",
        ),
    )
    await connect(ctx.session, town.id, entry.id, BondKind.TELLS_OF, ctx.epoch, description="lived through it")


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
            await remember_hunt(ctx, town, hunt)
            await record(ctx, "witchcraft.hunt_over", roles={IncidentRole.PLACE: town.id}, facts={"accused": hunt.accused}, place=town.id)


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


async def deeper_suspicion(ctx: TickContext, accuser: EntityRow | None, suspect: EntityRow) -> float:
    table = ctx.rules.witchcraft_depth
    score = 0.0
    traits = set(await ctx.session.scalars(select(TraitRow.trait).where(TraitRow.node_id == suspect.id)))
    if traits & ECCENTRIC:
        score += table.eccentric_weight
    if accuser is None:
        return score
    known = await ctx.session.scalar(
        select(RelationshipRow.id).where(RelationshipRow.holder_node_id == accuser.id, RelationshipRow.subject_node_id == suspect.id).limit(1)
    )
    if known is None:
        score += table.distance_weight
    believed = await ctx.session.scalar(
        select(BeliefRow.value).where(BeliefRow.holder_node_id == accuser.id, BeliefRow.subject_node_id == suspect.id, BeliefRow.attribute == HOSTILE).limit(1)
    )
    if believed is not None and believed > PERCENT // 2:
        score += table.belief_weight
    return score
