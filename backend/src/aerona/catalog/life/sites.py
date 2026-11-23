from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import partial, total
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.culture import ItemClass, Technique
from aerona.domain.enums.discovery import AnomalyKind
from aerona.domain.enums.site import BattlefieldFeature, ExcavationFind, ExcavationRisk, SiteChallenge, SiteRoomKind

RISKS = (ExcavationRisk.CURSE, ExcavationRisk.SPIRIT, ExcavationRisk.COLLAPSE)


@dataclass(frozen=True)
class RiskSpec:
    label: str
    ground: str | None
    rule: str | None


DIG_RISKS: Mapping[ExcavationRisk, RiskSpec] = total(
    ExcavationRisk,
    {
        ExcavationRisk.NONE: RiskSpec("No risk", None, None),
        ExcavationRisk.CURSE: RiskSpec("Curse", None, None),
        ExcavationRisk.SPIRIT: RiskSpec("Spirit", None, None),
        ExcavationRisk.COLLAPSE: RiskSpec("Collapse", None, None),
        ExcavationRisk.FLOODING: RiskSpec("Flooding", "porous", "flooding_pct"),
        ExcavationRisk.GAS: RiskSpec("Gas", "gassy", "gas_pct"),
        ExcavationRisk.DISEASE: RiskSpec("Sealed disease", "diseased", "disease_pct"),
    },
)


FINDS = (
    ExcavationFind.ARTIFACT,
    ExcavationFind.BOOK,
    ExcavationFind.TECHNIQUE,
    ExcavationFind.REGALIA,
    ExcavationFind.ROUTE_MAP,
    ExcavationFind.REMAINS,
    ExcavationFind.RECORDS,
)


CURSES = (PackageKind.HUNGER_CURSE, PackageKind.POSSESSION, PackageKind.VOID_TAINT)


FIND_CLASSES = partial(
    ExcavationFind,
    {
        ExcavationFind.ARTIFACT: ItemClass.IDOL,
        ExcavationFind.BOOK: ItemClass.BOOK,
        ExcavationFind.TECHNIQUE: ItemClass.TOOL,
        ExcavationFind.REGALIA: ItemClass.CROWN,
        ExcavationFind.ROUTE_MAP: ItemClass.MAP,
        ExcavationFind.RECORDS: ItemClass.SCROLL,
    },
    without={ExcavationFind.NOTHING, ExcavationFind.WAKING, ExcavationFind.REMAINS},
)
FIND_ANOMALIES = partial(
    ExcavationFind,
    {
        ExcavationFind.ARTIFACT: AnomalyKind.OUT_OF_PLACE_FIND,
        ExcavationFind.REMAINS: AnomalyKind.OUT_OF_PLACE_FIND,
        ExcavationFind.RECORDS: AnomalyKind.CONTRARY_RECORD,
        ExcavationFind.BOOK: AnomalyKind.CONTRARY_RECORD,
    },
    without={ExcavationFind.NOTHING, ExcavationFind.WAKING, ExcavationFind.TECHNIQUE, ExcavationFind.REGALIA, ExcavationFind.ROUTE_MAP},
)

FOUND_PLANS = frozenset({ExcavationFind.BOOK, ExcavationFind.RECORDS})


LOST_TECHNIQUES = (Technique.ARCH, Technique.CARTOGRAPHY, Technique.WARDING, Technique.ALCHEMY, Technique.ASTRONOMY_INSTRUMENTS, Technique.WRITTEN_LAW)


CHALLENGES = (SiteChallenge.TRAP, SiteChallenge.GUARDIAN, SiteChallenge.PUZZLE, SiteChallenge.HAZARD, SiteChallenge.MAZE)


@dataclass(frozen=True)
class ChallengeSpec:
    label: str
    harms: bool
    stops: bool


ROOM_CHALLENGES: Mapping[SiteChallenge, ChallengeSpec] = total(
    SiteChallenge,
    {
        SiteChallenge.NONE: ChallengeSpec("None", harms=False, stops=False),
        SiteChallenge.TRAP: ChallengeSpec("Trap", harms=True, stops=True),
        SiteChallenge.GUARDIAN: ChallengeSpec("Guardian", harms=True, stops=True),
        SiteChallenge.PUZZLE: ChallengeSpec("Puzzle", harms=True, stops=True),
        SiteChallenge.HAZARD: ChallengeSpec("Hazard", harms=True, stops=True),
        SiteChallenge.SEAL: ChallengeSpec("Seal", harms=False, stops=True),
        SiteChallenge.MAZE: ChallengeSpec("Maze", harms=False, stops=True),
    },
)


@dataclass(frozen=True)
class FeatureSpec:
    label: str
    decays: bool


FEATURES: Mapping[BattlefieldFeature, FeatureSpec] = total(
    BattlefieldFeature,
    {
        BattlefieldFeature.MASS_GRAVE: FeatureSpec("Mass grave", decays=True),
        BattlefieldFeature.SALVAGE_FIELD: FeatureSpec("Field of salvage", decays=True),
        BattlefieldFeature.EARTHWORKS: FeatureSpec("Old earthworks", decays=True),
        BattlefieldFeature.ORDNANCE: FeatureSpec("Remnants of arms", decays=False),
        BattlefieldFeature.MEMORIAL: FeatureSpec("Memorial", decays=False),
    },
)
EVERY_BATTLE_FEATURES = (BattlefieldFeature.MASS_GRAVE, BattlefieldFeature.SALVAGE_FIELD)

FURNISH_SITE_ROOM_KINDS = (SiteRoomKind.LAIR, SiteRoomKind.HEART)
FURNISH_SITE_ROOM_KINDS_2 = (SiteRoomKind.CRYPT, SiteRoomKind.SHRINE, SiteRoomKind.HEART)
