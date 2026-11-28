from aerona.db.columns import within_bounds
from aerona.db.profile_guard import column_frozen
from aerona.db.record_context import add_term, isolated


def move_amount(payer: object, payee: object, column: str, amount: int) -> bool:
    if column_frozen(payer, column) or column_frozen(payee, column):
        return False
    left, right = getattr(payer, column) - amount, getattr(payee, column) + amount
    if not (within_bounds(payer, column, left) and within_bounds(payee, column, right)):
        return False
    setattr(payer, column, left)
    setattr(payee, column, right)
    return True


def move_told(payer: object, payee: object, column: str, amount: int, *, key: str, source: int) -> bool:
    if column_frozen(payer, column) or column_frozen(payee, column):
        return False
    left, right = getattr(payer, column) - amount, getattr(payee, column) + amount
    if not (within_bounds(payer, column, left) and within_bounds(payee, column, right)):
        return False
    for row, value, part in ((payer, left, -amount), (payee, right, amount)):
        with isolated():
            add_term(key, part, source_node_id=source)
            setattr(row, column, value)
    return True
