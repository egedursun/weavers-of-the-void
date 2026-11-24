from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.carriers import CARRIERS
from aerona.core.total import total
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.environment import MovementMode
from aerona.domain.enums.mind import SkillKind, TraitKind
from aerona.domain.enums.operations import (
    CarrierKind,
    CrewStation,
    EchelonLevel,
    ExpeditionEvent,
    ExpeditionGround,
    ExpeditionRole,
    QuirkKind,
    ResolveKind,
    ShotKind,
)
from aerona.domain.enums.vehicles import VehicleSection
from aerona.rules.registry import Rules

Q = QuirkKind
V = VehicleSection


@dataclass(frozen=True)
class TransportSpec:
    kind: CarrierKind
    label: str
    capacity: int
    river_only: bool = False
    sea_only: bool = False


TRANSPORTS: dict[CarrierKind, TransportSpec] = {
    kind: TransportSpec(
        kind,
        spec.label,
        spec.capacity,
        river_only=spec.modes == frozenset({TradeMode.RIVER}),
        sea_only=spec.modes == frozenset({TradeMode.SEA}),
    )
    for kind, spec in CARRIERS.items()
}

ECHELON_LABELS: dict[EchelonLevel, str] = {
    EchelonLevel.ARMY_GROUP: "Army group",
    EchelonLevel.ARMY: "Army",
    EchelonLevel.CORPS: "Corps",
    EchelonLevel.DIVISION: "Division",
    EchelonLevel.BRIGADE: "Brigade",
    EchelonLevel.DETACHMENT: "Detachment",
}

SHOT_TARGETS: dict[ShotKind, tuple[VehicleSection, ...]] = {
    ShotKind.ROUND: (V.HULL, V.KEEL, V.BOW, V.STERN, V.GUN_DECK, V.HOLD, V.ENGINE, V.BOILER, V.DRIVE, V.ARMOUR_PLATING),
    ShotKind.CHAIN: (V.RIGGING, V.MAST, V.SAILS, V.OARS, V.ENVELOPE, V.WINGS, V.ROTOR),
    ShotKind.GRAPE: (V.DECK, V.CREW_QUARTERS, V.BRIDGE, V.COCKPIT, V.TROOP_BAY),
    ShotKind.FIRE: (V.SAILS, V.RIGGING, V.DECK, V.FUEL_STORE, V.MAGAZINE, V.ENVELOPE),
    ShotKind.SOLID: (V.HULL, V.KEEL, V.BOW, V.STERN, V.GUN_DECK),
    ShotKind.SPREAD: (V.DECK, V.CREW_QUARTERS, V.BRIDGE, V.TROOP_BAY, V.RIGGING),
    ShotKind.INCENDIARY: (V.DECK, V.FUEL_STORE, V.MAGAZINE, V.SAILS, V.ENVELOPE),
    ShotKind.EXPLOSIVE: (V.HULL, V.GUN_DECK, V.HOLD, V.ENGINE, V.BOILER, V.MAGAZINE),
    ShotKind.PIERCING: (V.ARMOUR_PLATING, V.ENGINE, V.BOILER, V.DRIVE, V.HULL),
    ShotKind.GUIDED: (V.BRIDGE, V.ENGINE, V.MAGAZINE, V.COCKPIT, V.DRIVE),
    ShotKind.ENERGY: (V.ARMOUR_PLATING, V.ENGINE, V.DRIVE, V.BRIDGE, V.HULL),
    ShotKind.SMOKE: (V.BRIDGE, V.GUN_DECK, V.COCKPIT),
}
SHOT_WEIGHT: dict[ShotKind, int] = {
    ShotKind.ROUND: 100,
    ShotKind.CHAIN: 100,
    ShotKind.GRAPE: 100,
    ShotKind.FIRE: 100,
    ShotKind.SOLID: 110,
    ShotKind.SPREAD: 110,
    ShotKind.INCENDIARY: 120,
    ShotKind.EXPLOSIVE: 150,
    ShotKind.PIERCING: 140,
    ShotKind.GUIDED: 200,
    ShotKind.ENERGY: 220,
    ShotKind.SMOKE: 60,
}

RAKED_SECTIONS: tuple[VehicleSection, ...] = (V.BOW, V.STERN, V.RUDDER, V.STEERING, V.GUN_DECK)


@dataclass(frozen=True)
class StationSpec:
    label: str
    share: int
    sections: frozenset[VehicleSection]
    fights: bool
    effect: Callable[[Rules], int]
    storm_care: bool = False


C = CrewStation
CREW_STATIONS: Mapping[CrewStation, StationSpec] = total(
    CrewStation,
    {
        C.GUNNERS: StationSpec("Gunners", 40, frozenset(), True, lambda rules: rules.crews.gunners_effect),
        C.RIGGERS: StationSpec("Riggers", 25, frozenset({V.MAST, V.RIGGING, V.SAILS}), False, lambda rules: rules.crews.riggers_effect, storm_care=True),
        C.MARINES: StationSpec("Marines", 20, frozenset(), True, lambda rules: rules.crews.marines_effect),
        C.OFFICERS: StationSpec("Officers", 5, frozenset(), True, lambda rules: rules.crews.officers_effect),
        C.ROWERS: StationSpec("Rowers", 10, frozenset({V.OARS}), True, lambda rules: rules.crews.rowers_effect),
        C.PILOTS: StationSpec("Pilots", 6, frozenset({V.COCKPIT, V.WINGS, V.ROTOR, V.ENVELOPE}), True, lambda rules: rules.crews.pilots_effect),
        C.ENGINEERS: StationSpec("Engineers", 10, frozenset({V.ENGINE, V.BOILER, V.POWER_CORE, V.DRIVE}), True, lambda rules: rules.crews.engineers_effect),
        C.SENSOR_OPERATORS: StationSpec("Sensor operators", 4, frozenset({V.SENSORS}), True, lambda rules: rules.crews.sensor_operators_effect),
        C.MEDICS: StationSpec("Medics", 4, frozenset({V.CREW_QUARTERS, V.LIFE_SUPPORT}), False, lambda rules: rules.crews.medics_effect),
        C.HANDLERS: StationSpec(
            "Handlers", 6, frozenset({V.MOUNT_BODY, V.DRAFT_TEAM, V.HARNESS, V.SADDLE}), False, lambda rules: rules.crews.handlers_effect, storm_care=True
        ),
        C.LINK_OPERATORS: StationSpec("Link operators", 3, frozenset({V.CORE}), True, lambda rules: rules.crews.link_operators_effect),
        C.CASTERS: StationSpec("Casters", 4, frozenset({V.WARD}), True, lambda rules: rules.crews.casters_effect),
        C.NAVIGATORS: StationSpec("Navigators", 4, frozenset({V.NAVIGATION, V.BRIDGE}), False, lambda rules: rules.crews.navigators_effect),
    },
)
STATION_SHARES: Mapping[CrewStation, int] = MappingProxyType({station: spec.share for station, spec in CREW_STATIONS.items()})
CLASSIC_STATIONS = frozenset(station for station, spec in CREW_STATIONS.items() if not spec.sections) | {CrewStation.RIGGERS, CrewStation.ROWERS}
STORM_CARE = frozenset(station for station, spec in CREW_STATIONS.items() if spec.storm_care)
FIGHTING_STATIONS = frozenset(station for station, spec in CREW_STATIONS.items() if spec.fights)


@dataclass(frozen=True)
class GroundSpec:
    label: str
    air: bool = False
    breathed_by: MovementMode | None = None
    harm: HarmCause = HarmCause.QUEST
    close: bool = False
    placed: bool = False


GROUNDS: Mapping[ExpeditionGround, GroundSpec] = total(
    ExpeditionGround,
    {
        ExpeditionGround.SITE: GroundSpec("a site", close=True),
        ExpeditionGround.WILDS: GroundSpec("the wilds"),
        ExpeditionGround.UNDERWORLD: GroundSpec("an underworld stratum", close=True),
        ExpeditionGround.REALM: GroundSpec("a mythic realm"),
        ExpeditionGround.UNDER_WATER: GroundSpec("the waters below", air=True, breathed_by=MovementMode.SUBMERGED, harm=HarmCause.EXPOSURE, placed=True),
        ExpeditionGround.SPACE: GroundSpec("the void between worlds", air=True, harm=HarmCause.DECOMPRESSION, placed=True),
        ExpeditionGround.DIMENSION: GroundSpec("another dimension", placed=True),
    },
)
GROUND_LABELS: Mapping[ExpeditionGround, str] = MappingProxyType({ground: spec.label for ground, spec in GROUNDS.items()})
AIRLESS = frozenset(ground for ground, spec in GROUNDS.items() if spec.air)
CLOSE_GROUNDS = frozenset(ground for ground, spec in GROUNDS.items() if spec.close)
PLACED_GROUNDS = frozenset(ground for ground, spec in GROUNDS.items() if spec.placed)


@dataclass(frozen=True)
class RoleSpec:
    capacity: str
    skill: SkillKind | None


ROLES: Mapping[ExpeditionRole, RoleSpec] = total(
    ExpeditionRole,
    {
        ExpeditionRole.SCOUT: RoleSpec("scouting", SkillKind.TRACKING),
        ExpeditionRole.GUIDE: RoleSpec("finding the way", SkillKind.NAVIGATION),
        ExpeditionRole.HEALER: RoleSpec("healing", SkillKind.MEDICINE),
        ExpeditionRole.FIGHTER: RoleSpec("fighting", SkillKind.TACTICS),
        ExpeditionRole.SCHOLAR: RoleSpec("reading inscriptions", SkillKind.LORE),
        ExpeditionRole.PORTER: RoleSpec("carrying", None),
        ExpeditionRole.WARDER: RoleSpec("warding against spirits, curses and workings", SkillKind.RITUAL),
        ExpeditionRole.INTERPRETER: RoleSpec("speaking with those the party meets", SkillKind.LANGUAGES),
        ExpeditionRole.CARTOGRAPHER: RoleSpec("mapping what is crossed", SkillKind.ASTRONOMY),
        ExpeditionRole.ENGINEER: RoleSpec("shoring collapses and opening seals", SkillKind.ENGINEERING),
    },
)
ROLE_CAPACITY: Mapping[ExpeditionRole, str] = MappingProxyType({role: spec.capacity for role, spec in ROLES.items()})
ROLE_SKILLS: tuple[tuple[ExpeditionRole, SkillKind], ...] = tuple((role, spec.skill) for role, spec in ROLES.items() if spec.skill is not None)

AFFLICTIONS = frozenset({ResolveKind.PARANOID, ResolveKind.HOPELESS, ResolveKind.SELFISH, ResolveKind.ABUSIVE, ResolveKind.FEARFUL, ResolveKind.IRRATIONAL})
VIRTUES = frozenset({ResolveKind.COURAGEOUS, ResolveKind.FOCUSED, ResolveKind.STALWART, ResolveKind.COMPASSIONATE, ResolveKind.INSPIRED})

RESOLVE_EFFECTS: Mapping[ResolveKind, str] = total(
    ResolveKind,
    {
        ResolveKind.STEADY: "holds steady",
        ResolveKind.PARANOID: "will not rest at camp",
        ResolveKind.HOPELESS: "lingers, eating a companion's share, and gains more stress",
        ResolveKind.SELFISH: "eats a companion's provisions",
        ResolveKind.ABUSIVE: "raises the stress of every companion",
        ResolveKind.COURAGEOUS: "lifts the stress of every companion",
        ResolveKind.FOCUSED: "lowers the danger of every leg",
        ResolveKind.STALWART: "sheds stress and shrugs off exposure",
        ResolveKind.FEARFUL: "flees from blows and will not enter rooms",
        ResolveKind.IRRATIONAL: "acts at random and stirs up danger",
        ResolveKind.COMPASSIONATE: "tends every companion, easing stress and exposure",
        ResolveKind.INSPIRED: "lifts the resolve of every companion",
    },
)
RESOLVE_LEANINGS: Mapping[TraitKind, ResolveKind] = MappingProxyType(
    {
        TraitKind.CRAVEN: ResolveKind.FEARFUL,
        TraitKind.ANXIOUS: ResolveKind.FEARFUL,
        TraitKind.IMPULSIVE: ResolveKind.IRRATIONAL,
        TraitKind.SCATTERBRAINED: ResolveKind.IRRATIONAL,
        TraitKind.PARANOID: ResolveKind.PARANOID,
        TraitKind.CRUEL: ResolveKind.ABUSIVE,
        TraitKind.GREEDY: ResolveKind.SELFISH,
        TraitKind.PESSIMISTIC: ResolveKind.HOPELESS,
        TraitKind.BRAVE: ResolveKind.COURAGEOUS,
        TraitKind.DISCIPLINED: ResolveKind.FOCUSED,
        TraitKind.RESILIENT: ResolveKind.STALWART,
        TraitKind.COMPASSIONATE: ResolveKind.COMPASSIONATE,
        TraitKind.KIND: ResolveKind.COMPASSIONATE,
        TraitKind.IDEALISTIC: ResolveKind.INSPIRED,
        TraitKind.OPTIMISTIC: ResolveKind.INSPIRED,
    }
)
QUARRELSOME = frozenset({TraitKind.WRATHFUL, TraitKind.STUBBORN, TraitKind.COMPETITIVE, TraitKind.RUDE, TraitKind.PROUD, TraitKind.BLUNT})


@dataclass(frozen=True)
class QuirkSpec:
    kind: QuirkKind
    label: str
    positive: bool
    effect: str


QUIRKS: Mapping[QuirkKind, QuirkSpec] = total(
    QuirkKind,
    {
        spec.kind: spec
        for spec in (
            QuirkSpec(Q.FEARS_DARK, "Fears the dark", False, "gains twice the stress on a leg in the dark"),
            QuirkSpec(Q.DARK_SIGHTED, "Sees in the dark", True, "darkness adds no danger to a party it walks with"),
            QuirkSpec(Q.KNOWS_WAYS, "Knows the ways", True, "a party it leads needs one leg fewer"),
            QuirkSpec(Q.EATS_ANYTHING, "Eats anything", True, "eats no provisions on a leg"),
            QuirkSpec(Q.HARDY, "Hardy", True, "takes half the exposure"),
            QuirkSpec(Q.FRAIL, "Frail", False, "takes half again the exposure"),
            QuirkSpec(Q.JUMPY, "Jumpy", False, "gains twice the stress from an ambush"),
            QuirkSpec(Q.STEADY_NERVES, "Steady nerves", True, "gains half the stress on a leg"),
            QuirkSpec(Q.KEEN_EYED, "Keen-eyed", True, "scouts for the party whatever its role"),
            QuirkSpec(Q.HOMESICK, "Homesick", False, "sets out on expeditions half as often and gains stress on the way"),
            QuirkSpec(Q.RESTLESS, "Restless", True, "sets out on expeditions twice as often"),
            QuirkSpec(Q.LIGHT_FINGERED, "Light-fingered", False, "brings home an extra find and unsettles its companions"),
            QuirkSpec(Q.CLAUSTROPHOBIC, "Fears close places", False, "gains twice the stress on a leg through a site or an underworld"),
            QuirkSpec(Q.COLD_HARDY, "Cold-hardy", True, "takes no cold"),
            QuirkSpec(Q.SWIMMER, "Swimmer", True, "needs no air under the water and takes half the wet"),
            QuirkSpec(Q.LUCKY, "Lucky", True, "often escapes a blow that would fall on it"),
        )
    },
)

QUIRK_ORIGINS: Mapping[ExpeditionEvent, tuple[QuirkKind, ...]] = MappingProxyType(
    {
        ExpeditionEvent.LEG: (Q.KNOWS_WAYS, Q.KEEN_EYED, Q.SWIMMER),
        ExpeditionEvent.ROOM: (Q.FEARS_DARK, Q.DARK_SIGHTED, Q.CLAUSTROPHOBIC),
        ExpeditionEvent.EXPOSURE: (Q.FRAIL, Q.HARDY, Q.COLD_HARDY),
        ExpeditionEvent.AMBUSH: (Q.JUMPY, Q.STEADY_NERVES),
        ExpeditionEvent.CAMP: (Q.EATS_ANYTHING, Q.STEADY_NERVES),
        ExpeditionEvent.RETURN: (Q.HOMESICK, Q.RESTLESS),
        ExpeditionEvent.SETOUT: (Q.RESTLESS, Q.LIGHT_FINGERED),
        ExpeditionEvent.DISCOVERY: (Q.LUCKY, Q.KEEN_EYED),
        ExpeditionEvent.QUARREL: (Q.JUMPY, Q.STEADY_NERVES),
    }
)
