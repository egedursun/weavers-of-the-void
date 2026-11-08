from aerona.db.columns import within_bounds
from aerona.db.profile_guard import column_frozen


def move_amount(payer: object, payee: object, column: str, amount: int) -> bool:
    if column_frozen(payer, column) or column_frozen(payee, column):
        return False
    left, right = getattr(payer, column) - amount, getattr(payee, column) + amount
    if not (within_bounds(payer, column, left) and within_bounds(payee, column, right)):
        return False
    setattr(payer, column, left)
    setattr(payee, column, right)
    return True
