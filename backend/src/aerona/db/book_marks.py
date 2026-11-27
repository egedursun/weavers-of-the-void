import hashlib
import re
import secrets
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

WRITE = re.compile(r"^\s*(?:INSERT(?:\s+OR\s+\w+)?\s+INTO|REPLACE\s+INTO|UPDATE(?:\s+OR\s+\w+)?|DELETE\s+FROM)\s+[\"`\[]?(\w+)", re.IGNORECASE)
WRITING_CTE = re.compile(r"^\s*WITH\b.*\b(?:INSERT|UPDATE|DELETE|REPLACE)\b", re.IGNORECASE | re.DOTALL)
REWRITE = re.compile(r"^\s*(?:INSERT\s+OR\s+REPLACE\s+INTO|REPLACE\s+INTO|UPDATE(?:\s+OR\s+\w+)?|DELETE\s+FROM)\s+[\"`\[]?(\w+)", re.IGNORECASE)
QUIET_TABLES = frozenset({"jobs", "notifications", "notification_reads", "notification_preferences", "applied_fixups", "bond_reviews"})
PAST_TABLES = frozenset({"state_changes", "state_change_terms"})
LEDGER_FOLDER = "book-ledger"
PAST_STAMP = "past"
FOLDER_KEY_LENGTH = 16
STAMP_BYTES = 16


def changes_the_book(statement: str) -> bool:
    found = WRITE.match(statement)
    if found is not None:
        return found.group(1).lower() not in QUIET_TABLES
    return WRITING_CTE.match(statement) is not None


def rewrites_the_past(statement: str) -> bool:
    found = REWRITE.match(statement)
    if found is not None:
        return found.group(1).lower() in PAST_TABLES
    return WRITING_CTE.match(statement) is not None and any(table in statement.lower() for table in PAST_TABLES)


def ledger_folder(url: str) -> Path:
    database = make_url(url).database
    place = Path(database).resolve() if database and database != ":memory:" else Path(tempfile.gettempdir()) / "aerona"
    return place.parent / LEDGER_FOLDER / hashlib.sha256(str(place).encode()).hexdigest()[:FOLDER_KEY_LENGTH]


def renew_past(url: str) -> str:
    folder = ledger_folder(url)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = secrets.token_hex(STAMP_BYTES)
    writing = folder / f"{PAST_STAMP}.{secrets.token_hex(STAMP_BYTES)}"
    writing.write_text(stamp, encoding="utf-8")
    writing.replace(folder / PAST_STAMP)
    return stamp


def past_stamp(url: str) -> str:
    try:
        return (ledger_folder(url) / PAST_STAMP).read_text(encoding="utf-8")
    except FileNotFoundError:
        return renew_past(url)


class BookMarks:
    def __init__(self) -> None:
        self.dirty = False
        self.past = False

    def note(self, _connection: Any, _cursor: Any, statement: str, _parameters: Any, _context: Any, _executemany: bool) -> None:
        if not self.dirty and changes_the_book(statement):
            self.dirty = True
        if not self.past and rewrites_the_past(statement):
            self.past = True

    def taken(self) -> bool:
        dirty, self.dirty = self.dirty, False
        return dirty

    def past_taken(self) -> bool:
        past, self.past = self.past, False
        return past
