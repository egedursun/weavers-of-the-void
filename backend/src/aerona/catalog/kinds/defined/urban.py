from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.urban import HousingLevel

HOUSING_LEVEL = total(
    HousingLevel,
    {
        HousingLevel.HUT: Defined(
            "Huts",
            checked_by=("catalog.urban.HOUSING_RULE",),
            used_by=("catalog.genetics.DWELLINGS", "catalog.urban.HOUSING_ORDER", "db.kind_concepts.dwellings.LEVEL_LABELS"),
        ),
        HousingLevel.COTTAGE: Defined(
            "Cottages", checked_by=("catalog.urban.HOUSING_RULE",), used_by=("catalog.urban.HOUSING_ORDER", "db.kind_concepts.dwellings.LEVEL_LABELS")
        ),
        HousingLevel.HOUSE: Defined(
            "Houses",
            checked_by=(),
            used_by=(
                "catalog.genetics.DWELLINGS",
                "catalog.urban.HOUSING_ORDER",
                "db.kind_concepts.dwellings.LEVEL_LABELS",
                "db.tables.settlement.DistrictRow",
            ),
        ),
        HousingLevel.TOWNHOUSE: Defined(
            "Townhouses",
            checked_by=("catalog.urban.HOUSING_RULE",),
            used_by=("catalog.genetics.DWELLINGS", "catalog.urban.FINE_HOMES", "catalog.urban.HOUSING_ORDER", "db.kind_concepts.dwellings.LEVEL_LABELS"),
        ),
        HousingLevel.MANOR: Defined(
            "Manors",
            checked_by=("catalog.urban.HOUSING_RULE",),
            used_by=("catalog.genetics.DWELLINGS", "catalog.urban.FINE_HOMES", "catalog.urban.HOUSING_ORDER", "db.kind_concepts.dwellings.LEVEL_LABELS"),
        ),
        HousingLevel.APARTMENT: Defined(
            "Apartments",
            checked_by=("catalog.urban.HOUSING_GATES", "catalog.urban.HOUSING_RULE"),
            used_by=("catalog.genetics.DWELLINGS", "catalog.urban.HOUSING_ORDER", "db.kind_concepts.dwellings.LEVEL_LABELS"),
        ),
        HousingLevel.TENEMENT: Defined(
            "Tenements",
            checked_by=("catalog.urban.HOUSING_GATES", "catalog.urban.HOUSING_RULE"),
            used_by=("catalog.urban.HOUSING_ORDER", "db.kind_concepts.dwellings.LEVEL_LABELS"),
        ),
        HousingLevel.TOWER_BLOCK: Defined(
            "Tower blocks",
            checked_by=("catalog.urban.HOUSING_GATES", "catalog.urban.HOUSING_RULE"),
            used_by=("catalog.urban.HOUSING_ORDER", "catalog.urban.TALL_HOMES", "db.kind_concepts.dwellings.LEVEL_LABELS"),
        ),
        HousingLevel.ARCOLOGY_UNIT: Defined(
            "Arcology units",
            checked_by=("catalog.urban.HOUSING_GATES", "catalog.urban.HOUSING_RULE", "engine.settlement.life.quarter_wants"),
            used_by=("catalog.urban.FINE_HOMES", "catalog.urban.HOUSING_ORDER", "catalog.urban.TALL_HOMES", "db.kind_concepts.dwellings.LEVEL_LABELS"),
        ),
        HousingLevel.HABITAT_MODULE: Defined(
            "Habitat modules",
            checked_by=("catalog.urban.HOUSING_GATES", "catalog.urban.HOUSING_RULE"),
            used_by=("catalog.urban.HOUSING_ORDER", "db.kind_concepts.dwellings.LEVEL_LABELS"),
        ),
        HousingLevel.SHIP_BERTH: Defined(
            "Ship berths",
            checked_by=("catalog.urban.HOUSING_GATES", "catalog.urban.HOUSING_RULE"),
            used_by=("catalog.genetics.DWELLINGS", "catalog.urban.HOUSING_ORDER", "db.kind_concepts.dwellings.LEVEL_LABELS"),
        ),
    },
)
