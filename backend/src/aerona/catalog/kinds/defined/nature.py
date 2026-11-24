from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.nature import PlantDefence, SymbiosisKind

PLANT_DEFENCE = total(
    PlantDefence,
    {
        PlantDefence.NONE: Defined("Undefended", checked_by=("engine.nature.cover.defence_cover",), used_by=("db.tables.flora.PlantProfileRow",)),
        PlantDefence.THORNS: Defined("Thorns", checked_by=(), used_by=("engine.cycles.nomads.pasture", "engine.environment.book.EnvironmentBook.load")),
        PlantDefence.TOXINS: Defined("Toxins", checked_by=(), used_by=("engine.nature.plants.keep_plant_defences", "engine.phases.environment.region_harvest")),
        PlantDefence.ALLELOPATHY: Defined("Poisons its neighbours", checked_by=(), used_by=("engine.phases.environment.region_harvest",)),
        PlantDefence.CARNIVOROUS: Defined("Eats flesh", checked_by=(), used_by=("engine.nature.plants.keep_plant_defences",)),
        PlantDefence.STINGING: Defined("Stinging hairs", checked_by=(), used_by=("engine.nature.plants.keep_plant_defences",)),
        PlantDefence.GUARDIANS: Defined(
            "Guarded by allies", checked_by=("engine.nature.plants.guard_plants",), used_by=("engine.nature.plants.keep_plant_defences",)
        ),
        PlantDefence.MIMICRY: Defined("Looks like a guarded plant", checked_by=(), used_by=("engine.nature.plants.keep_plant_defences",)),
        PlantDefence.REGROWTH: Defined("Grows back fast", checked_by=(), used_by=("engine.nature.plants.keep_plant_defences",)),
    },
)

SYMBIOSIS_KIND = total(
    SymbiosisKind,
    {
        SymbiosisKind.MUTUALISM: Defined(
            "Mutualism",
            checked_by=("engine.nature.plants.guard_plants", "engine.nature.symbiosis.SymbiosisBook.room"),
            used_by=("engine.nature.symbiosis.kind_between", "services.player.nature.SpeciesRelationDraft"),
        ),
        SymbiosisKind.COMMENSALISM: Defined(
            "Commensalism", checked_by=("engine.nature.symbiosis.SymbiosisBook.room",), used_by=("engine.nature.symbiosis.kind_between",)
        ),
        SymbiosisKind.PARASITISM: Defined(
            "Parasitism",
            checked_by=("engine.nature.symbiosis.plague_herds",),
            used_by=("catalog.life.nature.DRAINING_BONDS", "engine.nature.symbiosis.kind_between"),
        ),
        SymbiosisKind.MIMICRY: Defined(
            "Mimicry",
            checked_by=("engine.nature.symbiosis.SymbiosisBook.shield", "engine.nature.symbiosis.mimics_of"),
            used_by=("engine.nature.symbiosis.kind_between",),
        ),
        SymbiosisKind.AMENSALISM: Defined(
            "Harms without gain", checked_by=(), used_by=("catalog.life.nature.DRAINING_BONDS", "engine.nature.symbiosis.kind_between")
        ),
        SymbiosisKind.FARMING: Defined(
            "Tends and harvests", checked_by=("engine.nature.symbiosis.SymbiosisBook.room",), used_by=("engine.nature.symbiosis.kind_between",)
        ),
    },
)
