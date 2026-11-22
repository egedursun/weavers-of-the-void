from aerona.catalog.materials import MATERIALS
from aerona.domain.enums.ecology import YieldProduct
from aerona.domain.enums.material import MaterialKind
from aerona.rules.renames import canonical_overrides

IMAGERY = ("salt", "bone", "flesh")


def test_no_material_or_yield_is_named_with_an_imagery_word() -> None:
    names = [*(kind.value for kind in MaterialKind), *(kind.value for kind in YieldProduct), *(spec.label.lower() for spec in MATERIALS.values())]
    assert [name for name in names if any(word in name.split("_") or word in name.split() for word in IMAGERY)] == []


def test_old_rule_keys_reach_the_renamed_ones() -> None:
    assert canonical_overrides({("prosthetics", "bone"): 50.0, ("environment", "desert_salt"): 30.0}) == {
        ("prosthetics", "calcified_tissue"): 50.0,
        ("environment", "desert_halite"): 30.0,
    }
