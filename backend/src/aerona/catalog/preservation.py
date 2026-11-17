from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.urban import PreservationMethod
from aerona.rules.registry import Rules

P = PreservationMethod


@dataclass(frozen=True)
class PreservationSpec:
    label: str
    hint: str
    technique: Technique | None
    keeping: Callable[[Rules], int]


PRESERVATION: Mapping[PreservationMethod, PreservationSpec] = total(
    PreservationMethod,
    {
        P.NONE: PreservationSpec("Not kept", "Goods carried as they are", None, lambda rules: 0),
        P.DRYING: PreservationSpec(
            "Drying",
            "Water drawn out by air, sun or heat",
            None,
            lambda rules: rules.preservation.drying_pct,
        ),
        P.SMOKING: PreservationSpec(
            "Smoking",
            "Kept over smoke",
            None,
            lambda rules: rules.preservation.smoking_pct,
        ),
        P.CURING: PreservationSpec(
            "Curing",
            "Packed with a mineral that draws out water",
            None,
            lambda rules: rules.preservation.curing_pct,
        ),
        P.PICKLING: PreservationSpec(
            "Pickling",
            "Kept in an acid or a brine",
            None,
            lambda rules: rules.preservation.pickling_pct,
        ),
        P.FERMENTING: PreservationSpec(
            "Fermenting",
            "Turned by microbes into something that keeps",
            None,
            lambda rules: rules.preservation.fermenting_pct,
        ),
        P.CHILLING: PreservationSpec(
            "Chilling",
            "Kept cold",
            Technique.REFRIGERATION,
            lambda rules: rules.preservation.chilling_pct,
        ),
        P.FREEZING: PreservationSpec(
            "Freezing",
            "Kept frozen",
            Technique.REFRIGERATION,
            lambda rules: rules.preservation.freezing_pct,
        ),
        P.SEALING: PreservationSpec(
            "Sealing",
            "Shut in closed vessels",
            Technique.CANNED_FOOD,
            lambda rules: rules.preservation.sealing_pct,
        ),
        P.CANNING: PreservationSpec(
            "Canning",
            "Heated and sealed in metal",
            Technique.CANNED_FOOD,
            lambda rules: rules.preservation.canning_pct,
        ),
        P.IRRADIATING: PreservationSpec(
            "Irradiating",
            "Rays that kill what spoils food",
            Technique.NUCLEAR_POWER,
            lambda rules: rules.preservation.irradiating_pct,
        ),
        P.BY_WORKING: PreservationSpec(
            "By a working",
            "Kept by a rite or a power",
            Technique.WARDING,
            lambda rules: rules.preservation.by_working_pct,
        ),
        P.LIVING: PreservationSpec(
            "Kept alive",
            "Carried alive or in living vessels",
            Technique.GENETIC_ENGINEERING,
            lambda rules: rules.preservation.living_pct,
        ),
    },
)
WATER_DEFAULT = P.CURING
