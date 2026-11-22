from itertools import pairwise

from aerona.catalog.equipment import FAMILIES, ROLE_ARMS
from aerona.catalog.eras import ERA_FLOORS
from aerona.catalog.materials import MATERIALS
from aerona.catalog.techniques import UNIT_TECHNIQUES
from aerona.catalog.units import SUCCESSORS, UNITS
from aerona.catalog.vehicles import FRAMES
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.equipment import ArmamentSlot, EquipmentFamily
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import UnitKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.vehicles import Propulsion
from aerona.domain.enums.world import TechnologyEra as E
from aerona.engine.equipment.models import best_family
from aerona.engine.eras.effects import era_order, technique_era
from aerona.engine.eras.progress import begun_by
from aerona.engine.primitives.knowledge import KnowledgeMap

ORDER = list(E)
HOLDERS = range(1, 40)
SIDEARMS = {EquipmentFamily.PISTOL, EquipmentFamily.HANDGUN}
PROPULSION_ERAS = {
    Propulsion.STEAM: E.STEAM,
    Propulsion.COMBUSTION: E.ELECTRICAL,
    Propulsion.ELECTRIC: E.ELECTRICAL,
    Propulsion.REACTION: E.INFORMATION,
    Propulsion.SOLAR_SAIL: E.ADVANCED,
    Propulsion.FOLD_DRIVE: E.INTERSTELLAR,
}


def before(era: E) -> E:
    return ORDER[max(0, era_order(era) - 1)]


def test_no_engine_driven_frame_opens_before_the_era_of_its_engine() -> None:
    early = [
        f"{frame.value} opens in the {before(era).value} age"
        for frame, spec in FRAMES.items()
        if (era := PROPULSION_ERAS.get(spec.propulsion)) is not None
        and era_order(era) > 0
        and (spec.branch is None or ERA_FLOORS[before(era)].get(spec.branch, 0) >= spec.level)
    ]
    assert early == []


def test_every_soldier_needing_a_technique_can_be_fielded_soon_after_its_era_and_not_two_eras_before() -> None:
    wrong = []
    for kind, technique in UNIT_TECHNIQUES.items():
        spec = UNITS[kind]
        era = technique_era(technique)
        if era is None or spec.branch is None or spec.branch not in ERA_FLOORS[E.BEYOND]:
            continue
        settled = ORDER[min(len(ORDER) - 1, era_order(era) + 1)]
        if ERA_FLOORS[settled].get(spec.branch, 0) < spec.level:
            wrong.append(f"{kind.value} cannot be fielded by the {settled.value} age")
        if era_order(era) >= 2 and ERA_FLOORS[ORDER[era_order(era) - 2]].get(spec.branch, 0) >= spec.level:
            wrong.append(f"{kind.value} can be fielded two ages before the {era.value} age")
    assert wrong == []


def test_a_soldier_of_an_information_age_people_carries_the_guns_of_its_age_and_not_a_musket() -> None:
    level = ERA_FLOORS[E.INFORMATION][KnowledgeBranch.METALLURGY]
    knowledge = KnowledgeMap({holder: {KnowledgeBranch.METALLURGY} for holder in HOLDERS}, {holder: {KnowledgeBranch.METALLURGY: level} for holder in HOLDERS})
    allowed = ROLE_ARMS[UnitKind.GUNNERS][ArmamentSlot.MISSILE_WEAPON]
    chosen = {best_family(knowledge, holder, ArmamentSlot.MISSILE_WEAPON, allowed) for holder in HOLDERS}
    assert EquipmentFamily.MUSKET not in chosen and EquipmentFamily.BEAM_WEAPON not in chosen
    assert chosen <= {EquipmentFamily.MACHINE_GUN, EquipmentFamily.SNIPER_RIFLE, EquipmentFamily.REPEATING_GUN, EquipmentFamily.RIFLE}


def test_every_soldier_with_firearms_and_no_successor_has_arms_of_the_steam_age_or_later() -> None:
    newest = ERA_FLOORS[E.STEAM][KnowledgeBranch.METALLURGY]
    stale = [
        kind.value
        for kind, kit in ROLE_ARMS.items()
        if kind not in SUCCESSORS
        and (missile := kit.get(ArmamentSlot.MISSILE_WEAPON))
        and not set(missile) <= SIDEARMS
        and any(FAMILIES[family].branch is KnowledgeBranch.METALLURGY for family in missile)
        and not any(FAMILIES[family].branch is KnowledgeBranch.METALLURGY and FAMILIES[family].level >= newest for family in missile)
    ]
    assert stale == []


AGE_MATERIALS = {
    E.BRONZE: (MaterialKind.COPPER, MaterialKind.TIN, MaterialKind.BRONZE, MaterialKind.FIRED_BRICK),
    E.IRON: (MaterialKind.IRON, MaterialKind.DRESSED_STONE, MaterialKind.TILE),
    E.STEAM: (MaterialKind.STEEL,),
}


def test_every_age_works_the_materials_it_is_named_for_from_its_first_day() -> None:
    unworkable = [
        (era.value, material.value)
        for era, materials in AGE_MATERIALS.items()
        for material in materials
        if MATERIALS[material].branch is not None and ERA_FLOORS[era].get(MATERIALS[material].branch, 0) < MATERIALS[material].level
    ]
    assert unworkable == []


def test_no_floor_falls_from_one_age_to_the_next() -> None:
    fallen = [
        (era.value, branch.value) for earlier, era in pairwise(ORDER) for branch, level in ERA_FLOORS[earlier].items() if ERA_FLOORS[era].get(branch, 0) < level
    ]
    assert fallen == []


def test_every_age_from_bronze_knows_trade_and_the_iron_age_begins_with_coinage() -> None:
    lacking = [era.value for era in ORDER if era_order(era) >= era_order(E.BRONZE) and ERA_FLOORS[era].get(KnowledgeBranch.TRADE, 0) < 1]
    assert lacking == []
    assert Technique.COINAGE in begun_by(E.IRON, ERA_FLOORS[E.IRON])
    assert Technique.COINAGE not in begun_by(E.STONE, ERA_FLOORS[E.STONE])
