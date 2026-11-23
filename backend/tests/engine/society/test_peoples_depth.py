import pytest

from aerona.catalog.peoples import CULTURAL_FUNERALS, DIETS, FUNERALS, KIN, SIZES, VALUE_STYLE, MountFit
from aerona.catalog.terrain import TERRAIN
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.unions import UnionCustomRow
from aerona.db.tables.warfare import BattleRow, WarRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ArtMode, RiteStage, TraditionFunction
from aerona.domain.enums.demography import (
    FuneralCustom,
    InheritanceCustom,
    MartialStyle,
    NaturalTrait,
)
from aerona.domain.enums.ecology import Diet, SizeClass
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, TemperatureBand, TerrainKind, WeatherKind
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch
from aerona.domain.enums.unions import PartnerScope, PluralSide, UnionForm
from aerona.domain.enums.war import BattleOutcome, WarCause
from aerona.domain.models.entity_stats import EventStats, LanguageStats, SpeciesStats
from aerona.engine.demography import biology as kin
from aerona.engine.demography import control, kinship, rites, tongues, urban
from aerona.engine.demography.martial import BattleTally, record_battles
from aerona.engine.demography.peoples import (
    Kin,
    customs_of,
    ensure_profiles,
    funeral_of,
    kin_from,
    liturgical_of,
    martial_choice,
    refresh_culture,
    spousing_for,
    tally_battle,
    trade_language_of,
)
from aerona.engine.lore.style import style_fit, style_message
from aerona.engine.phases.demography import people_cycles
from aerona.engine.unions.axes import Spousing
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, mortal, people, settlement

RULES = Rules()


def biology(**values: object) -> PeopleBiologyRow:
    base: dict[str, object] = {
        "people_entity_id": 1,
        "maturity_years": 16,
        "adult_years": 40,
        "elder_years": 15,
        "fertility_pct": 100,
        "acclimatised": TemperatureBand.TEMPERATE,
        "traits": [],
        "staple": CommodityKind.GRAIN,
        "immunities": [],
        "body_plan": BodyPlan.HUMANOID,
        "size_class": SizeClass.MEDIUM,
        "diet": Diet.OMNIVORE,
        "locked": [],
    }
    base.update(values)
    return PeopleBiologyRow(**base)


def culture(**values: object) -> PeopleCultureRow:
    base: dict[str, object] = {
        "people_entity_id": 1,
        "cohesion": 50,
        "literacy": 10,
        "urbanisation": 30,
        "staples": [],
        "ornament": 15,
        "martial_style": MartialStyle.SHIELDWALL,
        "funeral_rite": FuneralCustom.BURIAL,
        "inheritance": InheritanceCustom.PRIMOGENITURE,
        "slavery_lawful": False,
        "martial_record": {},
        "martial_epoch": 0,
        "locked": [],
    }
    base.update(values)
    return PeopleCultureRow(**base)


def ground(**values: object) -> RegionEnvironmentRow:
    row = RegionEnvironmentRow()
    defaults: dict[str, object] = {
        "farmed": 40,
        "grazed": 20,
        "coast_kind": CoastKind.NONE,
        "temperature_band": TemperatureBand.TEMPERATE,
        "magic_density": 0,
        "dominant_terrain": TerrainKind.PLAIN,
        "forest_cover": 10,
    }
    defaults.update(values)
    for key, value in defaults.items():
        setattr(row, key, value)
    return row


def test_every_body_plan_and_size_changes_food_room_and_strength() -> None:
    human = biology()
    assert kin.food_need(RULES, human) == pytest.approx(1.0)
    needs = {plan: (kin.food_need(RULES, biology(body_plan=plan)), kin.footprint(RULES, biology(body_plan=plan))) for plan in BodyPlan}
    assert len(set(needs.values())) >= len(BodyPlan) - 1
    for size in SizeClass:
        row = biology(size_class=size)
        assert kin.food_need(RULES, row) == pytest.approx(SIZES[size].food_pct / 100)
        assert kin.footprint(RULES, row) == pytest.approx(SIZES[size].space_pct / 100)
        edge = kin.battle_edge(RULES, row, None, terrain=None, weather=None, night=False, river=False, defending=False)
        assert edge == pytest.approx(SIZES[size].strength_pct / 100)
    assert kin.food_need(RULES, biology(size_class=SizeClass.HUGE)) > kin.food_need(RULES, biology(size_class=SizeClass.SMALL))


def test_every_body_plan_has_a_distinct_profile() -> None:
    profiles = {
        (
            spec.food_pct,
            spec.space_pct,
            spec.disease_pct,
            spec.naval_pct,
            spec.mount,
            tuple(spec.labour.items()),
            tuple(sorted((terrain.value, fit.body_fit.get(plan, 100)) for terrain, fit in TERRAIN.items())),
        )
        for plan, spec in KIN.items()
    }
    assert len(profiles) == len(BodyPlan)
    assert set(KIN) == set(BodyPlan)


def test_every_natural_trait_branches_battle_work_food_or_room() -> None:
    base_food = kin.food_need(RULES, biology())
    base_room = kin.footprint(RULES, biology())
    base_work = kin.job_factors(RULES, biology())
    for trait in NaturalTrait:
        row = biology(traits=[trait.value])
        battle = {
            kin.battle_edge(RULES, row, None, terrain=terrain, weather=weather, night=night, river=river, defending=defending)
            for terrain in (None, TerrainKind.MOUNTAINS, TerrainKind.MARSH)
            for weather in (None, WeatherKind.SNOW, WeatherKind.HEAT_WAVE)
            for night in (False, True)
            for river in (False, True)
            for defending in (False, True)
        }
        changed = (
            battle != {1.0} or kin.food_need(RULES, row) != base_food or kin.footprint(RULES, row) != base_room or kin.job_factors(RULES, row) != base_work
        )
        assert changed, trait


def test_mounts_fleets_and_the_raised_dead_follow_body_and_rite() -> None:
    plan = {UnitKind.HEAVY_CAVALRY: 0.2, UnitKind.NAVAL_CREW: 0.1, UnitKind.LINE_INFANTRY: 0.3}
    needs = {UnitKind.HEAVY_CAVALRY: "mount"}
    rider = kin.kin_army(RULES, biology(), None, plan, beasts=set(), mount_needs=needs)
    assert UnitKind.HEAVY_CAVALRY not in rider
    horse_folk = kin.kin_army(RULES, biology(body_plan=BodyPlan.QUADRUPED), None, plan, beasts=set(), mount_needs=needs)
    assert horse_folk[UnitKind.HEAVY_CAVALRY] == pytest.approx(0.2)
    birds = kin.kin_army(RULES, biology(body_plan=BodyPlan.AVIAN), None, plan, beasts={"mount"}, mount_needs=needs)
    assert UnitKind.HEAVY_CAVALRY not in birds and birds[UnitKind.SKY_RIDERS] == pytest.approx(0.2)
    fish = kin.kin_army(RULES, biology(body_plan=BodyPlan.AQUATIC), None, plan, beasts={"mount"}, mount_needs=needs)
    assert fish[UnitKind.NAVAL_CREW] > plan[UnitKind.NAVAL_CREW]
    giants = kin.mount_fit(biology(size_class=SizeClass.HUGE))
    assert giants is MountFit.CANNOT
    dead = kin.kin_army(RULES, biology(), culture(funeral_rite=FuneralCustom.REANIMATION), plan, beasts=set(), mount_needs=needs)
    assert dead[UnitKind.SUMMONED_HOST] > 0


def test_every_diet_feeds_differently_from_the_land() -> None:
    land = ground(coast_kind=next(item for item in CoastKind if item is not CoastKind.NONE))
    fed = {diet: kin.nourishment(RULES, diet, land, 100, magic_level=1) for diet in Diet}
    assert len(set(fed.values())) >= len(Diet) - 2
    assert set(DIETS) == set(Diet)
    inland = ground()
    assert kin.nourishment(RULES, Diet.PISCIVORE, inland, 100) == 0.0
    assert kin.hunger_level(RULES, biology(diet=Diet.PISCIVORE), inland, 100) == pytest.approx(1.0)
    assert kin.hunger_level(RULES, biology(diet=Diet.MINERAL), inland, 0) < 0.2
    assert kin.edible(Diet.HERBIVORE) == frozenset({CommodityKind.GRAIN, CommodityKind.BREAD, CommodityKind.FODDER})
    assert kin.staple_for(RULES, Diet.CARNIVORE, inland) is CommodityKind.LIVESTOCK


def test_acclimatisation_and_climate_fit() -> None:
    temperate = biology()
    assert kin.acclimatised(RULES, temperate, TemperatureBand.WARM)
    assert not kin.acclimatised(RULES, temperate, TemperatureBand.SEARING)
    cold = biology(acclimatised=TemperatureBand.COLD, traits=[NaturalTrait.COLD_BLOODED.value])
    assert not kin.acclimatised(RULES, biology(acclimatised=TemperatureBand.TEMPERATE, traits=[NaturalTrait.COLD_BLOODED.value]), TemperatureBand.COLD)
    assert kin.acclimatised(RULES, cold, TemperatureBand.TEMPERATE)
    assert kin.climate_fit(RULES, temperate, TemperatureBand.FROZEN) < 1.0
    assert kin.climate_fit(RULES, temperate, TemperatureBand.TEMPERATE) == 1.0


def test_immunity_body_and_funeral_rite_set_plague_deaths() -> None:
    immune = biology(immunities=[7])
    assert kin.immunity_factor(RULES, immune, None, 7) == pytest.approx(RULES.biology.homeland_immunity_pct / 100)
    assert kin.immunity_factor(RULES, immune, None, 9, parent_id=7) < 1.0
    assert kin.immunity_factor(RULES, biology(body_plan=BodyPlan.CONSTRUCT), None, 9) < 0.5
    rates = {rite: kin.immunity_factor(RULES, None, culture(funeral_rite=rite), 9) for rite in FuneralCustom}
    assert rates[FuneralCustom.ENDOCANNIBALISM] > rates[FuneralCustom.BURIAL] > rates[FuneralCustom.CREMATION]


def test_every_funeral_rite_has_distinct_mechanics() -> None:
    effects = {
        (
            round(rites.contagion(RULES, rite), 3),
            round(rites.spirit_factor(RULES, rite), 3),
            rites.restless_shift(RULES, rite),
            round(rites.mourning_factor(RULES, rite), 3),
            rites.raises_dead(rite),
            rites.binds_spirits(rite),
        )
        for rite in FuneralCustom
    }
    assert len(effects) == len(FuneralCustom) == len(FUNERALS)
    assert not rites.restless(RULES, FuneralCustom.SOUL_BINDING, 99, 10)
    assert rites.restless(RULES, FuneralCustom.REANIMATION, 0, 10)


def test_customs_produce_every_inheritance_and_marriage() -> None:
    inheritances = {
        customs_of({ValueAxis.HIERARCHY: 30, ValueAxis.KINSHIP: 30, ValueAxis.MERCY: 30})[0],
        customs_of({ValueAxis.HIERARCHY: 30})[0],
        customs_of({ValueAxis.KINSHIP: 60})[0],
        customs_of({ValueAxis.KNOWLEDGE: 30})[0],
        customs_of({ValueAxis.KINSHIP: 30, ValueAxis.TRADITION: 30})[0],
        customs_of({ValueAxis.LAW: 30})[0],
        customs_of({ValueAxis.HIERARCHY: -30})[0],
        customs_of({})[0],
    }
    assert inheritances == set(InheritanceCustom)
    spousings = {
        spousing_for({}),
        spousing_for({ValueAxis.HIERARCHY: 60, ValueAxis.TRADITION: 30}),
        spousing_for({ValueAxis.HIERARCHY: -30, ValueAxis.KINSHIP: 30}),
        spousing_for({ValueAxis.KINSHIP: -60}),
    }
    assert {(item.form, item.side) for item in spousings} == {
        (UnionForm.PAIR, PluralSide.EITHER),
        (UnionForm.PLURAL, PluralSide.FIRST),
        (UnionForm.PLURAL, PluralSide.SECOND),
        (UnionForm.GROUP, PluralSide.EITHER),
    }


def test_funeral_rites_follow_land_knowledge_and_values() -> None:
    found = {
        funeral_of(None, {KnowledgeBranch.MAGIC: 3}, {ValueAxis.DEATH: 30}),
        funeral_of(None, {KnowledgeBranch.MAGIC: 2}, {ValueAxis.PIETY: 30}),
        funeral_of(None, {KnowledgeBranch.ARCHITECTURE: 2}, {ValueAxis.HIERARCHY: 30}),
        funeral_of(ground(rainfall=10), {KnowledgeBranch.MEDICINE: 2}, {ValueAxis.DEATH: 30}),
        funeral_of(None, {}, {ValueAxis.KINSHIP: 30, ValueAxis.TRADITION: 30}),
        funeral_of(None, {}, {ValueAxis.KINSHIP: 60}),
        funeral_of(None, {}, {ValueAxis.KINSHIP: 30, ValueAxis.MERCY: -60}),
        funeral_of(ground(dominant_terrain=TerrainKind.MOUNTAINS), {}, {}),
        funeral_of(ground(coast_kind=next(item for item in CoastKind if item is not CoastKind.NONE)), {KnowledgeBranch.SEAFARING: 1}, {}),
        funeral_of(None, {}, {ValueAxis.PIETY: 30}),
        funeral_of(None, {}, {}),
    }
    assert found == CULTURAL_FUNERALS


def test_fantasy_kin_come_from_creature_traits_and_species() -> None:
    hive = kin_from(None, None, None, {CreatureTrait.HIVE_MIND}, nocturnal=False, height_rank=None)
    assert hive.plan is BodyPlan.INSECTOID and NaturalTrait.HIVE_MINDED in hive.traits and NaturalTrait.COLD_BLOODED in hive.traits
    stone = kin_from(BodyPlan.HUMANOID, SizeClass.LARGE, None, {CreatureTrait.STONESKIN}, nocturnal=True, height_rank=None)
    assert stone.diet is Diet.MINERAL and NaturalTrait.THICK_HIDE in stone.traits and NaturalTrait.DARK_SIGHT in stone.traits
    giant = kin_from(BodyPlan.COLOSSAL, None, None, set(), nocturnal=False, height_rank=None)
    assert giant == Kin(BodyPlan.COLOSSAL, SizeClass.COLOSSAL, Diet.OMNIVORE, ())


def test_a_style_that_wins_is_kept_and_one_that_loses_takes_the_victors() -> None:
    row = culture(martial_style=MartialStyle.SHIELDWALL)
    for _ in range(RULES.customs.martial_hold_wins):
        tally_battle(row, won=True)
    assert martial_choice(RULES, row, MartialStyle.HORSE_ARCHER, None) is MartialStyle.SHIELDWALL
    beaten = culture(martial_style=MartialStyle.PHALANX)
    for _ in range(RULES.customs.martial_defeat_losses):
        tally_battle(beaten, won=False)
    assert martial_choice(RULES, beaten, MartialStyle.PHALANX, MartialStyle.SHOCK) is MartialStyle.SHOCK
    fresh = culture(martial_style=MartialStyle.SKIRMISHER)
    assert martial_choice(RULES, fresh, MartialStyle.CHARIOT, None) is MartialStyle.CHARIOT
    assert kin.mastery(RULES, row) > 1.0


def test_refresh_honours_every_hold() -> None:
    row = culture(locked=["ornament", "martial_style", "funeral_rite", "trade_language_id"], trade_language_id=5)
    fresh = culture(ornament=90, martial_style=MartialStyle.PHALANX, funeral_rite=FuneralCustom.CREMATION, trade_language_id=9, literacy=80)
    refresh_culture(RULES, row, fresh)
    assert row.ornament == 15
    assert row.martial_style is MartialStyle.SHIELDWALL
    assert row.funeral_rite is FuneralCustom.BURIAL
    assert row.trade_language_id == 5
    assert row.literacy == 80


def test_marriage_customs_limit_spouses_and_endogamy_blocks_foreign_matches() -> None:
    first_plural = Spousing(UnionForm.PLURAL, PluralSide.FIRST)
    one = kinship.Terms(1, first_plural, first="begetter", second="bearer")
    assert kinship.may_wed_terms(RULES, (one, "begetter", 2), (one, "bearer", 0))
    assert not kinship.may_wed_terms(RULES, (one, "bearer", 1), (one, "begetter", 0))
    flipped = kinship.Terms(1, first_plural, first="bearer", second="begetter")
    assert kinship.may_wed_terms(RULES, (flipped, "bearer", 2), (flipped, "begetter", 0))
    mono = kinship.Terms(1, Spousing())
    assert not kinship.may_wed_terms(RULES, (mono, "begetter", 1), (mono, "bearer", 0))
    closed = kinship.Terms(1, Spousing(endogamy=PartnerScope.PEOPLE))
    stranger = kinship.Terms(2, Spousing())
    assert not kinship.may_wed_terms(RULES, (closed, "begetter", 0), (stranger, "bearer", 0))
    assert kinship.match_bonus(RULES, stranger, mono) == RULES.customs.exogamy_match_bonus
    customs = (
        Spousing(),
        first_plural,
        Spousing(UnionForm.PLURAL, PluralSide.SECOND),
        Spousing(UnionForm.GROUP),
        Spousing(UnionForm.PLURAL, PluralSide.EITHER),
    )
    sided = [kinship.Terms(1, custom, first="begetter", second="bearer") for custom in customs]
    limits = {(kinship.spouse_limit(RULES, terms, "begetter"), kinship.spouse_limit(RULES, terms, "bearer")) for terms in sided}
    assert len(limits) == len(customs)
    closed_custom = UnionCustomRow(people_entity_id=1, endogamy=PartnerScope.PEOPLE)
    open_custom = UnionCustomRow(people_entity_id=1, endogamy=PartnerScope.NONE)
    assert kinship.assimilation_factor(RULES, closed_custom) < kinship.assimilation_factor(RULES, open_custom)


def test_urbanisation_moves_founding_growth_pull_and_classes() -> None:
    town = culture(urbanisation=90)
    field = culture(urbanisation=0)
    assert urban.founding_factor(RULES, town) > 1.0 > urban.founding_factor(RULES, field)
    assert urban.growth_factor(RULES, town) > urban.growth_factor(RULES, field)
    assert urban.town_pull_factor(RULES, town) > urban.town_pull_factor(RULES, field)
    assert urban.class_shift(RULES, town, 1000, 100) > 0
    assert urban.class_shift(RULES, field, 1000, 100) < 0


def test_shared_trade_tongues_are_found_either_way() -> None:
    assert tongues.shares_tongue(4, 4, set(), set())
    assert tongues.shares_tongue(4, None, set(), {4})
    assert tongues.shares_tongue(None, 4, {4}, set())
    assert not tongues.shares_tongue(4, 5, {1}, {2})


def test_taste_steers_the_pull_of_art() -> None:
    rich = VALUE_STYLE[ValueAxis.WEALTH]
    assert style_fit(RULES, rich, ArtMode.FLAT_IMAGE) > 1.0
    assert style_fit(RULES, VALUE_STYLE[ValueAxis.MARTIAL], ArtMode.MOVEMENT) < 1.0
    assert style_fit(RULES, None, ArtMode.MOVEMENT) == 1.0
    assert style_message(RULES, rich, ArtMode.FLAT_IMAGE, {}) == {ValueAxis.WEALTH.value: RULES.customs.aesthetic_message}


async def test_heirs_follow_the_custom(realm: Realm) -> None:
    elder = await mortal(realm, "Elder", age=40, intellect=10, charisma=90)
    youngest = await mortal(realm, "Youngest", age=12, intellect=90, charisma=10)
    middle = await mortal(realm, "Middle", age=25, intellect=50, charisma=50)
    children = [middle, youngest, elder]
    assert kinship.heirs_by_custom(InheritanceCustom.PRIMOGENITURE, children) == [elder]
    assert kinship.heirs_by_custom(InheritanceCustom.ULTIMOGENITURE, children) == [youngest]
    assert kinship.heirs_by_custom(InheritanceCustom.EQUAL_SHARES, children) == [elder, middle, youngest]
    assert kinship.heirs_by_custom(InheritanceCustom.BY_MERIT, children) == [youngest]
    assert kinship.heirs_by_custom(InheritanceCustom.ELECTIVE, children) == [elder]
    assert len(kinship.heirs_by_custom(InheritanceCustom.THROUGH_SECOND_LINE, children)) == 1


async def test_profiles_are_derived_edited_held_and_released(realm: Realm) -> None:
    session = realm.session
    folk = await people(realm, "Hollowfolk")
    ctx = context(session)
    biology_row, culture_row = await control.profiles(ctx, folk)
    assert biology_row.body_plan is BodyPlan.HUMANOID
    disease = await settlement(realm, "Not a disease")
    assert disease.id
    await control.edit_people(
        ctx,
        folk.id,
        {
            "body_plan": "avian",
            "size_class": "small",
            "diet": "piscivore",
            "traits": ["winged", "keen_senses"],
            "acclimatised": "cold",
            "staples": ["fish"],
            "funeral_rite": "cremation",
            "martial_wins": 4,
            "martial_losses": 1,
            "urbanisation": 70,
        },
        release=[],
    )
    assert biology_row.body_plan is BodyPlan.AVIAN and biology_row.traits == ["keen_senses", "winged"]
    assert culture_row.funeral_rite is FuneralCustom.CREMATION and culture_row.funeral_rite_id is not None
    profile = await session.get(TraditionProfileRow, culture_row.funeral_rite_id)
    assert profile is not None and profile.kind is TraditionFunction.RITE_OF_PASSAGE and profile.stage is RiteStage.DEATH
    assert culture_row.martial_record[culture_row.martial_style.value] == [4, 1]
    assert {"body_plan", "traits", "diet"} <= set(biology_row.locked)
    assert {"funeral_rite", "martial_record", "urbanisation"} <= set(culture_row.locked)
    with pytest.raises(ValidationFailedError):
        await control.edit_people(ctx, folk.id, {"immunities": [disease.id]}, release=[])
    with pytest.raises(ValidationFailedError):
        await control.edit_people(ctx, folk.id, {"traits": ["gills"]}, release=[])
    await control.edit_people(ctx, folk.id, {}, release=["body_plan", "martial_wins"])
    assert "body_plan" not in biology_row.locked and "martial_record" not in culture_row.locked


async def test_a_people_is_founded_with_its_profile(realm: Realm) -> None:
    ctx = context(realm.session)
    founded = await control.found_people(
        ctx,
        name="Stonekin",
        region_id=realm.region.id,
        population=900,
        species_id=None,
        language_id=None,
        values={"diet": "mineral", "martial_style": "phalanx"},
    )
    biology_row, culture_row = await control.profiles(ctx, founded)
    assert biology_row.diet is Diet.MINERAL and "diet" in biology_row.locked
    assert culture_row.martial_style is MartialStyle.PHALANX
    assert culture_row.funeral_rite_id is not None


async def test_battles_reinforce_a_peoples_way_of_war(realm: Realm) -> None:
    session = realm.session
    victors = await people(realm, "Victors")
    beaten = await people(realm, "Beaten")
    ctx = context(session, epoch=5)
    _, first = await ensure_profiles(session, RULES, victors, None)
    _, second = await ensure_profiles(session, RULES, beaten, None)
    first.martial_style = MartialStyle.SHOCK
    second.martial_style = MartialStyle.PHALANX
    event = await make(session, "The Long War", EntityType.EVENT, EventStats(), world_id=realm.world.id)
    war = WarRow(event_entity_id=event.id, world_id=realm.world.id, cause=next(iter(WarCause)), started_epoch=4)
    session.add(war)
    await session.flush()
    for sequence in range(RULES.customs.martial_defeat_losses):
        session.add(
            BattleRow(
                war_id=war.id, epoch=5, sequence=sequence, winner_entity_id=victors.id, loser_entity_id=beaten.id, outcome=BattleOutcome.FIELD_VICTORY, gap=1.0
            )
        )
    await session.flush()
    tally = await BattleTally.load(session, 0, ctx.epoch)
    assert await record_battles(session, tally, first, ctx.epoch) is None
    victor = await record_battles(session, tally, second, ctx.epoch)
    assert victor is MartialStyle.SHOCK
    assert first.martial_record[MartialStyle.SHOCK.value] == [RULES.customs.martial_defeat_losses, 0]
    assert martial_choice(RULES, second, MartialStyle.PHALANX, victor) is MartialStyle.SHOCK
    again = await BattleTally.load(session, 0, ctx.epoch)
    await record_battles(session, again, first, ctx.epoch)
    assert first.martial_record[MartialStyle.SHOCK.value] == [RULES.customs.martial_defeat_losses, 0]


async def test_trade_tongue_is_the_partners_tongue_and_widens_routes(realm: Realm) -> None:
    session = realm.session
    folk = await people(realm, "Traders")
    partner = await settlement(realm, "Port")
    ours = await make(session, "Hollow Speech", EntityType.LANGUAGE, LanguageStats(), world_id=realm.world.id)
    theirs = await make(session, "Port Cant", EntityType.LANGUAGE, LanguageStats(), world_id=realm.world.id)
    await link(session, folk.id, ours.id, BondKind.SPEAKS)
    await link(session, partner.id, theirs.id, BondKind.SPEAKS)
    await link(session, folk.id, partner.id, BondKind.TRADES_WITH)
    assert await trade_language_of(session, folk) == theirs.id
    _, row = await ensure_profiles(session, RULES, folk, None)
    assert row.trade_language_id == theirs.id
    assert await tongues.shared_trade_tongue(session, folk.id, partner.id)
    assert await tongues.trade_barrier(session, RULES, folk.id, partner.id, 3) == pytest.approx(RULES.customs.trade_tongue_pct / 100)
    assert await tongues.tongue_link(session, RULES, folk.id, partner.id) > 1.0
    assert await liturgical_of(session, folk) == ours.id


async def test_people_cycles_derive_fantasy_kin_rites_and_records(realm: Realm) -> None:
    session = realm.session
    species = await make(session, "Skyhawk", EntityType.SPECIES, SpeciesStats(), world_id=realm.world.id, traits=[CreatureTrait.FLYING])
    folk = await people(realm, "Wingkin")
    await link(session, folk.id, species.id, BondKind.DESCENDS_FROM)
    ctx = context(session, epoch=4)
    await people_cycles(ctx)
    biology_row = await session.get(PeopleBiologyRow, folk.id)
    culture_row = await session.get(PeopleCultureRow, folk.id)
    assert biology_row is not None and culture_row is not None
    assert biology_row.body_plan is BodyPlan.AVIAN
    assert NaturalTrait.WINGED.value in biology_row.traits
    assert culture_row.funeral_rite_id is not None and culture_row.martial_epoch == 4
    assert await session.get(AppliedFixupRow, "peoples.depth_backfill") is not None
    biology_row.locked = ["body_plan"]
    biology_row.body_plan = BodyPlan.COLOSSAL
    await people_cycles(context(session, epoch=5))
    assert biology_row.body_plan is BodyPlan.COLOSSAL
