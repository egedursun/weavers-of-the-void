from dataclasses import replace

from aerona.domain.enums.economy import MaterialFamily
from aerona.engine.economy.materials import MaterialProps, corruption_lure, hull_wear, march_drag, sanctity_ward
from aerona.rules.registry import Rules

RULES = Rules()
PLAIN = MaterialProps("plain", next(iter(MaterialFamily)), 50, 0, 0, 50, 50, 0, 0, 50, 50, 0, None, 0)


def test_heavy_goods_drag_a_march_and_tough_hulls_keep_their_armour() -> None:
    assert march_drag(RULES, PLAIN) == 0
    assert march_drag(RULES, replace(PLAIN, weight=100)) > march_drag(RULES, replace(PLAIN, weight=20)) > 0
    assert hull_wear(RULES, None, 10) == 10 == hull_wear(RULES, PLAIN, 10)
    assert hull_wear(RULES, replace(PLAIN, toughness=100), 10) < 10


def test_holy_goods_ward_and_corrupt_goods_lure() -> None:
    assert sanctity_ward(RULES, PLAIN) == 0 == corruption_lure(RULES, PLAIN)
    assert sanctity_ward(RULES, replace(PLAIN, sanctity=100)) == RULES.materials.sanctity_ward_pct
    assert corruption_lure(RULES, replace(PLAIN, corruption=100)) == RULES.materials.corruption_lure_pct
