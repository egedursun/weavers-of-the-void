from sqlalchemy import ColumnElement, and_, or_

from aerona.db.tables.body import InjuryRow
from aerona.domain.enums.body import InjuryState


def leaves_mark(row: InjuryRow) -> bool:
    return row.state is InjuryState.PERMANENT or (row.state is InjuryState.HEALED_SCAR and (row.visible or row.function_loss > 0))


def marked() -> ColumnElement[bool]:
    return or_(
        InjuryRow.state == InjuryState.PERMANENT,
        and_(InjuryRow.state == InjuryState.HEALED_SCAR, or_(InjuryRow.visible.is_(True), InjuryRow.function_loss > 0)),
    )
