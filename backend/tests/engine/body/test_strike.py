from aerona.catalog.materials import MATERIALS
from aerona.catalog.units import UNITS
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.domain.enums.body import BodyRegion, DamageType, HarmCause
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import ArmourType, ShieldType, UnitKind
from aerona.domain.enums.mortal import EquipmentSlot
from aerona.engine.body.strike import BODY, HEAD, Layer, generic_layers, heat_of, resolve, strike_of, through_layer
from aerona.engine.economy.materials import from_spec
from aerona.engine.military.battle import Stack, penetration
from aerona.engine.mortal.equipment import fits_slot
from aerona.rules.registry import Rules

RULES = Rules()
M = MaterialKind


def layer(kind: MaterialKind, slot: EquipmentSlot = EquipmentSlot.ARMOUR_BODY, item_id: int | None = None) -> Layer:
    return Layer(slot, from_spec(MATERIALS[kind]), 100, HEAD if slot is EquipmentSlot.ARMOUR_HEAD else BODY, item_id)


def stack(kind: UnitKind, material: MaterialKind, armour: ArmourType, weapons: list[str]) -> Stack:
    row = ArmyUnitRow(id=1, army_entity_id=1, kind=kind, count=100, quality=50, armour=armour, shield=ShieldType.NONE, helmet=False, weapons=weapons)
    row.material = material.value
    return Stack(row, UNITS[kind], 100)


def test_a_soft_edge_turns_aside_on_hard_armour_and_carries_on_as_blunt_force() -> None:
    bronze = strike_of(RULES, from_spec(MATERIALS[M.BRONZE]), damage_type=DamageType.CUT, heft=None, skill=1.0)
    after = through_layer(RULES, bronze, layer(M.STEEL))
    assert not after.edged and after.momentum < bronze.momentum
    steel = strike_of(RULES, from_spec(MATERIALS[M.STEEL]), damage_type=DamageType.CUT, heft=None, skill=1.0)
    cut = through_layer(RULES, steel, layer(M.LEATHER))
    assert cut.edged and cut.momentum > after.momentum


def test_a_blow_is_soaked_by_layers_it_cannot_break_and_skill_adds_momentum() -> None:
    clumsy = strike_of(RULES, from_spec(MATERIALS[M.IRON]), damage_type=DamageType.BLUNT, heft=None, skill=0.0)
    deft = strike_of(RULES, from_spec(MATERIALS[M.IRON]), damage_type=DamageType.BLUNT, heft=None, skill=1.0)
    assert deft.momentum > clumsy.momentum
    soaked = through_layer(RULES, clumsy, layer(M.STEEL))
    assert soaked.momentum < clumsy.momentum


def test_fire_burns_through_metal_more_than_cloth_and_melts_what_it_outheats() -> None:
    assert heat_of(RULES, HarmCause.MONSTER, DamageType.FIRE, None) == RULES.strike.dragon_heat
    assert heat_of(RULES, HarmCause.BATTLE, DamageType.CUT, None) == 0
    flame = strike_of(RULES, None, damage_type=DamageType.FIRE, heft=None, skill=0.5, heat=RULES.strike.dragon_heat)
    through_steel = resolve(RULES, flame, (layer(M.STEEL, item_id=7),), BodyRegion.TORSO, SeededRandom(RandomKey(1, 1, "strike")))
    through_cloth = resolve(RULES, flame, (layer(M.CLOTH),), BodyRegion.TORSO, SeededRandom(RandomKey(1, 1, "strike")))
    assert through_steel.spent > through_cloth.spent
    lead = resolve(RULES, flame, (layer(M.LEAD, item_id=9),), BodyRegion.TORSO, SeededRandom(RandomKey(1, 1, "strike")))
    assert lead.scorched and lead.scorched[0].item_id == 9 and lead.scorched[0].destroyed


def test_layers_only_guard_the_regions_they_cover() -> None:
    blow = strike_of(RULES, from_spec(MATERIALS[M.STEEL]), damage_type=DamageType.CUT, heft=None, skill=1.0)
    helm = (layer(M.STEEL, EquipmentSlot.ARMOUR_HEAD),)
    assert resolve(RULES, blow, helm, BodyRegion.TORSO, SeededRandom(RandomKey(2, 1, "strike"))).spent == 1.0
    generic = generic_layers(60, 60, 30, 3)
    assert {item.props.kind for item in generic} == {M.IRON}
    assert generic_layers(0, 0, 0, 0) == ()


def test_only_one_rigid_layer_is_worn_per_covering() -> None:
    mail = ItemProfileRow(item_entity_id=1, item_class=ItemClass.PADDING, material=M.IRON.value)
    quilt = ItemProfileRow(item_entity_id=2, item_class=ItemClass.PADDING, material=M.CLOTH.value)
    cloak = ItemProfileRow(item_entity_id=3, item_class=ItemClass.CLOAK, material=M.HIDE.value)
    assert not fits_slot(EquipmentSlot.ARMOUR_UNDER, mail)
    assert fits_slot(EquipmentSlot.ARMOUR_UNDER, quilt)
    assert fits_slot(EquipmentSlot.ARMOUR_COVER, cloak)
    assert not fits_slot(EquipmentSlot.ARMOUR_COVER, quilt)


def test_battle_piercing_compares_weapon_and_armour_materials() -> None:
    steel_blades = [stack(UnitKind.LINE_INFANTRY, M.STEEL, ArmourType.NONE, ["blade"])]
    bronze_blades = [stack(UnitKind.LINE_INFANTRY, M.BRONZE, ArmourType.NONE, ["blade"])]
    plate = stack(UnitKind.LINE_INFANTRY, M.STEEL, ArmourType.PLATE, ["spear"])
    hide = stack(UnitKind.LINE_INFANTRY, M.STEEL, ArmourType.HIDE, ["spear"])
    bare = stack(UnitKind.LINE_INFANTRY, M.STEEL, ArmourType.NONE, ["spear"])
    assert penetration(RULES, steel_blades, plate) > penetration(RULES, bronze_blades, plate)
    assert penetration(RULES, steel_blades, hide) >= penetration(RULES, steel_blades, plate)
    assert penetration(RULES, steel_blades, bare) == 0.0
