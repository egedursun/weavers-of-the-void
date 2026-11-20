import re
import sqlite3
import sys
import tempfile
from pathlib import Path

import sqlalchemy as sa

from aerona.db.base import Base
from aerona.db.migrations import replay_migrations_sync


def constraint_values(sql: str, column: str) -> set[str] | None:
    found = re.search(rf"CHECK \({re.escape(column)} IN \(([^)]*)\)\)", sql)
    return {value.strip().strip("'") for value in found.group(1).split(",")} if found else None


def findings() -> list[str]:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "head.db"
        replay_migrations_sync(f"sqlite:///{path}")
        schema = dict(sqlite3.connect(path).execute("select name, sql from sqlite_master where type='table'").fetchall())
    found: list[str] = []
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            kind = getattr(column.type, "enum_class", None)
            if not isinstance(column.type, sa.Enum) or kind is None or table.name not in schema:
                continue
            stored = constraint_values(schema[table.name], column.name)
            wanted = {value.value for value in kind}
            if stored is not None and stored != wanted:
                missing = sorted(wanted - stored)
                extra = sorted(stored - wanted)
                found.append(f"{table.name}.{column.name}: the migrated check differs from {kind.__name__}; missing {missing}, stale {extra}")
    return found


def main() -> int:
    found = findings()
    for line in found:
        print(line)
    print(f"enum constraints out of step: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
