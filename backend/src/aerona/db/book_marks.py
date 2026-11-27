import re
from typing import Any

WRITE = re.compile(r"^\s*(?:INSERT(?:\s+OR\s+\w+)?\s+INTO|REPLACE\s+INTO|UPDATE(?:\s+OR\s+\w+)?|DELETE\s+FROM)\s+[\"`\[]?(\w+)", re.IGNORECASE)
WRITING_CTE = re.compile(r"^\s*WITH\b.*\b(?:INSERT|UPDATE|DELETE|REPLACE)\b", re.IGNORECASE | re.DOTALL)
QUIET_TABLES = frozenset({"jobs", "notifications", "notification_reads", "notification_preferences", "applied_fixups", "bond_reviews"})


def changes_the_book(statement: str) -> bool:
    found = WRITE.match(statement)
    if found is not None:
        return found.group(1).lower() not in QUIET_TABLES
    return WRITING_CTE.match(statement) is not None


class BookMarks:
    def __init__(self) -> None:
        self.dirty = False

    def note(self, _connection: Any, _cursor: Any, statement: str, _parameters: Any, _context: Any, _executemany: bool) -> None:
        if not self.dirty and changes_the_book(statement):
            self.dirty = True

    def taken(self) -> bool:
        dirty, self.dirty = self.dirty, False
        return dirty
