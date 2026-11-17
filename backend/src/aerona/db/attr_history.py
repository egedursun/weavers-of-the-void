from typing import Any

from sqlalchemy.orm import InstanceState
from sqlalchemy.orm.attributes import History
from sqlalchemy.orm.base import PASSIVE_NO_INITIALIZE


def history_of(state: InstanceState[Any], key: str) -> History:
    return state.get_history(key, PASSIVE_NO_INITIALIZE)


def changed(state: InstanceState[Any], key: str) -> bool:
    return history_of(state, key).has_changes()
