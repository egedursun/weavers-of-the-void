import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from aerona.constants.accounts import PASSWORD_MAX_LENGTH, TEMPORARY_PASSWORD_ALPHABET, TEMPORARY_PASSWORD_LENGTH

HASHER = PasswordHasher()
TOO_SHORT = "A password needs at least {length} characters."
TOO_LONG = "A password may have at most {length} characters."
HOLDS_NAME = "A password may not contain the username or the e-mail name."
NO_DECOY_HASH = HASHER.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return HASHER.hash(password)


def password_matches(stored: str, password: str) -> bool:
    try:
        return HASHER.verify(stored, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def spend_time_on_missing_account(password: str) -> None:
    password_matches(NO_DECOY_HASH, password)


def needs_rehash(stored: str) -> bool:
    return HASHER.check_needs_rehash(stored)


def temporary_password() -> str:
    return "".join(secrets.choice(TEMPORARY_PASSWORD_ALPHABET) for _ in range(TEMPORARY_PASSWORD_LENGTH))


def password_problem(password: str, *, username: str, email: str, min_length: int) -> str | None:
    if len(password) < min_length:
        return TOO_SHORT.format(length=min_length)
    if len(password) > PASSWORD_MAX_LENGTH:
        return TOO_LONG.format(length=PASSWORD_MAX_LENGTH)
    folded = password.casefold()
    names = {username.casefold(), email.split("@", 1)[0].casefold()}
    if any(name and len(name) >= 3 and name in folded for name in names):
        return HOLDS_NAME
    return None
