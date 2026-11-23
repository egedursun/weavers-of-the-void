from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.disease import ClimateMoisture, ClimateWarmth

CLIMATE_MOISTURE = total(
    ClimateMoisture,
    {
        ClimateMoisture.WET: Defined("Wet", checked_by=("engine.disease.outbreaks.moisture_fit",), used_by=("engine.disease.emergence.affinity_of",)),
        ClimateMoisture.DRY: Defined("Dry", checked_by=(), used_by=("engine.disease.emergence.affinity_of",)),
        ClimateMoisture.ANY: Defined(
            "Any",
            checked_by=("engine.disease.outbreaks.moisture_fit",),
            used_by=("db.tables.disease.DiseaseProfileRow", "engine.disease.emergence.affinity_of", "tools.son.disease.LooseDiseaseInput"),
        ),
    },
)

CLIMATE_WARMTH = total(
    ClimateWarmth,
    {
        ClimateWarmth.WARM: Defined("Warm", checked_by=("engine.disease.outbreaks.warmth_fit",), used_by=("engine.disease.emergence.affinity_of",)),
        ClimateWarmth.COLD: Defined("Cold", checked_by=(), used_by=("engine.disease.emergence.affinity_of",)),
        ClimateWarmth.ANY: Defined(
            "Any",
            checked_by=("engine.disease.outbreaks.warmth_fit",),
            used_by=("db.tables.disease.DiseaseProfileRow", "engine.disease.emergence.affinity_of", "tools.son.disease.LooseDiseaseInput"),
        ),
    },
)
