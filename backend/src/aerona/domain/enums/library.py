from enum import StrEnum


class UniverseStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class UniverseOrigin(StrEnum):
    CREATED = "created"
    IMPORTED = "imported"
    DUPLICATED = "duplicated"
    ADOPTED = "adopted"


class UniverseSort(StrEnum):
    OPENED = "opened"
    CREATED = "created"
    NAME = "name"
    EPOCH = "epoch"
    SIZE = "size"


class LibraryEventKind(StrEnum):
    CREATED = "created"
    ADOPTED = "adopted"
    OPENED = "opened"
    RENAMED = "renamed"
    EDITED = "edited"
    EXPORTED = "exported"
    IMPORTED = "imported"
    DUPLICATED = "duplicated"
    ARCHIVED = "archived"
    RESTORED = "restored"
    DELETED = "deleted"
    RECOVERED = "recovered"
    PURGED = "purged"
