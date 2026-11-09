from aerona.constants.units import PERCENT
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.mind import MemoryKind
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import god_of
from aerona.engine.mind.memories import remember
from aerona.engine.relations.book import ensure_relation, shift


async def god_grudge(ctx: TickContext, wronged_id: int | None, wronger_id: int | None, kind: MemoryKind, note: str) -> bool:
    if wronged_id is None or wronger_id is None or wronged_id == wronger_id:
        return False
    wronged, wronger = await god_of(ctx.session, wronged_id), await god_of(ctx.session, wronger_id)
    if wronged is None or wronger is None:
        return False
    table = ctx.rules.god_relations
    size = table.aid_memory if kind is MemoryKind.AIDED_CHOSEN else -table.theft_memory
    await remember(ctx.session, ctx.rules, holder_id=wronged.id, subject_id=wronger.id, kind=kind, magnitude=size, epoch=ctx.epoch, note=note)
    if isinstance(wronged, SonRow) and isinstance(wronger, SonRow):
        await SonRepository(ctx.session).change_relation(wronged.id, wronger.id, round(size * table.son_relation_pct / PERCENT), note)
    else:
        row = await ensure_relation(ctx.session, wronged.id, wronger.id, ctx.epoch)
        if row is not None:
            shift(ctx.rules, row, ctx.epoch, friendship=size)
    return True
