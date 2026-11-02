from sqlalchemy import select

from aerona.agents.ask import ask
from aerona.agents.context.scope import load_scope
from aerona.agents.roles import AgentRole
from aerona.agents.runtime import AgentRuntime
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.world import LoreLanguage
from aerona.prompts import PromptId
from aerona.prompts.contexts.localisation import EngineLine, LocaliseContext
from aerona.prompts.schemas.localisation import LocalisedLinesOutput


async def localise_epoch(runtime: AgentRuntime, epoch: int) -> int:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        if scope.cosmos.lore_language is LoreLanguage.ENGLISH:
            return 0
        rows = list(
            await session.scalars(
                select(ChronicleRow)
                .where(ChronicleRow.epoch == epoch, ChronicleRow.template_key.is_not(None), ChronicleRow.kind != ChronicleKind.ENGINE_RAW)
                .order_by(ChronicleRow.id)
            )
        )
        language, world_name = scope.cosmos.lore_language, scope.cosmos.name
    if not rows:
        return 0
    runtime.require_llm("localisation")
    translated = 0
    size = rules.agents.localise_batch
    for start in range(0, len(rows), size):
        batch = rows[start : start + size]
        context = LocaliseContext(lore_language=language, world_name=world_name, lines=[EngineLine(id=row.id, text=row.text) for row in batch])
        output = await ask(
            runtime.model,
            rules,
            label=AgentRole.LOCALISATION,
            system=(PromptId.LOCALISE_SYSTEM, context),
            user=(PromptId.LOCALISE_USER, context),
            output=LocalisedLinesOutput,
        )
        wanted = {row.id for row in batch}
        async with runtime.database.write() as session:
            for line in output.lines:
                row = await session.get(ChronicleRow, line.id)
                if line.id in wanted and row is not None and line.text.strip():
                    row.text = line.text.strip()
                    translated += 1
    return translated
