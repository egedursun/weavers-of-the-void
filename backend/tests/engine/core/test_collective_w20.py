from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.collective_lines import mortal_collective_lines, son_collective_lines
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.collective import (
    AccountRow,
    AccountStanceRow,
    ArmsRow,
    ComponentWearRow,
    CrowdMoodRow,
    DatingSystemRow,
    DemographicTransitionRow,
    DesignComponentRow,
    DiasporaRow,
    FoundingMythRow,
    GenerationRow,
    LearningEventRow,
    LostLandRow,
    MemoryStrikeRow,
    MobRow,
    MovementRow,
    NormChangeRow,
    RoleNormRow,
    SexRatioRow,
    SocialNormRow,
    StoryletRunRow,
)
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.mind import CultureValueRow, PersonalityValueRow
from aerona.db.tables.mortal import MarriageRow, MortalProfileRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, HouseProfileRow, OfficeRow, PolityMemberRow, PolityProfileRow, PolityTerritoryRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import CasusBelliRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.collective import (
    AccountKind,
    AccountStance,
    CascadeOutcome,
    CollectiveActKind,
    CollectiveTrigger,
    CrowdFeeling,
    DatingSystemKind,
    DesignComponentKind,
    DesignKind,
    HeraldicCharge,
    HeraldicDivision,
    HeraldryHolderKind,
    MobEnd,
    MobStatus,
    MobTarget,
    NormBehaviour,
    NormSituation,
    RoleEligibility,
    RoleKind,
    StoryletId,
    StoryletRole,
    StoryletStatus,
)
from aerona.domain.enums.demography import AgeBand, CohortCondition, SexKind
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.mind import EthicalStance, ValueAxis
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.domain.models.entity_stats import HouseStats, MortalStats, PeopleStats, PolityStats, VesselStats
from aerona.engine.collective.accounts import (
    HistoryTally,
    believe_myths,
    debunk,
    distance_from_truth,
    fade_struck,
    find_scandals,
    press_lost_lands,
    record,
    remember_loss,
    rewrite_reigns,
    write_accounts,
)
from aerona.engine.collective.book import population_of
from aerona.engine.collective.control import edit_arms, set_norm
from aerona.engine.collective.crowds import CrowdTally, cascade, crowd_for, mood_of, rage_mobs, ready_to_arm, spark, state_triggers
from aerona.engine.collective.dating import render_date
from aerona.engine.collective.demography import DemographyTally, fertility_factor, measure
from aerona.engine.collective.designs import DesignTally, design_power, draw_design, frame_sizes, mend, wear_leg
from aerona.engine.collective.feelings import feelings_of, set_feeling
from aerona.engine.collective.generations import GenerationTally, keep_generations
from aerona.engine.collective.heraldry import HeraldryTally, grant_arms, invent, quarter_on_marriage, signature, signature_of
from aerona.engine.collective.learning import LearningTally, learn_socially
from aerona.engine.collective.norms import NormTally, keep_norms, stance_in, volition
from aerona.engine.collective.roles import allowed_heirs, combat_sexes
from aerona.engine.collective.storylets import StoryletTally, begin, cast_hoarded_store, settle_due
from aerona.engine.context import TickContext
from aerona.engine.phases.collective import ArmedTally, arm_movements
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules
from aerona.services.integrity.collective_links import mend_collective_links
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules


async def context(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "collective", rules=tuned_rules(**namespaces))


async def town_of(session: AsyncSession, world: CoreWorld, name: str = "Ashby", *, militia: int = 0, population: int = 2000) -> EntityRow:
    town = await settlement(session, name, world, world.regions[0], population=population)
    session.add(
        SettlementProfileRow(
            settlement_entity_id=town.id, size_tier=SizeTier.TOWN, treasury=500, unrest=20, crime=10, militia=militia, locked=[], foreigners={}
        )
    )
    await session.flush()
    return town


async def realm_of(session: AsyncSession, world: CoreWorld, town: EntityRow, ruler: EntityRow | None = None) -> EntityRow:
    polity = await entity(session, f"Crown of {town.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            capital_entity_id=town.id,
            legitimacy=50,
            stability=50,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    if ruler is not None:
        session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, since_epoch=0, locked=[]))
    await session.flush()
    return polity


async def values(session: AsyncSession, holder: EntityRow, **axes: int) -> None:
    for axis, value in axes.items():
        session.add(CultureValueRow(entity_id=holder.id, axis=ValueAxis(axis), value=value))
    await session.flush()


async def personal(session: AsyncSession, holder: EntityRow, **axes: int) -> None:
    for axis, value in axes.items():
        session.add(PersonalityValueRow(node_id=holder.id, axis=ValueAxis(axis), value=value))
    await session.flush()


async def homeland(session: AsyncSession, people: EntityRow, town: EntityRow) -> None:
    await BondRepository(session).connect(BondDraft(people.id, town.id, BondKind.LIVES_IN, 0, role=BondRole.HOMELAND))
    await session.flush()


async def house_with(session: AsyncSession, world: CoreWorld, name: str, member: EntityRow, *, parent: int | None = None) -> EntityRow:
    house = await entity(session, name, EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    session.add(HouseProfileRow(house_entity_id=house.id, parent_house_id=parent, emblem={}, traits=[], seats=[], locked=[]))
    session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=member.id, joined_epoch=0, by_marriage=False))
    await session.flush()
    return house


async def test_cascades_are_reproducible_and_deterrence_raises_thresholds(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, collective={"riot_threshold": 40})
    town = await town_of(session, world)
    mood = await mood_of(ctx, town.id)
    mood.deterrence = 0
    await set_feeling(session, town.id, CrowdFeeling.ANGER, 90, hold=None)
    first = cascade(ctx, crowd_for(ctx, mood, await feelings_of(session, town.id), CollectiveActKind.RIOT, 0.2), ctx.rng("same"))
    again = cascade(ctx, crowd_for(ctx, mood, await feelings_of(session, town.id), CollectiveActKind.RIOT, 0.2), ctx.rng("same"))
    assert first == again
    mood.deterrence = 100
    guarded = cascade(ctx, crowd_for(ctx, mood, await feelings_of(session, town.id), CollectiveActKind.RIOT, 0.2), ctx.rng("same"))
    assert first > ctx.rules.collective_behaviour.mob_share > guarded


async def test_with_the_default_rules_a_furious_town_can_riot_and_a_calm_one_does_not(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_of(session, world)
    mood = await mood_of(ctx, town.id)
    mood.deterrence = 0
    await set_feeling(session, town.id, CrowdFeeling.ANGER, 0, hold=None)
    calm = [cascade(ctx, crowd_for(ctx, mood, await feelings_of(session, town.id), CollectiveActKind.RIOT, 0.2), ctx.rng(f"calm.{seed}")) for seed in range(20)]
    await set_feeling(session, town.id, CrowdFeeling.ANGER, 95, hold=None)
    furious = [
        cascade(ctx, crowd_for(ctx, mood, await feelings_of(session, town.id), CollectiveActKind.RIOT, 0.2), ctx.rng(f"furious.{seed}")) for seed in range(20)
    ]
    mob = ctx.rules.collective_behaviour.mob_share
    assert max(calm) < mob
    assert sum(1 for share in furious if share >= mob) > len(furious) // 2


async def test_a_hungry_town_riots_storms_its_granary_and_is_broken_by_force(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, collective_behaviour={"movement_share": 101, "mob_share": 1, "force_pct": 100}, collective={"riot_threshold": 0})
    town = await town_of(session, world, militia=50000)
    session.add(CommunitySocietyRow(**society_defaults(town.id)))
    await session.flush()
    await mood_of(ctx, town.id)
    await set_feeling(session, town.id, CrowdFeeling.ANGER, 100, hold=None)
    row = await spark(ctx, town, CollectiveTrigger.FAMINE, CrowdTally(), forced=True)
    assert row is not None and row.outcome is CascadeOutcome.MOB
    mob = await session.scalar(select(MobRow).where(MobRow.cascade_id == row.id))
    assert mob is not None and mob.target is MobTarget.GRANARY
    await rage_mobs(ctx, CrowdTally())
    assert mob.status is MobStatus.DISPERSED and mob.ended_by is MobEnd.FORCE


def society_defaults(town_id: int) -> dict[str, object]:
    shares = {f"share_{item.value}": 0.1 for item in SocialClass}
    satisfaction = {f"satisfaction_{item.value}": 50 for item in SocialClass}
    return {
        "entity_id": town_id,
        **shares,
        **satisfaction,
        "stock_food": 0,
        "stock_ore": 0,
        "stock_goods": 0,
        "price_food": 300,
        "price_ore": 100,
        "price_goods": 100,
    }


async def test_a_large_town_with_full_stores_feels_no_famine_and_an_empty_one_does(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    full = await town_of(session, world, "Greatfold", population=5000)
    session.add(CommunitySocietyRow(**{**society_defaults(full.id), "stock_food": ctx.rules.economy.supply_index_epoch, "price_food": 100}))
    empty = await town_of(session, world, "Barrenfold", population=5000)
    session.add(CommunitySocietyRow(**{**society_defaults(empty.id), "price_food": 100}))
    await session.flush()
    full_profile = await session.get(SettlementProfileRow, full.id)
    empty_profile = await session.get(SettlementProfileRow, empty.id)
    assert full_profile is not None and empty_profile is not None
    assert CollectiveTrigger.FAMINE not in await state_triggers(ctx, full, full_profile)
    assert CollectiveTrigger.FAMINE in await state_triggers(ctx, empty, empty_profile)
    refilled = await session.get(CommunitySocietyRow, empty.id)
    assert refilled is not None
    refilled.stock_food = ctx.rules.economy.supply_index_epoch
    await realm_of(session, world, full, await mortal(session, "Ostra", world, full.id))
    assert await cast_hoarded_store(ctx, world.world.id) is None
    stores = await session.get(CommunitySocietyRow, full.id)
    assert stores is not None
    stores.stock_food = 0
    await session.flush()
    cast = await cast_hoarded_store(ctx, world.world.id)
    assert cast is not None and cast[StoryletRole.TOWN] == full.id


async def test_a_panic_sends_folk_fleeing_and_tramples_the_crowded(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, collective_behaviour={"mob_share": 1, "panic_flight_pct": 20, "trample_per_mille": 10}, collective={"panic_threshold": 0})
    town = await town_of(session, world, population=5000)
    await mood_of(ctx, town.id)
    await set_feeling(session, town.id, CrowdFeeling.FEAR, 100, hold=None)
    row = await spark(ctx, town, CollectiveTrigger.FIRE, CrowdTally(), forced=True)
    assert row is not None and row.outcome is CascadeOutcome.PANIC
    assert row.fled > 0 and row.deaths > 0
    assert stat_or(town, "population", 0) == 5000 - row.fled - row.deaths


async def test_a_strong_movement_takes_up_arms_as_rebels(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_of(session, world)
    session.add(
        MovementRow(
            settlement_entity_id=town.id, act=CollectiveActKind.RIOT, trigger=CollectiveTrigger.PRICE_SPIKE, members=300, strength=90, since_epoch=0, locked=[]
        )
    )
    await session.flush()
    assert len(await ready_to_arm(ctx)) == 1
    tally = ArmedTally()
    await arm_movements(ctx, tally)
    movement = await session.scalar(select(MovementRow))
    assert tally.revolts == 1 and movement.faction_entity_id is not None and movement.act is CollectiveActKind.REVOLT


async def test_norms_follow_values_and_volition_weighs_conformity_against_rebellion(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    people = await entity(session, "Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    await values(session, people, honour=100, kinship=100, mercy=60)
    await keep_norms(ctx, NormTally())
    norms = {
        (row.situation, row.behaviour): row.stance for row in await session.scalars(select(SocialNormRow).where(SocialNormRow.holder_entity_id == people.id))
    }
    insult = stance_in(norms, NormSituation.HOSPITALITY, NormBehaviour.INSULT)
    assert insult in {EthicalStance.SHAMEFUL, EthicalStance.UNTHINKABLE}
    conformist = volition(ctx.rules, insult, conformity=1.0, rebel=0.0)
    rebel = volition(ctx.rules, insult, conformity=-1.0, rebel=1.0)
    assert conformist < 1 < volition(ctx.rules, EthicalStance.REQUIRED, conformity=1.0, rebel=0.0)
    assert rebel > conformist


async def test_story_16_the_revised_king(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, historiography={"revise_pct": 100, "scandal_pct": 100, "strike_fade": 10})
    town = await town_of(session, world)
    old_king = await mortal(session, "Aldric", world, town.id)
    new_king = await mortal(session, "Brannoc", world, town.id)
    scholar = await mortal(session, "Ysolde", world, town.id)
    realm = await realm_of(session, world, town, old_king)
    for someone, education in ((old_king, 10), (new_king, 10), (scholar, 90)):
        session.add(MortalProfileRow(entity_id=someone.id, polity_id=realm.id, education=education, renown=60, locked=[]))
    await house_with(session, world, "House Aldric", old_king)
    await house_with(session, world, "House Brannoc", new_king)
    people = await entity(session, "Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    coronation = CollectionRow(kind=CollectionKind.CORONATION, name="The crowning of Aldric", world_id=world.world.id, start_epoch=ctx.epoch, locked=[])
    session.add(coronation)
    await session.flush()
    session.add_all([CollectionMemberRow(collection_id=coronation.id, node_id=old_king.id, role=CollectionRole.WINNER, since_epoch=0)])
    await session.flush()
    await write_accounts(ctx, HistoryTally())
    official = await session.scalar(select(AccountRow).where(AccountRow.holder_entity_id == realm.id, AccountRow.kind == AccountKind.OFFICIAL_CHRONICLE))
    assert official is not None
    assert (await session.get(AccountStanceRow, (official.id, old_king.id))).stance is AccountStance.GLORIFY
    folk = await record(ctx, people, AccountKind.FOLK_MEMORY, fidelity=50, stances={old_king.id: AccountStance.GLORIFY}, collection_id=coronation.id)
    assert folk is not None
    office = await session.scalar(select(OfficeRow).where(OfficeRow.polity_entity_id == realm.id))
    office.holder_entity_id, office.since_epoch = new_king.id, ctx.epoch
    await session.flush()
    tally = HistoryTally()
    await rewrite_reigns(ctx, tally)
    revision = await session.scalar(select(AccountRow).where(AccountRow.revised_from_id == official.id))
    assert tally.revisions == 1 and revision is not None
    assert (await session.get(AccountStanceRow, (revision.id, old_king.id))).stance in {AccountStance.VILIFY, AccountStance.OMIT}
    revised_stances = [row.stance for row in await session.scalars(select(AccountStanceRow).where(AccountStanceRow.account_id == revision.id))]
    original_stances = [row.stance for row in await session.scalars(select(AccountStanceRow).where(AccountStanceRow.account_id == official.id))]
    assert distance_from_truth(revision, revised_stances) > distance_from_truth(official, original_stances)
    assert (await session.get(MemoryStrikeRow, (old_king.id, realm.id))).active
    before = (await session.get(MortalProfileRow, old_king.id)).renown
    await fade_struck(ctx, tally)
    assert (await session.get(MortalProfileRow, old_king.id)).renown == before
    credence = revision.credence
    await find_scandals(ctx, tally)
    assert revision.credence < credence and tally.scandals == 1
    secret = await session.scalar(select(SecretRow).where(SecretRow.holder_node_id == scholar.id, SecretRow.kind == IntrigueSecret.TRUE_HISTORY))
    assert secret is not None
    rising = await session.scalar(select(MovementRow).where(MovementRow.settlement_entity_id == town.id))
    assert rising is not None and rising.trigger is CollectiveTrigger.RUMOUR
    claim = await session.scalar(select(ClaimRow).where(ClaimRow.polity_entity_id == realm.id, ClaimRow.claimant_entity_id == old_king.id))
    assert claim is not None


async def test_founding_myths_lend_legitimacy_until_debunked(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, historiography={"myth_legitimacy": 20, "scandal_pct": 0})
    town = await town_of(session, world)
    realm = await realm_of(session, world, town)
    await believe_myths(ctx, HistoryTally())
    myth = await session.get(FoundingMythRow, realm.id)
    profile = await session.get(PolityProfileRow, realm.id)
    myth.credence = 100
    before = profile.legitimacy
    await believe_myths(ctx, HistoryTally())
    assert profile.legitimacy > before
    lifted = profile.legitimacy
    await debunk(ctx, myth, realm, HistoryTally())
    assert profile.legitimacy < lifted and myth.debunked_epoch == ctx.epoch


async def test_a_remembered_lost_land_becomes_a_claim(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, historiography={"irredentist_claim_at": 50})
    first, second = await town_of(session, world, "Ashby"), await town_of(session, world, "Brook")
    loser, holder = await realm_of(session, world, first), await realm_of(session, world, second)
    session.add(PolityTerritoryRow(polity_entity_id=holder.id, region_entity_id=world.regions[0].id, control=80, locked=[]))
    await session.flush()
    await remember_loss(ctx, loser.id, world.regions[0].id)
    tally = HistoryTally()
    await press_lost_lands(ctx, tally)
    claim = await session.scalar(select(CasusBelliRow).where(CasusBelliRow.holder_entity_id == loser.id, CasusBelliRow.target_entity_id == holder.id))
    assert tally.claims == 1 and claim is not None
    assert (await session.get(LostLandRow, (loser.id, world.regions[0].id))).claimed_epoch == ctx.epoch


async def test_a_storylet_left_to_its_chooser_is_settled_by_their_values(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, storylets={"open_epochs": 0})
    town = await town_of(session, world)
    ruler = await mortal(session, "Mercia", world, town.id)
    realm = await realm_of(session, world, town, ruler)
    await personal(session, ruler, mercy=100, kinship=100, wealth=-100)
    run = await begin(ctx, StoryletId.HOARDED_STORE, world.world.id, {StoryletRole.TOWN: town.id, StoryletRole.RULER: ruler.id, StoryletRole.REALM: realm.id})
    assert run.status is StoryletStatus.OPEN and run.collection_id is not None
    tally = StoryletTally()
    await settle_due(ctx, tally)
    assert run.status is StoryletStatus.RESOLVED and run.choice == 0 and tally.by_personality == 1


async def test_a_choice_schedules_a_follow_up_in_the_same_chain(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, storylets={"open_epochs": 0})
    town = await town_of(session, world)
    ruler = await mortal(session, "Old", world, town.id)
    elder, younger = await mortal(session, "Elder", world, town.id), await mortal(session, "Younger", world, town.id)
    realm = await realm_of(session, world, town, ruler)
    await personal(session, ruler, tradition=-100, competition=100)
    cast = {StoryletRole.RULER: ruler.id, StoryletRole.REALM: realm.id, StoryletRole.ELDER_HEIR: elder.id, StoryletRole.YOUNGER_HEIR: younger.id}
    run = await begin(ctx, StoryletId.DYING_RULER, world.world.id, cast)
    await settle_due(ctx, StoryletTally())
    follow = await session.scalar(select(StoryletRunRow).where(StoryletRunRow.follows_run_id == run.id))
    assert run.choice == 1 and follow is not None and follow.step == 1 and follow.collection_id == run.collection_id


async def test_social_learning_copies_the_renowned_and_records_the_lesson(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, social_learning={"learners_pct": 100, "prestige_floor": 10})
    town = await town_of(session, world)
    people = await entity(session, "Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    await homeland(session, people, town)
    await values(session, people, hierarchy=100, tradition=-100, superstition=-100)
    star, learner = await mortal(session, "Famed", world, town.id), await mortal(session, "Plain", world, town.id)
    session.add_all([MortalProfileRow(entity_id=star.id, renown=90, locked=[]), MortalProfileRow(entity_id=learner.id, renown=0, locked=[])])
    await personal(session, star, martial=100)
    await personal(session, learner, martial=0)
    await learn_socially(ctx, LearningTally())
    lesson = await session.scalar(select(LearningEventRow).where(LearningEventRow.learner_entity_id == learner.id))
    assert lesson is not None and lesson.model_entity_id == star.id and lesson.shift > 0


async def test_a_generation_is_shaped_by_its_youth_and_passes(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 6
    await session.flush()
    ctx = await context(session, generations={"youth_years": 50, "lifespan_years": 50, "turnover_unrest": 10})
    town = await town_of(session, world)
    war = CollectionRow(kind=CollectionKind.WAR, name="The war", world_id=world.world.id, start_epoch=ctx.epoch, locked=[])
    session.add(war)
    await session.flush()
    session.add(CollectionMemberRow(collection_id=war.id, node_id=town.id, role=CollectionRole.LOSER, since_epoch=0))
    await session.flush()
    await keep_generations(ctx, GenerationTally())
    row = await session.get(GenerationRow, (town.id, ctx.epoch))
    assert row is not None and "great_war" in row.formative and "defeat" in row.formative
    older = GenerationRow(**{column.key: getattr(row, column.key) for column in GenerationRow.__mapper__.column_attrs} | {"generation_epoch": ctx.epoch - 3})
    await session.delete(row)
    session.add(older)
    await session.flush()
    tally = GenerationTally()
    await keep_generations(ctx, tally)
    assert tally.passed >= 1


async def test_towns_and_letters_lower_fertility_and_war_skews_the_sexes(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, demographic_transition={"lag_pct": 100})
    town = await town_of(session, world)
    for sex, count in ((SexKind.BEARER, 100), (SexKind.BEGETTER, 50)):
        session.add(
            CohortRow(
                community_entity_id=town.id,
                age_band=AgeBand.ADULT,
                sex_kind=sex,
                social_class=SocialClass.FARMER,
                condition=CohortCondition.NONE,
                count=count,
                generation_epoch=0,
            )
        )
    await session.flush()
    await measure(ctx, town, DemographyTally())
    transition = await session.get(DemographicTransitionRow, town.id)
    ratio = await session.get(SexRatioRow, town.id)
    assert transition.fertility_pct < 100 and ratio.begetters_per_hundred == 50 and ratio.bereaved_partners == 0
    assert await fertility_factor(ctx, town.id) < transition.fertility_pct / 100


async def test_role_norms_bar_soldiers_and_heirs(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world)
    people = await entity(session, "Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    await homeland(session, people, town)
    session.add(
        RoleNormRow(holder_entity_id=people.id, role=RoleKind.COMBAT, eligibility=RoleEligibility.BEARERS_ONLY, min_age=0, classes=[], since_epoch=0, locked=[])
    )
    session.add(
        RoleNormRow(
            holder_entity_id=people.id, role=RoleKind.INHERITANCE, eligibility=RoleEligibility.BEGETTERS_ONLY, min_age=0, classes=[], since_epoch=0, locked=[]
        )
    )
    await session.flush()
    assert await combat_sexes(session, town) == {SexKind.BEARER, SexKind.BOTH, SexKind.NONE}
    daughter = await entity(session, "Daughter", EntityType.MORTAL, MortalStats(age=20, sex="bearer"), world_id=world.world.id, location_id=town.id)
    son = await entity(session, "Son", EntityType.MORTAL, MortalStats(age=22, sex="begetter"), world_id=world.world.id, location_id=town.id)
    assert await allowed_heirs(session, daughter, [daughter, son]) == [son]


async def test_dates_are_told_in_the_holders_era(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world)
    realm = await realm_of(session, world, town)
    session.add(
        DatingSystemRow(
            holder_entity_id=realm.id, kind=DatingSystemKind.FOUNDING, anchor_year=100, label_node_id=realm.id, cycle_years=60, since_epoch=0, locked=[]
        )
    )
    await session.flush()
    assert await render_date(session, realm.id, 109) == f"the 10th year since the founding of {realm.name}"
    row = await session.get(DatingSystemRow, realm.id)
    row.kind = DatingSystemKind.CELESTIAL_CYCLE
    assert await render_date(session, realm.id, 225) == "the 6th year of the 3rd cycle"


async def test_arms_are_granted_differenced_for_cadets_and_quartered_by_marriage(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, heraldry={"cadet_bordure_pct": 100, "quarter_pct": 100})
    town = await town_of(session, world)
    first, second = await mortal(session, "Ann", world, town.id), await mortal(session, "Bel", world, town.id)
    elder = await house_with(session, world, "House Ann", first)
    cadet = await house_with(session, world, "House Ann the Younger", await mortal(session, "Cyd", world, town.id), parent=elder.id)
    other = await house_with(session, world, "House Bel", second)
    await grant_arms(ctx, HeraldryTally())
    assert (await session.get(ArmsRow, cadet.id)).division is HeraldicDivision.BORDURE
    assert (await session.get(ArmsRow, cadet.id)).parent_entity_id == elder.id
    session.add(MarriageRow(first_id=first.id, second_id=second.id, start_epoch=ctx.epoch))
    await session.flush()
    await quarter_on_marriage(ctx, HeraldryTally())
    arms = await session.get(ArmsRow, elder.id)
    assert arms.division is HeraldicDivision.QUARTERLY and arms.quartered_entity_id == other.id
    assert arms.holder_kind is HeraldryHolderKind.HOUSE and (await session.get(HouseProfileRow, elder.id)).emblem["field"]


async def test_no_two_holders_are_granted_the_same_arms(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_of(session, world)
    houses = [await house_with(session, world, f"House {name}", await mortal(session, name, world, town.id)) for name in ("Ari", "Bo", "Cy", "Di")]
    first_roll = invent(ctx.rng(f"arms.{houses[1].id}.0"), None, [])
    session.add(ArmsRow(holder_entity_id=houses[0].id, holder_kind=HeraldryHolderKind.HOUSE, since_epoch=0, locked=[], **first_roll))
    await session.flush()
    await grant_arms(ctx, HeraldryTally())
    rows = [await session.get(ArmsRow, house.id) for house in houses]
    assert all(row is not None for row in rows)
    assert len({signature_of(row) for row in rows if row is not None}) == len(houses)
    assert signature_of(rows[1]) != signature(first_roll)


async def test_choosing_no_charge_in_the_editor_clears_the_charge(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_of(session, world)
    house = await house_with(session, world, "House Eda", await mortal(session, "Eda", world, town.id))
    await grant_arms(ctx, HeraldryTally())
    row = await edit_arms(ctx, house.id, {"charge_two": None, "supporter": None, "charge_two_tincture": None}, [])
    assert row.charge_two is HeraldicCharge.NONE and row.supporter is HeraldicCharge.NONE and row.charge_two_tincture is None


async def test_designs_derive_performance_wear_on_legs_fail_and_are_mended(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, designs={"wear_per_leg": 50, "failure_at": 40, "failure_pct": 100, "shipyard_repair": 100})
    town = await town_of(session, world)
    realm = await realm_of(session, world, town)
    design = await draw_design(ctx, realm, VehicleFrame.CARRACK, sizes=frame_sizes(VehicleFrame.CARRACK))
    assert design.cargo > 0 and design.seaworthiness > 0 and design.speed >= 0
    parts = list(await session.scalars(select(DesignComponentRow).where(DesignComponentRow.design_id == design.id)))
    assert {part.component for part in parts} >= {DesignComponentKind.HULL, DesignComponentKind.HOLD}
    ship = await entity(session, "Swift", EntityType.VESSEL, VesselStats(), world_id=world.world.id, location_id=town.id)
    row = VesselProfileRow(
        entity_id=ship.id,
        kind=VehicleKind.SHIP,
        frame=VehicleFrame.CARRACK,
        condition=100,
        crew=40,
        home_port_entity_id=town.id,
        design_id=design.id,
        locked=[],
    )
    session.add(row)
    session.add(WorkshopRow(community_entity_id=town.id, kind=WorkshopKind.SHIPYARD, level=1, built_epoch=0))
    await session.flush()
    strong = await design_power(session, row)
    tally = DesignTally()
    await wear_leg(ctx, ship, row, stormy=True, tally=tally)
    assert tally.failures > 0 and row.condition < 100
    assert await design_power(session, row) < strong
    row.status = VesselStatus.DOCKED
    await mend(ctx, row, tally)
    worn = list(await session.scalars(select(ComponentWearRow.wear).where(ComponentWearRow.vessel_entity_id == ship.id)))
    assert worn and max(worn) == 0
    engine = await draw_design(ctx, realm, VehicleFrame.TREBUCHET)
    assert engine.kind is DesignKind.SIEGE_ENGINE and engine.armament > 0


async def test_vanished_towns_end_their_crowds_and_storylets(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_of(session, world)
    chooser = await mortal(session, "Gone", world, town.id)
    session.add(
        MobRow(settlement_entity_id=town.id, act=CollectiveActKind.RIOT, target=MobTarget.DISTRICT, status=MobStatus.RAMPAGING, since_epoch=0, locked=[])
    )
    session.add(
        StoryletRunRow(
            storylet=StoryletId.LOST_HEIR, world_id=world.world.id, cast={}, status=StoryletStatus.OPEN, chooser_node_id=chooser.id, opened_epoch=0, locked=[]
        )
    )
    session.add(CrowdMoodRow(settlement_entity_id=town.id, locked=[]))
    await session.flush()
    town.status = chooser.status = EntityStatus.DESTROYED
    town.end_epoch = chooser.end_epoch = ctx.epoch
    await session.flush()
    assert await mend_collective_links(session, ctx.epoch) >= 2
    assert (await session.scalar(select(MobRow))).status is MobStatus.DISPERSED
    assert (await session.scalar(select(StoryletRunRow))).status is StoryletStatus.EXPIRED


async def test_a_mortal_reads_role_classes_kept_as_json_in_context(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world)
    people = await entity(session, "Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    await homeland(session, people, town)
    role = RoleNormRow(
        holder_entity_id=people.id,
        role=RoleKind.OFFICE,
        eligibility=RoleEligibility.ANY,
        min_age=16,
        classes=[SocialClass.NOBLE.value],
        since_epoch=0,
        locked=[],
    )
    session.add(role)
    someone = await mortal(session, "Ilse", world, town.id)
    await session.flush()
    await session.refresh(role)
    lines = await mortal_collective_lines(await load_scope(session, Rules()), someone)
    assert any("only for noble" in line for line in lines)


async def test_a_mortal_knows_the_memory_generation_and_diaspora_around_them(session: AsyncSession, world: CoreWorld) -> None:
    town = await town_of(session, world)
    someone = await mortal(session, "Juna", world, town.id)
    realm = await realm_of(session, world, town)
    struck = await mortal(session, "Kade", world, town.id)
    folk = await entity(session, "Far Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    session.add_all(
        [
            FoundingMythRow(holder_entity_id=realm.id, credence=64, since_epoch=0, locked=[]),
            LostLandRow(claimant_entity_id=realm.id, region_entity_id=world.regions[1].id, strength=55, lost_epoch=2, locked=[]),
            MemoryStrikeRow(node_id=struck.id, by_entity_id=realm.id, active=True, since_epoch=1, locked=[]),
            GenerationRow(community_entity_id=town.id, generation_epoch=4, formative=["famine"], value_shifts={}, alive=120, locked=[]),
            DiasporaRow(people_entity_id=folk.id, host_entity_id=town.id, population=80, ties=45, since_epoch=1, locked=[]),
        ]
    )
    await session.flush()
    lines = "\n".join(await mortal_collective_lines(await load_scope(session, Rules()), someone))
    assert f"the founding story of {realm.name} is believed at credence 64" in lines
    assert f"{realm.name} remembers losing {world.regions[1].name} in epoch 2, memory strength 55" in lines
    assert f"Kade is struck from the records of {realm.name}" in lines
    assert "young in epoch 4 was shaped by famine; 120 of them live" in lines
    assert "Far Folk keep a diaspora of 80 here, ties to home 45" in lines


async def test_a_son_sees_stirred_towns_crowds_rewritten_accounts_and_waiting_storylets(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await town_of(session, world)
    realm = await realm_of(session, world, town)
    await mood_of(ctx, town.id)
    await set_feeling(session, town.id, CrowdFeeling.ANGER, 80, hold=None)
    await set_feeling(session, town.id, CrowdFeeling.FEAR, 10, hold=None)
    await set_feeling(session, town.id, CrowdFeeling.FERVOUR, 5, hold=None)
    session.add(MobRow(settlement_entity_id=town.id, act=CollectiveActKind.RIOT, size=250, anger=70, target=MobTarget.GRANARY, since_epoch=1, locked=[]))
    older = AccountRow(holder_entity_id=realm.id, kind=AccountKind.OFFICIAL_CHRONICLE, fidelity=80, credence=60, epoch=1, locked=[])
    session.add(older)
    await session.flush()
    newer = AccountRow(holder_entity_id=realm.id, kind=AccountKind.OFFICIAL_CHRONICLE, fidelity=30, credence=70, revised_from_id=older.id, epoch=2, locked=[])
    session.add(newer)
    session.add(
        StoryletRunRow(storylet=next(iter(StoryletId)), world_id=world.world.id, cast={}, status=StoryletStatus.OPEN, due_epoch=9, opened_epoch=1, locked=[])
    )
    await session.flush()
    world.son.current_world_id = world.world.id
    lines = "\n".join(await son_collective_lines(await load_scope(session, Rules()), world.son))
    assert f"{town.name} (town {town.id}) is stirred: anger 80" in lines
    assert f"a crowd of 250 in {town.name}" in lines
    assert f"account {newer.id}: the official chronicle kept by {realm.name} hides an older telling" in lines
    assert "waits on its chooser until epoch 9" in lines


async def test_a_custom_set_by_the_gods_records_what_it_was_before(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    people = await entity(session, "Folk", EntityType.PEOPLE, PeopleStats(), world_id=world.world.id)
    await set_norm(ctx, people.id, NormSituation.FEAST, NormBehaviour.JEST, EthicalStance.ADMIRABLE)
    await set_norm(ctx, people.id, NormSituation.FEAST, NormBehaviour.JEST, EthicalStance.ADMIRABLE)
    changes = list(await session.scalars(select(NormChangeRow).where(NormChangeRow.holder_entity_id == people.id)))
    assert [(row.before, row.after) for row in changes] == [(EthicalStance.ACCEPTABLE, EthicalStance.ADMIRABLE)]


async def test_a_storylet_whose_cast_died_meanwhile_lapses_instead_of_telling_the_dead(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, storylets={"open_epochs": 0})
    town = await town_of(session, world)
    ruler = await mortal(session, "Gone", world, town.id)
    realm = await realm_of(session, world, town, ruler)
    run = await begin(ctx, StoryletId.HOARDED_STORE, world.world.id, {StoryletRole.TOWN: town.id, StoryletRole.RULER: ruler.id, StoryletRole.REALM: realm.id})
    ruler.status, ruler.end_epoch = EntityStatus.DEAD, 1
    await session.flush()
    tally = StoryletTally()
    await settle_due(ctx, tally)
    assert run.status is StoryletStatus.EXPIRED and tally.expired == 1 and tally.by_personality == 0


async def test_living_generations_never_outnumber_their_town(session: AsyncSession, world: CoreWorld) -> None:
    world.cosmos.epoch = 6
    await session.flush()
    ctx = await context(session, generations={"youth_years": 50, "lifespan_years": 200})
    town = await town_of(session, world)
    people = population_of(town)
    for born, alive in ((2, people), (3, people), (4, people // 2)):
        session.add(GenerationRow(community_entity_id=town.id, generation_epoch=born, formative=[], value_shifts={}, alive=alive, locked=[]))
    await session.flush()
    await keep_generations(ctx, GenerationTally())
    living = await session.scalars(select(GenerationRow).where(GenerationRow.community_entity_id == town.id, GenerationRow.passed_epoch.is_(None)))
    assert sum(row.alive for row in living) <= people
