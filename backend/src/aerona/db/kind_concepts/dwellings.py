from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.dwelling_kinds import DwellingKindRow
from aerona.domain.enums.kinds import KindConcept
from aerona.domain.enums.urban import HousingLevel

LEVEL_LABELS = {
    HousingLevel.HUT.value: "Hut",
    HousingLevel.COTTAGE.value: "Cottage",
    HousingLevel.HOUSE.value: "House",
    HousingLevel.TOWNHOUSE.value: "Townhouse",
    HousingLevel.MANOR.value: "Manor",
    HousingLevel.APARTMENT.value: "Apartment",
    HousingLevel.TENEMENT.value: "Tenement",
    HousingLevel.TOWER_BLOCK.value: "Tower block",
    HousingLevel.ARCOLOGY_UNIT.value: "Arcology unit",
    HousingLevel.HABITAT_MODULE.value: "Habitat module",
    HousingLevel.SHIP_BERTH.value: "Ship berth",
}

SPEC = ConceptSpec(
    concept=KindConcept.DWELLING,
    label="Dwelling",
    plural="Dwellings",
    hint="Kinds of home a people builds, each standing on a step of the housing ladder",
    table=DwellingKindRow,
    category=HousingLevel,
    category_labels=LEVEL_LABELS,
    properties=(
        KindProperty("rooms", "Rooms", "Rooms a household of this kind has to live in", 1, 60),
        KindProperty("quality", "Quality", "How well it shelters and how fine it seems to those who see it"),
        KindProperty("upkeep", "Upkeep", "Coin a household spends each epoch to keep it standing", 0, 50),
        KindProperty("mobile", "Moves with its folk", "1 when the household carries it along as it travels", 0, 1),
    ),
    readers=("households", "household_life", "household_formation"),
)
