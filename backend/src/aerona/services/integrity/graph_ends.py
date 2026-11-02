from sqlalchemy.ext.asyncio import AsyncSession

from aerona.events.bus import EventBus
from aerona.rules.registry import Rules
from aerona.services.integrity.network import RepairCounters, RepairLog, repair_dangling_ends


async def repair_graph_ends(session: AsyncSession, rules: Rules, epoch: int, log: RepairLog, bus: EventBus | None = None) -> RepairCounters:
    return await repair_dangling_ends(session, rules, epoch, log, bus)


async def repair_at_epoch_end(session: AsyncSession, rules: Rules, epoch: int, log: RepairLog, bus: EventBus | None = None) -> RepairCounters | None:
    if not rules.link_graph.auto_repair:
        return None
    return await repair_dangling_ends(session, rules, epoch, log, bus)
