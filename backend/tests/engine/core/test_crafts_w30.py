from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.catch import GEAR
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.ages import IrregularSeasonRow, WinterForecastRow
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.crafts import (
    AssistiveAidRow,
    CatchGroundRow,
    ChemicalWorksRow,
    EmotionSpiritRow,
    IncorporealRightRow,
    InsurancePolicyRow,
    InsurerRow,
    MaterialAffinityRow,
    NumberSystemRow,
    PublicClockRow,
    SympatheticLinkRow,
)
from aerona.db.tables.culture import ArtworkProfileRow, HolderTechniqueRow
from aerona.db.tables.customs import EvidenceRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.economy import CommunityStockRow, ResourceProfileRow, ResourceWorkerRow, WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import AccusationRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.mind import SkillRow, ThoughtRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.ages import SeasonCause, SeasonSpell
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.crafts import (
    AffinityMode,
    AssistiveAid,
    CatchGround,
    CatchRight,
    ChemicalProduct,
    ClockKind,
    Gear,
    InsuranceCover,
    LinkToken,
    Notation,
    RightAcquired,
    RightKind,
)
from aerona.domain.enums.culture import ArtMode, MagicSchool, Technique
from aerona.domain.enums.customs import EvidenceKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.kind_crafts import GameCategory
from aerona.domain.enums.mind import Emotion, SkillKind, SkillSource, ThoughtKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import ArtworkStats, ResourceStats
from aerona.engine.body.state import has_reader, reading_of
from aerona.engine.context import TickContext
from aerona.engine.crafts.aids import AidTally, keep_aids
from aerona.engine.crafts.catch import catch_factor, regrowth_scale, trap_factors
from aerona.engine.crafts.chemistry import ChemistryTally, keep_chemistry
from aerona.engine.crafts.clocks import ClockTally, keep_clocks
from aerona.engine.crafts.cover import cargo_holders, claim
from aerona.engine.crafts.games import GameTally, keep_games, made_by, shaped
from aerona.engine.crafts.grounds import GroundTally, keep_grounds
from aerona.engine.crafts.haunting import bind_spirit, spirit_feelings
from aerona.engine.crafts.heirs import pass_rights
from aerona.engine.crafts.insurance import InsuranceTally, keep_insurance
from aerona.engine.crafts.linking import affinity_value, link_boost, link_strength
from aerona.engine.crafts.numbers import NumberTally, keep_numbers
from aerona.engine.crafts.reckoning import notation_boost, reckoned
from aerona.engine.crafts.rights import RightsTally, keep_rights
from aerona.engine.crafts.spirits import SpiritTally, keep_spirits
from aerona.engine.crafts.sympathy import SympathyTally, keep_sympathy
from aerona.engine.crafts.timekeeping import clock_muster, clock_output
from aerona.engine.crafts.works import blasted, fertilised, soap_relief
from aerona.engine.environment.long_seasons import SeasonTally, keep_seasons
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import set_stats, stat
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "crafts", rules=tuned_rules(**rules))


async def home(session: AsyncSession, world: CoreWorld, name: str, *techniques: Technique) -> EntityRow:
    town = await settlement(session, name, world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN))
    session.add_all([HolderTechniqueRow(holder_entity_id=town.id, technique=technique) for technique in techniques])
    await session.flush()
    return town


async def test_a_fishing_ground_takes_its_catch_from_gear_and_collapses_when_worked_out(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    water = await entity(session, "Cold Shoals", EntityType.RESOURCE, ResourceStats(abundance=60), world_id=world.world.id, location_id=world.regions[0].id)
    profile = ResourceProfileRow(
        resource_entity_id=water.id, commodity=CommodityKind.FISH, reserve=100, initial_reserve=100, richness=50, extraction_difficulty=10, quality=50
    )
    session.add(profile)
    await session.flush()
    await keep_grounds(await at(session, 3, grounds={"marine_hunt_chance": 0, "owned_chance": 0}), GroundTally())
    ground = await session.scalar(select(CatchGroundRow).where(CatchGroundRow.source_entity_id == water.id))
    assert ground is not None and ground.ground is CatchGround.FISHERY and ground.gear in {Gear.LINES, Gear.NETS, Gear.WEIRS}
    pct = {Gear.LINES: rules.grounds.lines_pct, Gear.NETS: rules.grounds.nets_pct, Gear.WEIRS: rules.grounds.weirs_pct}[ground.gear]
    assert await catch_factor(session, rules, water.id) == pct / 100
    profile.reserve = 10
    tally = GroundTally()
    await keep_grounds(await at(session, 4), tally)
    assert ground.collapsed and tally.collapsed == 1 and await catch_factor(session, rules, water.id) == 0
    pressed = 1 - GEAR[ground.gear].depletion(rules) / 100 / 2
    assert await regrowth_scale(session, rules, water.id) == pressed * rules.grounds.collapsed_regrowth_pct / 100
    profile.reserve = 60
    await keep_grounds(await at(session, 5), tally)
    assert not ground.collapsed and tally.recovered == 1


async def test_a_small_range_collapses_only_below_a_share_of_its_first_stock(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0].id
    session.add(SpeciesRangeRow(species_entity_id=world.people.id, region_entity_id=region, abundance=8, hunted=2, locked=[]))
    await session.flush()
    tally = GroundTally()
    await keep_grounds(await at(session, 3), tally)
    ground = await session.get(CatchGroundRow, (world.people.id, region))
    assert ground is not None and ground.first_stock == 8 and not ground.collapsed
    stock = await session.get(SpeciesRangeRow, (world.people.id, region))
    assert stock is not None
    stock.abundance = 1
    await keep_grounds(await at(session, 4), tally)
    assert ground.collapsed and tally.collapsed == 1


async def test_a_trapped_range_is_hunted_by_its_gear_and_effort(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    session.add(
        CatchGroundRow(
            source_entity_id=world.people.id, region_entity_id=world.regions[0].id, ground=CatchGround.TRAPPING, gear=Gear.TRAPS, effort=100, locked=[]
        )
    )
    await session.flush()
    factors = await trap_factors(session, rules)
    assert factors[(world.people.id, world.regions[0].id)] == rules.grounds.traps_pct / 100 * (0.5 + rules.grounds.effort_pct / 100)


async def test_chemical_works_turn_raw_goods_into_their_product_and_their_products_reach_the_town(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    town = await home(session, world, "Vatham", Technique.HERBALISM)
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.HERBS, quantity=50))
    await session.flush()
    tally = ChemistryTally()
    await keep_chemistry(await at(session, 3, chemistry={"found_chance": 100}), tally)
    works = await session.get(ChemicalWorksRow, (town.id, ChemicalProduct.DYE))
    assert works is not None and tally.founded == 1
    works.output, works.hazard = 50, 0
    await keep_chemistry(await at(session, 4, chemistry={"found_chance": 0}), tally)
    dye = await session.scalar(
        select(func.coalesce(func.sum(CommunityStockRow.quantity), 0)).where(
            CommunityStockRow.community_entity_id == town.id, CommunityStockRow.commodity == CommodityKind.DYE
        )
    )
    assert works.output == 55 and int(dye or 0) >= 5
    session.add_all(
        [
            ChemicalWorksRow(settlement_entity_id=town.id, product=ChemicalProduct.SOAP, output=100, locked=[]),
            ChemicalWorksRow(settlement_entity_id=town.id, product=ChemicalProduct.FERTILISER, output=100, locked=[]),
            ChemicalWorksRow(settlement_entity_id=town.id, product=ChemicalProduct.EXPLOSIVE, output=100, locked=[]),
        ]
    )
    await session.flush()
    assert (await soap_relief(session, rules))[world.regions[0].id] == rules.chemistry.soap_disease
    assert await fertilised(session, rules, town.id) > 1 and await blasted(session, rules, town.id) > 1


async def test_an_insurer_pays_a_life_from_its_pool_and_a_pool_run_dry_ruins_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await home(session, world, "Surety")
    insured = await mortal(session, "Brin", world, town.id)
    house = HouseholdRow(name="Brin's hearth", settlement_node_id=town.id, locked=[])
    session.add(house)
    await session.flush()
    session.add(HouseholdMemberRow(member_node_id=insured.id, household_id=house.id, role=HouseholdRole.HEAD))
    session.add(InsurerRow(insurer_entity_id=town.id, pool=2, locked=[]))
    session.add(InsurancePolicyRow(insurer_entity_id=town.id, holder_node_id=insured.id, cover=InsuranceCover.LIFE, sum_insured=20, locked=[]))
    session.add(InsurancePolicyRow(insurer_entity_id=town.id, holder_node_id=town.id, cover=InsuranceCover.CARGO, sum_insured=20, locked=[]))
    await session.flush()
    assert town.id in await cargo_holders(session)
    assert await claim(session, insured.id, InsuranceCover.LIFE, 5) == 5 and house.wealth == 5
    tally = InsuranceTally()
    await keep_insurance(await at(session, 3, insurance={"found_chance": 0}), tally)
    insurer = await session.get(InsurerRow, town.id)
    assert insurer is not None and insurer.ruined and tally.ruined == 1 and insurer.claims_seen == 1


async def test_a_work_becomes_its_makers_right_passes_to_the_heir_and_is_taken_with_insult(session: AsyncSession, world: CoreWorld) -> None:
    town = await home(session, world, "Lyrebury")
    maker = await mortal(session, "Sael", world, town.id)
    heir = await mortal(session, "Sael the Younger", world, town.id)
    await mortal(session, "Tamm", world, town.id)
    song = await entity(session, "The Long Air", EntityType.ARTWORK, ArtworkStats(renown=40), world_id=world.world.id, location_id=town.id)
    session.add(ArtworkProfileRow(artwork_entity_id=song.id, medium=ArtMode.MUSICAL, author_entity_id=maker.id))
    await session.flush()
    tally = RightsTally()
    await keep_rights(await at(session, 3, incorporeal={"infringe_chance": 0}), tally)
    right = await session.scalar(select(IncorporealRightRow).where(IncorporealRightRow.subject_node_id == song.id))
    assert right is not None and right.kind is RightKind.SONG and right.holder_node_id == maker.id and tally.claimed >= 1
    assert await pass_rights(session, maker.id, heir.id, 4) >= 1 and right.holder_node_id == heir.id and right.acquired is RightAcquired.INHERITED
    heir.location_id = town.id
    await keep_rights(await at(session, 5, incorporeal={"infringe_chance": 100}), tally)
    assert tally.infringed >= 1


async def test_spectacles_let_the_weak_sighted_read_and_a_cane_restores_walking(session: AsyncSession, world: CoreWorld) -> None:
    town = await home(session, world, "Glasswick", Technique.ASTRONOMY_INSTRUMENTS)
    elder = await mortal(session, "Oma", world, town.id, age=68)
    session.add(ConditionRow(bearer_node_id=elder.id, kind=ConditionKind.AGE_BLINDNESS, severity=3, source=HarmCause.AGE, since_epoch=1))
    await session.flush()
    assert not await has_reader(session, elder)
    tally = AidTally()
    await keep_aids(await at(session, 3, aids={"fit_chance": 100}), tally)
    assert await session.get(AssistiveAidRow, (elder.id, AssistiveAid.SPECTACLES)) is not None and tally.fitted == 1
    assert await has_reader(session, elder)
    session.add(AssistiveAidRow(holder_node_id=elder.id, kind=AssistiveAid.CANE, quality=100, locked=[]))
    await session.flush()
    reading = await reading_of(session, tuned_rules(), elder)
    assert reading.reader and reading.cane == tuned_rules().aids.cane_aid_pct / 100


async def test_a_town_that_keeps_time_sets_up_a_clock_that_raises_output_and_unrest(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    town = await home(session, world, "Bellhour", Technique.CALENDAR)
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None
    before = profile.unrest
    tally = ClockTally()
    await keep_clocks(await at(session, 3, clocks={"build_chance": 100}), tally)
    clock = await session.get(PublicClockRow, town.id)
    assert clock is not None and clock.kind is ClockKind.SUNDIAL and tally.built == 1
    assert await clock_output(session, rules, town.id) > 1 and await clock_muster(session, rules, town.id) > 1 and profile.unrest > before


async def test_games_shape_their_players_by_their_properties(session: AsyncSession, world: CoreWorld) -> None:
    town = await home(session, world, "Boardham")
    noble = await mortal(session, "Lord Cass", world, town.id)
    noble.social_class = SocialClass.NOBLE
    strategy = shaped("Fourfold", GameCategory.BOARD, world.people, 0)
    tactics = shaped("Fieldplan", GameCategory.TEAM, world.people, 0)
    chance = shaped("Knucklebones", GameCategory.CHANCE, world.people, 0)
    session.add_all([strategy, tactics, chance])
    await session.flush()
    for game in (strategy, tactics, chance):
        holding = made_by(game, world.people.id, 0)
        holding.strength = 100
        session.add(holding)
    profile = await session.get(SettlementProfileRow, town.id)
    assert profile is not None
    crime = profile.crime
    await session.flush()
    tally = GameTally()
    await keep_games(await at(session, 3, games={"invent_chance": 0, "strategy_xp": 50}), tally)
    trained = await session.scalar(select(SkillRow).where(SkillRow.holder_node_id == noble.id, SkillRow.skill == SkillKind.TACTICS))
    planned = await session.scalar(select(SkillRow).where(SkillRow.holder_node_id == noble.id, SkillRow.skill == SkillKind.STRATEGY))
    assert trained is not None and planned is not None and tally.trained >= 2 and tally.gambled >= 1 and profile.crime > crime


async def test_a_people_that_knows_logic_finds_the_zero_and_reckons_sharper(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    town = await home(session, world, "Countwell")
    session.add(HolderTechniqueRow(holder_entity_id=world.people.id, technique=Technique.LOGIC))
    await session.flush()
    tally = NumberTally()
    await keep_numbers(await at(session, 3, numeracy={"milestone_chance": 100}), tally)
    system = await session.get(NumberSystemRow, world.people.id)
    assert system is not None and system.zero and tally.milestones == 1 and system.base in {10, 12, 20, 60}
    assert await reckoned(session, town.id, rules.numeracy.tax_pct) > 1
    assert await notation_boost(session, rules, town.id, KnowledgeBranch.ASTRONOMY) > 1
    assert await notation_boost(session, rules, town.id, KnowledgeBranch.WARFARE) == 1


async def test_links_and_affinities_strengthen_magic_and_a_link_is_evidence_against_the_accused(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules()
    town = await home(session, world, "Hexmere")
    caster = await mortal(session, "Wren", world, town.id)
    target = await mortal(session, "Ash", world, town.id)
    session.add(SympatheticLinkRow(holder_node_id=caster.id, target_node_id=target.id, token=LinkToken.HAIR, strength=100, locked=[]))
    case = CrimeCaseRow(settlement_entity_id=town.id, crime=CrimeKind.THEFT, accused_entity_id=caster.id, stage=CaseStage.TRIAL, opened_epoch=3, locked=[])
    session.add(case)
    await session.flush()
    session.add(AccusationRow(accused_node_id=caster.id, case_id=case.id, settlement_entity_id=town.id, locked=[]))
    await session.flush()
    assert await link_strength(session, caster.id, target.id) == 100 and await link_boost(session, rules, caster.id, target.id) > 1
    material = await session.scalar(select(WorldMaterialRow).order_by(WorldMaterialRow.id).limit(1))
    if material is not None:
        session.add(MaterialAffinityRow(material_id=material.id, school=MagicSchool.EARTH, mode=AffinityMode.WORN, power=100, locked=[]))
        await session.flush()
        assert await affinity_value(session, rules, material.id) == 1 + rules.affinities.mining_pct / 100
    tally = SympathyTally()
    await keep_sympathy(await at(session, 3, sympathy={"take_chance": 0, "decay": 0}), tally)
    laid = await session.scalar(select(EvidenceRow).where(EvidenceRow.case_id == case.id, EvidenceRow.kind == EvidenceKind.MAGIC))
    assert laid is not None and laid.points_to_node_id == caster.id and tally.evidence == 1


async def test_shared_feeling_in_a_land_of_magic_takes_shape_feeds_and_can_be_bound(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    set_stats(region, magic=90)
    town = await home(session, world, "Glee")
    revellers = [await mortal(session, f"Reveller {index}", world, town.id) for index in range(3)]
    session.add_all(
        [ThoughtRow(holder_node_id=item.id, kind=ThoughtKind.MARRIED, emotion=Emotion.JOY, intensity=40, epoch=3, decay_pct=10) for item in revellers]
    )
    await session.flush()
    tally = SpiritTally()
    await keep_spirits(await at(session, 3, emotion_spirits={"spawn_from": 100, "spawn_density": 50}), tally)
    spirit = await session.scalar(select(EmotionSpiritRow).where(EmotionSpiritRow.region_entity_id == region.id))
    assert spirit is not None and spirit.emotion is Emotion.JOY and tally.born == 1
    assert await has_flag(session, region.id, EntityFlag.OMEN)
    feelings = await spirit_feelings(session, tuned_rules())
    assert any(town.id in towns and feeling is Emotion.JOY for towns, feeling, _ in feelings)
    assert await bind_spirit(session, revellers[0].id, region.id) and spirit.bound_by_node_id == revellers[0].id
    await keep_spirits(await at(session, 4), tally)
    assert tally.reagents > 0 and (stat(region, "magic") or 0) == 90


async def test_an_owner_holding_its_poachers_in_contempt_goes_to_war_over_its_waters(session: AsyncSession, world: CoreWorld) -> None:
    owner = await home(session, world, "Netholm")
    poacher = await settlement(session, "Hookby", world, world.regions[0])
    water = await entity(session, "The Narrows", EntityType.RESOURCE, ResourceStats(abundance=60), world_id=world.world.id, location_id=world.regions[0].id)
    session.add(
        ResourceProfileRow(
            resource_entity_id=water.id, commodity=CommodityKind.FISH, reserve=100, initial_reserve=100, richness=50, extraction_difficulty=10, quality=50
        )
    )
    session.add(ResourceWorkerRow(resource_entity_id=water.id, community_entity_id=poacher.id, workers=20))
    await session.flush()
    session.add(
        CatchGroundRow(
            source_entity_id=water.id,
            region_entity_id=world.regions[0].id,
            ground=CatchGround.FISHERY,
            gear=Gear.NETS,
            right=CatchRight.OWNED,
            owner_node_id=owner.id,
            locked=[],
        )
    )
    await session.flush()
    tally = GroundTally()
    await keep_grounds(await at(session, 3, grounds={"poach_opinion": 100, "war_at": -1, "war_pct": 100}), tally)
    war = await session.scalar(
        select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.war_cause == WarCause.RESOURCE, BondRow.source_node_id == owner.id)
    )
    assert tally.poached == 1 and tally.wars == 1 and war is not None


async def test_numeracy_and_a_telescope_sharpen_a_forecast_of_the_long_seasons(session: AsyncSession, world: CoreWorld) -> None:
    town = await home(session, world, "Starwatch")
    scholar = await mortal(session, "Ilen", world, town.id)
    session.add(SkillRow(holder_node_id=scholar.id, skill=SkillKind.ASTRONOMY, level=3, peak=3, last_used_epoch=1, source=SkillSource.PRACTICE))
    session.add(NumberSystemRow(people_entity_id=world.people.id, base=10, numeracy=100, zero=True, notation=Notation.POSITIONAL, locked=[]))
    session.add(AssistiveAidRow(holder_node_id=scholar.id, kind=AssistiveAid.TELESCOPE, quality=100, locked=[]))
    season = IrregularSeasonRow(
        world_id=world.world.id, cause=SeasonCause.ORBIT, spell=SeasonSpell.WINTER, severity=50, spell_length=4, spell_started_epoch=2, locked=[]
    )
    session.add(season)
    await session.flush()
    rules = {"scholar_skill": 1, "scholar_error": 13}
    await keep_seasons(await at(session, 3, long_seasons=rules, numeracy={"forecast_pct": 50}, aids={"telescope_forecast_pct": 50}), SeasonTally())
    forecast = await session.scalar(select(WinterForecastRow).where(WinterForecastRow.people_entity_id == world.people.id))
    assert forecast is not None and forecast.predicted_end_epoch == 6
