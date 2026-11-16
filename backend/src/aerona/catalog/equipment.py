from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.equipment import ArmamentSlot, EquipmentFamily
from aerona.domain.enums.military import ArmourType, ShieldType, UnitFamily, UnitKind, VesselArmament
from aerona.domain.enums.society import KnowledgeBranch

E = EquipmentFamily
S = ArmamentSlot
B = KnowledgeBranch
A = ArmourType
H = ShieldType
V = VesselArmament
C = CommodityKind
D = DamageType


EDGE_DAMAGE = MappingProxyType(
    {
        "blade": D.CUT,
        "spear": D.PIERCE,
        "pike": D.PIERCE,
        "bow": D.PIERCE,
        "crossbow": D.PIERCE,
        "firearm": D.BALLISTIC,
        "launcher": D.EXPLOSIVE,
        "beam": D.ENERGY,
        "stun": D.ELECTRIC,
        "spray": D.CHEMICAL,
    }
)
SPECIAL_DAMAGE = MappingProxyType({E.GRENADE: D.EXPLOSIVE, E.FLAMETHROWER: D.FIRE, E.FOCUS: D.MAGIC})


@dataclass(frozen=True)
class FamilySpec:
    family: EquipmentFamily
    slot: ArmamentSlot
    label: str
    damage: int = 0
    piercing: int = 0
    reach: int = 0
    rate: int = 1
    accuracy: int = 0
    protection: int = 0
    coverage: int = 0
    weight: int = 0
    edge: str = "blunt"
    branch: KnowledgeBranch | None = None
    level: int = 0
    armour: ArmourType | None = None
    shield: ShieldType | None = None
    armament: VesselArmament | None = None
    ammunition: CommodityKind | None = None
    crew: int = 0
    damage_type: DamageType = DamageType.BLUNT
    stock: CommodityKind = CommodityKind.WEAPONS


def weapon(
    head: tuple[EquipmentFamily, ArmamentSlot, str],
    values: tuple[int, int, int, int, int],
    edge: str,
    gate: tuple[KnowledgeBranch | None, int] = (None, 0),
    ammunition: CommodityKind | None = None,
) -> FamilySpec:
    family, slot, label = head
    damage, piercing, reach, rate, accuracy = values
    return FamilySpec(
        family,
        slot,
        label,
        damage,
        piercing,
        reach,
        rate,
        accuracy,
        edge=edge,
        branch=gate[0],
        level=gate[1],
        ammunition=ammunition,
        weight=damage // 10,
        damage_type=SPECIAL_DAMAGE.get(family, EDGE_DAMAGE.get(edge, DamageType.BLUNT)),
    )


def guard(
    head: tuple[EquipmentFamily, ArmamentSlot, str],
    values: tuple[int, int, int],
    kind: ArmourType | ShieldType | None,
    gate: tuple[KnowledgeBranch | None, int] = (None, 0),
) -> FamilySpec:
    family, slot, label = head
    protection, coverage, weight = values
    armour = kind if isinstance(kind, ArmourType) else None
    shield = kind if isinstance(kind, ShieldType) else None
    return FamilySpec(
        family,
        slot,
        label,
        protection=protection,
        coverage=coverage,
        weight=weight,
        branch=gate[0],
        level=gate[1],
        armour=armour,
        shield=shield,
        stock=CommodityKind.ARMOUR,
    )


def gear(
    head: tuple[EquipmentFamily, ArmamentSlot, str],
    values: tuple[int, int, int],
    gate: tuple[KnowledgeBranch | None, int] = (None, 0),
) -> FamilySpec:
    family, slot, label = head
    damage, protection, accuracy = values
    return FamilySpec(
        family,
        slot,
        label,
        damage=damage,
        protection=protection,
        accuracy=accuracy,
        weight=max(1, (damage + protection) // 10),
        branch=gate[0],
        level=gate[1],
        stock=CommodityKind.TOOLS,
    )


def engine(
    head: tuple[EquipmentFamily, str],
    values: tuple[int, int, int, int, int, int],
    armament: VesselArmament,
    gate: tuple[KnowledgeBranch | None, int] = (None, 0),
    hit: tuple[DamageType, CommodityKind | None] = (DamageType.BLUNT, CommodityKind.SIEGE_MATERIEL),
) -> FamilySpec:
    family, label = head
    damage, piercing, reach, rate, accuracy, crew = values
    return FamilySpec(
        family,
        S.VEHICLE_WEAPON,
        label,
        damage,
        piercing,
        reach,
        rate,
        accuracy,
        weight=damage // 5,
        edge="blunt",
        branch=gate[0],
        level=gate[1],
        armament=armament,
        ammunition=hit[1],
        crew=crew,
        damage_type=hit[0],
        stock=CommodityKind.SIEGE_MATERIEL,
    )


FAMILIES: MappingProxyType[EquipmentFamily, FamilySpec] = total(
    EquipmentFamily,
    {
        spec.family: spec
        for spec in (
            weapon((E.CLUB, S.HAND_WEAPON, "Club"), (20, 5, 1, 1, 40), "blunt"),
            weapon((E.DAGGER, S.HAND_WEAPON, "Dagger"), (18, 25, 0, 1, 50), "blade"),
            weapon((E.BLADE, S.HAND_WEAPON, "Blade"), (35, 25, 1, 1, 50), "blade", (B.METALLURGY, 1)),
            weapon((E.LONGBLADE, S.HAND_WEAPON, "Longblade"), (45, 30, 2, 1, 45), "blade", (B.METALLURGY, 2)),
            weapon((E.AXE, S.HAND_WEAPON, "Axe"), (40, 35, 1, 1, 40), "blade", (B.METALLURGY, 1)),
            weapon((E.MACE, S.HAND_WEAPON, "Mace"), (38, 40, 1, 1, 40), "blunt", (B.METALLURGY, 1)),
            weapon((E.HAMMER, S.HAND_WEAPON, "Hammer"), (42, 50, 1, 1, 35), "blunt", (B.METALLURGY, 2)),
            weapon((E.FLAIL, S.HAND_WEAPON, "Flail"), (40, 35, 1, 1, 30), "blunt", (B.METALLURGY, 2)),
            weapon((E.SPEAR, S.HAND_WEAPON, "Spear"), (35, 30, 2, 1, 45), "spear"),
            weapon((E.PIKE, S.HAND_WEAPON, "Pike"), (40, 40, 4, 1, 40), "pike", (B.WARFARE, 2)),
            weapon((E.POLEARM, S.HAND_WEAPON, "Polearm"), (45, 40, 3, 1, 40), "pike", (B.METALLURGY, 2)),
            weapon((E.STAFF, S.HAND_WEAPON, "Staff"), (20, 5, 2, 1, 45), "staff"),
            weapon((E.WHIP, S.HAND_WEAPON, "Whip"), (12, 0, 3, 1, 40), "blunt"),
            weapon((E.FIST_WEAPON, S.HAND_WEAPON, "Fist weapon"), (22, 15, 0, 1, 55), "blunt"),
            weapon((E.SLING, S.MISSILE_WEAPON, "Sling"), (20, 15, 40, 2, 40), "sling", ammunition=C.STONE),
            weapon((E.JAVELIN, S.MISSILE_WEAPON, "Javelin"), (35, 35, 25, 1, 45), "spear"),
            weapon((E.THROWING_WEAPON, S.MISSILE_WEAPON, "Throwing weapon"), (22, 20, 15, 2, 45), "blade"),
            weapon((E.BLOWGUN, S.MISSILE_WEAPON, "Blowgun"), (8, 10, 20, 2, 55), "bow"),
            weapon((E.BOW, S.MISSILE_WEAPON, "Bow"), (30, 30, 60, 3, 50), "bow", ammunition=C.TIMBER),
            weapon((E.LONGBOW, S.MISSILE_WEAPON, "Longbow"), (38, 45, 80, 3, 55), "bow", (B.WARFARE, 2), C.TIMBER),
            weapon((E.COMPOSITE_BOW, S.MISSILE_WEAPON, "Composite bow"), (36, 40, 75, 3, 55), "bow", (B.WARFARE, 2), C.TIMBER),
            weapon((E.CROSSBOW, S.MISSILE_WEAPON, "Crossbow"), (45, 70, 70, 1, 60), "crossbow", (B.METALLURGY, 2), C.TIMBER),
            weapon((E.REPEATING_CROSSBOW, S.MISSILE_WEAPON, "Repeating crossbow"), (30, 40, 45, 4, 45), "crossbow", (B.METALLURGY, 3), C.TIMBER),
            weapon((E.HANDGUN, S.MISSILE_WEAPON, "Handgun"), (50, 75, 40, 1, 35), "firearm", (B.METALLURGY, 3), C.ORE),
            weapon((E.MUSKET, S.MISSILE_WEAPON, "Musket"), (60, 85, 70, 1, 45), "firearm", (B.METALLURGY, 4), C.ORE),
            weapon((E.RIFLE, S.MISSILE_WEAPON, "Rifle"), (65, 90, 110, 2, 65), "firearm", (B.METALLURGY, 5), C.ORE),
            weapon((E.PISTOL, S.MISSILE_WEAPON, "Pistol"), (45, 65, 25, 2, 45), "firearm", (B.METALLURGY, 4), C.ORE),
            weapon((E.REPEATING_GUN, S.MISSILE_WEAPON, "Repeating gun"), (55, 80, 90, 6, 50), "firearm", (B.METALLURGY, 5), C.ORE),
            weapon((E.GRENADE, S.MISSILE_WEAPON, "Grenade"), (60, 30, 15, 1, 35), "blunt", (B.METALLURGY, 4), C.SIEGE_MATERIEL),
            weapon((E.FLAMETHROWER, S.MISSILE_WEAPON, "Flamethrower"), (65, 20, 10, 2, 50), "blunt", (B.METALLURGY, 5), C.FUEL),
            weapon((E.BEAM_WEAPON, S.MISSILE_WEAPON, "Beam weapon"), (70, 95, 120, 3, 75), "beam", (B.METALLURGY, 6), C.FUEL),
            weapon((E.FOCUS, S.MISSILE_WEAPON, "Focus"), (50, 60, 60, 2, 55), "staff", (B.MAGIC, 2), C.MAGICAL_REAGENTS),
            guard((E.HIDE, S.ARMOUR, "Hide"), (8, 60, 10), A.HIDE),
            guard((E.PADDED, S.ARMOUR, "Padded"), (12, 70, 12), A.PADDED),
            guard((E.QUILTED, S.ARMOUR, "Quilted"), (14, 75, 14), A.PADDED, (B.AGRICULTURE, 1)),
            guard((E.LAMELLAR, S.ARMOUR, "Lamellar"), (24, 75, 26), A.SCALE, (B.METALLURGY, 2)),
            guard((E.SCALE, S.ARMOUR, "Scale"), (26, 75, 28), A.SCALE, (B.METALLURGY, 2)),
            guard((E.MAIL, S.ARMOUR, "Mail"), (22, 80, 24), A.MAIL, (B.METALLURGY, 2)),
            guard((E.BRIGANDINE, S.ARMOUR, "Brigandine"), (28, 75, 26), A.MAIL, (B.METALLURGY, 3)),
            guard((E.PLATE, S.ARMOUR, "Plate"), (35, 90, 34), A.PLATE, (B.METALLURGY, 3)),
            guard((E.LAMINAR, S.ARMOUR, "Laminar"), (32, 85, 30), A.PLATE, (B.METALLURGY, 3)),
            guard((E.COMPOSITE, S.ARMOUR, "Composite"), (38, 85, 22), A.COMPOSITE, (B.METALLURGY, 5)),
            guard((E.CERAMIC, S.ARMOUR, "Ceramic"), (40, 70, 18), A.BALLISTIC, (B.METALLURGY, 5)),
            guard((E.SYNTHETIC, S.ARMOUR, "Synthetic"), (42, 90, 12), A.COMPOSITE, (B.METALLURGY, 6)),
            guard((E.POWERED, S.ARMOUR, "Powered"), (55, 95, 40), A.POWERED, (B.METALLURGY, 6)),
            guard((E.WARDED, S.ARMOUR, "Warded"), (45, 90, 15), A.ENCHANTED, (B.MAGIC, 3)),
            guard((E.BUCKLER, S.SHIELD, "Buckler"), (5, 15, 4), H.SMALL),
            guard((E.ROUND_SHIELD, S.SHIELD, "Round shield"), (8, 25, 8), H.SMALL),
            guard((E.HEATER, S.SHIELD, "Heater"), (10, 30, 9), H.LARGE, (B.METALLURGY, 2)),
            guard((E.KITE, S.SHIELD, "Kite"), (12, 35, 11), H.LARGE, (B.METALLURGY, 2)),
            guard((E.TOWER_SHIELD, S.SHIELD, "Tower shield"), (18, 50, 18), H.TOWER, (B.WARFARE, 1)),
            guard((E.PAVISE, S.SHIELD, "Pavise"), (20, 55, 22), H.TOWER, (B.WARFARE, 2)),
            guard((E.PROJECTED, S.SHIELD, "Projected"), (25, 60, 2), H.TOWER, (B.MAGIC, 3)),
            guard((E.CAP, S.HELMET, "Cap"), (4, 10, 2), None),
            guard((E.OPEN_HELM, S.HELMET, "Open helm"), (7, 12, 4), None, (B.METALLURGY, 1)),
            guard((E.CLOSED_HELM, S.HELMET, "Closed helm"), (10, 14, 6), None, (B.METALLURGY, 2)),
            guard((E.FULL_HELM, S.HELMET, "Full helm"), (13, 16, 8), None, (B.METALLURGY, 3)),
            guard((E.LIGHT_BARDING, S.BARDING, "Light barding"), (10, 50, 20), None, (B.WARFARE, 1)),
            guard((E.HEAVY_BARDING, S.BARDING, "Heavy barding"), (25, 75, 45), None, (B.METALLURGY, 3)),
            engine((E.RAM, "Ram"), (60, 70, 0, 1, 50, 0), V.RAMS, hit=(D.BLUNT, None)),
            engine((E.BALLISTA, "Ballista"), (45, 70, 80, 1, 55, 3), V.MISSILES, (B.WARFARE, 2), (D.PIERCE, C.TIMBER)),
            engine((E.CATAPULT_ENGINE, "Catapult engine"), (55, 40, 90, 1, 35, 5), V.SIEGE_ENGINES, (B.WARFARE, 2)),
            engine((E.TREBUCHET_ENGINE, "Trebuchet engine"), (80, 50, 120, 1, 30, 10), V.SIEGE_ENGINES, (B.WARFARE, 3)),
            engine((E.BOMBARD, "Bombard"), (85, 80, 100, 1, 25, 8), V.SIEGE_ENGINES, (B.METALLURGY, 3)),
            engine((E.CANNON, "Cannon"), (70, 80, 120, 1, 40, 6), V.SIEGE_ENGINES, (B.METALLURGY, 4)),
            engine((E.CARRONADE, "Carronade"), (75, 60, 60, 1, 35, 4), V.SIEGE_ENGINES, (B.METALLURGY, 4)),
            engine((E.HOWITZER, "Howitzer"), (85, 75, 160, 1, 45, 6), V.SIEGE_ENGINES, (B.METALLURGY, 5), (D.EXPLOSIVE, C.SIEGE_MATERIEL)),
            engine((E.MORTAR, "Mortar"), (75, 60, 120, 1, 35, 4), V.SIEGE_ENGINES, (B.METALLURGY, 4), (D.EXPLOSIVE, C.SIEGE_MATERIEL)),
            engine((E.ROCKET_LAUNCHER, "Rocket launcher"), (70, 50, 150, 3, 35, 3), V.MISSILES, (B.METALLURGY, 5), (D.EXPLOSIVE, C.FUEL)),
            engine((E.MISSILE_LAUNCHER, "Missile launcher"), (90, 85, 250, 2, 75, 2), V.MISSILES, (B.METALLURGY, 6), (D.EXPLOSIVE, C.FUEL)),
            engine((E.TORPEDO, "Torpedo"), (95, 90, 120, 1, 55, 3), V.MISSILES, (B.SHIPBUILDING, 5), (D.EXPLOSIVE, C.FUEL)),
            engine((E.MINE_LAYER, "Mine layer"), (85, 70, 0, 1, 30, 2), V.SIEGE_ENGINES, (B.METALLURGY, 5), (D.EXPLOSIVE, C.SIEGE_MATERIEL)),
            engine((E.HEAVY_FLAMETHROWER, "Heavy flamethrower"), (70, 30, 25, 2, 55, 2), V.SIEGE_ENGINES, (B.METALLURGY, 5), (D.FIRE, C.FUEL)),
            engine((E.BEAM_CANNON, "Beam cannon"), (95, 100, 200, 2, 80, 3), V.MISSILES, (B.METALLURGY, 6), (D.ENERGY, C.FUEL)),
            engine((E.FOCUS_ARRAY, "Focus array"), (75, 70, 140, 2, 60, 4), V.RITES, (B.MAGIC, 3), (D.MAGIC, C.MAGICAL_REAGENTS)),
            engine((E.HARPOON, "Harpoon"), (40, 60, 40, 1, 50, 2), V.RAMS, (B.SEAFARING, 1), (D.PIERCE, C.TIMBER)),
            engine((E.BOARDING_GEAR, "Boarding gear"), (30, 20, 5, 1, 50, 0), V.RAMS, (B.SEAFARING, 1), (D.CUT, None)),
            weapon((E.ASSAULT_RIFLE, S.MISSILE_WEAPON, "Assault rifle"), (62, 85, 90, 5, 60), "firearm", (B.METALLURGY, 6), C.ORE),
            weapon((E.SUBMACHINE_GUN, S.MISSILE_WEAPON, "Submachine gun"), (48, 60, 35, 7, 45), "firearm", (B.METALLURGY, 5), C.ORE),
            weapon((E.SHOTGUN, S.MISSILE_WEAPON, "Shotgun"), (70, 45, 20, 2, 55), "firearm", (B.METALLURGY, 5), C.ORE),
            weapon((E.SNIPER_RIFLE, S.MISSILE_WEAPON, "Sniper rifle"), (75, 95, 180, 1, 85), "firearm", (B.METALLURGY, 6), C.ORE),
            weapon((E.MACHINE_GUN, S.MISSILE_WEAPON, "Machine gun"), (60, 80, 120, 9, 45), "firearm", (B.METALLURGY, 6), C.ORE),
            weapon((E.RAILGUN, S.MISSILE_WEAPON, "Railgun"), (85, 100, 160, 2, 70), "firearm", (B.METALLURGY, 7), C.FUEL),
            weapon((E.PLASMA_GUN, S.MISSILE_WEAPON, "Plasma gun"), (80, 90, 80, 3, 60), "beam", (B.METALLURGY, 7), C.FUEL),
            weapon((E.STUN_WEAPON, S.MISSILE_WEAPON, "Stun weapon"), (25, 10, 15, 2, 55), "stun", (B.METALLURGY, 5), C.FUEL),
            weapon((E.CHEMICAL_SPRAYER, S.MISSILE_WEAPON, "Chemical sprayer"), (55, 30, 15, 2, 45), "spray", (B.MEDICINE, 4), C.POISON),
            guard((E.BALLISTIC_VEST, S.ARMOUR, "Ballistic vest"), (36, 60, 10), A.BALLISTIC, (B.METALLURGY, 5)),
            guard((E.RIOT_SHIELD, S.SHIELD, "Riot shield"), (16, 45, 8), H.RIOT, (B.METALLURGY, 5)),
            guard((E.ENERGY_SHIELD, S.SHIELD, "Energy shield"), (30, 65, 3), H.ENERGY, (B.METALLURGY, 7)),
            guard((E.COMBAT_HELMET, S.HELMET, "Combat helmet"), (14, 16, 4), None, (B.METALLURGY, 5)),
            gear((E.OPTICS, S.SENSOR, "Optics"), (0, 0, 70), (B.ASTRONOMY, 3)),
            gear((E.SCANNER, S.SENSOR, "Scanner"), (0, 4, 85), (B.METALLURGY, 6)),
            gear((E.NEURAL_IMPLANT, S.IMPLANT, "Neural implant"), (20, 6, 75), (B.BIOMANCY, 3)),
            gear((E.BIONIC_LIMB, S.IMPLANT, "Bionic limb"), (60, 12, 50), (B.BIOMANCY, 2)),
            gear((E.MEDKIT, S.SUPPORT, "Medkit"), (0, 10, 40), (B.MEDICINE, 3)),
            gear((E.JAMMER, S.SUPPORT, "Jammer"), (0, 14, 60), (B.METALLURGY, 6)),
            gear((E.RECON_DRONE, S.SUPPORT, "Recon drone"), (10, 8, 80), (B.SKY_NAVIGATION, 6)),
            engine((E.AUTOCANNON, "Autocannon"), (70, 75, 140, 6, 55, 2), V.MISSILES, (B.METALLURGY, 6), (D.BALLISTIC, C.ORE)),
            engine((E.MASS_DRIVER, "Mass driver"), (95, 100, 260, 1, 70, 3), V.MISSILES, (B.METALLURGY, 7), (D.BALLISTIC, C.ORE)),
            engine((E.PLASMA_CANNON, "Plasma cannon"), (95, 95, 180, 2, 65, 3), V.MISSILES, (B.METALLURGY, 7), (D.ENERGY, C.FUEL)),
        )
    },
)

SLOT_FAMILIES: MappingProxyType[ArmamentSlot, tuple[EquipmentFamily, ...]] = total(
    ArmamentSlot, {slot: tuple(spec.family for spec in FAMILIES.values() if spec.slot is slot) for slot in ArmamentSlot}
)
UNIT_SLOTS: MappingProxyType[UnitFamily, tuple[ArmamentSlot, ...]] = total(
    UnitFamily,
    {
        UnitFamily.INFANTRY: (S.HAND_WEAPON, S.MISSILE_WEAPON, S.ARMOUR, S.SHIELD, S.HELMET, S.SENSOR, S.IMPLANT, S.SUPPORT),
        UnitFamily.MISSILE: (S.MISSILE_WEAPON, S.HAND_WEAPON, S.ARMOUR, S.SHIELD, S.HELMET, S.SENSOR, S.IMPLANT),
        UnitFamily.MOUNTED: (S.HAND_WEAPON, S.MISSILE_WEAPON, S.ARMOUR, S.SHIELD, S.HELMET, S.BARDING, S.SENSOR),
        UnitFamily.VEHICLE: (S.HAND_WEAPON, S.MISSILE_WEAPON, S.ARMOUR, S.SHIELD, S.HELMET, S.BARDING, S.SENSOR, S.SUPPORT),
        UnitFamily.BEAST: (S.BARDING,),
        UnitFamily.ENGINEER: (S.HAND_WEAPON, S.ARMOUR, S.SHIELD, S.HELMET, S.SUPPORT),
        UnitFamily.MAGIC: (S.MISSILE_WEAPON, S.HAND_WEAPON, S.ARMOUR, S.IMPLANT),
        UnitFamily.EXOTIC: (S.ARMOUR,),
        UnitFamily.AIR: (S.MISSILE_WEAPON, S.HAND_WEAPON, S.ARMOUR, S.HELMET, S.SENSOR, S.IMPLANT),
        UnitFamily.SPACE: (S.HAND_WEAPON, S.MISSILE_WEAPON, S.ARMOUR, S.HELMET, S.SENSOR, S.IMPLANT, S.SUPPORT),
        UnitFamily.ELECTRONIC: (S.MISSILE_WEAPON, S.HAND_WEAPON, S.ARMOUR, S.HELMET, S.SENSOR, S.SUPPORT),
        UnitFamily.SPECIAL: (S.HAND_WEAPON, S.MISSILE_WEAPON, S.ARMOUR, S.SHIELD, S.HELMET, S.SENSOR, S.IMPLANT, S.SUPPORT),
    },
)

U = UnitKind
LIGHT_GUARD = (E.QUILTED, E.PADDED, E.HIDE, E.SYNTHETIC)
MEDIUM_GUARD = (E.MAIL, E.SCALE, E.LAMELLAR, E.BRIGANDINE, E.COMPOSITE, E.SYNTHETIC, E.QUILTED, E.PADDED)
HEAVY_GUARD = (E.POWERED, E.PLATE, E.LAMINAR, E.CERAMIC, E.COMPOSITE, E.MAIL, E.SCALE)
VEST_GUARD = (E.BALLISTIC_VEST, E.SYNTHETIC, E.CERAMIC, E.COMPOSITE, E.QUILTED, E.PADDED)
WARD_GUARD = (E.WARDED, E.QUILTED, E.PADDED)
SMALL_SHIELDS = (E.BUCKLER, E.ROUND_SHIELD)
BIG_SHIELDS = (E.PROJECTED, E.HEATER, E.KITE, E.ROUND_SHIELD)
WALL_SHIELDS = (E.PROJECTED, E.TOWER_SHIELD, E.PAVISE, E.KITE, E.ROUND_SHIELD)
LIGHT_HELMS = (E.COMBAT_HELMET, E.OPEN_HELM, E.CAP)
MEDIUM_HELMS = (E.COMBAT_HELMET, E.CLOSED_HELM, E.OPEN_HELM, E.CAP)
HEAVY_HELMS = (E.FULL_HELM, E.CLOSED_HELM, E.OPEN_HELM)
SIDEARMS = (E.BLADE, E.DAGGER, E.AXE, E.CLUB)
CREW_ARMS = (E.SUBMACHINE_GUN, E.PISTOL, E.HANDGUN, E.CROSSBOW, E.BOW)
RIFLES = (E.RAILGUN, E.PLASMA_GUN, E.ASSAULT_RIFLE, E.RIFLE, E.MUSKET, E.HANDGUN)
SIGHTS = (E.SCANNER, E.OPTICS)
AIDS = (E.MEDKIT,)
LIGHT_BARDING = (E.LIGHT_BARDING,)
HEAVY_BARDING = (E.HEAVY_BARDING, E.LIGHT_BARDING)


def arms(
    *,
    hand: tuple[EquipmentFamily, ...] = (),
    missile: tuple[EquipmentFamily, ...] = (),
    armour: tuple[EquipmentFamily, ...] = LIGHT_GUARD,
    shield: tuple[EquipmentFamily, ...] = SMALL_SHIELDS,
    helmet: tuple[EquipmentFamily, ...] = LIGHT_HELMS,
    barding: tuple[EquipmentFamily, ...] = (),
    sensor: tuple[EquipmentFamily, ...] = (),
    implant: tuple[EquipmentFamily, ...] = (),
    support: tuple[EquipmentFamily, ...] = (),
) -> MappingProxyType[ArmamentSlot, tuple[EquipmentFamily, ...]]:
    return MappingProxyType(
        {
            slot: families
            for slot, families in (
                (S.HAND_WEAPON, hand),
                (S.MISSILE_WEAPON, missile),
                (S.ARMOUR, armour),
                (S.SHIELD, shield),
                (S.HELMET, helmet),
                (S.BARDING, barding),
                (S.SENSOR, sensor),
                (S.IMPLANT, implant),
                (S.SUPPORT, support),
            )
            if families
        }
    )


ROLE_ARMS: MappingProxyType[UnitKind, MappingProxyType[ArmamentSlot, tuple[EquipmentFamily, ...]]] = total(
    UnitKind,
    {
        U.LEVY: arms(hand=(E.SPEAR, E.CLUB, E.AXE, E.STAFF)),
        U.LINE_INFANTRY: arms(hand=(E.SPEAR, E.BLADE, E.AXE), missile=RIFLES, armour=MEDIUM_GUARD, shield=BIG_SHIELDS, helmet=MEDIUM_HELMS, sensor=SIGHTS),
        U.GUARD_INFANTRY: arms(hand=(E.POLEARM, E.LONGBLADE, E.HAMMER, E.BLADE), armour=HEAVY_GUARD, shield=BIG_SHIELDS, helmet=HEAVY_HELMS),
        U.HEAVY_INFANTRY: arms(hand=(E.MACE, E.HAMMER, E.LONGBLADE, E.AXE, E.BLADE), armour=HEAVY_GUARD, shield=BIG_SHIELDS, helmet=HEAVY_HELMS),
        U.LIGHT_INFANTRY: arms(hand=(E.SPEAR, E.BLADE, E.AXE, E.DAGGER), missile=(E.JAVELIN, E.THROWING_WEAPON, E.SLING)),
        U.SHIELD_INFANTRY: arms(hand=(E.SPEAR, E.BLADE, E.AXE), armour=MEDIUM_GUARD, shield=WALL_SHIELDS, helmet=MEDIUM_HELMS),
        U.SHOCK_INFANTRY: arms(hand=(E.AXE, E.HAMMER, E.FLAIL, E.MACE, E.LONGBLADE, E.FIST_WEAPON), armour=MEDIUM_GUARD, helmet=MEDIUM_HELMS),
        U.PIKE_INFANTRY: arms(hand=(E.PIKE, E.POLEARM, E.SPEAR), armour=MEDIUM_GUARD, helmet=MEDIUM_HELMS),
        U.MARINES: arms(
            hand=(E.BLADE, E.AXE, E.DAGGER, E.SPEAR), missile=(E.ASSAULT_RIFLE, E.SHOTGUN, E.PISTOL, E.HANDGUN, E.CROSSBOW, E.JAVELIN), sensor=SIGHTS
        ),
        U.GRENADIERS: arms(hand=(E.BLADE, E.DAGGER), missile=(E.GRENADE, E.ASSAULT_RIFLE, E.MUSKET, E.RIFLE), armour=MEDIUM_GUARD, helmet=MEDIUM_HELMS),
        U.ARCHERS: arms(hand=SIDEARMS, missile=(E.LONGBOW, E.COMPOSITE_BOW, E.BOW)),
        U.CROSSBOW_INFANTRY: arms(hand=SIDEARMS, missile=(E.REPEATING_CROSSBOW, E.CROSSBOW), armour=MEDIUM_GUARD, shield=WALL_SHIELDS, helmet=MEDIUM_HELMS),
        U.SLINGERS: arms(hand=(E.CLUB, E.DAGGER), missile=(E.SLING,)),
        U.JAVELINEERS: arms(hand=(E.SPEAR, E.BLADE, E.AXE), missile=(E.JAVELIN, E.THROWING_WEAPON)),
        U.GUNNERS: arms(
            hand=(E.BLADE, E.DAGGER),
            missile=(E.BEAM_WEAPON, E.MACHINE_GUN, E.SNIPER_RIFLE, E.REPEATING_GUN, E.RIFLE, E.MUSKET, E.HANDGUN),
            armour=MEDIUM_GUARD,
            sensor=SIGHTS,
        ),
        U.MOUNTED_ARCHERS: arms(hand=(E.BLADE, E.LONGBLADE, E.AXE), missile=(E.COMPOSITE_BOW, E.BOW), barding=LIGHT_BARDING),
        U.MOUNTED_GUNNERS: arms(
            hand=(E.LONGBLADE, E.BLADE), missile=(E.ASSAULT_RIFLE, E.RIFLE, E.PISTOL, E.HANDGUN, E.MUSKET), armour=MEDIUM_GUARD, barding=LIGHT_BARDING
        ),
        U.LIGHT_CAVALRY: arms(hand=(E.SPEAR, E.LONGBLADE, E.BLADE, E.AXE), missile=(E.JAVELIN, E.BOW), barding=LIGHT_BARDING),
        U.HEAVY_CAVALRY: arms(
            hand=(E.SPEAR, E.LONGBLADE, E.MACE, E.POLEARM, E.HAMMER),
            armour=HEAVY_GUARD,
            shield=BIG_SHIELDS,
            helmet=HEAVY_HELMS,
            barding=HEAVY_BARDING,
        ),
        U.CHARIOTS: arms(hand=(E.SPEAR, E.AXE, E.BLADE), missile=(E.COMPOSITE_BOW, E.BOW, E.JAVELIN), armour=MEDIUM_GUARD, barding=HEAVY_BARDING),
        U.BEAST_RIDERS: arms(hand=(E.SPEAR, E.POLEARM, E.LONGBLADE), missile=(E.JAVELIN, E.BOW), armour=MEDIUM_GUARD, barding=HEAVY_BARDING),
        U.SKY_RIDERS: arms(hand=(E.SPEAR, E.LONGBLADE, E.BLADE), missile=(E.RIFLE, E.CROSSBOW, E.BOW, E.JAVELIN), barding=LIGHT_BARDING),
        U.WAR_BEASTS: arms(armour=(), shield=(), helmet=(), barding=HEAVY_BARDING),
        U.BOUND_BEASTS: arms(armour=(), shield=(), helmet=(), barding=HEAVY_BARDING),
        U.CONSTRUCTS: arms(armour=(E.WARDED, E.POWERED, E.PLATE, E.CERAMIC), shield=(), helmet=()),
        U.SUMMONED_HOST: arms(armour=(E.WARDED, E.HIDE), shield=(), helmet=()),
        U.ENGINEERS: arms(hand=(E.HAMMER, E.AXE, E.CLUB), armour=MEDIUM_GUARD),
        U.SAPPERS: arms(hand=(E.AXE, E.HAMMER, E.DAGGER)),
        U.SIEGE_CREW: arms(hand=(E.AXE, E.CLUB, E.DAGGER), missile=CREW_ARMS),
        U.ARTILLERY_CREW: arms(hand=(E.BLADE, E.DAGGER), missile=CREW_ARMS),
        U.VEHICLE_CREW: arms(hand=(E.BLADE, E.DAGGER), missile=CREW_ARMS),
        U.NAVAL_CREW: arms(hand=(E.BLADE, E.AXE, E.DAGGER, E.SPEAR), missile=(E.PISTOL, E.CROSSBOW, E.BOW, E.JAVELIN)),
        U.SKY_CREW: arms(hand=(E.BLADE, E.DAGGER), missile=(E.RIFLE, E.PISTOL, E.CROSSBOW)),
        U.VOID_CREW: arms(hand=(E.BLADE, E.DAGGER), missile=(E.PLASMA_GUN, E.BEAM_WEAPON, E.RIFLE, E.PISTOL), sensor=SIGHTS, support=AIDS),
        U.BATTLE_CASTERS: arms(hand=(E.STAFF, E.DAGGER), missile=(E.FOCUS,), armour=WARD_GUARD, shield=(), helmet=()),
        U.SUPPORT_CASTERS: arms(hand=(E.STAFF,), missile=(E.FOCUS,), armour=WARD_GUARD, shield=(), helmet=()),
        U.SUMMONERS: arms(hand=(E.STAFF, E.DAGGER), missile=(E.FOCUS,), armour=WARD_GUARD, shield=(), helmet=()),
        U.GIFTED: arms(hand=(E.STAFF, E.DAGGER), missile=(E.FOCUS,), armour=WARD_GUARD, shield=(), helmet=()),
        U.DAMPENERS: arms(hand=(E.DAGGER,), missile=(E.FOCUS,), armour=WARD_GUARD, shield=(), helmet=()),
        U.DETECTORS: arms(hand=(E.DAGGER,), missile=(E.FOCUS,), shield=(), helmet=()),
        U.MECHANISED_INFANTRY: arms(hand=(E.BLADE, E.DAGGER), missile=RIFLES, armour=VEST_GUARD, shield=(), helmet=MEDIUM_HELMS, sensor=SIGHTS, support=AIDS),
        U.SPECIAL_FORCES: arms(
            hand=(E.BLADE, E.DAGGER),
            missile=(E.SNIPER_RIFLE, E.SUBMACHINE_GUN, E.ASSAULT_RIFLE, E.SHOTGUN, E.RIFLE, E.CROSSBOW, E.BOW),
            armour=VEST_GUARD,
            shield=(),
            helmet=LIGHT_HELMS,
            sensor=SIGHTS,
            implant=(E.NEURAL_IMPLANT, E.BIONIC_LIMB),
            support=(E.RECON_DRONE, E.JAMMER, E.MEDKIT),
        ),
        U.PARTISANS: arms(
            hand=(E.BLADE, E.AXE, E.CLUB, E.DAGGER), missile=(E.ASSAULT_RIFLE, E.RIFLE, E.MUSKET, E.HANDGUN, E.BOW, E.SLING), shield=(), helmet=()
        ),
        U.PEACEKEEPERS: arms(
            hand=(E.CLUB, E.STAFF, E.BLADE),
            missile=(E.STUN_WEAPON, E.ASSAULT_RIFLE, E.RIFLE, E.CROSSBOW),
            armour=VEST_GUARD,
            shield=(E.RIOT_SHIELD, E.HEATER, E.ROUND_SHIELD),
            helmet=MEDIUM_HELMS,
        ),
        U.MEDICS: arms(hand=(E.DAGGER,), missile=(E.PISTOL,), shield=(), support=(E.MEDKIT,)),
        U.DRONE_OPERATORS: arms(
            hand=(E.DAGGER,), missile=(E.SUBMACHINE_GUN, E.PISTOL), armour=VEST_GUARD, shield=(), sensor=SIGHTS, support=(E.RECON_DRONE, E.JAMMER)
        ),
        U.SIGNALS_TROOPS: arms(
            hand=(E.DAGGER,), missile=(E.ASSAULT_RIFLE, E.RIFLE, E.PISTOL), armour=VEST_GUARD, shield=(), sensor=SIGHTS, support=(E.JAMMER,)
        ),
        U.POWERED_TROOPERS: arms(
            hand=(E.LONGBLADE, E.HAMMER, E.FIST_WEAPON),
            missile=(E.PLASMA_GUN, E.RAILGUN, E.MACHINE_GUN, E.FLAMETHROWER),
            armour=(E.POWERED, E.COMPOSITE, E.CERAMIC),
            shield=(E.ENERGY_SHIELD, E.PROJECTED, E.TOWER_SHIELD),
            helmet=HEAVY_HELMS,
            sensor=SIGHTS,
            implant=(E.NEURAL_IMPLANT, E.BIONIC_LIMB),
        ),
        U.DROP_TROOPS: arms(
            hand=(E.BLADE, E.DAGGER),
            missile=(E.PLASMA_GUN, E.ASSAULT_RIFLE, E.GRENADE, E.RIFLE),
            armour=VEST_GUARD,
            shield=(),
            helmet=MEDIUM_HELMS,
            sensor=SIGHTS,
            support=AIDS,
        ),
        U.PILOTS: arms(hand=(E.DAGGER,), missile=(E.PISTOL, E.HANDGUN), shield=(), helmet=(E.COMBAT_HELMET, E.CAP), sensor=SIGHTS, implant=(E.NEURAL_IMPLANT,)),
    },
)
