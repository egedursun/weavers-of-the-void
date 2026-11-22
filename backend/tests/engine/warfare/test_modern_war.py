from aerona.catalog.anatomy import anatomy_of
from aerona.catalog.harm_kinds import DAMAGE
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.domain.enums.body import BodyPlan, DamageType, HarmCause, InjuryKind
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.integrity import SectionHazard
from aerona.domain.enums.military import Tactic, UnitKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.engine.body.hits import cause_mix, kind_for
from aerona.engine.demography.peoples import martial_of
from aerona.engine.military.battle import Field, choose_tactic, fielded, missiles, treat
from aerona.engine.vehicles.wrecks import wreck_cause
from aerona.rules.registry import Rules
from tests.engine.warfare.test_battle_depth import seeded, side, unit

RULES = Rules()
PLAIN = Field(TerrainKind.PLAIN, None, night=False)
HUMAN = anatomy_of(BodyPlan.HUMANOID)


def test_each_new_tactic_needs_the_troops_that_carry_it() -> None:
    levy = side("Levy", [unit(UnitKind.LEVY, 100, ident=1)])
    guns = side("Guns", [unit(UnitKind.ARTILLERY_CREW, 20, ident=2)])
    drop = side("Drop", [unit(UnitKind.DROP_TROOPS, 50, ident=3)])
    jammers = side("Jammers", [unit(UnitKind.SIGNALS_TROOPS, 20, ident=4)])
    assert not fielded(Tactic.ARTILLERY_BARRAGE, levy) and fielded(Tactic.ARTILLERY_BARRAGE, guns)
    assert not fielded(Tactic.ORBITAL_BOMBARDMENT, levy) and fielded(Tactic.ORBITAL_BOMBARDMENT, drop)
    assert fielded(Tactic.DROP_ASSAULT, drop) and not fielded(Tactic.DROP_ASSAULT, guns)
    assert fielded(Tactic.ELECTRONIC_WARFARE, jammers) and not fielded(Tactic.ELECTRONIC_WARFARE, levy)
    assert fielded(Tactic.HOLD_LINE, levy)


def test_a_modern_doctrine_without_its_troops_falls_back_to_what_the_army_can_do() -> None:
    for seed in range(40):
        levy = side("Levy", [unit(UnitKind.LEVY, 100, ident=1)])
        levy.profile.doctrine = MartialStyle.ORBITAL.value
        chosen = choose_tactic(RULES, seeded(seed)("tactic"), levy, "shieldwall", PLAIN)
        assert fielded(chosen, levy)


def test_barrages_hit_harder_and_jamming_dulls_the_fire() -> None:
    def fire(shooting: Tactic, jammed: bool) -> int:
        guns = side("Guns", [unit(UnitKind.ARTILLERY_CREW, 200, ident=1)])
        guns.tactic = shooting
        guns.stacks[0].row.ammunition = 20
        target = side("Target", [unit(UnitKind.LEVY, 5000, ident=2, army=2)], ident=2)
        target.tactic = Tactic.ELECTRONIC_WARFARE if jammed else Tactic.HOLD_LINE
        return missiles(RULES, seeded(3), guns, target, PLAIN, families=frozenset({guns.stacks[0].spec.family}))

    plain = fire(Tactic.HOLD_LINE, jammed=False)
    assert fire(Tactic.ARTILLERY_BARRAGE, jammed=False) > plain > fire(Tactic.HOLD_LINE, jammed=True)


def test_medics_save_the_wounded_without_any_priest() -> None:
    medics = side("Medics", [unit(UnitKind.MEDICS, 20, ident=1)])
    plain = side("Plain", [unit(UnitKind.LEVY, 20, ident=2)])
    assert treat(RULES, medics, 10, 60) > treat(RULES, plain, 10, 60)


def test_every_kind_of_damage_leaves_a_wound_and_every_cause_has_a_mix() -> None:
    assert set(DAMAGE) == set(DamageType)
    torso = next(part for part in HUMAN.parts if part.key == "torso")
    for damage in DamageType:
        assert isinstance(kind_for(RULES.injury, damage, torso, 3, HarmCause.BATTLE), InjuryKind)
    assert kind_for(RULES.injury, DamageType.BALLISTIC, torso, 2, HarmCause.BATTLE) is InjuryKind.GUNSHOT
    for cause in (HarmCause.BOMBARDMENT, HarmCause.INDUSTRIAL, HarmCause.CRASH, HarmCause.RADIATION, HarmCause.DECOMPRESSION, HarmCause.EXPERIMENT):
        assert cause_mix(RULES.injury, cause)


def test_a_wreck_harms_its_captain_by_crash_or_lost_air_only_where_it_can() -> None:
    starship = VesselProfileRow(frame=VehicleFrame.STARSHIP)
    boat = VesselProfileRow(frame=VehicleFrame.LONGSHIP)
    assert wreck_cause(starship, SectionHazard.CRASH) is HarmCause.CRASH
    assert wreck_cause(starship, SectionHazard.BREACH) is HarmCause.DECOMPRESSION
    assert wreck_cause(boat, SectionHazard.BREACH) is None
    assert wreck_cause(boat, SectionHazard.FIRE) is None


def test_peoples_reach_modern_doctrines_through_their_knowledge() -> None:
    assert martial_of(None, {KnowledgeBranch.VOID_LIVING: 9}, {}) is MartialStyle.ORBITAL
    assert martial_of(None, {KnowledgeBranch.SKY_NAVIGATION: 4}, {}) is MartialStyle.AIR_MOBILE
    assert martial_of(None, {KnowledgeBranch.METALLURGY: 8, KnowledgeBranch.SKY_NAVIGATION: 4}, {}) is MartialStyle.COMBINED_ARMS
    assert martial_of(None, {KnowledgeBranch.METALLURGY: 8}, {}) is MartialStyle.MECHANISED
    assert martial_of(None, {}, {}) is MartialStyle.SHIELDWALL
