from collections.abc import Awaitable, Callable

AccountLookup = Callable[[int], Awaitable[bool]]

LEGACY_AUTHORS: dict[str, str] = {}


def remember_legacy(database_url: str, name: str) -> None:
    if name:
        LEGACY_AUTHORS[database_url] = name
    else:
        LEGACY_AUTHORS.pop(database_url, None)


def legacy_name(database_url: str) -> str:
    return LEGACY_AUTHORS.get(database_url, "")


ACCOUNT_LOOKUPS: dict[str, AccountLookup] = {}


def remember_accounts(database_url: str, lookup: AccountLookup) -> None:
    ACCOUNT_LOOKUPS[database_url] = lookup


async def account_remains(database_url: str, account_id: int) -> bool:
    lookup = ACCOUNT_LOOKUPS.get(database_url)
    return True if lookup is None else await lookup(account_id)
