from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.interconnect.registry import suppression_key
from aerona.engine.phase import Phase
from aerona.engine.primitives.modifiers import ModifierDraft, ModifierIndex, add_modifier
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx


async def _guard(session: AsyncSession, node_id: int, key: str, source: ModifierSource) -> None:
    await add_modifier(session, ModifierDraft(node_id, key, ModifierOp.ADD, 0, source, "guard.test", start_epoch=1))


async def test_a_pinned_field_is_not_changed_by_any_phase(session: AsyncSession, world_id: int) -> None:
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, piety=40, craft=30)
    await _guard(session, folk.id, "piety", ModifierSource.PIN)

    async def run(ctx: TickContext) -> None:
        set_stats(folk, piety=90, craft=70)

    await run_guarded(Phase("test_writer", run), make_ctx(session, Rules(), epoch=5))
    assert stat(folk, "piety") == 40
    assert stat(folk, "craft") == 70


async def test_a_suppressed_mechanic_cannot_write_to_its_target(session: AsyncSession, world_id: int) -> None:
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, piety=40)
    other = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=900, piety=40)
    await _guard(session, folk.id, suppression_key("test_writer"), ModifierSource.SUPPRESSION)

    async def run(ctx: TickContext) -> None:
        set_stats(folk, piety=90)
        set_stats(other, piety=90)

    await run_guarded(Phase("test_writer", run), make_ctx(session, Rules(), epoch=5))
    assert stat(folk, "piety") == 40
    assert stat(other, "piety") == 90


async def test_guards_do_not_apply_outside_engine_phases(session: AsyncSession, world_id: int) -> None:
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, piety=40)
    await _guard(session, folk.id, "piety", ModifierSource.PIN)
    set_stats(folk, piety=55)
    assert stat(folk, "piety") == 55
    assert (await ModifierIndex.load(session, epoch=5)).contributions(folk.id, "piety") == []
