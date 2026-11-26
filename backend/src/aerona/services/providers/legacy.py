from datetime import UTC, datetime

from sqlalchemy import select

from aerona.constants.providers import LEGACY_CLAUDE_LABEL, LEGACY_CLAUDE_MODEL, LEGACY_WORKER_LABEL
from aerona.db.library.tables import AccountRow, WorkspaceRow
from aerona.domain.enums.accounts import ServerRole, WorkspaceKind
from aerona.domain.enums.providers import ModelRole, ProviderKind
from aerona.services.providers.secrets import SecretBox, hint_of
from aerona.services.providers.store import ChainLink, NewConnection, ProviderStore

TEXT_ROLES = (ModelRole.WORLD_AGENTS, ModelRole.WRITING, ModelRole.CONVERSATION)


async def owners_workspace(store: ProviderStore) -> int | None:
    async with store.read() as session:
        return await session.scalar(
            select(WorkspaceRow.id)
            .join(AccountRow, AccountRow.id == WorkspaceRow.owner_account_id)
            .where(AccountRow.server_role == ServerRole.OWNER, WorkspaceRow.kind == WorkspaceKind.PERSONAL)
            .order_by(WorkspaceRow.id)
            .limit(1)
        )


async def adopt_legacy(store: ProviderStore, box: SecretBox, claude_token: str, worker_url: str) -> bool:
    present = {row.kind for row in await store.connections()}
    now = datetime.now(UTC)
    adopted = False
    workspace_id = await owners_workspace(store) if claude_token and ProviderKind.CLAUDE_SUBSCRIPTION not in present else None
    if workspace_id is not None:
        claude = await store.add_connection(
            NewConnection(workspace_id, ProviderKind.CLAUDE_SUBSCRIPTION, LEGACY_CLAUDE_LABEL, box.seal(claude_token), hint_of(claude_token), "", None, now)
        )
        await store.mark_login(claude, now)
        for role in TEXT_ROLES:
            await store.replace_chain(workspace_id, role, [ChainLink(claude, LEGACY_CLAUDE_MODEL)])
        adopted = True
    if worker_url and ProviderKind.IMAGE_WORKER not in present:
        worker = await store.add_connection(NewConnection(None, ProviderKind.IMAGE_WORKER, LEGACY_WORKER_LABEL, "", "", worker_url, None, now))
        await store.replace_chain(None, ModelRole.IMAGES, [ChainLink(worker, "")])
        adopted = True
    return adopted
