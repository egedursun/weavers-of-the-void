from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ConflictError, NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.team import QueuedActRow
from aerona.domain.enums.presence import PresenceRecord
from aerona.rules.registry import Rules
from aerona.services.container import Services
from aerona.services.presence.speakers import Speaker, require_speaker
from aerona.services.presence.tools import speaker_tools
from aerona.services.team.execute import rules_in
from aerona.tools.toolkit import Toolkits

NO_SPEAKER = "The queued act names no speaker."
CANNOT_ACT = "{name} can no longer act."
NO_TOOLKITS = "The world's tools are not available."


async def speaker_now(session: AsyncSession, rules: Rules, node_id: int | None) -> Speaker:
    if node_id is None:
        raise NotFoundError(NO_SPEAKER)
    return await require_speaker(session, rules, node_id)


async def replay_tool(services: Services, row: QueuedActRow) -> str:
    found = services.agents.toolkits
    if not isinstance(found, Toolkits):
        raise ConflictError(NO_TOOLKITS)
    async with services.database.read() as session:
        rules = await rules_in(services, session)
        speaker = await speaker_now(session, rules, row.speaker_node_id)
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
    tools = await speaker_tools(services.database, found, rules, speaker, record=PresenceRecord.ON_RECORD, epoch=epoch, world_busy=False)
    if not tools.acting or tools.toolkit is None or row.action_id not in tools.names:
        raise ConflictError(CANNOT_ACT.format(name=speaker.name))
    await tools.open_turn()
    outcome = await tools.toolkit.runtime.call(row.action_id, dict(row.payload))
    await tools.toolkit.settle_long_jobs()
    if outcome.is_error:
        raise ConflictError(outcome.text)
    return outcome.text
