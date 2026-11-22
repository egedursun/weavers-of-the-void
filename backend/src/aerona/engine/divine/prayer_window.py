from sqlalchemy import ColumnElement, and_

from aerona.db.tables.lore import MessageRow


def judged_epoch(run_epoch: int, wait: int = 1) -> int:
    return run_epoch - max(1, wait)


def judged_in_run(run_epoch: int) -> ColumnElement[bool]:
    return MessageRow.epoch == judged_epoch(run_epoch)


def overdue_in_run(run_epoch: int) -> ColumnElement[bool]:
    return and_(MessageRow.answered.is_(False), MessageRow.epoch < run_epoch)


def still_awaiting() -> ColumnElement[bool]:
    return MessageRow.answered.is_(False)


def last_run(epoch: int) -> int:
    return epoch - 1
