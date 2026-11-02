from aerona.agents.fate.naming import name_pending_records, pending_count
from aerona.epoch.context import EpochContext


async def name_pending(ec: EpochContext) -> None:
    if not ec.runtime.llm_enabled:
        return
    async with ec.database.read() as session:
        waiting = await pending_count(session)
    if not waiting:
        return
    try:
        await name_pending_records(ec.runtime)
    except Exception as error:
        ec.runtime.error(f"Naming of unnamed records: {error}")
