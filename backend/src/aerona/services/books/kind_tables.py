from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.tables.kinds import KindHoldingRow

KIND_TABLES = frozenset(spec.table.__tablename__ for spec in CONCEPTS.values()) | {KindHoldingRow.__tablename__}
