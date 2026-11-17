from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.ages_lines import mortal_ages_lines, son_ages_lines
from aerona.agents.context.chronicle_facts import payoff_facts, tale_facts, tales_of
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.ages import (
    AgeEchoRow,
    AgeRow,
    ArcBeatRow,
    ArcFigureRow,
    ArcRow,
    EcoTransformationRow,
    FormationHistoryRow,
    IrregularSeasonRow,
    SetupRow,
    WinterForecastRow,
)
from aerona.db.tables.agrarian import FamineLoreRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.collective import AccountRow
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.physics import ImpactEventRow
from aerona.db.tables.sacred import ForesightRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.ages import AgeCycle, ArcOutcome, ArcRole, ArcStage, ArcTemplate, FormationZone, PayoffKind, SeasonCause, SeasonSpell, SetupKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import StoryletId
from aerona.domain.enums.culture import ProphecyPredicate
from aerona.domain.enums.cycles import LongPlanKind
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.sacred import ForesightSource, ForesightStatus
from aerona.domain.enums.society import Commodity, NaturalLaw, SocialClass
from aerona.domain.models.entity_stats import KnowledgeStats, LegendStats, PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.formation import FormationTally, form_worlds
from aerona.engine.cosmos.orbits import infer
from aerona.engine.cycles.ecology import EcologyTally, keep_transformations, remake, set_back
from aerona.engine.environment.long_seasons import SeasonTally, keep_seasons, winter_share
from aerona.engine.phases.environment import environment_survey
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import connect, has_flag
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.storyteller import control as tales
from aerona.engine.storyteller.ages import AgeTally, keep_ages, turn_age
from aerona.engine.storyteller.arcs import ArcTally, detect, keep_arcs, open_arc
from aerona.engine.storyteller.drama import DramaTally, keep_drama, pay_setups, pressed, pressing_foe, world_drama
from aerona.prompts import PromptId
from aerona.prompts.catalog import render
from aerona.prompts.contexts.narrative import VoicesContext
from aerona.services.integrity.ages_links import mend_ages_links
from tests.engine.core.factories import CoreWorld, add_empty_world, bond, entity, mortal, natural_law, settlement, tell_history, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "ages", rules=tuned_rules(**rules))


def society(town_id: int, food: int) -> CommunitySocietyRow:
    shares = {f"share_{item.value}": 10.0 for item in SocialClass}
    satisfaction = {f"satisfaction_{item.value}": 50 for item in SocialClass}
    return CommunitySocietyRow(
        entity_id=town_id, **shares, **satisfaction, stock_food=food, stock_ore=0, stock_goods=0, price_food=300, price_ore=100, price_goods=100
    )


async def test_a_new_world_takes_its_shape_from_its_forming_and_an_old_one_keeps_its_own(session: AsyncSession, world: CoreWorld) -> None:
    young, _ = await add_empty_world(session, "Quorvan")
    old, _ = await add_empty_world(session, "Thessin")
    young.created_epoch = 5
    young_physics = infer(tuned_rules(), young, None)
    old_physics = infer(tuned_rules(), old, None)
    session.add_all([young_physics, old_physics])
    await session.flush()
    before = old_physics.iron
    tally = FormationTally()
    await form_worlds(await at(session, 5, formation={"recorded_craters": 2}), tally)
    shaped = await session.get(FormationHistoryRow, young.id)
    kept = await session.get(FormationHistoryRow, old.id)
    assert shaped is not None and shaped.shaped and young_physics.iron == shaped.core_share
    assert young_physics.hydrosphere == shaped.water_delivered and young.magnetism == min(100, shaped.core_share * 2)
    assert kept is not None and not kept.shaped and old_physics.iron == before == kept.core_share
    craters = list(await session.scalars(select(ImpactEventRow).where(ImpactEventRow.world_id == young.id)))
    assert tally.shaped >= 1 and len(craters) == min(2, shaped.craters)


async def test_a_chaotic_orbit_brings_long_winters_that_starve_the_unprepared_more(session: AsyncSession, world: CoreWorld) -> None:
    home, _ = await add_empty_world(session, "Ysradel")
    physics = infer(tuned_rules(), home, None)
    physics.eccentricity = 0.4
    session.add(physics)
    folk = await entity(session, "Ysrani", EntityType.PEOPLE, PeopleStats(population=900), world_id=home.id)
    regions = list(await session.scalars(select(EntityRow).where(EntityRow.world_id == home.id, EntityRow.entity_type == EntityType.REGION)))
    heeding = await settlement(session, "Heedford", world, regions[0], population=900)
    careless = await settlement(session, "Carelow", world, regions[1], population=900)
    heeding.world_id = careless.world_id = home.id
    await bond(session, heeding.id, folk.id, BondKind.DESCENDS_FROM)
    session.add_all([society(heeding.id, 0), society(careless.id, 0)])
    await session.flush()
    for town in (heeding, careless):
        await shift_stock(session, tuned_rules(), town.id, Commodity.FOOD, 1000, epoch=1, flow=GoodsFlow.PRODUCTION)
    sage = await mortal(session, "Ilse", world, heeding.id)
    sage.world_id = home.id
    session.add(SkillRow(holder_node_id=sage.id, skill=SkillKind.ASTRONOMY, level=8, peak=8, last_used_epoch=1, source=SkillSource.PRACTICE))
    await session.flush()
    tally = SeasonTally()
    rules = {"shortest_spell": 1, "longest_spell": 1, "heed_base": 100, "winter_loss_pct": 50, "prepared_share": 20}
    await keep_seasons(await at(session, 3, long_seasons=rules), tally)
    row = await session.get(IrregularSeasonRow, home.id)
    assert row is not None and row.cause is SeasonCause.ORBIT
    row.severity = 100
    await session.flush()
    await keep_seasons(await at(session, 4, long_seasons=rules), tally)
    forecast = await session.scalar(select(WinterForecastRow).where(WinterForecastRow.people_entity_id == folk.id))
    assert row.spell is SeasonSpell.WINTER and forecast is not None and forecast.heeded and forecast.scholar_entity_id == sage.id
    fed = await stock(session, tuned_rules(), heeding.id, Commodity.FOOD)
    hungry = await stock(session, tuned_rules(), careless.id, Commodity.FOOD)
    assert fed > hungry and tally.starved == 2


async def test_a_people_that_remembers_its_famines_loses_less_to_a_long_winter(session: AsyncSession, world: CoreWorld) -> None:
    home, _ = await add_empty_world(session, "Corvane")
    regions = list(await session.scalars(select(EntityRow).where(EntityRow.world_id == home.id, EntityRow.entity_type == EntityType.REGION)))
    wise = await entity(session, "Corvani", EntityType.PEOPLE, PeopleStats(population=900), world_id=home.id)
    stored = await settlement(session, "Granary Hold", world, regions[0], population=900)
    bare = await settlement(session, "Barewick", world, regions[1], population=900)
    stored.world_id = bare.world_id = home.id
    await bond(session, stored.id, wise.id, BondKind.DESCENDS_FROM)
    session.add_all([society(stored.id, 0), society(bare.id, 0), FamineLoreRow(people_entity_id=wise.id, memory=80, famine_foods=True, storage=100, locked=[])])
    session.add(IrregularSeasonRow(world_id=home.id, spell=SeasonSpell.WINTER, spell_started_epoch=3, spell_length=5, severity=100, locked=[]))
    await session.flush()
    for town in (stored, bare):
        await shift_stock(session, tuned_rules(), town.id, Commodity.FOOD, 1000, epoch=1, flow=GoodsFlow.PRODUCTION)
    rules = {"winter_loss_pct": 50, "storage_ease_pct": 50, "famine_foods_share": 50}
    await keep_seasons(await at(session, 4, long_seasons=rules), SeasonTally())
    kept = await stock(session, tuned_rules(), stored.id, Commodity.FOOD)
    left = await stock(session, tuned_rules(), bare.id, Commodity.FOOD)
    assert 1000 - left == 500 and 1000 - kept == 120


async def test_a_natural_law_makes_seasons_irregular_until_it_is_lifted(session: AsyncSession, world: CoreWorld) -> None:
    law = await natural_law(session, world, "Long Measure", NaturalLaw.LONG_SEASONS)
    tally = SeasonTally()
    await keep_seasons(await at(session, 3), tally)
    row = await session.get(IrregularSeasonRow, world.world.id)
    assert row is not None and row.cause is SeasonCause.NATURAL_LAW and row.spell is SeasonSpell.SUMMER
    law.status, law.end_epoch = EntityStatus.DESTROYED, 4
    await session.flush()
    await keep_seasons(await at(session, 4, long_seasons={"longest_spell": 50, "shortest_spell": 50}), tally)
    assert await session.get(IrregularSeasonRow, world.world.id) is None and tally.settled == 1


async def test_a_plan_remakes_the_land_against_its_climate_and_its_folk(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3, eco_transformations={"step": 10, "resistance_pct": 100, "sabotage_chance": 100})
    plan = LongPlanRow(
        holder_node_id=world.son.id,
        target_node_id=world.regions[0].id,
        kind=LongPlanKind.ECOLOGICAL_TRANSFORMATION,
        name="The Greening",
        steps=10,
        progress=5,
        step_cost=0,
        locked=[],
    )
    session.add(plan)
    await settlement(session, "Dustwell", world, world.regions[0])
    await session.flush()
    work = EcoTransformationRow(plan_id=plan.id, target_moisture=90, target_forest=50, target_fertility=60, locked=[])
    mild = RegionEnvironmentRow(moisture=40, forest_cover=50, soil_fertility=60, temperature=50, rainfall=60, locked=[])
    harsh = RegionEnvironmentRow(moisture=40, forest_cover=50, soil_fertility=60, temperature=95, rainfall=10, locked=[])
    tally = EcologyTally()
    await remake(ctx, work, mild, tally)
    await remake(ctx, work, harsh, tally)
    assert mild.moisture == 50 and harsh.moisture < 50 and tally.resisted == 1
    session.add(work)
    await session.flush()
    await keep_transformations(ctx, tally)
    assert plan.progress == 4 and work.sabotage == 1 and tally.sabotaged == 1


async def test_a_turning_age_carries_tales_loses_arts_and_echoes_a_great_life_into_a_newborn(session: AsyncSession, world: CoreWorld) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.age_cycle = AgeCycle.CYCLIC
    town = await settlement(session, "Old Hearth", world, world.regions[0])
    folk = await entity(session, "Hearthfolk", EntityType.PEOPLE, PeopleStats(population=500), world_id=world.world.id)
    tale = await entity(session, "The Long Road", EntityType.LEGEND, LegendStats(), world_id=world.world.id)
    tale.affiliated_entity_id = folk.id
    art = await entity(session, "Star Reckoning", EntityType.KNOWLEDGE, KnowledgeStats(level=2, spread=30), world_id=world.world.id)
    hero = await mortal(session, "Aldis", world, town.id)
    session.add(MortalProfileRow(entity_id=hero.id, renown=90, locked=[]))
    await session.flush()
    ctx = await at(session, 3, ages={"carry_pct": 0, "rebirth_chance": 100})
    await keep_ages(ctx, AgeTally())
    first = await session.scalar(select(AgeRow).where(AgeRow.number == 1))
    assert first is not None
    await open_arc(ctx, hero.id, ArcTemplate.QUEST)
    opened = await turn_age(ctx, None)
    assert first.ended_epoch == 3 and opened.number == 2
    assert await session.scalar(select(AccountRow).where(AccountRow.subject_node_id == tale.id)) is not None
    assert await has_flag(session, art.id, EntityFlag.LOST)
    echo = await session.scalar(select(AgeEchoRow).where(AgeEchoRow.age_id == opened.id, AgeEchoRow.source_node_id == hero.id))
    assert echo is not None and echo.template is ArcTemplate.QUEST
    child = await mortal(session, "Brin", world, town.id)
    child.birth_epoch = 4
    await session.flush()
    tally = AgeTally()
    await keep_ages(await at(session, 4, ages={"rebirth_chance": 100}), tally)
    assert echo.echo_node_id == child.id and tally.reborn == 1
    reborn_arc = await session.scalar(select(ArcRow).where(ArcRow.subject_node_id == child.id, ArcRow.echo_id == echo.id))
    soul = await session.scalar(
        select(BondRow).where(BondRow.source_node_id == hero.id, BondRow.target_node_id == child.id, BondRow.kind == BondKind.SOUL_DESCENDED_TO)
    )
    assert reborn_arc is not None and soul is not None


async def test_an_age_turns_by_itself_once_its_period_is_spent(session: AsyncSession, world: CoreWorld) -> None:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.age_cycle = AgeCycle.CYCLIC
    await session.flush()
    await keep_ages(await at(session, 3, ages={"period_epochs": 4}), AgeTally())
    tally = AgeTally()
    await keep_ages(await at(session, 6, ages={"period_epochs": 4}), tally)
    assert tally.turned == 0
    await keep_ages(await at(session, 7, ages={"period_epochs": 4}), tally)
    second = await session.scalar(select(AgeRow).where(AgeRow.number == 2))
    assert tally.turned == 1 and second is not None and second.began_epoch == 7


async def test_a_killing_of_kin_starts_a_revenge_that_ends_when_the_avenger_slays_the_foe(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brackmoor", world, world.regions[0])
    avenger = await mortal(session, "Tarn", world, town.id)
    victim = await mortal(session, "Old Tarn", world, town.id)
    killer = await mortal(session, "Varek", world, town.id)
    await bond(session, victim.id, avenger.id, BondKind.PARENT_OF, 2)
    await bond(session, killer.id, victim.id, BondKind.KILLED, 2)
    ctx = await at(session, 3, arcs={"detect_chance": 100})
    tally = ArcTally()
    await detect(ctx, tally)
    arc = await session.scalar(select(ArcRow).where(ArcRow.subject_node_id == avenger.id, ArcRow.template == ArcTemplate.REVENGE))
    assert arc is not None and tally.begun >= 1
    figure = await session.get(ArcFigureRow, (arc.id, killer.id))
    assert figure is not None and figure.role is ArcRole.FOE
    ctx = await at(session, 4)
    await tell_history(ctx, "Tarn met Varek at the ford.", ids=[avenger.id, killer.id])
    await keep_arcs(ctx, ArcTally())
    assert arc.stage is ArcStage.RISING and arc.beats == 1
    await connect(session, avenger.id, killer.id, BondKind.KILLED, 5)
    killer.status, killer.end_epoch = EntityStatus.DEAD, 5
    await session.flush()
    tally = ArcTally()
    await keep_arcs(await at(session, 5), tally)
    assert arc.outcome is ArcOutcome.FULFILLED and tally.fulfilled == 1


async def test_a_stalled_revenge_presses_its_avenger_toward_the_foe_and_its_counterpart_keeps_rhythm(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Stillwater", world, world.regions[0])
    one = await mortal(session, "Iona", world, town.id)
    two = await mortal(session, "Cass", world, town.id)
    ctx = await at(session, 2)
    feud = await open_arc(ctx, one.id, ArcTemplate.REVENGE, ((two.id, ArcRole.FOE),))
    rival = await open_arc(ctx, two.id, ArcTemplate.RIVALRY, ((one.id, ArcRole.RIVAL),))
    tally = DramaTally()
    await keep_drama(await at(session, 9, arcs={"stall_epochs": 3, "drama_step": 50}), [], tally)
    assert feud.drama == 50 and tally.pressed == 2
    found = await pressing_foe(ctx, one.id)
    assert found == (50, two.id) and pressed(ctx, 10, 100) > 10
    await keep_drama(await at(session, 9, arcs={"counterpoint": 15, "stall_epochs": 50}), [feud], DramaTally())
    assert rival.drama == 65 and feud.drama == 0


async def test_a_foresight_is_set_up_and_paid_off_and_the_chronicler_is_told(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Seers Rest", world, world.regions[0])
    seer = await mortal(session, "Nima", world, town.id)
    doomed = await mortal(session, "Rolf", world, town.id)
    sight = ForesightRow(
        seer_node_id=seer.id, subject_node_id=doomed.id, predicate=ProphecyPredicate.DIES, source=ForesightSource.POWER, made_epoch=3, locked=[]
    )
    session.add(sight)
    await session.flush()
    await keep_drama(await at(session, 3), [], DramaTally())
    setup = await session.scalar(select(SetupRow).where(SetupRow.kind == SetupKind.FORESIGHT, SetupRow.source_id == sight.id))
    assert setup is not None and setup.subject_node_id == doomed.id
    sight.status = ForesightStatus.FULFILLED
    await session.flush()
    tally = DramaTally()
    await keep_drama(await at(session, 4), [], tally)
    assert setup.payoff is PayoffKind.FULFILLED and setup.paid_epoch == 4 and tally.fulfilled == 1
    scope = await load_scope(session, tuned_rules())
    payoffs = await payoff_facts(scope, 4)
    assert payoffs and payoffs[0].subject == doomed.name
    await open_arc(await at(session, 4), seer.id, ArcTemplate.QUEST)
    tales = await tale_facts(scope, 4)
    assert any(item.subject == seer.name for item in tales)
    voices = render(
        PromptId.VOICES_USER,
        VoicesContext(lore_language="english", rules=tuned_rules(), world_name="W", world_header="W", age=4, tales=tales, payoffs=payoffs),
    )
    assert "TALES UNDER WAY" in voices and "PAYOFFS THIS AGE" in voices and seer.name in voices and doomed.name in voices
    await open_arc(await at(session, 4), world.son.id, ArcTemplate.APOTHEOSIS)
    assert any(item.subject == world.son.name for item in await tale_facts(scope, 4))
    assert [item.template for item in await tales_of(scope, world.son.id)] == ["apotheosis"]


async def test_integrity_fails_the_tales_of_vanished_lives_and_lapses_their_setups(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Gone", world, world.regions[0])
    ghost = await mortal(session, "Wisp", world, town.id)
    ctx = await at(session, 3)
    arc = await open_arc(ctx, ghost.id, ArcTemplate.QUEST)
    setup = SetupRow(kind=SetupKind.OMEN, subject_node_id=ghost.id, locked=[])
    session.add(setup)
    ghost.status, ghost.end_epoch = EntityStatus.DEAD, 3
    await session.flush()
    assert await mend_ages_links(session, 4) >= 2
    await session.refresh(arc)
    await session.refresh(setup)
    assert arc.outcome is ArcOutcome.FAILED and setup.payoff is PayoffKind.LAPSED


async def test_mortals_and_gods_read_their_tales_and_seasons_in_context(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Readmoor", world, world.regions[0])
    hero = await mortal(session, "Edda", world, town.id)
    rival = await mortal(session, "Gale", world, town.id)
    ctx = await at(session, 3)
    await open_arc(ctx, hero.id, ArcTemplate.RIVALRY, ((rival.id, ArcRole.RIVAL),))
    session.add(IrregularSeasonRow(world_id=world.world.id, spell=SeasonSpell.WINTER, spell_started_epoch=2, locked=[]))
    await session.flush()
    scope = await load_scope(session, tuned_rules())
    lines = await mortal_ages_lines(scope, hero)
    assert any("rivalry" in line for line in lines) and any("long winter" in line for line in lines)
    assert any("your part is rival" in line for line in await mortal_ages_lines(scope, rival))
    world.son.current_world_id = world.world.id
    assert any("tale" in line for line in await son_ages_lines(scope, world.son))


async def test_a_quest_runs_through_the_stages_of_the_heros_journey_and_keeps_each_beat_whole(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Wayford", world, world.regions[0])
    hero = await mortal(session, "Selk", world, town.id)
    guide = await mortal(session, "Orla", world, town.id)
    ctx = await at(session, 2)
    arc = await open_arc(ctx, hero.id, ArcTemplate.QUEST, ((guide.id, ArcRole.MENTOR),))
    assert arc.stage is ArcStage.CALL
    long_line = "Selk and Orla crossed the high pass together. " * 20
    await tell_history(await at(session, 3), long_line, ids=[hero.id, guide.id])
    await keep_arcs(await at(session, 3), ArcTally())
    assert arc.stage is ArcStage.REFUSAL
    beat = await session.scalar(select(ArcBeatRow).where(ArcBeatRow.arc_id == arc.id, ArcBeatRow.stage == ArcStage.REFUSAL))
    told = await session.scalar(select(ChronicleRow.text).where(ChronicleRow.template_key == "player.history", ChronicleRow.text.startswith("Selk and Orla")))
    assert beat is not None and told is not None and beat.text == told and len(beat.text) > 480
    feud = await open_arc(ctx, guide.id, ArcTemplate.REVENGE, ((hero.id, ArcRole.FOE),))
    assert feud.stage is ArcStage.INCITING


async def test_a_gods_portent_presses_the_tale_of_its_subject_and_is_paid_by_its_next_beat(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Omenmere", world, world.regions[0])
    marked = await mortal(session, "Ysa", world, town.id)
    other = await mortal(session, "Brann", world, town.id)
    ctx = await at(session, 2)
    arc = await open_arc(ctx, marked.id, ArcTemplate.RIVALRY, ((other.id, ArcRole.RIVAL),))
    setup = await tales.add_setup(ctx, SetupKind.PORTENT, world.son.id, marked.id)
    await keep_drama(await at(session, 3, arcs={"setup_pull": 25, "stall_epochs": 50}), [], DramaTally())
    assert arc.drama == 25 and setup.payoff is PayoffKind.OPEN
    await tell_history(await at(session, 4), "Ysa and Brann met at the market.", ids=[marked.id, other.id])
    await keep_arcs(await at(session, 4), ArcTally())
    tally = DramaTally()
    await pay_setups(await at(session, 5), tally)
    assert setup.payoff is PayoffKind.FULFILLED and setup.payoff_text == "Ysa and Brann met at the market." and tally.fulfilled == 1


async def test_a_stalled_tale_presses_only_the_storylets_that_would_bring_its_next_beat(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Lovers Leap", world, world.regions[0])
    lover = await mortal(session, "Arin", world, town.id)
    beloved = await mortal(session, "Ilse", world, town.id)
    ctx = await at(session, 2)
    arc = await open_arc(ctx, lover.id, ArcTemplate.FORBIDDEN_LOVE, ((beloved.id, ArcRole.BELOVED),))
    arc.drama = 80
    await session.flush()
    assert await world_drama(ctx, world.world.id, StoryletId.WEDDING_CHALLENGE) == 80
    assert await world_drama(ctx, world.world.id, StoryletId.HOARDED_STORE) == 0


async def test_a_long_winter_cuts_the_harvest_of_its_world_by_its_severity(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3, long_seasons={"winter_harvest_pct": 60})
    season = IrregularSeasonRow(world_id=world.world.id, cause=SeasonCause.ORBIT, spell=SeasonSpell.SUMMER, severity=50, spell_length=3, locked=[])
    session.add(season)
    await session.flush()
    assert await winter_share(ctx, world.world.id) == 100
    season.spell = SeasonSpell.WINTER
    assert await winter_share(ctx, world.world.id) == 70


async def test_a_turning_age_remakes_every_world_fades_its_lore_and_counts_rightly(session: AsyncSession, world: CoreWorld) -> None:
    far, _ = await add_empty_world(session, "Farrow")
    folk = await entity(session, "Farfolk", EntityType.PEOPLE, PeopleStats(population=300), world_id=world.world.id)
    tale = await entity(session, "The Only Tale", EntityType.LEGEND, LegendStats(spread=80), world_id=world.world.id)
    tale.affiliated_entity_id = folk.id
    craft = await entity(session, "Far Craft", EntityType.KNOWLEDGE, KnowledgeStats(level=2, spread=30), world_id=far.id)
    await session.flush()
    await turn_age(await at(session, 3, ages={"carry_pct": 30}), None)
    assert tale.stats.model_dump().get("spread") == 24
    ruins = await session.scalar(select(EntityRow.id).where(EntityRow.world_id == far.id, EntityRow.subtype == "ruin of the previous creation"))
    told = await session.scalar(select(ChronicleRow.text).where(ChronicleRow.template_key == "ages.turned"))
    assert told is not None and "1 tale was half-remembered" in told
    await turn_age(await at(session, 4, ages={"carry_pct": 0}), None)
    assert await has_flag(session, craft.id, EntityFlag.LOST)
    assert ruins is not None


async def test_a_moon_forms_where_its_planet_circles_its_star(session: AsyncSession, world: CoreWorld) -> None:
    planet, _ = await add_empty_world(session, "Glacis")
    moon, _ = await add_empty_world(session, "Shard")
    planet.orbit, moon.orbit, moon.parent_world_id = 40.0, 0.05, planet.id
    await session.flush()
    await form_worlds(await at(session, 3), FormationTally())
    history = await session.get(FormationHistoryRow, moon.id)
    assert history is not None and history.zone is FormationZone.OUTER


async def test_a_sabotage_takes_the_land_back_a_step_away_from_the_plans_aim(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3, eco_transformations={"step": 10, "sabotage_loss": 1})
    plan = LongPlanRow(
        holder_node_id=world.son.id,
        target_node_id=world.regions[0].id,
        kind=LongPlanKind.ECOLOGICAL_TRANSFORMATION,
        name="The Drowning",
        steps=10,
        progress=5,
        step_cost=0,
        locked=[],
    )
    session.add(plan)
    await session.flush()
    work = EcoTransformationRow(plan_id=plan.id, target_moisture=90, target_forest=10, target_fertility=60, locked=[])
    session.add(work)
    await environment_survey(ctx)
    land = await session.get(RegionEnvironmentRow, world.regions[0].id)
    assert land is not None
    land.moisture, land.forest_cover, land.soil_fertility = 50, 40, 60
    await session.flush()
    await set_back(ctx, plan, work)
    assert (land.moisture, land.forest_cover, land.soil_fertility) == (40, 50, 60)
    assert plan.progress == 4 and work.sabotage == 1
