from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease import SpreadPath
from aerona.rules.registry import Rules

P = SpreadPath
T = Transmission


@dataclass(frozen=True)
class PathSpec:
    label: str
    contact: bool
    carrier: str
    routes: frozenset[Transmission]
    chance: Callable[[Rules], int] | None = None


ANY_ROUTE = frozenset(Transmission)
SPREAD_PATHS: Mapping[SpreadPath, PathSpec] = total(
    SpreadPath,
    {
        P.ORIGIN: PathSpec("Rose there", contact=False, carrier="the land itself", routes=ANY_ROUTE),
        P.ROUTE: PathSpec("Along a trade road", contact=True, carrier="traders on a trade road", routes=ANY_ROUTE),
        P.ARMY: PathSpec("With an army", contact=True, carrier="soldiers on the march", routes=ANY_ROUTE),
        P.JOURNEY: PathSpec("With travellers", contact=True, carrier="travellers and voyagers", routes=ANY_ROUTE),
        P.SIEGE: PathSpec("In a siege", contact=True, carrier="a besieged town", routes=ANY_ROUTE),
        P.LOOSED: PathSpec("Loosed on purpose", contact=False, carrier="whoever loosed it", routes=ANY_ROUTE),
        P.MUTATION: PathSpec("A new strain", contact=False, carrier="its parent sickness", routes=ANY_ROUTE),
        P.WILDLIFE: PathSpec(
            "With wild creatures",
            contact=False,
            carrier="a host species",
            routes=frozenset({T.BITE, T.BLOOD, T.CONTACT}),
            chance=lambda rules: rules.spread.wildlife_pct,
        ),
        P.MIGRATION: PathSpec(
            "With migrants", contact=True, carrier="refugees and migrants", routes=ANY_ROUTE, chance=lambda rules: rules.spread.migration_pct
        ),
        P.GATHERING: PathSpec(
            "Home from a gathering",
            contact=True,
            carrier="a crowd at a gathering",
            routes=frozenset({T.INHALATION, T.CONTACT, T.INGESTION, T.INTIMATE, T.OBJECTS, T.WATER}),
            chance=lambda rules: rules.spread.gathering_pct,
        ),
        P.WATERWAY: PathSpec(
            "Downstream", contact=False, carrier="a river or canal", routes=frozenset({T.WATER}), chance=lambda rules: rules.spread.waterway_pct
        ),
    },
)
CONTACT_PATHS = frozenset(path for path, spec in SPREAD_PATHS.items() if spec.contact)
