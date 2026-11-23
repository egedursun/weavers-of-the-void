from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.laws import PENALTY_CRUELTY
from aerona.db.tables.dominion import DominionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import (
    AppealRow,
    DefectionRow,
    JurisdictionRow,
    LegalSystemRow,
    MoleHuntRow,
    OutlawRow,
    PardonRow,
    PrecedentRow,
    PrisonerRow,
    RegistryRow,
    SpyCellRow,
)
from aerona.db.tables.military import SpyAgentRow, SpyNetworkRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.mythic import ServitorRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.justice import CaseStage, TrialKind, Verdict
from aerona.domain.enums.law_depth import CourtLevel, JurisdictionClaim, KillMethod, LegalSystem, MoleHuntOutcome, RecruitMotive, RegistryKind
from aerona.domain.enums.military import AgentStatus, SpyCover, SpyOwnerKind
from aerona.domain.enums.mind import MemoryKind, SkillKind, SkillSource, TraitKind, TraitSource
from aerona.domain.enums.mortal import CrimeKind, PunishmentKind
from aerona.domain.enums.mythic import ServitorRole
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import CultStats, PolityStats, SpiritStats, StructureStats
from aerona.engine.context import TickContext
from aerona.engine.demography.mobility import debtors_prison
from aerona.engine.law.appeals import AppealTally, file_appeal, hear_appeals
from aerona.engine.law.jurisdictions import claimed_court
from aerona.engine.law.outlawry import OutlawTally, hunt_outlaws
from aerona.engine.law.pardons import PardonTally, declare_amnesty, grant_pardon
from aerona.engine.law.prisons import PrisonTally, keep_prisons
from aerona.engine.law.registries import RegistryTally, enforce
from aerona.engine.law.systems import SystemTally, adopt_systems, by_system, system_for_case
from aerona.engine.military.forensics import examine
from aerona.engine.military.mole_hunts import MoleTally, hunt
from aerona.engine.military.spy_depth import CellTally, compromise, defect, loyalty_for, motive_for, organise
from aerona.engine.mind.book import add_trait, set_skill, skill_level
from aerona.engine.mortal.justice import CODE_PUNISHMENTS, cruelty_of, sentence
from aerona.engine.mythic.divine_spies import DivineSpyTally, spy_for_gods
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.trials import TrialTally, try_case
from aerona.engine.primitives.manual import manual_context
from aerona.services.integrity.law_links import mend_law_links
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def context(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "law", rules=tuned_rules(**namespaces))


async def realm_of(session: AsyncSession, world: CoreWorld, town: EntityRow, *, religion: int | None = None) -> EntityRow:
    polity = await entity(session, f"Crown of {town.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            capital_entity_id=town.id,
            state_religion_id=religion,
            stability=100,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    return polity


async def rich(session: AsyncSession, someone: EntityRow, wealth: int = 100) -> None:
    session.add(MortalProfileRow(entity_id=someone.id, wealth=wealth, locked=[]))
    await session.flush()


def case_for(town: EntityRow, polity: EntityRow | None, accused: EntityRow, *, evidence: int = 50, culprit: EntityRow | None = None) -> CrimeCaseRow:
    return CrimeCaseRow(
        settlement_entity_id=town.id,
        polity_entity_id=polity.id if polity is not None else None,
        crime=CrimeKind.THEFT,
        accused_entity_id=accused.id,
        culprit_entity_id=(culprit or accused).id,
        stage=CaseStage.TRIAL,
        trial=TrialKind.JUDGE,
        evidence=evidence,
        locked=[],
    )


async def test_realms_take_the_system_their_faith_favours(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    plain = await realm_of(session, world, town)
    church = await entity(session, "The Church", EntityType.CULT, CultStats(), world_id=world.world.id)
    other = await settlement(session, "Brook", world, world.regions[0])
    sacred = await realm_of(session, world, other, religion=church.id)
    await adopt_systems(ctx, SystemTally())
    assert (await session.get(LegalSystemRow, plain.id)).system is LegalSystem.CUSTOMARY
    assert (await session.get(LegalSystemRow, sacred.id)).system is LegalSystem.RELIGIOUS


async def test_friends_who_swear_acquit_under_custom_but_not_under_a_code(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, legal_systems={"compurgator_weight": 40}, trials={"standard": 50, "friend_at": 10})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    accused = await mortal(session, "Ilse", world, town.id)
    friend = await mortal(session, "Oren", world, town.id)
    session.add(RelationshipRow(holder_node_id=friend.id, subject_node_id=accused.id, friendship=80, since_epoch=0, last_epoch=0))
    case = case_for(town, polity, accused, evidence=60)
    session.add_all([case, LegalSystemRow(holder_entity_id=polity.id, system=LegalSystem.CUSTOMARY, since_epoch=0, locked=[])])
    await session.flush()
    assert not await by_system(ctx, case, accused, True)
    (await session.get(LegalSystemRow, polity.id)).system = LegalSystem.CODIFIED
    assert await by_system(ctx, case, accused, False)


async def test_case_law_is_set_down_and_then_followed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, legal_systems={"follow_pct": 100})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    accused = await mortal(session, "Ilse", world, town.id)
    session.add(LegalSystemRow(holder_entity_id=polity.id, system=LegalSystem.PRECEDENT, since_epoch=0, locked=[]))
    first = case_for(town, polity, accused)
    session.add(first)
    await session.flush()
    assert not await by_system(ctx, first, accused, False)
    ruling = await session.scalar(select(PrecedentRow).where(PrecedentRow.holder_entity_id == polity.id))
    assert ruling is not None and ruling.verdict is Verdict.ACQUITTED
    ruling.authority = 100
    second = case_for(town, polity, accused, evidence=100)
    session.add(second)
    await session.flush()
    assert not await by_system(ctx, second, accused, True)


async def test_the_oracle_speaks_the_answer_its_god_gave(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    accused = await mortal(session, "Ilse", world, town.id)
    session.add(LegalSystemRow(holder_entity_id=polity.id, system=LegalSystem.ORACLE, since_epoch=0, locked=[]))
    case = case_for(town, polity, accused)
    case.oracle_answer = Verdict.ACQUITTED
    session.add(case)
    await session.flush()
    assert not await by_system(ctx, case, accused, True)


async def test_an_appeal_climbs_a_court_for_its_fee_and_frees_the_reversed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, appeals={"reversal_pct": 100, "evidence_pct": 0, "delay_years": 0})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    accused = await mortal(session, "Ilse", world, town.id)
    governor = await mortal(session, "Oren", world, town.id)
    session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.GOVERNOR, holder_entity_id=governor.id))
    await rich(session, accused)
    case = case_for(town, polity, accused)
    case.stage, case.verdict = CaseStage.CLOSED, Verdict.GUILTY
    session.add(case)
    await session.flush()
    session.add(PrisonerRow(mortal_entity_id=accused.id, prison_entity_id=town.id, case_id=case.id, term=3, gang_rank=0, since_epoch=0, locked=[]))
    appeal = await file_appeal(ctx, case, accused)
    assert appeal is not None and appeal.to_court is CourtLevel.PROVINCIAL
    assert (await session.get(MortalProfileRow, accused.id)).wealth < 100
    appeal.filed_epoch = ctx.epoch - 1
    tally = AppealTally()
    await hear_appeals(ctx, tally)
    assert tally.reversed == 1 and case.verdict is Verdict.ACQUITTED and case.court is CourtLevel.PROVINCIAL
    assert await session.get(PrisonerRow, accused.id) is None


async def test_without_a_higher_court_no_appeal_is_filed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    accused = await mortal(session, "Ilse", world, town.id)
    await rich(session, accused)
    case = case_for(town, polity, accused)
    case.verdict = Verdict.GUILTY
    session.add(case)
    await session.flush()
    assert await file_appeal(ctx, case, accused) is None
    assert await session.get(AppealRow, case.id) is None


async def test_a_registered_debt_is_paid_through_the_courts_until_settled(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, registries={"enforce_pct": 100, "unregistered_pct": 100})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    lender = await mortal(session, "Ilse", world, town.id, strength=90)
    debtor = await mortal(session, "Oren", world, town.id, strength=10)
    await rich(session, debtor)
    row = RegistryRow(
        holder_entity_id=polity.id,
        kind=RegistryKind.DEBT,
        owner_entity_id=lender.id,
        counterparty_entity_id=debtor.id,
        amount=ctx.rules.taxation.wealth_per_treasury,
        registered_epoch=ctx.epoch - 1,
        locked=[],
    )
    session.add(row)
    await session.flush()
    tally = RegistryTally()
    await enforce(ctx, tally)
    assert tally.settled == 1
    assert (await session.get(MortalProfileRow, lender.id)).wealth > 0


async def test_a_claimant_court_spares_its_own_and_takes_faith_cases(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, jurisdictions={"leniency": 50}, courts={"religious_bias": 0})
    town = await settlement(session, "Ashby", world, world.regions[0])
    church = await entity(session, "The Church", EntityType.CULT, CultStats(), world_id=world.world.id)
    polity = await realm_of(session, world, town, religion=church.id)
    priest = await mortal(session, "Ilse", world, town.id)
    priest.affiliated_entity_id = church.id
    session.add(
        JurisdictionRow(holder_entity_id=polity.id, claimant_entity_id=church.id, claim=JurisdictionClaim.CLERGY, strength=100, since_epoch=0, locked=[])
    )
    case = case_for(town, polity, priest, evidence=80)
    session.add(case)
    await session.flush()
    await claimed_court(ctx, case, priest)
    assert case.evidence == 30 and case.court is CourtLevel.RELIGIOUS


async def test_a_ruler_who_pardons_a_friend_is_read_as_corrupt_and_an_amnesty_frees_all(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, pardons={"friend_at": 10})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    ruler = await mortal(session, "Ilse", world, town.id)
    friend = await mortal(session, "Oren", world, town.id)
    other = await mortal(session, "Pell", world, town.id)
    session.add(RelationshipRow(holder_node_id=ruler.id, subject_node_id=friend.id, friendship=80, since_epoch=0, last_epoch=0))
    session.add_all(
        [
            OutlawRow(mortal_entity_id=friend.id, polity_entity_id=polity.id, bounty=10, renown=0, declared_epoch=0, locked=[]),
            OutlawRow(mortal_entity_id=other.id, polity_entity_id=polity.id, bounty=10, renown=0, declared_epoch=0, locked=[]),
        ]
    )
    await session.flush()
    pardon = await grant_pardon(ctx, ruler, friend, polity_id=polity.id, case_id=None)
    assert pardon.corrupt and (await session.get(PolityProfileRow, polity.id)).corruption > 0
    assert await session.get(OutlawRow, friend.id) is None
    assert await declare_amnesty(ctx, polity.id, ruler) == 1
    assert await session.get(OutlawRow, other.id) is None
    assert await session.scalar(select(PardonRow.id).where(PardonRow.amnesty.is_(True))) is not None
    assert PardonTally().amnesties == 0


async def test_who_flees_the_court_is_outlawed_and_hunted_for_the_bounty(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, outlaws={"hunt_pct": 100, "hunter_skill": 1})
    town = await settlement(session, "Ashby", world, world.regions[0])
    elsewhere = await settlement(session, "Brook", world, world.regions[0])
    polity = await realm_of(session, world, town)
    polity_row = await session.get(PolityProfileRow, polity.id)
    polity_row.treasury = 500
    fled = await mortal(session, "Ilse", world, elsewhere.id)
    hunter = await mortal(session, "Oren", world, town.id)
    await set_skill(session, hunter.id, SkillKind.TRACKING, 80, epoch=0, source=SkillSource.PLAYER)
    case = case_for(town, polity, fled)
    session.add(case)
    await session.flush()
    await try_case(ctx, case, await LawBook.load(session), TrialTally())
    outlaw = await session.get(OutlawRow, fled.id)
    assert case.verdict is Verdict.FLED and outlaw is not None
    fled.location_id = town.id
    outlaw.declared_epoch = ctx.epoch - 1
    tally = OutlawTally()
    await hunt_outlaws(ctx, tally)
    assert tally.caught == 1 and await session.get(OutlawRow, fled.id) is None
    assert polity_row.treasury < 500


async def prison_in(session: AsyncSession, world: CoreWorld, town: EntityRow) -> EntityRow:
    jail = await entity(session, "The Keep", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=jail.id, kind=StructureKind.PRISON, host_entity_id=town.id))
    await session.flush()
    return jail


async def test_a_prison_sentence_is_served_learning_intrigue_and_leaves_a_stigma(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, prisons={"term_years": 50, "escape_pct": 0, "intrigue_gain": 10})
    town = await settlement(session, "Ashby", world, world.regions[0])
    await prison_in(session, world, town)
    convict = await mortal(session, "Ilse", world, town.id)
    assert await sentence(ctx, convict, CrimeKind.THEFT, PunishmentKind.IMPRISONMENT)
    row = await session.get(PrisonerRow, convict.id)
    assert row is not None
    row.since_epoch = ctx.epoch - 1
    tally = PrisonTally()
    await keep_prisons(ctx, tally)
    assert tally.released == 1 and await session.get(PrisonerRow, convict.id) is None
    assert await skill_level(session, convict.id, SkillKind.INTRIGUE) == 10
    assert (await session.get(MortalProfileRow, convict.id)).infamy > 0


async def test_with_no_prison_a_prison_sentence_becomes_a_fine(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    convict = await mortal(session, "Ilse", world, town.id)
    assert await sentence(ctx, convict, CrimeKind.THEFT, PunishmentKind.IMPRISONMENT)
    assert await session.get(PrisonerRow, convict.id) is None


async def test_a_crowded_prison_breeds_escapes_and_the_escaped_are_outlawed(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, prisons={"escape_pct": 100, "capacity": 1})
    town = await settlement(session, "Ashby", world, world.regions[0])
    await realm_of(session, world, town)
    jail = await prison_in(session, world, town)
    convicts = [await mortal(session, name, world, town.id, strength=100) for name in ("Ilse", "Oren", "Pell")]
    for convict in convicts:
        session.add(PrisonerRow(mortal_entity_id=convict.id, prison_entity_id=jail.id, term=9, gang_rank=100, since_epoch=0, locked=[]))
    await session.flush()
    tally = PrisonTally()
    await keep_prisons(ctx, tally)
    assert tally.escaped >= 1
    assert await session.scalar(select(OutlawRow.mortal_entity_id).limit(1)) is not None


async def network_on(session: AsyncSession, owner: EntityRow, target: EntityRow) -> SpyNetworkRow:
    row = SpyNetworkRow(
        owner_entity_id=owner.id, owner_kind=SpyOwnerKind.POLITY, target_entity_id=target.id, cover=SpyCover.ENVOY, agent_ids=[], since_epoch=0, locked=[]
    )
    session.add(row)
    await session.flush()
    return row


async def test_recruits_join_for_money_or_pride_and_loyalty_follows_the_motive(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    network = await network_on(session, polity, town)
    greedy = await mortal(session, "Ilse", world, town.id)
    proud = await mortal(session, "Oren", world, town.id)
    await add_trait(session, greedy.id, TraitKind.GREEDY, TraitSource.BIRTH, 0)
    await add_trait(session, proud.id, TraitKind.PROUD, TraitSource.BIRTH, 0)
    assert await motive_for(ctx, network, greedy) is RecruitMotive.MONEY
    assert await motive_for(ctx, network, proud) is RecruitMotive.EGO
    assert loyalty_for(ctx, RecruitMotive.IDEOLOGY) > loyalty_for(ctx, RecruitMotive.MONEY)


async def test_a_caught_agent_exposes_only_their_cell(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, spy_depth={"cell_size": 2, "cell_exposure": 30, "safe_house_relief": 0})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    network = await network_on(session, polity, town)
    agents = []
    for index in range(4):
        spy = await mortal(session, f"Agent {index}", world, town.id)
        row = SpyAgentRow(network_id=network.id, mortal_entity_id=spy.id, cover=SpyCover.ENVOY, status=AgentStatus.ACTIVE, since_epoch=0, locked=[])
        session.add(row)
        agents.append(row)
    await session.flush()
    await organise(ctx, network, CellTally())
    cells = list(await session.scalars(select(SpyCellRow).where(SpyCellRow.network_id == network.id)))
    assert len(cells) == 2
    caught = agents[0]
    await compromise(ctx, network, caught)
    mates = [row for row in agents[1:] if row.cell_id == caught.cell_id]
    strangers = [row for row in agents[1:] if row.cell_id != caught.cell_id]
    assert all(row.exposure == 30 for row in mates) and all(row.exposure == 0 for row in strangers)


async def test_a_paranoid_hunt_purges_or_drives_an_innocent_to_defect(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, mole_hunts={"false_pct": 100, "defect_pct": 100}, pardons={"friend_at": 100})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    rival = await realm_of(session, world, await settlement(session, "Brook", world, world.regions[0]))
    await network_on(session, rival, polity)
    spymaster = await mortal(session, "Ilse", world, town.id)
    official = await mortal(session, "Oren", world, town.id)
    session.add_all(
        [
            OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.SPYMASTER, holder_entity_id=spymaster.id),
            OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.TREASURER, holder_entity_id=official.id),
            SecretRow(holder_node_id=polity.id, kind=next(iter(IntrigueSecret)), severity=60, known_by=[], locked=[]),
        ]
    )
    await session.flush()
    tally = MoleTally()
    await hunt(ctx, polity.id, spymaster, tally, forced=True)
    hunted = await session.scalar(select(MoleHuntRow))
    assert tally.defected == 1 and hunted is not None and hunted.outcome is MoleHuntOutcome.DEFECTED and not hunted.mole
    defection = await session.scalar(select(DefectionRow))
    assert defection is not None and defection.to_entity_id == rival.id and defection.secrets == 1


async def test_a_blade_is_always_seen_and_a_curse_can_pass_unseen(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, forensics={"curse_stealth": 100, "theory_bonus": 0})
    town = await settlement(session, "Ashby", world, world.regions[0])
    victim = await mortal(session, "Ilse", world, town.id)
    assert (await examine(ctx, victim, None, KillMethod.BLADE)).recognised
    assert not (await examine(ctx, victim, None, KillMethod.CURSE)).recognised


async def test_a_spying_servitor_brings_secrets_unless_another_god_guards_the_place(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, divine_spies={"spy_pct": 100, "ward_pct": 100})
    town = await settlement(session, "Ashby", world, world.regions[0])
    keeper = await mortal(session, "Ilse", world, town.id)
    secret = SecretRow(holder_node_id=keeper.id, kind=next(iter(IntrigueSecret)), severity=50, known_by=[], locked=[])
    spirit = await entity(session, "Whisper", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id)
    session.add_all(
        [
            secret,
            ServitorRow(spirit_entity_id=spirit.id, god_node_id=world.son.id, role=ServitorRole.SPY, post_entity_id=town.id, loyalty=80, locked=[]),
            DominionRow(god_node_id=world.son.id, region_entity_id=world.regions[0].id, strength=100, locked=[]),
        ]
    )
    await session.flush()
    tally = DivineSpyTally()
    await spy_for_gods(ctx, tally)
    assert tally.learned == 1 and world.son.id in secret.known_by


async def test_integrity_frees_prisoners_whose_prison_is_gone(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ashby", world, world.regions[0])
    convict = await mortal(session, "Ilse", world, town.id)
    session.add(PrisonerRow(mortal_entity_id=convict.id, prison_entity_id=town.id, term=3, gang_rank=0, since_epoch=0, locked=[]))
    await session.flush()
    assert await mend_law_links(session) == 1
    assert await session.get(PrisonerRow, convict.id) is None


async def test_a_realm_with_no_system_yet_keeps_the_verdict_of_its_trial(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    accused = await mortal(session, "Ilse", world, town.id)
    case = case_for(town, polity, accused, evidence=0)
    session.add(case)
    await session.flush()
    assert await by_system(ctx, case, accused, True)
    assert not await by_system(ctx, case, accused, False)


async def test_a_town_judges_by_its_own_system_and_faith_courts_by_the_church(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    church = await entity(session, "The Church", EntityType.CULT, CultStats(), world_id=world.world.id)
    polity = await realm_of(session, world, town, religion=church.id)
    accused = await mortal(session, "Ilse", world, town.id)
    session.add_all(
        [
            LegalSystemRow(holder_entity_id=polity.id, system=LegalSystem.CODIFIED, since_epoch=0, locked=[]),
            LegalSystemRow(holder_entity_id=town.id, system=LegalSystem.ORACLE, since_epoch=0, locked=[]),
        ]
    )
    case = case_for(town, polity, accused)
    session.add(case)
    await session.flush()
    assert await system_for_case(session, case) is LegalSystem.ORACLE
    case.court = CourtLevel.RELIGIOUS
    assert await system_for_case(session, case) is LegalSystem.RELIGIOUS
    await adopt_systems(ctx, SystemTally())
    assert (await session.get(LegalSystemRow, church.id)).system is LegalSystem.RELIGIOUS


async def test_a_prisoner_who_leaves_the_town_of_the_prison_has_escaped(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, prisons={"escape_pct": 0})
    town = await settlement(session, "Ashby", world, world.regions[0])
    away = await settlement(session, "Brook", world, world.regions[0])
    await realm_of(session, world, town)
    jail = await prison_in(session, world, town)
    convict = await mortal(session, "Ilse", world, away.id)
    session.add(PrisonerRow(mortal_entity_id=convict.id, prison_entity_id=jail.id, term=5, gang_rank=0, since_epoch=0, locked=[]))
    await session.flush()
    tally = PrisonTally()
    await keep_prisons(ctx, tally)
    assert tally.escaped == 1 and await session.get(OutlawRow, convict.id) is not None


async def test_a_defector_is_protected_only_by_a_side_with_a_spymaster(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    home = await realm_of(session, world, town)
    guarded = await realm_of(session, world, await settlement(session, "Brook", world, world.regions[0]))
    open_side = await realm_of(session, world, await settlement(session, "Dale", world, world.regions[0]))
    keeper = await mortal(session, "Pell", world, town.id)
    session.add(OfficeRow(polity_entity_id=guarded.id, kind=OfficeKind.SPYMASTER, holder_entity_id=keeper.id))
    await session.flush()
    first = await defect(ctx, await mortal(session, "Ilse", world, town.id), home.id, guarded.id)
    second = await defect(ctx, await mortal(session, "Oren", world, town.id), home.id, open_side.id)
    assert first is not None and first.protected and second is not None and not second.protected


async def test_one_in_registered_debt_is_recruited_for_money(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    network = await network_on(session, polity, town)
    debtor = await mortal(session, "Ilse", world, town.id)
    await add_trait(session, debtor.id, TraitKind.PROUD, TraitSource.BIRTH, 0)
    session.add(RegistryRow(holder_entity_id=polity.id, kind=RegistryKind.DEBT, counterparty_entity_id=debtor.id, amount=10, registered_epoch=0, locked=[]))
    await session.flush()
    assert await motive_for(ctx, network, debtor) is RecruitMotive.MONEY


async def test_killing_an_outlaw_for_the_bounty_is_no_murder(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, outlaws={"hunt_pct": 100, "hunter_skill": 1})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    outlaw = await mortal(session, "Ilse", world, town.id)
    hunter = await mortal(session, "Oren", world, town.id)
    await set_skill(session, hunter.id, SkillKind.TRACKING, 80, epoch=0, source=SkillSource.PLAYER)
    session.add(OutlawRow(mortal_entity_id=outlaw.id, polity_entity_id=polity.id, bounty=0, renown=0, declared_epoch=0, locked=[]))
    await session.flush()
    await hunt_outlaws(ctx, OutlawTally())
    assert outlaw.status is not EntityStatus.CANON
    blamed = await session.scalar(select(MemoryRow.id).where(MemoryRow.kind == MemoryKind.KILLED_KIN, MemoryRow.subject_node_id == hunter.id))
    assert blamed is None


async def test_a_debtor_goes_to_the_town_prison_when_one_stands(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    await prison_in(session, world, town)
    lender = await mortal(session, "Ilse", world, town.id)
    debtor = await mortal(session, "Oren", world, town.id)
    await debtors_prison(ctx, lender, debtor)
    assert await session.get(PrisonerRow, debtor.id) is not None


def test_every_punishment_a_code_can_choose_has_its_cruelty() -> None:
    assert {kind: cruelty_of(kind) for kind in CODE_PUNISHMENTS.values()} == {
        kind: PENALTY_CRUELTY[name] for name, kind in reversed(list(CODE_PUNISHMENTS.items()))
    } | {PunishmentKind.FINE: PENALTY_CRUELTY["fine"]}
    assert cruelty_of(PunishmentKind.EYES) == PENALTY_CRUELTY["blinding"] and cruelty_of(PunishmentKind.PUBLIC_SHAMING) == PENALTY_CRUELTY["pillory"]
