from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.sacred_lines import mortal_sacred_lines, son_sacred_lines
from aerona.agents.context.scope import load_scope
from aerona.catalog.sacred import DOMAIN_FEEDINGS
from aerona.catalog.tenets import STRATUM_NAMES
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.cycles import LongPlanRow, PolityStressRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.dominion import MiracleRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.faith import (
    AfterlifeStratumRow,
    CultDoctrineRow,
    CultHoldingRow,
    CultOfficeRow,
    CultTenetRow,
    HeresyRow,
    SoulJudgementRow,
    SpiritProfileRow,
)
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.mind import ThoughtRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.sacred import (
    DivinationSystemRow,
    DoctrineAfterlifeRow,
    DoctrineSacramentRow,
    EmotionHarvestRow,
    FaithClimateRow,
    ForecastModelRow,
    ForesightRow,
    GeniusLocusRow,
    GodFeedingRow,
    MillenarianRow,
    MysticRow,
    PetitionRow,
    SacramentRow,
    SpiritOfficeRow,
    TheodicyCrisisRow,
)
from aerona.db.tables.society import ArchiveHoldingRow, CommunitySocietyRow
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ProphecyPredicate, Technique
from aerona.domain.enums.demography import InheritanceCustom, MartialStyle
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.faith import AfterlifeState, ClergyFunction, HoldingKind, JudgementDoctrine, StratumKind, TenetKind
from aerona.domain.enums.mind import Emotion, ThoughtKind, ValueAxis, ValueHolder
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OfficeKind
from aerona.domain.enums.sacred import (
    AfterlifeModel,
    BureauRank,
    DivinationKind,
    DivinationQuestion,
    DivinationValidity,
    ForesightStatus,
    GeniusLocusKind,
    MillenarianStage,
    MysticState,
    OmenVerdict,
    PetitionKind,
    PetitionStatus,
    SacramentKind,
    SacramentProtection,
    SpiritOffence,
    TheodicyCause,
    TheodicyResolution,
)
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import (
    CultStats,
    DiseaseStats,
    FactionStats,
    KnowledgeStats,
    PeopleStats,
    PlaceStats,
    PolityStats,
    RegionStats,
    SpiritStats,
    StructureStats,
)
from aerona.engine.body.conditions import condition_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.plans import PlanTally, complete
from aerona.engine.mind.book import write_values
from aerona.engine.phases.factions import blueprint
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat_or
from aerona.engine.sacred import control
from aerona.engine.sacred.bureau import BureauTally, keep_bureau
from aerona.engine.sacred.feeding import harvest_feelings
from aerona.engine.sacred.foresight import ForesightTally, court_systems, keep_divination, keep_prescience, keep_psychohistory
from aerona.engine.sacred.guards import guarded, perform, rite_chance, unrest_shift, warded_hosts
from aerona.engine.sacred.mysteries import (
    MysteryTally,
    become_mystic,
    contemplative,
    keep_millenarians,
    keep_mystics,
    keep_theodicy,
    pressure_on,
    seek_another_way,
)
from aerona.engine.sacred.omens import battle_omen, war_forbidden
from aerona.engine.sacred.rites import RiteTally, keep_afterlife_belief, keep_climates, keep_sacraments, weigh_town
from aerona.engine.sacred.spirits import SpiritTally, bring_offerings, keep_place_spirits
from aerona.engine.services.war import declare_war
from aerona.services.integrity.sacred_links import mend_sacred_links
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

ROGUE = tuned_rules().celestial_bureaucracy.rogue_at


def status(row: PetitionRow) -> PetitionStatus:
    return row.status


def stage(row: MillenarianRow) -> MillenarianStage:
    return row.stage


def validity(row: DivinationSystemRow) -> DivinationValidity:
    return row.validity


def society(town_id: int, food: int) -> CommunitySocietyRow:
    shares = {f"share_{item.value}": 0.1 for item in SocialClass}
    satisfaction = {f"satisfaction_{item.value}": 50 for item in SocialClass}
    return CommunitySocietyRow(
        entity_id=town_id, **shares, **satisfaction, stock_food=food, stock_ore=0, stock_goods=0, price_food=300, price_ore=100, price_goods=100
    )


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "sacred", rules=tuned_rules(**rules))


async def church(session: AsyncSession, world: CoreWorld, town: EntityRow, *, orthodoxy: int = 50, clergy: int = 4) -> EntityRow:
    cult = await entity(session, f"Church of {town.name}", EntityType.CULT, CultStats(followers=100, zeal=40), world_id=world.world.id, location_id=town.id)
    session.add(CultDoctrineRow(cult_entity_id=cult.id, orthodoxy=orthodoxy, clergy_count=clergy, locked=[]))
    await bond(session, cult.id, world.son.id, BondKind.WORSHIPS)
    await session.flush()
    return cult


async def test_a_place_spirit_rises_takes_offerings_and_favours_its_town_until_pollution_offends_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Wellbrook", world, world.regions[0], population=2000, piety=80)
    session.add(society(town.id, 5000))
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    spring = await entity(session, "Clearwell", EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(PlaceProfileRow(entity_id=spring.id, kind=PlaceKind.SPRING, locked=[]))
    await session.flush()
    ctx = await at(session, 3, genius_loci={"bind_chance": 100, "favour_gain": 40})
    tally = SpiritTally()
    await keep_place_spirits(ctx, tally)
    row = await session.scalar(select(GeniusLocusRow).where(GeniusLocusRow.place_entity_id == spring.id))
    assert row is not None and row.kind is GeniusLocusKind.SPRING and row.community_entity_id == town.id
    assert tally.bound >= 1 and tally.offerings > 0 and row.favour > 0
    office = await session.get(SpiritOfficeRow, row.spirit_entity_id)
    assert office is not None and office.rank is BureauRank.LOCAL and office.overseer_node_id == world.son.id
    session.add(RegionPollutionRow(region_node_id=world.regions[0].id, air=0, water=90, soil=0, polluters=1, epoch=3, locked=[]))
    await session.flush()
    before = stat_or(town, "population", 0)
    ctx = await at(session, 4)
    await keep_place_spirits(ctx, SpiritTally())
    assert row.offended is SpiritOffence.POLLUTION
    assert stat_or(town, "population", 0) < before


async def test_a_town_shares_its_offerings_among_the_spirits_it_keeps_instead_of_giving_each_the_whole(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Manyshrine", world, world.regions[0], population=4000, piety=100)
    session.add(society(town.id, 5000))
    rows = []
    for index in range(4):
        spirit = await entity(session, f"Spirit {index}", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=town.id)
        rows.append(GeniusLocusRow(spirit_entity_id=spirit.id, community_entity_id=town.id, kind=GeniusLocusKind.SPRING, locked=[]))
    session.add(rows[0])
    await session.flush()
    ctx = await at(session, 3, genius_loci={"offering_food": 0})
    alone = await bring_offerings(ctx, rows[0], town)
    session.add_all(rows[1:])
    await session.flush()
    shared = await bring_offerings(ctx, rows[0], town)
    assert alone > 1 and shared == round(alone / 4)


async def test_petitions_are_read_appealed_granted_and_an_unwatched_office_goes_rogue(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Fenmoor", world, world.regions[1])
    session.add(society(town.id, 5000))
    asker = await mortal(session, "Orla", world, town.id)
    session.add(MortalProfileRow(entity_id=asker.id, health=40, locked=[]))
    upper = await entity(session, "Spirit of Fenmoor", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=town.id)
    lower = await entity(session, "Spirit of the Ford", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=town.id)
    session.add(SpiritOfficeRow(spirit_entity_id=upper.id, rank=BureauRank.CITY, overseer_node_id=world.son.id, jurisdiction_entity_id=town.id, locked=[]))
    session.add(SpiritOfficeRow(spirit_entity_id=lower.id, rank=BureauRank.LOCAL, superior_spirit_id=upper.id, jurisdiction_entity_id=town.id, locked=[]))
    await session.flush()
    ctx = await at(session, 2, celestial_bureaucracy={"petition_chance": 0, "grant_base": 0, "merit_grant_pct": 0, "appeal_chance": 100, "delay": 0})
    lowered = await session.get(SpiritOfficeRow, lower.id)
    assert lowered is not None
    petition = await control.lodge_petition(ctx, asker.id, lower.id, PetitionKind.HEALING, defendant_id=None, bribe=0)
    await keep_bureau(ctx, BureauTally())
    assert petition.status is PetitionStatus.APPEALED and petition.office_spirit_id == upper.id
    ctx = await at(session, 3, celestial_bureaucracy={"petition_chance": 0, "grant_base": 100})
    await keep_bureau(ctx, BureauTally())
    profile = await session.get(MortalProfileRow, asker.id)
    assert status(petition) is PetitionStatus.GRANTED and profile is not None and profile.health > 40
    for epoch in range(4, 20):
        await keep_bureau(await at(session, epoch, celestial_bureaucracy={"petition_chance": 0}), BureauTally())
    assert lowered.corruption >= ROGUE and lowered.superior_spirit_id is None


async def test_a_wise_pious_mortal_has_visions_and_is_persecuted_into_founding_a_heresy(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Stillwater", world, world.regions[2])
    cult = await church(session, world, town, orthodoxy=90)
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    seer = await mortal(session, "Ysolde", world, town.id, wisdom=90, charisma=90)
    session.add(MortalProfileRow(entity_id=seer.id, locked=[]))
    await write_values(session, ValueHolder.PERSONAL, seer.id, {ValueAxis.PIETY: 95})
    await session.flush()
    rules = {"vision_chance": 100, "again_chance": 100, "answer_chance": 100, "followers_per_vision": 80, "found_at": 200, "persecuted_at": 20}
    for epoch in range(1, 5):
        await keep_mystics(await at(session, epoch, mysticism=rules), MysteryTally())
    row = await session.get(MysticRow, seer.id)
    assert row is not None and row.genuine_visions > 0 and row.answered_by_node_id == world.son.id
    assert row.persecution > 0 and row.state is MysticState.FOUNDER and row.founded_entity_id is not None
    heresy = await session.get(HeresyRow, row.founded_entity_id)
    assert heresy is not None and heresy.parent_entity_id == cult.id


async def test_an_omen_stirs_a_town_to_await_the_end_and_a_passed_date_is_read_anew_then_hardens_into_a_sect(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Ashkirk", world, world.regions[0], population=3000, wealth=60)
    session.add(society(town.id, 5000))
    await church(session, world, town)
    session.add(SkyEventRow(kind=next(iter(SkyEventKind)), epoch=1, world_id=world.world.id, text="a sign"))
    await session.flush()
    rules = {"stir_chance": 100, "horizon": 2, "vigil_epochs": 1, "march_at": 0, "redate_chance": 100, "redate_decay": 100, "sect_chance": 100}
    await keep_millenarians(await at(session, 1, millenarianism=rules), MysteryTally())
    row = await session.scalar(select(MillenarianRow).where(MillenarianRow.settlement_entity_id == town.id))
    assert row is not None and row.movement_id is not None and row.end_epoch == 3
    await keep_millenarians(await at(session, 2, millenarianism=rules), MysteryTally())
    assert row.stage is MillenarianStage.MARCHING and row.given_up > 0 and row.attacks == 1
    await keep_millenarians(await at(session, 3, millenarianism=rules), MysteryTally())
    assert stage(row) is MillenarianStage.REDATED and row.dates_set == 2 and row.end_epoch == 5
    await keep_millenarians(await at(session, 5, millenarianism=rules), MysteryTally())
    assert stage(row) is MillenarianStage.SECT and row.sect_entity_id is not None


async def test_unanswered_suffering_tests_a_doctrine_and_yields_a_teaching_of_trial(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Coldharbour", world, world.regions[1])
    session.add(society(town.id, 5000))
    cult = await church(session, world, town)
    disease = await entity(session, "The Grey Cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    session.add(
        OutbreakRow(disease_entity_id=disease.id, region_entity_id=world.regions[1].id, path=next(iter(SpreadPath)), severity=60, started_epoch=1, locked=[])
    )
    await session.flush()
    rules = {"argue_base": 0, "doctrine_chance": 100, "window": 1}
    await keep_theodicy(await at(session, 1, theodicy=rules), MysteryTally())
    crisis = await session.scalar(select(TheodicyCrisisRow).where(TheodicyCrisisRow.community_entity_id == town.id))
    assert crisis is not None and crisis.cause is TheodicyCause.PLAGUE and crisis.god_node_id == world.son.id
    await keep_theodicy(await at(session, 2, theodicy=rules), MysteryTally())
    assert crisis.resolution is TheodicyResolution.NEW_DOCTRINE
    assert await session.get(CultTenetRow, (cult.id, TenetKind.SACRED_SUFFERING)) is not None


async def test_a_visible_answer_ends_a_crisis_of_faith(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Glimmerford", world, world.regions[2])
    await church(session, world, town)
    ctx = await at(session, 2)
    crisis = await control.test_faith(ctx, town.id, TheodicyCause.FAMINE, 70)
    session.add(MiracleRecordRow(god_node_id=world.son.id, region_entity_id=world.regions[2].id, kind="rain", epoch=2, locked=[]))
    await session.flush()
    await keep_theodicy(await at(session, 2), MysteryTally())
    assert crisis.answered and crisis.resolution is TheodicyResolution.ANSWERED


async def test_sacraments_ward_against_possession_ease_routing_and_unrest_and_missing_one_is_felt(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Hearthmere", world, world.regions[0])
    cult = await church(session, world, town)
    priest = await mortal(session, "Aldric", world, town.id)
    session.add(CultOfficeRow(cult_entity_id=cult.id, kind=ClergyFunction.CELEBRANT, holder_entity_id=priest.id))
    child = await mortal(session, "Wren", world, town.id, age=0)
    elder = await mortal(session, "Mabyn", world, town.id, age=60)
    for person in (child, elder):
        session.add(MortalProfileRow(entity_id=person.id, locked=[]))
    child.birth_epoch = 3
    await session.flush()
    ctx = await at(session, 3, sacraments={"coverage": 100})
    await keep_sacraments(ctx, RiteTally())
    taught = await session.get(DoctrineSacramentRow, (cult.id, SacramentKind.BIRTH_BLESSING))
    assert taught is not None and taught.protection is SacramentProtection.POSSESSION
    given = await perform(ctx, child, SacramentKind.BIRTH_BLESSING, set(), priest_id=priest.id)
    assert given is not None and not given.missed
    assert child.id in set(await session.scalars(warded_hosts()))
    await perform(ctx, elder, SacramentKind.INITIATION, set(), priest_id=priest.id)
    await perform(ctx, elder, SacramentKind.MARRIAGE, set(), priest_id=priest.id)
    strength, lacking = await guarded(ctx, elder.id, SacramentProtection.ROUTING)
    assert strength > 0 and not lacking
    assert await rite_chance(ctx, elder, 50) < 50
    assert await unrest_shift(ctx, elder) < 0
    missed_ctx = await at(session, 3, sacraments={"coverage": 0})
    lone = await mortal(session, "Tamsin", world, town.id)
    session.add(MortalProfileRow(entity_id=lone.id, locked=[]))
    await session.flush()
    row = await perform(missed_ctx, lone, SacramentKind.INITIATION, set())
    assert row is not None and row.missed
    felt = await session.scalar(select(ThoughtRow).where(ThoughtRow.holder_node_id == lone.id, ThoughtRow.kind == ThoughtKind.FAITH_UNMET))
    assert felt is not None
    assert await rite_chance(missed_ctx, lone, 10) > 10


async def test_a_soul_meeting_another_afterlife_than_taught_is_shocked_and_aligning_it_ends_the_shock(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lowgate", world, world.regions[1])
    cult = await church(session, world, town)
    session.add(CultTenetRow(cult_entity_id=cult.id, tenet=TenetKind.ANCESTOR_VENERATION, since_epoch=0))
    dead = await mortal(session, "Corvin", world, town.id)
    realm = await entity(session, "The Far Halls", EntityType.REGION, RegionStats(), world_id=world.world.id)
    stratum = AfterlifeStratumRow(realm_entity_id=realm.id, kind=StratumKind.REWARD, name="The Bright Field", son_id=world.son.id)
    session.add(stratum)
    spirit = await entity(session, "Shade of Corvin", EntityType.SPIRIT, SpiritStats(strength=30, unrest=10), world_id=world.world.id)
    await session.flush()
    session.add(SpiritProfileRow(spirit_entity_id=spirit.id, origin_mortal_id=dead.id, state=AfterlifeState.IN_REALM, stratum_id=stratum.id, locked=[]))
    session.add(SoulJudgementRow(spirit_entity_id=spirit.id, doctrine=JudgementDoctrine.DEEDS, stratum_id=stratum.id, epoch=4))
    await session.flush()
    tally = RiteTally()
    await keep_afterlife_belief(await at(session, 4), tally)
    taught = await session.get(DoctrineAfterlifeRow, cult.id)
    assert taught is not None and taught.model is AfterlifeModel.REALM_OF_LINE
    assert taught.shocks == 1 and stat_or(spirit, "unrest", 0) > 10
    world.son.essence = 500
    aligned = await control.align(await at(session, 4), cult.id, world.son.id, charge=True)
    assert aligned.aligned and world.son.essence == 500 - tuned_rules().afterlife_belief.align_cost
    kinds = set(await session.scalars(select(AfterlifeStratumRow.kind).where(AfterlifeStratumRow.realm_entity_id == realm.id)))
    assert StratumKind.BY_LINE in kinds


async def test_literacy_and_silence_pull_a_town_into_godlessness_and_miracles_bring_it_back(session: AsyncSession, world: CoreWorld) -> None:
    people = await entity(session, "The Lettered", EntityType.PEOPLE, PeopleStats(population=900), world_id=world.world.id, location_id=world.regions[3].id)
    session.add(
        PeopleCultureRow(
            people_entity_id=people.id,
            cohesion=50,
            literacy=100,
            urbanisation=50,
            martial_style=next(iter(MartialStyle)),
            inheritance=next(iter(InheritanceCustom)),
            locked=[],
        )
    )
    town = await settlement(session, "Quillhaven", world, world.regions[3], piety=12, prosperity=90)
    await bond(session, town.id, people.id, BondKind.DESCENDS_FROM)
    await session.flush()
    rules = {"literacy_pct": 100, "drift_pct": 100, "godless_piety": 10}
    tally = RiteTally()
    await keep_climates(await at(session, 1, secularisation=rules), tally)
    climate = await session.get(FaithClimateRow, town.id)
    assert climate is not None and climate.prosperity_pull < 0 and climate.piety_drift < 0
    assert await has_flag(session, town.id, EntityFlag.GODLESS) and climate.godless
    session.add(MiracleRecordRow(god_node_id=world.son.id, region_entity_id=world.regions[3].id, kind="healing", epoch=2, locked=[]))
    await session.flush()
    await keep_climates(await at(session, 2, secularisation={"miracle_push": 100, "drift_pct": 100, "faithful_piety": 20, "prosperity_pct": 0}), RiteTally())
    assert not await has_flag(session, town.id, EntityFlag.GODLESS)


async def ruled_realm(session: AsyncSession, world: CoreWorld, town: EntityRow, ruler: EntityRow) -> EntityRow:
    realm = await entity(session, f"Crown of {town.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityProfileRow(polity_entity_id=realm.id, government=GovernmentKind.MONARCHY, decision_rule=DecisionRule.AUTOCRATIC, locked=[], emblem={}))
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=town.id))
    session.add(OfficeRow(polity_entity_id=realm.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id))
    await session.flush()
    return realm


async def test_divination_reads_truly_only_with_a_seer_and_a_heeded_ill_omen_holds_a_war(session: AsyncSession, world: CoreWorld) -> None:
    people = await entity(session, "Bird Watchers", EntityType.PEOPLE, PeopleStats(population=900), world_id=world.world.id, location_id=world.regions[0].id)
    town = await settlement(session, "Augurhold", world, world.regions[0])
    await bond(session, town.id, people.id, BondKind.DESCENDS_FROM)
    king = await mortal(session, "Reynard", world, town.id)
    session.add(MortalProfileRow(entity_id=king.id, legitimacy=50, locked=[]))
    await write_values(session, ValueHolder.PERSONAL, king.id, {ValueAxis.SUPERSTITION: 90})
    realm = await ruled_realm(session, world, town, king)
    other_town = await settlement(session, "Rivalton", world, world.regions[2])
    rival_king = await mortal(session, "Osric", world, other_town.id)
    rival = await ruled_realm(session, world, other_town, rival_king)
    system = DivinationSystemRow(people_entity_id=people.id, kind=DivinationKind.AUGURY, locked=[])
    session.add(system)
    await session.flush()
    ctx = await at(session, 3)
    await keep_divination(ctx, ForesightTally())
    assert system.validity is DivinationValidity.NOISE
    seer = await mortal(session, "Ilse", world, town.id)
    seer.mortal_role = MortalRole.SEER
    seer.affiliated_entity_id = people.id
    await session.flush()
    await keep_divination(await at(session, 3, divination={"consult_chance": 0}), ForesightTally())
    assert validity(system) is DivinationValidity.SEER_GIFT
    reading = await control.read_omens(ctx, realm.id, DivinationQuestion.WAR, verdict=OmenVerdict.INAUSPICIOUS, swayed_by=world.son.id, system_id=system.id)
    assert reading.heeded and reading.swayed_by_node_id == world.son.id
    assert await war_forbidden(ctx, realm.id)
    assert not await declare_war(ctx, realm.id, rival.id, "a border quarrel", world_cap=False)
    await control.read_omens(ctx, realm.id, DivinationQuestion.BATTLE, verdict=OmenVerdict.AUSPICIOUS, swayed_by=None, system_id=system.id)
    assert await battle_omen(ctx, town) > 0


async def test_a_seer_foresees_a_likely_death_rivals_cloud_it_and_renown_follows_what_comes(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Oldcrown", world, world.regions[1])
    king = await mortal(session, "Aldous", world, town.id, age=69, lifespan=70)
    await ruled_realm(session, world, town, king)
    seer = await mortal(session, "Morwen", world, town.id, wisdom=90)
    seer.mortal_role = MortalRole.SEER
    session.add(MortalProfileRow(entity_id=seer.id, renown=20, locked=[]))
    await session.flush()
    rules = {"foresee_chance": 100, "likely_at": 50, "proclaim_at": 100}
    await keep_prescience(await at(session, 2, prescience=rules), ForesightTally())
    row = await session.scalar(select(ForesightRow).where(ForesightRow.seer_node_id == seer.id))
    assert row is not None and row.predicate is ProphecyPredicate.DIES and row.subject_node_id == king.id
    clear = row.certainty
    for name in ("Ruan", "Tegan", "Jory"):
        rival = await mortal(session, name, world, town.id)
        rival.mortal_role = MortalRole.SEER
    await session.flush()
    clouded = await control.foretell(await at(session, 2), seer.id, ProphecyPredicate.DIES, king.id, certainty=clear, source=row.source, proclaimed=False)
    assert clouded.certainty < clear
    king.status = EntityStatus.DEAD
    king.end_epoch = 3
    await session.flush()
    await keep_prescience(await at(session, 3, prescience={"foresee_chance": 0}), ForesightTally())
    profile = await session.get(MortalProfileRow, seer.id)
    assert row.status is ForesightStatus.FULFILLED and profile is not None and profile.renown > 20


async def test_a_learned_order_forecasts_its_realm_and_a_fulfilled_steering_plan_eases_its_stress(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Scrollmere", world, world.regions[2])
    ruler = await mortal(session, "Hale", world, town.id)
    realm = await ruled_realm(session, world, town, ruler)
    session.add(PolityStressRow(polity_entity_id=realm.id, psi=70, locked=[]))
    order = await entity(session, "Academy of Scrollmere", EntityType.FACTION, FactionStats(strength=40), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=order.id, kind=FactionKind.SCHOLARS_ACADEMY, home_entity_id=town.id, locked=[]))
    library = await entity(session, "Great Library", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    for index in range(4):
        lore = await entity(session, f"Treatise {index}", EntityType.KNOWLEDGE, KnowledgeStats(), world_id=world.world.id)
        session.add(ArchiveHoldingRow(archive_entity_id=library.id, knowledge_entity_id=lore.id, epoch=1))
    session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.CENSUS))
    await session.flush()
    rules = {"archive_min": 4, "build_chance": 100, "accuracy_per_work": 20, "plan_at": 50}
    await keep_psychohistory(await at(session, 2, psychohistory=rules), ForesightTally())
    model = await session.scalar(select(ForecastModelRow).where(ForecastModelRow.order_entity_id == order.id))
    assert model is not None and model.subject_entity_id == realm.id and model.accuracy >= 80 and model.plan_id is not None
    plan = await session.get(LongPlanRow, model.plan_id)
    assert plan is not None
    ctx = await at(session, 3)
    await complete(ctx, plan, order, PlanTally())
    stress = await session.get(PolityStressRow, realm.id)
    assert stress is not None and stress.psi < 70


async def test_gods_draw_essence_from_the_feelings_of_their_faithful(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Weepwater", world, world.regions[0])
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    mourner = await mortal(session, "Elowen", world, town.id)
    await session.flush()
    ctx = await at(session, 5)
    book = await ctx.divine()
    feelings = {feeling for domain in book.gods[world.son.id].living_domains for feeling in DOMAIN_FEEDINGS[domain]}
    chosen = sorted(feelings)[0]
    session.add(ThoughtRow(holder_node_id=mourner.id, kind=ThoughtKind.SAW_KIN_DIE, emotion=chosen, intensity=80, epoch=5, decay_pct=10))
    await session.flush()
    gained = await harvest_feelings(ctx, book)
    feedings = list(await session.scalars(select(GodFeedingRow).where(GodFeedingRow.god_node_id == world.son.id)))
    assert {row.emotion for row in feedings} == feelings
    assert gained.get(world.son.id, 0) > 0
    harvest = await session.scalar(select(EmotionHarvestRow).where(EmotionHarvestRow.god_node_id == world.son.id, EmotionHarvestRow.emotion == chosen))
    assert harvest is not None and harvest.essence > 0
    await control.set_feeding(ctx, world.son.id, Emotion.JOY, 0)
    zero = await session.get(GodFeedingRow, (world.son.id, Emotion.JOY))
    assert zero is not None and zero.weight == 0 and "weight" in zero.locked


async def test_integrity_dismisses_vanished_offices_and_their_open_petitions(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Dimhollow", world, world.regions[1])
    asker = await mortal(session, "Brin", world, town.id)
    gone = await entity(session, "Spirit of Dimhollow", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=town.id)
    session.add(SpiritOfficeRow(spirit_entity_id=gone.id, rank=BureauRank.CITY, superior_spirit_id=gone.id, jurisdiction_entity_id=town.id, locked=[]))
    session.add(PetitionRow(petitioner_node_id=asker.id, office_spirit_id=gone.id, kind=PetitionKind.PROSPERITY, filed_epoch=1, due_epoch=2, locked=[]))
    gone.status = EntityStatus.DEAD
    gone.end_epoch = 2
    await session.flush()
    assert await mend_sacred_links(session) >= 2
    office = await session.get(SpiritOfficeRow, gone.id)
    petition = await session.scalar(select(PetitionRow).where(PetitionRow.office_spirit_id == gone.id))
    assert office is not None and office.dismissed and office.superior_spirit_id is None
    assert petition is not None and petition.status is PetitionStatus.DISMISSED


async def test_the_faithful_and_the_gods_read_their_spirits_visions_and_feelings_in_context(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brightmere", world, world.regions[2])
    me = await mortal(session, "Cass", world, town.id)
    spirit = await entity(session, "Spirit of Brightmere", EntityType.SPIRIT, SpiritStats(), world_id=world.world.id, location_id=town.id)
    session.add(GeniusLocusRow(spirit_entity_id=spirit.id, place_entity_id=town.id, community_entity_id=town.id, kind=GeniusLocusKind.CITY, locked=[]))
    session.add(SpiritOfficeRow(spirit_entity_id=spirit.id, rank=BureauRank.CITY, overseer_node_id=world.son.id, jurisdiction_entity_id=town.id, locked=[]))
    session.add(MysticRow(mortal_entity_id=me.id, state=MysticState.VISIONARY, visions=3, followers=12, locked=[]))
    session.add(SacramentRow(mortal_entity_id=me.id, kind=SacramentKind.INITIATION, epoch=1, missed=True, locked=[]))
    session.add(GodFeedingRow(god_node_id=world.son.id, emotion=Emotion.HOPE, weight=60, harvested=7, locked=[]))
    await session.flush()
    scope = await load_scope(session, tuned_rules())
    mine = " ".join(await mortal_sacred_lines(scope, me))
    assert "Spirit of Brightmere" in mine and "visionary mystic" in mine and "initiation missed" in mine
    theirs = " ".join(await son_sacred_lines(scope, world.son))
    assert "hope 60" in theirs and "spirit offices under your oversight: 1" in theirs


async def test_a_church_holding_a_town_serves_mortals_living_in_its_land(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Greyhold", world, world.regions[3], population=3000)
    cult = await entity(
        session, "Church of the Hold", EntityType.CULT, CultStats(followers=50, zeal=40), world_id=world.world.id, location_id=world.regions[3].id
    )
    session.add(CultDoctrineRow(cult_entity_id=cult.id, clergy_count=3, locked=[]))
    session.add(CultHoldingRow(cult_entity_id=cult.id, holding_entity_id=town.id, kind=next(iter(HoldingKind)), since_epoch=0))
    priest = await mortal(session, "Ansel", world, town.id)
    session.add(CultOfficeRow(cult_entity_id=cult.id, kind=ClergyFunction.CELEBRANT, holder_entity_id=priest.id))
    herder = await mortal(session, "Tobin", world, world.regions[3].id)
    session.add(MortalProfileRow(entity_id=herder.id, locked=[]))
    await session.flush()
    ctx = await at(session, 2, sacraments={"coverage": 100})
    await keep_sacraments(ctx, RiteTally())
    row = await perform(ctx, herder, SacramentKind.INITIATION, set())
    assert row is not None and row.cult_entity_id == cult.id and not row.missed
    crisis = await control.test_faith(ctx, town.id, TheodicyCause.FAMINE, 60)
    assert crisis.cult_entity_id == cult.id


def test_every_kind_of_faction_can_be_founded() -> None:
    assert [kind for kind in FactionKind if blueprint(kind).kind is not kind] == []


async def test_a_revered_mystic_founds_a_holy_order(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Calmwater", world, world.regions[0])
    await church(session, world, town, orthodoxy=10)
    await bond(session, town.id, world.son.id, BondKind.WORSHIPS)
    sage = await mortal(session, "Brannoc", world, town.id, wisdom=90, charisma=90)
    session.add(MortalProfileRow(entity_id=sage.id, locked=[]))
    await write_values(session, ValueHolder.PERSONAL, sage.id, {ValueAxis.PIETY: 95})
    await session.flush()
    rules = {"vision_chance": 100, "again_chance": 100, "followers_per_vision": 80, "found_at": 200, "revered_at": 20}
    for epoch in range(1, 5):
        await keep_mystics(await at(session, epoch, mysticism=rules), MysteryTally())
    row = await session.get(MysticRow, sage.id)
    assert row is not None and row.state is MysticState.FOUNDER and row.founded_entity_id is not None
    order = await session.get(FactionProfileRow, row.founded_entity_id)
    assert order is not None and order.kind is FactionKind.HOLY_ORDER


async def test_a_divination_system_counts_its_diviners_and_one_with_none_is_never_consulted(session: AsyncSession, world: CoreWorld) -> None:
    people = await entity(session, "Lot Casters", EntityType.PEOPLE, PeopleStats(population=900), world_id=world.world.id, location_id=world.regions[0].id)
    town = await settlement(session, "Lotby", world, world.regions[0])
    await bond(session, town.id, people.id, BondKind.DESCENDS_FROM)
    king = await mortal(session, "Brand", world, town.id)
    realm = await ruled_realm(session, world, town, king)
    system = DivinationSystemRow(people_entity_id=people.id, kind=DivinationKind.AUGURY, locked=[])
    session.add(system)
    await session.flush()
    await keep_divination(await at(session, 3, divination={"consult_chance": 0}), ForesightTally())
    assert system.diviners == 0
    assert await court_systems(await at(session, 3), realm.id) == []
    seer = await mortal(session, "Wren", world, town.id)
    seer.mortal_role = MortalRole.SEER
    seer.affiliated_entity_id = people.id
    await session.flush()
    await keep_divination(await at(session, 3, divination={"consult_chance": 0}), ForesightTally())
    assert system.diviners == 1 and await court_systems(await at(session, 3), realm.id) == [system]


async def test_a_mystic_s_vision_marks_its_body_and_a_contemplative_tradition_opens_the_way(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Cloisterby", world, world.regions[0])
    seeker = await mortal(session, "Anwen", world, town.id, wisdom=90)
    await session.flush()
    ctx = await at(session, 3)
    assert not await contemplative(ctx, seeker)
    session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=Technique.MONASTICISM, since_epoch=0, secret=False))
    await session.flush()
    assert await contemplative(ctx, seeker)
    await become_mystic(ctx, seeker, None, MysteryTally())
    assert await condition_of(ctx, seeker.id, ConditionKind.VISIONS) is not None


async def test_long_silence_makes_a_tested_faith_hold_its_god_hidden_and_silence_no_longer_erodes_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Stillwater", world, world.regions[0], piety=60)
    cult = await church(session, world, town)
    session.add(FaithClimateRow(community_entity_id=town.id, silent_epochs=10, updated_epoch=0, locked=[]))
    crisis = TheodicyCrisisRow(cult_entity_id=cult.id, community_entity_id=town.id, cause=TheodicyCause.PLAGUE, suffering=60, started_epoch=0, locked=[])
    session.add(crisis)
    await session.flush()
    ctx = await at(session, 9, theodicy={"argue_base": 0, "doctrine_chance": 100})
    assert await seek_another_way(ctx, crisis, town, cult, MysteryTally()) is TheodicyResolution.NEW_DOCTRINE
    assert await session.get(CultTenetRow, (cult.id, TenetKind.HIDDEN_GOD)) is not None
    row = await weigh_town(ctx, town, ({}, set(), {}))
    assert row.silence_pull == 0


async def test_a_doom_near_its_end_stirs_the_faithful_to_await_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lastlight", world, world.regions[0])
    ctx = await at(session, 3, millenarianism={"doom_at": 10})
    calm, _ = await pressure_on(ctx, town, set())
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.doom_clock = 20
    await session.flush()
    stirred, _ = await pressure_on(ctx, town, set())
    assert stirred == calm + 1


def test_afterlife_strata_take_plain_names_from_their_kind() -> None:
    assert all("Blessed" not in name and "Pits" not in name for name in STRATUM_NAMES.values())
    assert STRATUM_NAMES[StratumKind.REWARD] == "the realm of reward"
