from aerona.services.accounts.guard import GrantedAccess
from aerona.services.accounts.service import AccountService
from aerona.services.library.hub import OpenedHook, UniverseHub
from aerona.services.library.runtime import UniverseRuntime
from aerona.services.team.legacy import remember_accounts, remember_legacy
from aerona.services.team.state import GrantResolver


def resolver_for(hub: UniverseHub, accounts: AccountService, universe_id: str) -> GrantResolver:
    async def grant_of(account_id: int) -> GrantedAccess | None:
        record = await hub.catalogue.get(universe_id)
        if record is None:
            return None
        found = await accounts.universe_access(account_id, record)
        if not found.visible:
            return None
        return GrantedAccess(found, record.name, record.canon_approval)

    return grant_of


def grant_hook(hub: UniverseHub, accounts: AccountService) -> OpenedHook:
    async def bind(runtime: UniverseRuntime) -> None:
        runtime.services.team.grant_of = resolver_for(hub, accounts, runtime.universe_id)
        record = await hub.catalogue.get(runtime.universe_id)
        remember_legacy(str(runtime.services.database.engine.url), record.legacy_author_name if record is not None else "")

        async def remains(account_id: int) -> bool:
            return await accounts.store.account(account_id) is not None

        remember_accounts(str(runtime.services.database.engine.url), remains)

    return bind
