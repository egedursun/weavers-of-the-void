from dataclasses import dataclass

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
    spec.kind: spec
    for spec in (
        TransportSpec(CarrierKind.WAGONS, "Wagons", 10),
        TransportSpec(CarrierKind.PACK_ANIMALS, "Pack animals", 4),
        TransportSpec(CarrierKind.PORTERS, "Porters", 1),
        TransportSpec(CarrierKind.BARGES, "River barges", 25, river_only=True),
        TransportSpec(CarrierKind.SHIPS, "Supply ships", 60, sea_only=True),
        TransportSpec(CarrierKind.SKY_BARGES, "Sky barges", 40),
    )
}

ECHELON_LABELS: dict[EchelonLevel, str] = {
    EchelonLevel.ARMY_GROUP: "Army group",
    EchelonLevel.ARMY: "Army",
    EchelonLevel.CORPS: "Corps",
    EchelonLevel.DIVISION: "Division",
    EchelonLevel.BRIGADE: "Brigade",
}

SHOT_TARGETS: dict[ShotKind, tuple[VehicleSection, ...]] = {
    ShotKind.ROUND: (V.HULL, V.KEEL, V.BOW, V.STERN, V.GUN_DECK, V.HOLD, V.ENGINE, V.BOILER, V.DRIVE, V.ARMOUR_PLATING),
    ShotKind.CHAIN: (V.RIGGING, V.MAST, V.SAILS, V.OARS, V.ENVELOPE, V.WINGS, V.ROTOR),
    ShotKind.GRAPE: (V.DECK, V.CREW_QUARTERS, V.BRIDGE, V.COCKPIT, V.TROOP_BAY),
    ShotKind.FIRE: (V.SAILS, V.RIGGING, V.DECK, V.FUEL_STORE, V.MAGAZINE, V.ENVELOPE),
}

RAKED_SECTIONS: tuple[VehicleSection, ...] = (V.BOW, V.STERN, V.RUDDER, V.STEERING, V.GUN_DECK)

STATION_SHARES: dict[CrewStation, int] = {
    CrewStation.GUNNERS: 40,
    CrewStation.TOPMEN: 25,
    CrewStation.MARINES: 20,
    CrewStation.OFFICERS: 5,
    CrewStation.ROWERS: 10,
}

GROUND_LABELS: dict[ExpeditionGround, str] = {
    ExpeditionGround.SITE: "a site",
    ExpeditionGround.WILDS: "the wilds",
    ExpeditionGround.UNDERWORLD: "an underworld stratum",
    ExpeditionGround.REALM: "a mythic realm",
}

ROLE_CAPACITY: dict[ExpeditionRole, str] = {
    ExpeditionRole.SCOUT: "scouting",
    ExpeditionRole.GUIDE: "finding the way",
    ExpeditionRole.HEALER: "healing",
    ExpeditionRole.FIGHTER: "fighting",
    ExpeditionRole.SCHOLAR: "reading inscriptions",
    ExpeditionRole.PORTER: "carrying",
}

AFFLICTIONS = frozenset({ResolveKind.PARANOID, ResolveKind.HOPELESS, ResolveKind.SELFISH, ResolveKind.ABUSIVE})
VIRTUES = frozenset({ResolveKind.COURAGEOUS, ResolveKind.FOCUSED, ResolveKind.STALWART})

RESOLVE_EFFECTS: dict[ResolveKind, str] = {
    ResolveKind.STEADY: "holds steady",
    ResolveKind.PARANOID: "will not rest at camp",
    ResolveKind.HOPELESS: "lingers, eating a companion's share, and gains more stress",
    ResolveKind.SELFISH: "eats a companion's provisions",
    ResolveKind.ABUSIVE: "raises the stress of every companion",
    ResolveKind.COURAGEOUS: "lifts the stress of every companion",
    ResolveKind.FOCUSED: "lowers the danger of every leg",
    ResolveKind.STALWART: "sheds stress and shrugs off exposure",
}


@dataclass(frozen=True)
class QuirkSpec:
    kind: QuirkKind
    label: str
    positive: bool
    effect: str


QUIRKS: dict[QuirkKind, QuirkSpec] = {
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
    )
}

QUIRK_ORIGINS: dict[ExpeditionEvent, tuple[QuirkKind, QuirkKind]] = {
    ExpeditionEvent.LEG: (Q.KNOWS_WAYS, Q.KEEN_EYED),
    ExpeditionEvent.ROOM: (Q.FEARS_DARK, Q.DARK_SIGHTED),
    ExpeditionEvent.EXPOSURE: (Q.FRAIL, Q.HARDY),
    ExpeditionEvent.AMBUSH: (Q.JUMPY, Q.STEADY_NERVES),
    ExpeditionEvent.CAMP: (Q.EATS_ANYTHING, Q.STEADY_NERVES),
    ExpeditionEvent.RETURN: (Q.HOMESICK, Q.RESTLESS),
    ExpeditionEvent.SETOUT: (Q.RESTLESS, Q.LIGHT_FINGERED),
}
