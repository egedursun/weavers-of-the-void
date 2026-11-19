from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.body import ConditionRow, InjuryRow, MaimedCohortRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.disease import DiseaseProfileRow, EndemicDiseaseRow, ImmunityRow, OutbreakRow, QuarantineRow
from aerona.db.tables.ecology import SpeciesHostRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow, EntityTraitRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.body import BodyFunction, Capacity, ConditionKind, HarmCause, InjuryKind, MaimedKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, Job
from aerona.domain.enums.disease import DiseaseTarget, DiseaseVector, OutbreakStatus, SpreadPath
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityType
from aerona.domain.enums.environment import RiverClass, ScarKind, TemperatureBand
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import EventStats, SpeciesStats
from aerona.engine.body.book import afflicted_parts, anatomy_for, ensure_body
from aerona.engine.body.capacities import BearerStats, BodyState, capacities
from aerona.engine.body.hits import Harm
from aerona.engine.demography.cohorts import apply_flow, cohorts_of, seed, total
from aerona.engine.demography.control import set_dormancy
from aerona.engine.demography.labour import condition_work, fighting_age
from aerona.engine.demography.promotion import doze, matching_wound, orphan_memory, sync_maimed
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.control import DiseaseDesign, ProfileValue, create_disease, edit_disease
from aerona.engine.disease.course import army_weight, host_gone, run_course, settle_endemic
from aerona.engine.disease.harm import disease_harm, lasting_illness, sick_levy, sick_work, struck_part
from aerona.engine.disease.history import PLAGUE_FIXUP, backfill_plagues
from aerona.engine.disease.load import endemic_repel
from aerona.engine.disease.outbreaks import STATUS_LOCK, host_for, open_outbreak, spread_factor
from aerona.engine.disease.sickness import sicken_cohorts
from aerona.engine.disease.vectors import Spot, vector_factor
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.phase import Phase
from aerona.engine.phases.disasters import route_chance, strike_plague
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, mortal, settlement, son, tuned

RULES = Rules()


def ground(**values: object) -> RegionEnvironmentRow:
    base: dict[str, object] = {
        "river_class": RiverClass.NONE,
        "wetland": 0,
        "temperature_band": TemperatureBand.TEMPERATE,
        "rainfall": 50,
        "magic_density": 0,
        "scars": {},
        "disease_load": 0,
    }
    base.update(values)
    return RegionEnvironmentRow(**base)


async def forge(realm: Realm, **values: ProfileValue) -> EntityRow:
    chosen: dict[str, ProfileValue] = {"virulence": 40, "lethality": 30, **values}
    design = DiseaseDesign(name=None, values=chosen, hold=True)
    return await create_disease(context(realm.session), realm.region.id, design, son_id=None)


async def book_of(realm: Realm, rules: Rules = RULES) -> DiseaseBook:
    return await DiseaseBook.load(realm.session, rules, 3)


async def host_species(realm: Realm, name: str, abundance: int, *, bearer: bool = True) -> EntityRow:
    species = await make(realm.session, name, EntityType.SPECIES, SpeciesStats(), world_id=realm.world.id)
    realm.session.add(SpeciesRangeRow(species_entity_id=species.id, region_entity_id=realm.region.id, abundance=abundance))
    if bearer:
        realm.session.add(EntityTraitRow(entity_id=species.id, trait=CreatureTrait.PLAGUE_BEARER))
    await realm.session.flush()
    return species


async def test_a_forged_disease_keeps_its_design_its_locks_and_its_origin(realm: Realm) -> None:
    disease = await forge(realm, vector="water", target_functions=["breath", "sight"], incubation=4, climate_affinity="wet")
    profile = await realm.session.get(DiseaseProfileRow, disease.id)
    assert profile is not None
    assert profile.vector is DiseaseVector.WATER and profile.incubation == 4
    assert profile.target_functions == ["breath", "sight"]
    assert set(profile.locked) == {"virulence", "lethality", "vector", "target_functions", "incubation", "climate_affinity"}
    incident = await realm.session.get(IncidentRow, profile.origin_incident_id or 0)
    assert incident is not None and incident.kind in {"disease.loosed", "disease.loosed_host"}
    await edit_disease(context(realm.session), disease.id, {}, release=["vector"])
    assert "vector" not in profile.locked


async def test_each_vector_branches_on_its_own_ground(realm: Realm) -> None:
    town = await settlement(realm, "Well", population=4000)
    rows = {vector: await forge(realm, vector=vector.value, target_functions=["vital"]) for vector in DiseaseVector}
    book = await book_of(realm)

    def factor(vector: DiseaseVector, land: RegionEnvironmentRow, path: SpreadPath = SpreadPath.ORIGIN) -> float:
        return vector_factor(book, book.profiles[rows[vector].id], Spot(town, land, realm.region.id, path))

    assert factor(DiseaseVector.WATER, ground(river_class=RiverClass.GREAT_RIVER)) > factor(DiseaseVector.WATER, ground())
    assert factor(DiseaseVector.AIR, ground(temperature_band=TemperatureBand.COLD)) > factor(DiseaseVector.AIR, ground())
    assert factor(DiseaseVector.TOUCH, ground(), SpreadPath.ROUTE) > factor(DiseaseVector.TOUCH, ground(), SpreadPath.ORIGIN)
    assert factor(DiseaseVector.VOID, ground(scars={ScarKind.LEAK_WOUND.value: 80})) > factor(DiseaseVector.VOID, ground())
    assert factor(DiseaseVector.SPIRIT, ground(magic_density=90)) > factor(DiseaseVector.SPIRIT, ground())
    book.ley.add(realm.region.id)
    assert factor(DiseaseVector.SPIRIT, ground()) > 1.0 * RULES.epidemiology.spirit_faith_pct / 100
    hostless = factor(DiseaseVector.BITE, ground())
    book.hosts[rows[DiseaseVector.BITE].id] = {999}
    book.ranges[(999, realm.region.id)] = 100
    assert factor(DiseaseVector.BITE, ground()) > hostless * 10
    unbound = factor(DiseaseVector.CURSE, ground())
    god = await son(realm.session, "Hexer", realm.world.id)
    rows[DiseaseVector.CURSE].creator_son_id = god.id
    book.living_sons.add(god.id)
    assert factor(DiseaseVector.CURSE, ground()) > unbound


async def test_sanitation_matters_most_against_water_and_not_at_all_against_a_curse(realm: Realm) -> None:
    town = await settlement(realm, "Clean", population=4000)
    water = await forge(realm, vector="water", target_functions=["vital"])
    curse = await forge(realm, vector="curse", target_functions=["vital"])
    air = await forge(realm, vector="air", target_functions=["breath"])
    book = await book_of(realm)
    land = ground()
    dirty = {disease.id: spread_factor(book, disease.id, town, land, source_region=None) for disease in (water, curse, air)}
    book.sanitation[realm.region.id] = 100
    clean = {disease.id: spread_factor(book, disease.id, town, land, source_region=None) for disease in (water, curse, air)}
    assert clean[curse.id] == dirty[curse.id]
    assert clean[water.id] / dirty[water.id] < clean[air.id] / dirty[air.id] < 1


async def test_herd_immunity_stops_spread_and_quarantine_holds_it_back(realm: Realm) -> None:
    town = await settlement(realm, "Herd", population=4000)
    disease = await forge(realm, vector="air", target_functions=["breath"], incubation=0)
    book = await book_of(realm)
    free = spread_factor(book, disease.id, town, ground(), source_region=None)
    book.quarantines[realm.region.id] = QuarantineRow(region_entity_id=realm.region.id, started_epoch=1, until_epoch=9)
    sealed = spread_factor(book, disease.id, town, ground(), source_region=None)
    assert sealed == free * RULES.epidemiology.quarantine_spread_pct / 100
    for band in AgeBand:
        book.immunity.setdefault((town.id, disease.id), {})[band] = ImmunityRow(immune_pct=100, age_band=band)
    assert spread_factor(book, disease.id, town, ground(), source_region=None) == 0.0


async def test_incubation_spreads_unseen_past_a_quarantine(realm: Realm) -> None:
    town = await settlement(realm, "Unseen", population=4000)
    hidden = await forge(realm, vector="air", target_functions=["breath"], incubation=8)
    book = await book_of(realm)
    book.quarantines[realm.region.id] = QuarantineRow(region_entity_id=realm.region.id, started_epoch=1, until_epoch=9)
    share = book.hidden_share(hidden.id)
    assert share == min(1.0, 8 * RULES.epidemiology.incubation_hidden_pct / 100)
    seen = spread_factor(book, hidden.id, town, ground(), source_region=None)
    unseen = spread_factor(book, hidden.id, town, ground(), source_region=None, hidden=share)
    assert unseen > seen * 2


async def test_incubation_delays_the_first_toll(realm: Realm) -> None:
    quick_town = await settlement(realm, "Quick", population=20000)
    slow_town = await settlement(realm, "Slow", population=20000, location_id=realm.far_region.id)
    quick = await forge(realm, vector="air", target_functions=["breath"], incubation=0)
    slow = await forge(realm, vector="air", target_functions=["breath"], incubation=8)
    ctx = context(realm.session)
    await strike_plague(ctx, quick_town, 60, disease=quick)
    await strike_plague(ctx, slow_town, 60, disease=slow)
    assert (stat(slow_town, "population") or 0) > (stat(quick_town, "population") or 0)


async def test_route_chance_scales_with_trade_volume_and_army_spread_with_size() -> None:
    table = RULES.epidemiology
    assert route_chance(RULES, 0) == table.route_spread_chance * table.route_volume_floor_pct / 100
    assert route_chance(RULES, table.route_busy_volume) == table.route_spread_chance
    assert route_chance(RULES, table.route_busy_volume * 100) == table.route_spread_chance * table.route_volume_cap_pct / 100
    assert army_weight(table, table.army_spread_size // 2) == 0.5
    assert army_weight(table, table.army_spread_size * 100) == table.army_size_cap_pct / 100


async def test_target_functions_wound_the_matching_organ_and_leave_a_matching_weakness(realm: Realm) -> None:
    disease = await forge(realm, vector="air", target_functions=["breath"], chronic_rate=60)
    profile = await realm.session.get(DiseaseProfileRow, disease.id)
    patient = await mortal(realm, "Coughing Ane")
    ctx = context(realm.session)
    part = await struck_part(ctx, patient, profile)
    body = await ensure_body(realm.session, RULES, patient, 3)
    anatomy = anatomy_for(body)
    assert part is not None and BodyFunction.BREATH in (anatomy.part(part).functions if anatomy.part(part) else ())
    harm = await disease_harm(ctx, patient, profile, Harm(10, HarmCause.DISASTER, "died of the cough"))
    assert harm.part == part and harm.kind is InjuryKind.SICKNESS
    condition = await lasting_illness(ctx, patient, profile)
    assert condition is not None and condition.kind is ConditionKind.CHRONIC_ILLNESS and condition.part == part
    stats = BearerStats(strength=50, agility=50, intellect=50, charisma=50, endurance=50)
    whole = capacities(RULES, stats, BodyState(anatomy, (), anatomy.full_counts, 0))
    rotten = capacities(RULES, stats, BodyState(anatomy, (), anatomy.full_counts, 0, afflicted=afflicted_parts(RULES, [condition])))
    assert rotten[Capacity.MOBILITY] < whole[Capacity.MOBILITY]
    assert rotten[Capacity.SCHOLARSHIP] == whole[Capacity.SCHOLARSHIP]


async def test_sick_cohorts_work_and_fight_by_the_function_struck() -> None:
    assert sick_work(RULES, Job.MINING, frozenset({DiseaseTarget.BREATH})) == RULES.epidemiology.sick_work_pct / 100
    assert sick_work(RULES, Job.SCHOLARSHIP, frozenset({DiseaseTarget.BREATH})) == RULES.epidemiology.sick_spared_work_pct / 100
    assert condition_work(RULES, CohortCondition.MAIMED, Job.FARMING) == 1 - RULES.maimed.labour_loss_pct / 100
    assert sick_levy(RULES, frozenset({DiseaseTarget.BREATH})) == 0.0
    assert sick_levy(RULES, frozenset({DiseaseTarget.SKIN})) == RULES.epidemiology.sick_levy_pct / 100


async def test_outbreaks_lay_cohorts_sick_the_sick_die_first_and_cohorts_sum_to_population(realm: Realm) -> None:
    town = await settlement(realm, "Fevered", population=10000)
    disease = await forge(realm, vector="air", target_functions=["breath"], virulence=80)
    ctx = context(realm.session)
    await seed(realm.session, RULES, town, 3)
    book = await book_of(realm)
    outbreak = await open_outbreak(ctx, book, disease, realm.region.id, path=SpreadPath.ORIGIN, severity=80)
    fell, _ = await sicken_cohorts(ctx, book)
    rows = await cohorts_of(realm.session, town.id)
    sick = sum(row.count for key, row in rows.items() if key[3] is CohortCondition.SICK)
    assert fell == sick > 0
    assert total(rows) == stat(town, "population")
    adults = await fighting_age(realm.session, town.id, RULES)
    assert adults is not None and adults < sum(row.count for key, row in rows.items() if key[0] is AgeBand.ADULT)
    await apply_flow(realm.session, RULES, town, -500, category=FlowCategory.PLAGUE, epoch=3)
    after = await cohorts_of(realm.session, town.id)
    lost_sick = sick - sum(row.count for key, row in after.items() if key[3] is CohortCondition.SICK)
    assert lost_sick > 500 * sick / 10000
    outbreak.status = OutbreakStatus.ENDED
    book.outbreaks = []
    _, recovered = await sicken_cohorts(ctx, book)
    assert recovered > 0
    assert sum(row.count for key, row in (await cohorts_of(realm.session, town.id)).items() if key[3] is CohortCondition.SICK) == 0


async def test_maimed_civilians_form_the_maimed_cohort(realm: Realm) -> None:
    town = await settlement(realm, "Scarred", population=5000)
    await seed(realm.session, RULES, town, 3)
    realm.session.add(MaimedCohortRow(community_entity_id=town.id, kind=MaimedKind.ONE_ARMED, count=300, veterans=100, updated_epoch=3))
    await realm.session.flush()
    moved = await sync_maimed(context(realm.session), town)
    rows = await cohorts_of(realm.session, town.id)
    assert moved == 200
    assert sum(row.count for key, row in rows.items() if key[3] is CohortCondition.MAIMED) == 200
    assert total(rows) == 5000


async def test_promoted_mortals_carry_their_moment(realm: Realm) -> None:
    town = await settlement(realm, "Famine Town", population=5000)
    survivor = await mortal(realm, "One-Arm", location_id=town.id)
    orphan = await mortal(realm, "Orphan", location_id=town.id)
    ctx = context(realm.session)
    assert await matching_wound(ctx, survivor, MaimedKind.ONE_ARMED) == 1
    wounds = list(await realm.session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == survivor.id)))
    assert any(row.kind is InjuryKind.SEVERED and "arm" in row.part for row in wounds)
    await orphan_memory(ctx, orphan, town)
    memory = await realm.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == orphan.id))
    assert memory is not None and memory.subject_node_id == town.id and memory.magnitude < 0


async def test_a_held_mortal_is_neither_woken_nor_dozed_by_the_engine(realm: Realm) -> None:
    sleeper = await mortal(realm, "Sleeper")
    rules = tuned(cohorts={"dormant_after_epochs": 1, "dormant_importance": 1000})
    ctx = context(realm.session, rules, epoch=9)
    assert await set_dormancy(ctx, sleeper.id, dormant=False, hold=True) is False

    async def run(inner: object) -> None:
        await doze(ctx)

    await run_guarded(Phase("test_doze", run), ctx)
    assert await realm.session.get(EntityFlagRow, (sleeper.id, EntityFlag.DORMANT)) is None
    await set_dormancy(ctx, sleeper.id, dormant=None, hold=False)
    await run_guarded(Phase("test_doze", run), ctx)
    assert await realm.session.get(EntityFlagRow, (sleeper.id, EntityFlag.DORMANT)) is not None


async def test_a_host_species_carries_its_disease_and_its_death_starves_it(realm: Realm) -> None:
    town = await settlement(realm, "Ratford", population=4000)
    rats = await host_species(realm, "Grey Rats", 100)
    book = await book_of(realm)
    rules = tuned(epidemiology={"host_emergence_pct": 100})
    chosen = await host_for(context(realm.session, rules), book, realm.region.id)
    assert chosen is not None and chosen.id == rats.id
    disease = await forge(realm, vector="bite", target_functions=["vital"], host_species_id=rats.id)
    assert await realm.session.get(SpeciesHostRow, (rats.id, disease.id)) is not None
    book = await book_of(realm)
    carried = spread_factor(book, disease.id, town, ground(), source_region=None)
    ctx = context(realm.session)
    outbreak = await open_outbreak(ctx, book, disease, realm.region.id, path=SpreadPath.ORIGIN, severity=50)
    realm.session.add(EndemicDiseaseRow(region_entity_id=realm.region.id, disease_entity_id=disease.id, load=40, since_epoch=1, locked=False))
    range_row = await realm.session.get(SpeciesRangeRow, (rats.id, realm.region.id))
    assert range_row is not None
    await realm.session.delete(range_row)
    await realm.session.flush()
    book = await book_of(realm)
    assert spread_factor(book, disease.id, town, ground(), source_region=None) < carried / 5
    assert host_gone(book, outbreak)
    await settle_endemic(ctx, book)
    endemic = await realm.session.get(EndemicDiseaseRow, (realm.region.id, disease.id))
    assert endemic is not None and endemic.load == 40 - round(RULES.epidemiology.endemic_decay * RULES.epidemiology.host_gone_decay_pct / 100)


async def test_a_held_outbreak_status_is_kept_by_the_course(realm: Realm) -> None:
    await settlement(realm, "Held", population=4000)
    disease = await forge(realm, vector="air", target_functions=["breath"])
    ctx = context(realm.session, epoch=3)
    book = await book_of(realm)
    outbreak = await open_outbreak(ctx, book, disease, realm.region.id, path=SpreadPath.ORIGIN, severity=50)
    outbreak.started_epoch = 1
    outbreak.status = OutbreakStatus.WANING
    outbreak.locked = [STATUS_LOCK]
    await run_course(ctx, book)
    assert outbreak.status is OutbreakStatus.WANING


async def test_endemic_disease_repels_settlers_who_never_met_it(realm: Realm) -> None:
    home = await settlement(realm, "Home", population=3000, location_id=realm.far_region.id)
    immune = await settlement(realm, "Immune", population=3000, location_id=realm.far_region.id)
    disease = await forge(realm, vector="water", target_functions=["vital"])
    realm.session.add(EndemicDiseaseRow(region_entity_id=realm.region.id, disease_entity_id=disease.id, load=60, since_epoch=1, locked=False))
    realm.session.add(ImmunityRow(community_entity_id=immune.id, disease_entity_id=disease.id, age_band=AgeBand.ADULT, immune_pct=50, since_epoch=1))
    await realm.session.flush()
    assert await endemic_repel(realm.session, RULES, realm.region.id, home.id) == 1 - 0.6 * RULES.epidemiology.endemic_settler_pct / 100
    assert await endemic_repel(realm.session, RULES, realm.region.id, immune.id) == 1.0
    assert await endemic_repel(realm.session, RULES, realm.far_region.id, home.id) == 1.0


async def test_past_plagues_become_diseases_outbreaks_and_immunity_once(realm: Realm) -> None:
    town = await settlement(realm, "Old Plague", population=8000)
    event = await make(
        realm.session,
        "The Old Plague",
        EntityType.EVENT,
        EventStats(severity=70),
        world_id=realm.world.id,
        location_id=realm.region.id,
        engine_kind=EngineKind.PLAGUE,
    )
    await link(realm.session, event.id, town.id, BondKind.CAUSED, description="1200 lives lost")
    ctx = context(realm.session, epoch=3)
    result = await backfill_plagues(ctx)
    assert result["outbreaks"] == 1 and result["diseases"] == 1
    outbreak = await realm.session.scalar(select(OutbreakRow).where(OutbreakRow.event_entity_id == event.id))
    assert outbreak is not None and outbreak.dead == 1200
    assert list(await realm.session.scalars(select(ImmunityRow).where(ImmunityRow.community_entity_id == town.id)))
    assert await realm.session.get(AppliedFixupRow, PLAGUE_FIXUP) is not None
    assert await backfill_plagues(ctx) == {}


async def test_army_and_journey_spread_respect_size_and_path(realm: Realm) -> None:
    home = await settlement(realm, "Barracks", population=4000)
    touch = await forge(realm, vector="touch", target_functions=["skin"])
    book = await book_of(realm)
    marched = spread_factor(book, touch.id, home, ground(), source_region=realm.far_region.id, path=SpreadPath.ARMY)
    walked = spread_factor(book, touch.id, home, ground(), source_region=realm.far_region.id, path=SpreadPath.JOURNEY)
    still = spread_factor(book, touch.id, home, ground(), source_region=realm.far_region.id, path=SpreadPath.ORIGIN)
    assert marched == walked > still


async def test_a_living_curse_god_feeds_on_outbreaks(realm: Realm, session: AsyncSession) -> None:
    god = await son(session, "Pestis", realm.world.id)
    ctx = context(session)
    disease = await create_disease(ctx, realm.region.id, DiseaseDesign(values={"vector": "curse", "target_functions": ["vital"]}), son_id=god.id)
    assert disease.creator_son_id == god.id
    before = god.essence
    book = await book_of(realm)
    await open_outbreak(ctx, book, disease, realm.region.id, path=SpreadPath.LOOSED, severity=40)
    assert god.essence > before


async def test_conditions_with_a_part_are_read_as_function_loss() -> None:
    row = ConditionRow(kind=ConditionKind.CHRONIC_ILLNESS, severity=3, part="lungs", ended_epoch=None)
    assert afflicted_parts(RULES, [row]) == (("lungs", 3 * RULES.epidemiology.chronic_function_loss_pct),)


async def test_pins_on_the_sick_hold_a_community(realm: Realm) -> None:
    town = await settlement(realm, "Pinned", population=6000)
    disease = await forge(realm, vector="air", target_functions=["breath"], virulence=80)
    ctx = context(realm.session)
    await seed(realm.session, RULES, town, 3)
    await add_modifier(realm.session, ModifierDraft(town.id, "sick", ModifierOp.ADD, 0, ModifierSource.PIN, "test.pin", start_epoch=1))
    book = await book_of(realm)
    await open_outbreak(ctx, book, disease, realm.region.id, path=SpreadPath.ORIGIN, severity=80)

    async def run(inner: object) -> None:
        await sicken_cohorts(ctx, book)

    await run_guarded(Phase("test_sick", run), ctx)
    rows = await cohorts_of(realm.session, town.id)
    assert sum(row.count for key, row in rows.items() if key[3] is CohortCondition.SICK) == 0
    assert (await RegionAtlas.load(realm.session)).top_region(town.id) == realm.region.id
    assert await realm.session.scalar(select(CohortRow).where(CohortRow.community_entity_id == town.id)) is not None
