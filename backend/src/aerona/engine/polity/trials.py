from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.crimes import CRIMES
from aerona.catalog.crimes import TRIALS as TRIAL_SPECS
from aerona.constants.units import PERCENT
from aerona.core.grammar import an, spoken
from aerona.core.total import total
from aerona.db.tables.customs import EvidenceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import IdentityRow, SecretRow
from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow
from aerona.db.tables.polity import SentenceRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.customs import MemberRight
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intrigue import HookDemand, IntrigueSecret
from aerona.domain.enums.justice import CaseStage, Deposition, TrialKind, Verdict
from aerona.domain.enums.mind import ActKind, HonourModel, MemoryKind, SkillKind, TraitKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import CrimeKind, PunishmentKind
from aerona.domain.enums.polity import LawArea, LawKind, OfficeKind
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.engine.body.bands import banded
from aerona.engine.body.customs import people_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.customs.rights import has_right
from aerona.engine.faith.book import patron_node
from aerona.engine.intrigue.favours import hook_on, use_hook
from aerona.engine.intrigue.identities import EXPOSURE
from aerona.engine.intrigue.secrets import learn
from aerona.engine.law.appeals import file_appeal
from aerona.engine.law.jurisdictions import claimed_court
from aerona.engine.law.outlawry import declare_outlaw, is_outlaw
from aerona.engine.law.sentences import weigh_trial
from aerona.engine.law.systems import by_oracle, by_system, plead
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.civics import holders_know
from aerona.engine.mind.book import skill_level, traits_of, values_for
from aerona.engine.mind.ethics import culture_of, ethic_reading, honour_of
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.justice import CRIME_TEXT, MUTILATIONS, code_punishment, community_ruler, cruelty_of, sentence
from aerona.engine.mortal.kin import close_kin_of
from aerona.engine.mortal.standing import add_renown, add_stress
from aerona.engine.polity.justice import offenders
from aerona.engine.polity.laws import LawBook, law_param
from aerona.engine.polity.repute import shift_infamy
from aerona.engine.powers.sources import polity_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.relations.book import relation
from aerona.engine.relations.persuasion import office_holder
from aerona.engine.settlement.book import Town, credit

CRUEL = 60
AREA_SECRETS: Mapping[LawArea, frozenset[IntrigueSecret]] = total(
    LawArea,
    {
        LawArea.SUCCESSION: frozenset({IntrigueSecret.TRUE_PARENTAGE, IntrigueSecret.CRIME}),
        LawArea.PROPERTY: frozenset({IntrigueSecret.CRIME, IntrigueSecret.DEBT}),
        LawArea.FISCAL: frozenset({IntrigueSecret.CRIME, IntrigueSecret.DEBT}),
        LawArea.PENAL: frozenset({IntrigueSecret.CRIME}),
        LawArea.MILITARY: frozenset({IntrigueSecret.COWARDICE_IN_BATTLE, IntrigueSecret.BROKEN_OATH}),
        LawArea.SOCIAL: frozenset({IntrigueSecret.CRIME, IntrigueSecret.AFFAIR}),
        LawArea.PUBLIC_HEALTH: frozenset({IntrigueSecret.HIDDEN_CONDITION, IntrigueSecret.CRIME}),
        LawArea.MAGIC: frozenset({IntrigueSecret.DEAL_WITH_OUTER_BEING, IntrigueSecret.SECRET_CULT_MEMBERSHIP}),
        LawArea.CONSTITUTIONAL: frozenset({IntrigueSecret.CRIME, IntrigueSecret.BROKEN_OATH}),
    },
)
NAMED_CRIME_SECRETS: dict[CrimeKind, frozenset[IntrigueSecret]] = {
    CrimeKind.THEFT: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.MURDER: frozenset({IntrigueSecret.MURDER, IntrigueSecret.CRIME}),
    CrimeKind.BLASPHEMY: frozenset({IntrigueSecret.HERESY, IntrigueSecret.SECRET_CULT_MEMBERSHIP}),
    CrimeKind.TREASON: frozenset({IntrigueSecret.CRIME, IntrigueSecret.BROKEN_OATH}),
    CrimeKind.DESERTION: frozenset({IntrigueSecret.COWARDICE_IN_BATTLE}),
    CrimeKind.WITCHCRAFT: frozenset({IntrigueSecret.DEAL_WITH_OUTER_BEING, IntrigueSecret.SECRET_CULT_MEMBERSHIP}),
    CrimeKind.MIND_THEFT: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.UNLICENSED_COPYING: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.FORCED_EDIT: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.ERASURE: frozenset({IntrigueSecret.MURDER, IntrigueSecret.CRIME}),
    CrimeKind.MACHINE_SEIZURE: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.IMPERSONATION: frozenset({IntrigueSecret.CRIME}),
    CrimeKind.MIND_COMPULSION: frozenset({IntrigueSecret.CRIME}),
}
CRIME_SECRETS: Mapping[CrimeKind, frozenset[IntrigueSecret]] = total(
    CrimeKind, {crime: NAMED_CRIME_SECRETS.get(crime, AREA_SECRETS[CRIMES[crime].area]) for crime in CrimeKind}
)
TRIAL_KINDS = {kind.value: kind for kind in TrialKind}
SEEN_TRIALS = frozenset({TrialKind.ORDEAL, TrialKind.ORACLE})
TRIAL_TEXT = {kind: spec.text for kind, spec in TRIAL_SPECS.items()}
VERDICT = "verdict"


@dataclass
class TrialTally:
    tried: int = 0
    convicted: int = 0
    acquitted: int = 0
    wrongful: int = 0
    fled: int = 0


async def judge_for(ctx: TickContext, polity_id: int | None, town_id: int) -> EntityRow | None:
    holder = await office_holder(ctx.session, polity_id, OfficeKind.RULER) if polity_id is not None else None
    found = await living_entity(ctx.session, holder) if holder is not None else None
    return found or await community_ruler(ctx.session, town_id)


async def investigator_for(ctx: TickContext, polity_id: int | None, town_id: int) -> EntityRow | None:
    holder = await office_holder(ctx.session, polity_id, OfficeKind.HIGH_JUDGE, OfficeKind.GOVERNOR, OfficeKind.RULER) if polity_id is not None else None
    found = await living_entity(ctx.session, holder) if holder is not None else None
    return found or await community_ruler(ctx.session, town_id)


async def townsfolk(ctx: TickContext, town_id: int, *, besides: set[int]) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town_id]))
        .order_by(EntityRow.id)
    )
    return [row for row in rows if row.id not in besides]


async def testimony_of(ctx: TickContext, case: CrimeCaseRow, witness: EntityRow, culprit_id: int) -> tuple[Deposition, int]:
    table = ctx.rules.trials
    if await is_outlaw(ctx, witness.id):
        return Deposition.SILENT, 0
    hook = await hook_on(ctx, culprit_id, witness.id)
    if hook is not None and await use_hook(ctx, hook, HookDemand.SUPPORT):
        return Deposition.SHIELDS, table.witness_reliability // 2
    view = await relation(ctx.session, witness.id, culprit_id)
    friendship = view.friendship if view is not None else 0
    reliability = clamp_int(table.witness_reliability - abs(friendship) // 2, 0, PERCENT)
    if friendship >= table.friend_at:
        return Deposition.SHIELDS, reliability
    if friendship <= -table.foe_at or ctx.rng(f"trials.speak.{case.id}.{witness.id}").chance(table.speak_pct):
        return Deposition.ACCUSES, reliability
    return Deposition.SILENT, reliability


async def hear_witnesses(ctx: TickContext, case: CrimeCaseRow, culprit_id: int) -> list[CaseWitnessRow]:
    if case.settlement_entity_id is None:
        return []
    folk = [row for row in await townsfolk(ctx, case.settlement_entity_id, besides={culprit_id}) if not held(row.id)]
    chosen = ctx.rng(f"trials.witnesses.{case.id}").sample(folk, min(len(folk), ctx.rules.trials.witnesses))
    rows: list[CaseWitnessRow] = []
    for witness in chosen:
        testimony, reliability = await testimony_of(ctx, case, witness, culprit_id)
        row = CaseWitnessRow(case_id=case.id, witness_entity_id=witness.id, testimony=testimony, reliability=reliability)
        ctx.session.add(row)
        rows.append(row)
    await ctx.session.flush()
    return rows


async def witnesses_of(ctx: TickContext, case_id: int) -> list[CaseWitnessRow]:
    return list(await ctx.session.scalars(select(CaseWitnessRow).where(CaseWitnessRow.case_id == case_id).order_by(CaseWitnessRow.witness_entity_id)))


def testimony_weight(ctx: TickContext, witnesses: list[CaseWitnessRow]) -> int:
    pct = ctx.rules.trials.testimony_pct
    accusing = sum(row.reliability for row in witnesses if row.testimony is Deposition.ACCUSES)
    shielding = sum(row.reliability for row in witnesses if row.testimony is Deposition.SHIELDS)
    return round_half_up((accusing - shielding) * pct / PERCENT)


async def known_secret(ctx: TickContext, investigator_id: int | None, culprit_id: int, crime: CrimeKind) -> bool:
    secrets = await ctx.session.scalars(select(SecretRow).where(SecretRow.holder_node_id == culprit_id, SecretRow.kind.in_(list(CRIME_SECRETS[crime]))))
    return any(row.exposed_epoch is not None or (investigator_id is not None and investigator_id in (row.known_by or [])) for row in secrets)


async def weigh(ctx: TickContext, case: CrimeCaseRow, culprit_id: int, investigator: EntityRow | None) -> int:
    table = ctx.rules.trials
    skill = await skill_level(ctx.session, investigator.id, SkillKind.LAW) if investigator is not None else 0
    found = round_half_up(skill * table.skill_evidence_pct / PERCENT) + testimony_weight(ctx, await witnesses_of(ctx, case.id))
    if await known_secret(ctx, investigator.id if investigator is not None else None, culprit_id, case.crime):
        found += table.secret_evidence
    courts = [court for court in (case.settlement_entity_id, case.polity_entity_id) if court is not None]
    if await holders_know(ctx.session, courts, Technique.ORAL_LAW):
        found += ctx.rules.technique_effects.oral_law_evidence
    kinds = list(await ctx.session.scalars(select(EvidenceRow.kind).where(EvidenceRow.case_id == case.id)))
    found += sum(table.fitting_evidence for kind in kinds if kind in CRIMES[case.crime].evidence)
    return clamp_int(found, 0, PERCENT)


async def will_torture(ctx: TickContext, case: CrimeCaseRow, investigator: EntityRow | None) -> bool:
    if investigator is None or case.settlement_entity_id is None:
        return False
    if await law_param(ctx.session, case.settlement_entity_id, LawKind.PENAL_CODE, "torture") != "allowed":
        return False
    values = await values_for(ctx.session, investigator.id)
    return await ethic_reading(ctx.session, ctx.rules, investigator.id, ActKind.TORTURE, values) >= ctx.rules.trials.torture_reading


async def interrogate(ctx: TickContext, case: CrimeCaseRow, suspect: EntityRow, investigator: EntityRow) -> None:
    table = ctx.rules.trials
    harm = Harm(table.torture_hp, HarmCause.TORTURE, f"questioned under torture by {investigator.name}", killer_id=investigator.id)
    await apply_hits(ctx, suspect, harm, lethal=False)
    await judged(ctx, investigator.id, suspect.id, ActKind.TORTURE)
    case.tortured = True
    case.evidence = clamp_int(case.evidence + table.torture_evidence, 0, PERCENT)


async def scapegoat(ctx: TickContext, case: CrimeCaseRow, culprit_id: int) -> EntityRow | None:
    if case.settlement_entity_id is None:
        return None
    folk = [row for row in await townsfolk(ctx, case.settlement_entity_id, besides={culprit_id}) if not held(row.id)]
    if not folk or not ctx.rng(f"trials.scapegoat.{case.id}").chance(ctx.rules.trials.scapegoat_pct * (PERCENT - case.evidence) / PERCENT):
        return None
    return min(folk, key=lambda row: (stat(row, "charisma") or 0, row.id))


async def is_city(ctx: TickContext, place_id: int) -> bool:
    place = await ctx.session.get(EntityRow, place_id)
    return place is not None and place.entity_type is EntityType.SETTLEMENT


def close(ctx: TickContext, case: CrimeCaseRow, verdict: Verdict) -> None:
    case.stage, case.verdict, case.closed_epoch = CaseStage.CLOSED, verdict, ctx.epoch


async def uncover(ctx: TickContext, case: CrimeCaseRow, culprit_id: int, investigator_id: int) -> int:
    secrets = await ctx.session.scalars(
        select(SecretRow).where(SecretRow.holder_node_id == culprit_id, SecretRow.kind.in_(list(CRIME_SECRETS[case.crime]))).order_by(SecretRow.id)
    )
    found = 0
    for secret in list(secrets):
        if await learn(ctx, secret, investigator_id):
            found += 1
    mask = await ctx.session.get(IdentityRow, culprit_id)
    if mask is not None and mask.exposed_epoch is None and EXPOSURE not in (mask.locked or []) and not held(culprit_id):
        mask.exposure = clamp_int(mask.exposure + ctx.rules.intrigue.identity_investigation, 0, PERCENT)
        ctx.count("identities_traced")
    ctx.count("secrets_uncovered", found)
    return found


async def investigate(ctx: TickContext, case: CrimeCaseRow, culprit: EntityRow, investigator: EntityRow | None) -> None:
    table = ctx.rules.trials
    await hear_witnesses(ctx, case, culprit.id)
    case.evidence = await weigh(ctx, case, culprit.id, investigator)
    if case.evidence < table.name_at and investigator is not None and await will_torture(ctx, case, investigator):
        await interrogate(ctx, case, culprit, investigator)
        ctx.count("case_tortured")
    if case.evidence >= table.name_at:
        case.accused_entity_id = culprit.id
        if investigator is not None:
            await uncover(ctx, case, culprit.id, investigator.id)
    else:
        blamed = await scapegoat(ctx, case, culprit.id)
        if blamed is None:
            close(ctx, case, Verdict.DROPPED)
            ctx.count("case_dropped")
            return
        case.accused_entity_id = blamed.id
    case.stage = CaseStage.TRIAL
    case.trial = await trial_for(ctx, case.settlement_entity_id)


async def trial_for(ctx: TickContext, town_id: int | None) -> TrialKind:
    if town_id is None:
        return TrialKind.JUDGE
    chosen = TRIAL_KINDS.get(str(await law_param(ctx.session, town_id, LawKind.PENAL_CODE, "trial")), TrialKind.JUDGE)
    return chosen if await trial_open(ctx, town_id, chosen) else TrialKind.JUDGE


async def trial_open(ctx: TickContext, town_id: int, chosen: TrialKind) -> bool:
    town = await ctx.session.get(EntityRow, town_id)
    folk = await people_of(ctx.session, town) if town is not None else None
    if chosen is TrialKind.COMBAT:
        culture = await culture_of(ctx.session, folk.id if folk is not None else town_id)
        return await honour_of(ctx.session, culture.id if culture is not None else None) is HonourModel.HONOUR
    if chosen in SEEN_TRIALS:
        return (await values_for(ctx.session, folk.id if folk is not None else town_id)).get(ValueAxis.SUPERSTITION, 0) >= 0
    if chosen is TrialKind.DIVINE_JUDGEMENT:
        return await patron_node(ctx.session, town_id) is not None
    if chosen is TrialKind.MADE_JUDGE:
        realm = await polity_of(ctx.session, town_id)
        courts = [town_id, *([realm] if realm is not None else [])]
        return await holders_know(ctx.session, courts, Technique.ARTIFICIAL_MINDS)
    return True


async def open_case(ctx: TickContext, town: Town, laws: LawBook, *, judge: EntityRow | None) -> CrimeCaseRow | None:
    if held(town.entity.id):
        return None
    found = {kind: [row for row in rows if not held(row.id)] for kind, rows in (await offenders(ctx, town.entity.id, laws)).items()}
    found = {kind: rows for kind, rows in found.items() if rows}
    if not found:
        return None
    rng = ctx.rng(f"culprit.{town.entity.id}")
    crime = rng.pick(sorted(found, key=lambda kind: list(CrimeKind).index(kind)))
    culprit = rng.pick(found[crime])
    polity = laws.member_of.get(town.entity.id)
    investigator = await investigator_for(ctx, polity, town.entity.id)
    case = CrimeCaseRow(
        settlement_entity_id=town.entity.id,
        polity_entity_id=polity,
        crime=crime,
        culprit_entity_id=culprit.id,
        investigator_entity_id=investigator.id if investigator is not None else None,
        judge_entity_id=judge.id if judge is not None else None,
        opened_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(case)
    await ctx.session.flush()
    await investigate(ctx, case, culprit, investigator)
    ctx.count(f"case.{crime.value}")
    return case


async def report_crime(ctx: TickContext, town_id: int, culprit_id: int, crime: CrimeKind) -> CrimeCaseRow | None:
    if held(town_id) or not await is_city(ctx, town_id):
        return None
    laws = await LawBook.load(ctx.session)
    polity = laws.member_of.get(town_id)
    investigator = await investigator_for(ctx, polity, town_id)
    judge = await judge_for(ctx, polity, town_id)
    case = CrimeCaseRow(
        settlement_entity_id=town_id,
        polity_entity_id=polity,
        crime=crime,
        culprit_entity_id=culprit_id,
        accused_entity_id=None,
        investigator_entity_id=investigator.id if investigator is not None else None,
        judge_entity_id=judge.id if judge is not None else None,
        stage=CaseStage.INVESTIGATION,
        evidence=0,
        forged=False,
        opened_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(case)
    await ctx.session.flush()
    return case


async def frame_case(ctx: TickContext, target: EntityRow, framer_id: int, crime: CrimeKind = CrimeKind.THEFT) -> CrimeCaseRow | None:
    if target.location_id is None or held(target.id):
        return None
    if not await is_city(ctx, target.location_id):
        return None
    laws = await LawBook.load(ctx.session)
    polity = laws.member_of.get(target.location_id)
    investigator = await investigator_for(ctx, polity, target.location_id)
    judge = await judge_for(ctx, polity, target.location_id)
    case = CrimeCaseRow(
        settlement_entity_id=target.location_id,
        polity_entity_id=polity,
        crime=crime,
        culprit_entity_id=None,
        accused_entity_id=target.id,
        investigator_entity_id=investigator.id if investigator is not None else None,
        judge_entity_id=judge.id if judge is not None else None,
        stage=CaseStage.TRIAL,
        evidence=ctx.rules.trials.forged_evidence,
        forged=True,
        opened_epoch=ctx.epoch,
        locked=[],
    )
    case.trial = await trial_for(ctx, target.location_id)
    ctx.session.add(case)
    await ctx.session.flush()
    framer = await living_entity(ctx.session, framer_id)
    if framer is not None and not held(framer.id):
        ctx.session.add(
            CaseWitnessRow(case_id=case.id, witness_entity_id=framer.id, testimony=Deposition.ACCUSES, reliability=ctx.rules.trials.witness_reliability)
        )
        await ctx.session.flush()
    return case


async def by_judge(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    table = ctx.rules.trials
    score = case.evidence
    if not await has_right(ctx.session, accused.id, MemberRight.COURTS, case.polity_entity_id):
        score += ctx.rules.citizenship.rightless_court_bias
    if case.judge_entity_id is not None:
        traits = await traits_of(ctx.session, case.judge_entity_id)
        if TraitKind.ARBITRARY in traits and TraitKind.JUST not in traits:
            score += ctx.rng(f"trials.whim.{case.id}").integer(-table.arbitrary_swing, table.arbitrary_swing)
        view = await relation(ctx.session, case.judge_entity_id, accused.id)
        if view is not None and TraitKind.JUST not in traits:
            score -= round_half_up(view.friendship * table.bias_pct / PERCENT)
    return score >= table.standard


async def by_jury(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    return case.evidence + testimony_weight(ctx, await witnesses_of(ctx, case.id)) // 2 >= ctx.rules.trials.standard


async def by_combat(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    table = ctx.rules.trials
    accusers = [row.witness_entity_id for row in await witnesses_of(ctx, case.id) if row.testimony is Deposition.ACCUSES]
    champion_id = accusers[0] if accusers else case.investigator_entity_id
    champion = await living_entity(ctx.session, champion_id) if champion_id is not None else None
    if champion is None or champion.id == accused.id:
        return False
    rng = ctx.rng(f"trials.combat.{case.id}")
    accused_score = (stat(accused, "strength") or 0) + rng.integer(0, PERCENT // 3)
    champion_score = (stat(champion, "strength") or 0) + rng.integer(0, PERCENT // 3)
    loser = accused if accused_score < champion_score else champion
    if not held(loser.id):
        await apply_hits(ctx, loser, Harm(table.combat_hp, HarmCause.DUEL, "fell in a trial by combat", damage_type=DamageType.CUT), lethal=False)
    return loser.id == accused.id


async def by_ordeal(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    table = ctx.rules.trials
    innocent = case.culprit_entity_id != accused.id
    survived = ctx.rng(f"trials.ordeal.{case.id}").chance(table.ordeal_pct if innocent else PERCENT - table.ordeal_pct)
    if not held(accused.id):
        await apply_hits(
            ctx,
            accused,
            Harm(
                table.combat_hp // 2,
                HarmCause.PUNISHMENT,
                "bore the ordeal",
                damage_type=DamageType.FIRE,
                severity=banded(ctx, ctx.rules.harm_bands.ordeal, accused.id),
            ),
            lethal=False,
        )
    return not survived


async def by_council(ctx: TickContext, case: CrimeCaseRow, _accused: EntityRow) -> bool:
    return case.evidence + testimony_weight(ctx, await witnesses_of(ctx, case.id)) // 3 >= ctx.rules.trials.standard


async def by_arbitration(ctx: TickContext, case: CrimeCaseRow, _accused: EntityRow) -> bool:
    return case.evidence + ctx.rules.trials.arbitration_ease >= ctx.rules.trials.standard


async def by_seer(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    return by_oracle(ctx, case, accused)


async def by_god(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    god = await patron_node(ctx.session, case.settlement_entity_id) if case.settlement_entity_id is not None else None
    if god is None:
        return await by_judge(ctx, case, accused)
    return case.culprit_entity_id == accused.id


async def by_assembly(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    sway = round_half_up(stat_or(accused, "renown", 0) * ctx.rules.trials.renown_sway_pct / PERCENT)
    return case.evidence + testimony_weight(ctx, await witnesses_of(ctx, case.id)) // 2 - sway >= ctx.rules.trials.standard


async def by_inquisition(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> bool:
    if not held(accused.id):
        await add_stress(ctx.session, accused.id, ctx.rules.trials.inquisition_stress, ctx.epoch)
    return case.evidence + ctx.rules.trials.inquisition_bias >= ctx.rules.trials.standard


async def by_mediation(ctx: TickContext, case: CrimeCaseRow, _accused: EntityRow) -> bool:
    return case.evidence >= ctx.rules.trials.standard


async def by_made_judge(ctx: TickContext, case: CrimeCaseRow, _accused: EntityRow) -> bool:
    return case.evidence + ctx.rules.trials.made_judge_precision >= ctx.rules.trials.standard


TRIALS: Mapping[TrialKind, Callable[[TickContext, CrimeCaseRow, EntityRow], Awaitable[bool]]] = total(
    TrialKind,
    {
        TrialKind.JUDGE: by_judge,
        TrialKind.JURY: by_jury,
        TrialKind.COMBAT: by_combat,
        TrialKind.ORDEAL: by_ordeal,
        TrialKind.COUNCIL: by_council,
        TrialKind.ARBITRATION: by_arbitration,
        TrialKind.ORACLE: by_seer,
        TrialKind.DIVINE_JUDGEMENT: by_god,
        TrialKind.ASSEMBLY: by_assembly,
        TrialKind.INQUISITION: by_inquisition,
        TrialKind.MEDIATION: by_mediation,
        TrialKind.MADE_JUDGE: by_made_judge,
    },
)


def erred(ctx: TickContext, case: CrimeCaseRow, trial: TrialKind, guilty: bool) -> bool:
    chance = TRIAL_SPECS[trial].error * (PERCENT - case.evidence) // PERCENT
    return not guilty if ctx.rng(f"trials.error.{case.id}").chance(chance) else guilty


async def grieve(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow, punishment: PunishmentKind) -> None:
    table = ctx.rules.trials
    if case.judge_entity_id is not None:
        for kin in await close_kin_of(ctx.session, accused.id):
            if not held(kin):
                await remember(
                    ctx.session,
                    ctx.rules,
                    holder_id=kin,
                    subject_id=case.judge_entity_id,
                    kind=MemoryKind.BETRAYED_ME,
                    magnitude=-table.grievance_grudge,
                    epoch=ctx.epoch,
                    note=f"{accused.name} was condemned for {an(CRIME_TEXT[case.crime])} they did not commit",
                )
    if punishment is PunishmentKind.DEATH:
        await add_renown(ctx.session, accused.id, table.martyr_renown, ctx.epoch, rules=ctx.rules)
    town = await ctx.session.get(SettlementProfileRow, case.settlement_entity_id or -1)
    if town is not None and "unrest" not in (town.locked or []):
        town.unrest = clamp_int(town.unrest + table.wrongful_unrest, 0, PERCENT)


async def convict(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow, laws: LawBook, tally: TrialTally) -> None:
    judge = await living_entity(ctx.session, case.judge_entity_id) if case.judge_entity_id is not None else None
    punishment = TRIAL_SPECS[case.trial or TrialKind.JUDGE].sentence or await code_punishment(ctx, case.settlement_entity_id, case.crime)
    close(ctx, case, Verdict.GUILTY)
    case.wrongful = case.culprit_entity_id != accused.id
    code = laws.in_force(case.settlement_entity_id, LawKind.PENAL_CODE) if case.settlement_entity_id is not None else None
    ctx.session.add(
        SentenceRow(
            mortal_entity_id=accused.id,
            settlement_entity_id=case.settlement_entity_id,
            law_entity_id=code.law_entity_id if code is not None else None,
            crime=case.crime,
            penalty=punishment,
            epoch=ctx.epoch,
            case_id=case.id,
        )
    )
    town = await ctx.session.get(EntityRow, case.settlement_entity_id) if case.settlement_entity_id is not None else None
    if punishment is PunishmentKind.FINE and town is not None:
        await credit(ctx, town, TreasuryEntry.TAX, ctx.rules.legislation.fine_amount, f"fine for {spoken(case.crime)}")
    cruelty = cruelty_of(punishment)
    if judge is not None and punishment not in MUTILATIONS and cruelty >= CRUEL:
        await shift_infamy(ctx, judge.id, ctx.rules.legislation.penal_infamy * cruelty // PERCENT)
    applied = await sentence(ctx, accused, case.crime, punishment, judge=judge, case_id=case.id)
    case.penalty, case.immune = (punishment, False) if applied else (None, True)
    if case.wrongful:
        await grieve(ctx, case, accused, punishment)
        tally.wrongful += 1
    tally.convicted += 1
    ctx.count(f"sentence.{case.crime.value}")


async def tamper(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> None:
    for row in await witnesses_of(ctx, case.id):
        if row.locked or row.testimony is Deposition.SHIELDS or held(row.witness_entity_id):
            continue
        hook = await hook_on(ctx, accused.id, row.witness_entity_id)
        if hook is not None and await use_hook(ctx, hook, HookDemand.SUPPORT):
            row.testimony = Deposition.SHIELDS
            ctx.count("case_witness_turned")


async def try_case(ctx: TickContext, case: CrimeCaseRow, laws: LawBook, tally: TrialTally) -> None:
    accused = await living_entity(ctx.session, case.accused_entity_id) if case.accused_entity_id is not None else None
    if accused is None or accused.location_id != case.settlement_entity_id:
        close(ctx, case, Verdict.FLED)
        tally.fled += 1
        if accused is not None:
            await declare_outlaw(ctx, accused, case.polity_entity_id)
        return
    await tamper(ctx, case, accused)
    await claimed_court(ctx, case, accused)
    await plead(ctx, case, accused)
    trial: TrialKind = case.trial or TrialKind.JUDGE
    guilty = erred(ctx, case, trial, await by_system(ctx, case, accused, await TRIALS[trial](ctx, case, accused)))
    tally.tried += 1
    await weigh_trial(ctx, trial, case.settlement_entity_id, case.polity_entity_id)
    if guilty:
        await convict(ctx, case, accused, laws, tally)
        if ctx.rng(f"trials.appeal.{case.id}").chance(TRIAL_SPECS[trial].appeal):
            await file_appeal(ctx, case, accused)
    else:
        close(ctx, case, Verdict.ACQUITTED)
        tally.acquitted += 1
    witnesses = await witnesses_of(ctx, case.id)
    steps = (
        StepDraft(StepAction.ACCUSE, actor=case.investigator_entity_id, target=accused.id),
        *(
            StepDraft(
                StepAction.TESTIFY,
                actor=row.witness_entity_id,
                target=accused.id,
                outcome=StepOutcome.SUCCESS
                if row.testimony is Deposition.ACCUSES
                else StepOutcome.REFUSED
                if row.testimony is Deposition.SHIELDS
                else StepOutcome.NO_EFFECT,
            )
            for row in witnesses
        ),
        StepDraft(StepAction.PLEAD, actor=accused.id),
        StepDraft(StepAction.JUDGE, actor=case.judge_entity_id, target=accused.id, outcome=StepOutcome.SUCCESS if guilty else StepOutcome.FAILURE),
        *((StepDraft(StepAction.SENTENCE, actor=case.judge_entity_id, target=accused.id),) if guilty else ()),
    )
    await record(
        ctx,
        f"trials.{'condemned' if guilty else 'acquitted'}_{trial.value}",
        roles={
            IncidentRole.ACCUSED: accused.id,
            IncidentRole.JUDGE: case.judge_entity_id,
            IncidentRole.ADVOCATE: case.advocate_entity_id,
            IncidentRole.WITNESS: [row.witness_entity_id for row in witnesses],
            IncidentRole.AUTHORITY: case.polity_entity_id,
        },
        facts={"crime": case.crime, "evidence": case.evidence},
        steps=steps,
        place=case.settlement_entity_id,
    )


def case_held(case: CrimeCaseRow) -> bool:
    return any(node is not None and held(node) for node in (case.settlement_entity_id, case.accused_entity_id, case.judge_entity_id, case.polity_entity_id))


async def tend_cases(ctx: TickContext, tally: TrialTally) -> None:
    rows = await ctx.session.scalars(
        select(CrimeCaseRow).where(CrimeCaseRow.stage == CaseStage.TRIAL, CrimeCaseRow.opened_epoch < ctx.epoch).order_by(CrimeCaseRow.id)
    )
    laws = await LawBook.load(ctx.session)
    for case in list(rows):
        if VERDICT in (case.locked or []) or case_held(case) or case.opened_epoch + TRIAL_SPECS[case.trial or TrialKind.JUDGE].delay >= ctx.epoch:
            continue
        await try_case(ctx, case, laws, tally)


async def injustices(ctx: TickContext, member_id: int) -> int:
    since = ctx.epoch - ctx.rules.trials.injustice_epochs
    found = await ctx.session.scalar(
        select(func.count(CrimeCaseRow.id)).where(
            CrimeCaseRow.settlement_entity_id == member_id, CrimeCaseRow.wrongful.is_(True), CrimeCaseRow.closed_epoch >= since
        )
    )
    return int(found or 0)


async def accuse_case(ctx: TickContext, accuser: EntityRow, accused: EntityRow, crime: CrimeKind) -> CrimeCaseRow | None:
    town_id = accused.location_id
    if town_id is None or held(accused.id) or not await is_city(ctx, town_id):
        return None
    laws = await LawBook.load(ctx.session)
    guilty = any(row.id == accused.id for row in (await offenders(ctx, town_id, laws))[crime])
    polity = laws.member_of.get(town_id)
    investigator = await investigator_for(ctx, polity, town_id)
    judge = await judge_for(ctx, polity, town_id)
    trial = await trial_for(ctx, town_id)
    case = CrimeCaseRow(
        settlement_entity_id=town_id,
        polity_entity_id=polity,
        crime=crime,
        culprit_entity_id=accused.id if guilty else None,
        accused_entity_id=accused.id,
        investigator_entity_id=investigator.id if investigator is not None else None,
        judge_entity_id=judge.id if judge is not None else None,
        stage=CaseStage.TRIAL,
        trial=trial,
        opened_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(case)
    await ctx.session.flush()
    ctx.session.add(
        CaseWitnessRow(case_id=case.id, witness_entity_id=accuser.id, testimony=Deposition.ACCUSES, reliability=ctx.rules.trials.witness_reliability)
    )
    await ctx.session.flush()
    folk = [row for row in await townsfolk(ctx, town_id, besides={accused.id, accuser.id}) if not held(row.id)]
    for witness in ctx.rng(f"trials.accuse.{case.id}").sample(folk, min(len(folk), ctx.rules.trials.witnesses)):
        testimony, reliability = await testimony_of(ctx, case, witness, accused.id)
        if not guilty and testimony is Deposition.ACCUSES:
            testimony = Deposition.SILENT
        ctx.session.add(CaseWitnessRow(case_id=case.id, witness_entity_id=witness.id, testimony=testimony, reliability=reliability))
    await ctx.session.flush()
    case.evidence = await weigh(ctx, case, accused.id, investigator)
    return case
