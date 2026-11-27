from typing import Protocol

from aerona.catalog.stats import max_essence
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.sons import SonRow
from aerona.rules.registry import Rules


def gain(creator: CreatorRow, amount: float) -> int:
    gained = max(0, round(amount))
    creator.essence += gained
    return gained


def spend(creator: CreatorRow, amount: int, rule_name: str) -> int:
    if amount <= 0:
        return 0
    if creator.essence < amount:
        raise ValidationFailedError(f"This needs {amount} divine essence; you have {creator.essence}. (Cost is world rule {rule_name} = {amount}.)")
    creator.essence -= amount
    return amount


def refund(creator: CreatorRow, amount: int) -> int:
    returned = max(0, amount)
    creator.essence += returned
    return returned


def son_room(rules: Rules, son: SonRow) -> int:
    return max(0, max_essence(rules, son.might) - son.essence)


class Purse(Protocol):
    essence: int


def endow(rules: Rules, god: Purse, amount: float) -> int:
    gained = max(0, round(amount))
    if isinstance(god, SonRow):
        gained = min(gained, son_room(rules, god))
    god.essence += gained
    return gained
