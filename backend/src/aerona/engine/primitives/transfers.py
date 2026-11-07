from aerona.db.profile_guard import column_frozen


def move_amount(payer: object, payee: object, column: str, amount: int) -> bool:
    if column_frozen(payer, column) or column_frozen(payee, column):
        return False
    setattr(payer, column, getattr(payer, column) - amount)
    setattr(payee, column, getattr(payee, column) + amount)
    return True
