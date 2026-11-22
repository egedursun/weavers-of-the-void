from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.nature import Dormancy, PlantDefence, SymbiosisKind, Thermoregulation

DORMANCY = total(
    Dormancy,
    {
        Dormancy.NONE: Defined(
            "Never sleeps a season",
            checked_by=("agents.context.nature_lines.son_nature_lines", "engine.nature.sleepers.keep_sleepers"),
            used_by=("db.tables.ecology.SpeciesProfileRow", "engine.ecology.profiles.profile_of"),
        ),
        Dormancy.HIBERNATION: Defined("Sleeps through the cold", checked_by=("engine.nature.seasons.asleep",), used_by=("engine.ecology.profiles.profile_of",)),
        Dormancy.AESTIVATION: Defined("Sleeps through the heat", checked_by=("engine.nature.seasons.asleep",), used_by=("engine.ecology.profiles.profile_of",)),
    },
)

PLANT_DEFENCE = total(
    PlantDefence,
    {
        PlantDefence.NONE: Defined("Undefended", checked_by=("engine.nature.cover.defence_cover",), used_by=("db.tables.flora.PlantProfileRow",)),
        PlantDefence.THORNS: Defined("Thorns", checked_by=(), used_by=("engine.cycles.nomads.pasture", "engine.environment.book.EnvironmentBook.load")),
        PlantDefence.TOXINS: Defined("Toxins", checked_by=(), used_by=("engine.nature.plants.keep_plant_defences", "engine.phases.environment.region_harvest")),
        PlantDefence.ALLELOPATHY: Defined("Poisons its neighbours", checked_by=(), used_by=("engine.phases.environment.region_harvest",)),
        PlantDefence.CARNIVOROUS: Defined("Eats flesh", checked_by=(), used_by=("engine.nature.plants.keep_plant_defences",)),
    },
)

SYMBIOSIS_KIND = total(
    SymbiosisKind,
    {
        SymbiosisKind.MUTUALISM: Defined(
            "Mutualism",
            checked_by=("engine.nature.symbiosis.SymbiosisBook.room",),
            used_by=("engine.nature.symbiosis.kind_between", "services.player.nature.SpeciesRelationDraft"),
        ),
        SymbiosisKind.COMMENSALISM: Defined(
            "Commensalism", checked_by=("engine.nature.symbiosis.SymbiosisBook.room",), used_by=("engine.nature.symbiosis.kind_between",)
        ),
        SymbiosisKind.PARASITISM: Defined(
            "Parasitism",
            checked_by=("engine.nature.symbiosis.SymbiosisBook.drain", "engine.nature.symbiosis.plague_herds"),
            used_by=("engine.nature.symbiosis.kind_between",),
        ),
        SymbiosisKind.MIMICRY: Defined(
            "Mimicry",
            checked_by=("engine.nature.symbiosis.SymbiosisBook.shield", "engine.nature.symbiosis.mimics_of"),
            used_by=("engine.nature.symbiosis.kind_between",),
        ),
    },
)

THERMOREGULATION = total(
    Thermoregulation,
    {
        Thermoregulation.ENDOTHERM: Defined(
            "Warm-blooded",
            checked_by=("engine.nature.effects.cold_war", "engine.nature.effects.cold_work", "engine.nature.seasons.activity", "engine.nature.seasons.chilled"),
            used_by=(
                "db.tables.demography.PeopleBiologyRow",
                "db.tables.ecology.SpeciesProfileRow",
                "engine.ecology.profiles.profile_of",
                "engine.nature.effects.folk_warmth",
            ),
        ),
        Thermoregulation.ECTOTHERM: Defined(
            "Cold-blooded",
            checked_by=("agents.context.nature_lines.mortal_nature_lines", "engine.genetics.pools.climate_lean", "engine.nature.senses.BORN"),
            used_by=("engine.ecology.profiles.profile_of",),
        ),
    },
)
