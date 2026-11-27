from sqlalchemy.orm import Mapper

import aerona.db.tables
import aerona.engine.phases.rumours
from aerona.db.base import Base
from aerona.db.profile_guard import EXPLICIT_NODE_COLUMNS, NODE_TABLES, shape_of_table, table_name
from aerona.services.books.kind_tables import KIND_TABLES
from aerona.services.books.typed import OWNER_TABLES, SKIPPED_TABLES, _owner

LOADED = (aerona.db.tables, aerona.engine.phases.rumours)


def mappers() -> dict[str, Mapper[object]]:
    return {table_name(mapper): mapper for mapper in Base.registry.mappers}


def links_to(mapper: Mapper[object], column: str, tables: frozenset[str]) -> bool:
    return any(foreign.column.table.name in tables for foreign in mapper.columns[column].foreign_keys)


def test_every_registered_node_column_points_at_a_node() -> None:
    found = mappers()
    stray = sorted(f"{table}.{column}" for table, column in EXPLICIT_NODE_COLUMNS.items() if not links_to(found[table], column, NODE_TABLES))
    assert stray == []


def test_a_record_row_number_never_stands_for_the_node_that_owns_it() -> None:
    stray = []
    for table, mapper in sorted(mappers().items()):
        if table in OWNER_TABLES or table in SKIPPED_TABLES or table in KIND_TABLES:
            continue
        owner = _owner(mapper)
        if owner is not None and not links_to(mapper, owner, OWNER_TABLES):
            stray.append(f"{table}.{owner}")
    assert stray == []


def test_a_unit_design_belongs_to_its_own_kind_and_a_spy_agent_to_the_agent() -> None:
    designs = shape_of_table("unit_designs")
    agents = shape_of_table("spy_agents")
    assert designs is not None and designs.node_column == "entity_id"
    assert agents is not None and agents.node_column == "mortal_entity_id"
    assert LOADED
