import warnings
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import configure_mappers
from sqlalchemy.orm.base import NEVER_SET, NO_VALUE

from aerona.db.base import Base
from aerona.db.ledger_capture import UNCAPTURED_TABLES


class PrimaryKeyMoved(UserWarning):
    pass


def refuse_key_move(target: Any, value: Any, oldvalue: Any, initiator: Any) -> None:
    if target.key is None or oldvalue is NO_VALUE or oldvalue is NEVER_SET or oldvalue == value:
        return
    warnings.warn(
        f"{target.class_.__name__}.{initiator.key} of a stored row moved from {oldvalue} to {value}; delete the row and add a new one so the record follows it",
        PrimaryKeyMoved,
        stacklevel=2,
    )


def install_key_guard() -> None:
    configure_mappers()
    for mapper in Base.registry.mappers:
        if all(table.name in UNCAPTURED_TABLES for table in mapper.tables):
            continue
        for column in mapper.primary_key:
            attribute = getattr(mapper.class_, mapper.get_property_by_column(column).key)
            if not event.contains(attribute, "set", refuse_key_move):
                event.listen(attribute, "set", refuse_key_move, raw=True)
