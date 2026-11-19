from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.folk_knowledge import FolkTaking, LoreTransmission, NumberReading

FOLK_TAKING = total(
    FolkTaking,
    {
        FolkTaking.FOOD: Defined(
            "Food",
            checked_by=(),
            used_by=("engine.folk_knowledge.truth.BENIGN", "engine.folk_knowledge.truth.mistaken", "engine.folk_knowledge.truth.plant_truth"),
        ),
        FolkTaking.MEDICINE: Defined("Medicine", checked_by=(), used_by=("engine.folk_knowledge.truth.BENIGN", "engine.folk_knowledge.truth.plant_truth")),
        FolkTaking.POISON: Defined(
            "Poison",
            checked_by=(),
            used_by=("engine.folk_knowledge.truth.HARMFUL", "engine.folk_knowledge.truth.plant_truth", "engine.folk_knowledge.truth.truth_of"),
        ),
        FolkTaking.DANGER: Defined(
            "Danger",
            checked_by=("engine.folk_knowledge.truth.blames",),
            used_by=("engine.folk_knowledge.truth.HARMFUL", "engine.folk_knowledge.truth.mistaken", "engine.folk_knowledge.truth.truth_of"),
        ),
        FolkTaking.HARMLESS: Defined(
            "Harmless",
            checked_by=(),
            used_by=(
                "db.tables.folk_knowledge.FolkClassRow",
                "engine.folk_knowledge.truth.BENIGN",
                "engine.folk_knowledge.truth.mistaken",
                "engine.folk_knowledge.truth.truth_of",
            ),
        ),
        FolkTaking.CURSE: Defined(
            "Curse",
            checked_by=("engine.folk_knowledge.truth.blames", "engine.folk_knowledge.truth.misjudged"),
            used_by=("engine.folk_knowledge.truth.HARMFUL", "engine.folk_knowledge.truth.mistaken"),
        ),
        FolkTaking.OMEN: Defined("Omen", checked_by=(), used_by=("engine.folk_knowledge.truth.MEANINGS", "engine.folk_knowledge.truth.mistaken")),
        FolkTaking.SACRED: Defined("Sacred", checked_by=(), used_by=("engine.folk_knowledge.truth.MEANINGS",)),
    },
)

LORE_TRANSMISSION = total(
    LoreTransmission,
    {
        LoreTransmission.ORAL: Defined(
            "Oral",
            checked_by=(),
            used_by=("db.tables.folk_knowledge.FolkKnowledgeRow", "engine.folk_knowledge.lore.UNWRITTEN", "engine.folk_knowledge.seed.transmission_of"),
        ),
        LoreTransmission.WRITTEN: Defined("Written", checked_by=(), used_by=("engine.folk_knowledge.seed.transmission_of",)),
        LoreTransmission.APPRENTICESHIP: Defined(
            "Apprenticeship", checked_by=(), used_by=("engine.folk_knowledge.lore.UNWRITTEN", "engine.folk_knowledge.seed.transmission_of")
        ),
        LoreTransmission.RITE: Defined("Rite", checked_by=(), used_by=("engine.folk_knowledge.lore.UNWRITTEN", "engine.folk_knowledge.seed.transmission_of")),
    },
)

NUMBER_READING = total(
    NumberReading,
    {
        NumberReading.LUCKY: Defined("Lucky", checked_by=(), used_by=("engine.folk_knowledge.lore.CALMING",)),
        NumberReading.UNLUCKY: Defined("Unlucky", checked_by=(), used_by=("engine.folk_knowledge.lore.TROUBLING",)),
        NumberReading.SACRED: Defined("Sacred", checked_by=("engine.folk_knowledge.lore.read_the_epoch",), used_by=()),
        NumberReading.FORBIDDEN: Defined("Forbidden", checked_by=(), used_by=("engine.folk_knowledge.lore.TROUBLING",)),
    },
)
