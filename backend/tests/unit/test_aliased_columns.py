from aerona.db.tables.cycles import KinshipSystemRow
from aerona.domain.enums.cycles import KinTermSystem
from aerona.engine.primitives.edits import bounds, coerce


def test_a_field_stored_under_another_column_name_can_be_set() -> None:
    row = KinshipSystemRow(people_entity_id=1, locked=[])
    assert coerce(row, "kin_terms", KinTermSystem.GENERATIONAL.value, bounds(row)) is KinTermSystem.GENERATIONAL
