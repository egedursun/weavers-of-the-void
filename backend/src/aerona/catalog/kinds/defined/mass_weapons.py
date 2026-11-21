from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.mass_weapons import RemnantKind

REMNANT_KIND = total(
    RemnantKind,
    {
        RemnantKind.BURIED_CHARGES: Defined(
            "Buried charges",
            checked_by=(),
            used_by=("db.tables.mass_weapons.WarRemnantRow", "engine.mass_weapons.book.REMNANT_OF", "engine.mass_weapons.remnants.LAND_ARMS"),
        ),
        RemnantKind.POISONED_GROUND: Defined("Poisoned ground", checked_by=(), used_by=("engine.mass_weapons.book.REMNANT_OF",)),
        RemnantKind.FALLOUT: Defined("Fallout", checked_by=(), used_by=("engine.mass_weapons.book.REMNANT_OF",)),
        RemnantKind.WRECK_FIELD: Defined("Field of wrecks", checked_by=(), used_by=("engine.mass_weapons.remnants.left_by",)),
        RemnantKind.UNQUIET_DEAD: Defined("Unquiet dead", checked_by=(), used_by=("engine.mass_weapons.remnants.LAND_ARMS",)),
        RemnantKind.CURSED_GROUND: Defined("Cursed ground", checked_by=(), used_by=("engine.mass_weapons.book.REMNANT_OF",)),
        RemnantKind.ABANDONED_MACHINES: Defined("Abandoned machines", checked_by=(), used_by=("engine.mass_weapons.book.REMNANT_OF",)),
    },
)
