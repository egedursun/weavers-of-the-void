from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.disease import ClimateAffinity, SpreadPath

CLIMATE_AFFINITY = total(
    ClimateAffinity,
    {
        ClimateAffinity.WARM: Defined("Warm", checked_by=("engine.disease.outbreaks.climate_fit",), used_by=("engine.disease.emergence.affinity_of",)),
        ClimateAffinity.WET: Defined("Wet", checked_by=("engine.disease.outbreaks.climate_fit",), used_by=("engine.disease.emergence.affinity_of",)),
        ClimateAffinity.COLD: Defined("Cold", checked_by=("engine.disease.outbreaks.climate_fit",), used_by=("engine.disease.emergence.affinity_of",)),
        ClimateAffinity.DRY: Defined("Dry", checked_by=("engine.disease.outbreaks.climate_fit",), used_by=("engine.disease.emergence.affinity_of",)),
        ClimateAffinity.ANY: Defined(
            "Any", checked_by=("engine.disease.outbreaks.climate_fit",), used_by=("engine.disease.emergence.affinity_of", "tools.son.disease.LooseDiseaseInput")
        ),
    },
)

SPREAD_PATH = total(
    SpreadPath,
    {
        SpreadPath.ORIGIN: Defined(
            "Origin",
            checked_by=(),
            used_by=(
                "engine.disease.history.backfill_plagues",
                "engine.disease.outbreaks.disease_for",
                "engine.disease.outbreaks.spread_factor",
                "engine.disease.spillover.spill",
                "engine.ecology.fossils.reveal",
                "engine.phases.disasters._plague_spread",
                "engine.phases.disasters.strike_plague",
            ),
        ),
        SpreadPath.ROUTE: Defined(
            "Route",
            checked_by=("engine.disease.outbreaks.spread_factor",),
            used_by=("engine.disease.vectors.CONTACT_PATHS", "engine.economy.convoys.arrive", "engine.phases.disasters._plague_spread"),
        ),
        SpreadPath.ARMY: Defined("Army", checked_by=(), used_by=("engine.disease.course.carry_by_armies", "engine.disease.vectors.CONTACT_PATHS")),
        SpreadPath.JOURNEY: Defined(
            "Journey",
            checked_by=("engine.disease.outbreaks.spread_factor",),
            used_by=(
                "engine.cosmos.voyages.unload",
                "engine.disease.carriers.walk_carriers",
                "engine.disease.course.carry_by_journeys",
                "engine.disease.vectors.CONTACT_PATHS",
                "engine.faith.works.pilgrim_plague",
                "engine.orders.tourism.spread_sickness",
            ),
        ),
        SpreadPath.SIEGE: Defined("Siege", checked_by=(), used_by=("engine.disease.vectors.CONTACT_PATHS", "engine.settlement.life.endure_siege")),
        SpreadPath.LOOSED: Defined(
            "Loosed",
            checked_by=("engine.disease.emergence.ORIGIN_KEYS", "engine.disease.emergence.mark_origin"),
            used_by=(
                "engine.disease.control.create_disease",
                "engine.disease.control.loose",
                "engine.living.disease.loose_designed",
                "engine.phases.espionage.sabotage",
            ),
        ),
        SpreadPath.MUTATION: Defined("Mutation", checked_by=(), used_by=("engine.disease.course.mutate", "engine.disease.emergence.new_strain")),
    },
)
