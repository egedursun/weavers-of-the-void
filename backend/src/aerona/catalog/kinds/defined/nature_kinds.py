from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.nature_kinds import ProductPart

PRODUCT_PART = total(
    ProductPart,
    {
        ProductPart.FLESH: Defined("Flesh", checked_by=(), used_by=("db.kind_concepts.nature.YIELD_PARTS",)),
        ProductPart.HIDE: Defined("Hide", checked_by=(), used_by=("db.kind_concepts.nature.YIELD_PARTS",)),
        ProductPart.BONE: Defined("Bone", checked_by=(), used_by=("db.kind_concepts.nature.YIELD_PARTS",)),
        ProductPart.TUSK: Defined("Tusk or horn", checked_by=(), used_by=("db.kind_concepts.nature.YIELD_PARTS",)),
        ProductPart.SHELL: Defined("Shell", checked_by=(), used_by=("db.kind_concepts.nature.YIELD_PARTS",)),
        ProductPart.VENOM: Defined("Venom", checked_by=(), used_by=("db.kind_concepts.nature.YIELD_PARTS",)),
        ProductPart.FIBRE: Defined(
            "Fibre",
            checked_by=("engine.ecology.domestication.PART_PROCESS",),
            used_by=("db.kind_concepts.nature.PLANT_PARTS", "db.kind_concepts.nature.YIELD_PARTS"),
        ),
        ProductPart.MILK: Defined("Milk", checked_by=("engine.ecology.domestication.PART_PROCESS",), used_by=("db.kind_concepts.nature.YIELD_PARTS",)),
        ProductPart.EGGS: Defined("Eggs", checked_by=("engine.ecology.domestication.PART_PROCESS",), used_by=("db.kind_concepts.nature.YIELD_PARTS",)),
        ProductPart.FEATHERS: Defined("Feathers", checked_by=(), used_by=("db.kind_concepts.nature.YIELD_PARTS",)),
        ProductPart.REAGENT: Defined("Reagent", checked_by=(), used_by=("db.kind_concepts.nature.PLANT_PARTS", "db.kind_concepts.nature.YIELD_PARTS")),
        ProductPart.SEED: Defined("Seed or grain", checked_by=(), used_by=("db.kind_concepts.nature.PLANT_PARTS",)),
        ProductPart.ROOT: Defined("Root", checked_by=(), used_by=("db.kind_concepts.nature.PLANT_PARTS",)),
        ProductPart.FRUIT: Defined("Fruit", checked_by=(), used_by=("db.kind_concepts.nature.PLANT_PARTS",)),
        ProductPart.LEAF: Defined("Leaf", checked_by=(), used_by=("db.kind_concepts.nature.PLANT_PARTS",)),
        ProductPart.WOOD: Defined("Wood", checked_by=(), used_by=("db.kind_concepts.nature.PLANT_PARTS",)),
        ProductPart.SAP: Defined("Sap", checked_by=(), used_by=()),
        ProductPart.DYE: Defined("Dye", checked_by=(), used_by=("db.kind_concepts.nature.PLANT_PARTS",)),
        ProductPart.TOXIN: Defined("Toxin", checked_by=(), used_by=("db.kind_concepts.nature.PLANT_PARTS",)),
    },
)
