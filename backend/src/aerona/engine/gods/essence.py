from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmos import CreatorRow


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
