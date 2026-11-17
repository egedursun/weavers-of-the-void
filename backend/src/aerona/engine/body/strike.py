from dataclasses import dataclass, replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.harm import HARM_CAUSES
from aerona.catalog.materials import MATERIALS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalEquipmentRow
from aerona.domain.enums.body import BodyRegion, DamageType, HarmCause
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mortal import EquipmentSlot
from aerona.engine.economy.materials import MaterialBook, MaterialProps, from_spec, node_material
from aerona.rules.registry import Rules

EDGED = frozenset({DamageType.CUT, DamageType.PIERCE, DamageType.BALLISTIC})
HEAD = frozenset({BodyRegion.HEAD})
BODY = frozenset({BodyRegion.TORSO, BodyRegion.ARMS, BodyRegion.LEGS, BodyRegion.WINGS, BodyRegion.TAIL})
EVERYWHERE = frozenset(BodyRegion)
LIMBS = frozenset({BodyRegion.ARMS, BodyRegion.LEGS, BodyRegion.WINGS, BodyRegion.TAIL})
LAYER_ORDER = (EquipmentSlot.WIELDED_OFF, EquipmentSlot.ARMOUR_COVER, EquipmentSlot.ARMOUR_BODY, EquipmentSlot.ARMOUR_HEAD, EquipmentSlot.ARMOUR_UNDER)
LAYER_REGIONS: dict[EquipmentSlot, frozenset[BodyRegion]] = {
    EquipmentSlot.WIELDED_OFF: EVERYWHERE,
    EquipmentSlot.ARMOUR_COVER: BODY,
    EquipmentSlot.ARMOUR_BODY: BODY,
    EquipmentSlot.ARMOUR_HEAD: HEAD,
    EquipmentSlot.ARMOUR_UNDER: BODY,
}
GENERIC_MATERIALS = ((3, MaterialKind.IRON), (2, MaterialKind.BRONZE), (1, MaterialKind.COPPER), (0, MaterialKind.LEATHER))


@dataclass(frozen=True)
class Layer:
    slot: EquipmentSlot
    props: MaterialProps
    coverage: int
    regions: frozenset[BodyRegion]
    item_id: int | None = None


@dataclass(frozen=True)
class Strike:
    momentum: float
    edged: bool
    attack: int
    heat: int = 0


@dataclass(frozen=True)
class Scorch:
    item_id: int
    destroyed: bool


@dataclass(frozen=True)
class Outcome:
    strike: Strike
    damage_type: DamageType
    spent: float
    scorched: tuple[Scorch, ...] = ()
    stopped_by: EquipmentSlot | None = None


def strike_of(rules: Rules, weapon: MaterialProps | None, *, damage_type: DamageType, heft: int | None, skill: float, heat: int = 0) -> Strike:
    table = rules.strike
    mass = float(weapon.solid_density if weapon is not None else table.unarmed_mass)
    if heft is not None:
        mass = (mass + heft) / 2
    floor = table.speed_floor_pct / PERCENT
    speed = floor + (1 - floor) * max(0.0, min(1.0, skill))
    momentum = mass * speed * table.momentum_scale_pct / PERCENT
    edged = damage_type in EDGED
    attack = (weapon.shear_yield if weapon is not None else 0) if edged else round(momentum * table.blunt_force_pct / PERCENT)
    return Strike(momentum, edged, attack, heat)


@dataclass(frozen=True)
class Wielding:
    weapon: MaterialProps | None
    skill: float
    heft: int | None = None


def heat_of(rules: Rules, cause: HarmCause, damage_type: DamageType, heat: int | None) -> int:
    if damage_type is not DamageType.FIRE:
        return 0
    if heat is not None:
        return heat
    return int(getattr(rules.strike, HARM_CAUSES[cause].heat_rule))


def through_layer(rules: Rules, strike: Strike, layer: Layer) -> Strike:
    table = rules.strike
    props = layer.props
    if strike.heat > 0:
        return replace(strike, heat=round(strike.heat * props.thermal_conductivity / PERCENT * table.fire_conduct_pct / PERCENT))
    if strike.edged:
        if strike.attack < props.shear_yield:
            kept = strike.momentum * table.deflect_keep_pct / PERCENT
            return Strike(kept, False, round(kept * table.blunt_force_pct / PERCENT))
        share = (strike.attack - props.shear_yield + 1) / max(1, props.shear_fracture - props.shear_yield + 1)
        return replace(strike, momentum=strike.momentum * max(0.1, min(1.0, share)))
    if strike.attack < props.impact_yield:
        kept = strike.momentum * max(0.0, 1 - props.impact_yield / PERCENT * table.blunt_absorb_pct / PERCENT)
        return Strike(kept, False, round(kept * table.blunt_force_pct / PERCENT))
    share = (strike.attack - props.impact_yield + 1) / max(1, props.impact_fracture - props.impact_yield + 1)
    return replace(strike, momentum=strike.momentum * max(0.1, min(1.0, share)))


def scorch(layer: Layer, heat: int) -> Scorch | None:
    if layer.item_id is None or heat < layer.props.melting_point:
        return None
    return Scorch(layer.item_id, heat >= layer.props.boiling_point)


def resolve(rules: Rules, strike: Strike, layers: tuple[Layer, ...], region: BodyRegion, rng: SeededRandom) -> Outcome:
    current = strike
    scorched: list[Scorch] = []
    for layer in layers:
        if region not in layer.regions:
            continue
        cover = layer.coverage * (rules.strike.limb_cover_pct / PERCENT if region in LIMBS and BodyRegion.TORSO in layer.regions else 1)
        if layer.slot is EquipmentSlot.WIELDED_OFF:
            cover *= rules.strike.shield_block_pct / PERCENT
        if not rng.chance(cover):
            continue
        if current.heat > 0:
            burnt = scorch(layer, current.heat)
            if burnt is not None:
                scorched.append(burnt)
        current = through_layer(rules, current, layer)
    spent = current.momentum / strike.momentum if strike.momentum > 0 else 1.0
    if strike.heat > 0:
        spent = current.heat / strike.heat
    damage = (DamageType.CUT if current.edged else DamageType.BLUNT) if strike.heat <= 0 else DamageType.FIRE
    return Outcome(current, damage, spent, tuple(scorched))


async def item_props(session: AsyncSession, item_id: int, profile: ItemProfileRow) -> MaterialProps:
    row = await node_material(session, item_id, MaterialSlot.BODY)
    if row is not None:
        entity = await session.get(EntityRow, item_id)
        found = (await MaterialBook.load(session)).props(entity.world_id if entity is not None else None, row.material, row.world_material_id)
        if found is not None:
            return found
    kind = next((item for item in MaterialKind if item.value == profile.material), MaterialKind.LEATHER)
    return from_spec(MATERIALS[kind])


async def worn_layers(session: AsyncSession, bearer_id: int) -> tuple[Layer, ...]:
    equipment = await session.get(MortalEquipmentRow, bearer_id)
    if equipment is None:
        return ()
    layers: list[Layer] = []
    for slot in LAYER_ORDER:
        item_id = getattr(equipment, f"{slot.value}_id")
        profile = await session.get(ItemProfileRow, item_id) if item_id is not None else None
        if item_id is None or profile is None or profile.condition < 1:
            continue
        if slot is EquipmentSlot.WIELDED_OFF and profile.item_class is not ItemClass.SHIELD:
            continue
        layers.append(Layer(slot, await item_props(session, item_id, profile), profile.coverage or PERCENT, LAYER_REGIONS[slot], item_id))
    return tuple(layers)


def generic_layers(head: int, torso: int, limbs: int, metallurgy: int) -> tuple[Layer, ...]:
    kind = next(material for level, material in GENERIC_MATERIALS if metallurgy >= level)
    props = from_spec(MATERIALS[kind])
    layers = []
    if head > 0:
        layers.append(Layer(EquipmentSlot.ARMOUR_HEAD, props, head, HEAD))
    if torso > 0:
        layers.append(Layer(EquipmentSlot.ARMOUR_BODY, props, torso, frozenset({BodyRegion.TORSO})))
    if limbs > 0:
        layers.append(Layer(EquipmentSlot.ARMOUR_BODY, props, limbs, LIMBS))
    return tuple(layers)
