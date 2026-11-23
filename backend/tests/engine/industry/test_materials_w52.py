from dataclasses import replace

from aerona.catalog.goods_tables import ORIGIN_BASE, ORIGIN_WORDS, SOURCED_ORIGINS
from aerona.catalog.materials import MATERIALS
from aerona.domain.enums.economy import MaterialFamily, MaterialOrigin
from aerona.domain.enums.material import MaterialKind
from aerona.engine.economy.materials import from_spec, hardness_of, value_of, weapon_damage
from aerona.rules.registry import Rules
from tests.engine.society.factories import tuned

NEW = (MaterialKind.CERAMIC, MaterialKind.SILK, MaterialKind.RESIN, MaterialKind.SHELL, MaterialKind.POLYMER, MaterialKind.COMPOSITE)


def test_the_six_new_materials_have_their_group_hardness_and_worth() -> None:
    assert all(kind in MATERIALS for kind in NEW) and len(MATERIALS) == len(MaterialKind)
    assert MATERIALS[MaterialKind.SILK].family is MaterialFamily.PRECIOUS
    assert MATERIALS[MaterialKind.COMPOSITE].level > MATERIALS[MaterialKind.STEEL].level


def test_a_materials_hardness_and_worth_come_from_its_rules() -> None:
    props = from_spec(MATERIALS[MaterialKind.CERAMIC])
    rules = Rules()
    assert hardness_of(rules, props) == rules.materials.ceramic_hardness and value_of(rules, props) == rules.materials.ceramic_value
    harder = tuned(rules, materials={"ceramic_hardness": 95})
    assert weapon_damage(harder, props, 50) > weapon_damage(rules, props, 50)
    assert hardness_of(harder, replace(props, world_material_id=7)) == props.hardness


def test_the_three_new_origins_name_their_sources_and_bases() -> None:
    for origin in (MaterialOrigin.FOSSIL, MaterialOrigin.LIVING_LINE, MaterialOrigin.SALVAGE):
        assert origin in SOURCED_ORIGINS and origin in ORIGIN_BASE and ORIGIN_WORDS[origin]
    assert MaterialOrigin.CATALOG not in SOURCED_ORIGINS
