from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow


def test_every_kind_of_node_loads_its_own_columns_in_a_query_over_nodes() -> None:
    kinds = [mapper for mapper in NodeRow.__mapper__.self_and_descendants if mapper is not NodeRow.__mapper__]
    assert EntityRow.__mapper__ in kinds
    lazy = sorted(mapper.class_.__name__ for mapper in kinds if mapper.polymorphic_load != "inline")
    assert not lazy, f"these kinds of node would load their columns lazily from a query over nodes: {lazy}"
