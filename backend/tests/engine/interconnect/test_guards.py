import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.body import ConditionRow
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.body.book import injuries_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.interconnect.registry import suppression_key
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.phase import Phase
from aerona.engine.phases.interconnect import modifier_upkeep
from aerona.engine.primitives.modifiers import ModifierDraft, ModifierIndex, add_modifier
from aerona.engine.primitives.queries import add_flag
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


async def test_suppressing_the_injury_mechanic_stops_wounds(session: AsyncSession, world_id: int) -> None:
    kept = await make(session, "Arn", EntityType.MORTAL, world_id, hp=100, strength=50, agility=50)
    hurt = await make(session, "Bera", EntityType.MORTAL, world_id, hp=100, strength=50, agility=50)
    await _guard(session, kept.id, suppression_key("injuries"), ModifierSource.SUPPRESSION)

    async def run(ctx: TickContext) -> None:
        for mortal in (kept, hurt):
            await apply_hits(ctx, mortal, Harm(30, HarmCause.BATTLE, "fell in a test"), lethal=False)

    await run_guarded(Phase("war_casualties", run), make_ctx(session, Rules(), epoch=5))
    assert await injuries_of(session, kept.id) == []
    assert await injuries_of(session, hurt.id)


async def test_engine_steps_read_through_modifiers_and_write_the_base(session: AsyncSession, world_id: int) -> None:
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, piety=40)
    await add_modifier(session, ModifierDraft(folk.id, "piety", ModifierOp.ADD, 20, ModifierSource.BLESSING, "modifier.blessing", start_epoch=1))
    seen: list[int | None] = []

    async def run(ctx: TickContext) -> None:
        seen.append(stat(folk, "piety"))
        set_stats(folk, piety=(stat(folk, "piety") or 0) + 5)
        seen.append(stat(folk, "piety"))

    await run_guarded(Phase("test_writer", run), make_ctx(session, Rules(), epoch=5))
    assert seen == [60, 65]
    assert stat(folk, "piety") == 45
    with pytest.raises(ValueError, match="conserved"):
        await add_modifier(session, ModifierDraft(folk.id, "population", ModifierOp.ADD, 20, ModifierSource.BLESSING, "modifier.blessing", start_epoch=1))


async def test_wonders_and_conditions_become_modifiers_each_epoch(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Saltmere", EntityType.SETTLEMENT, world_id, population=900, prosperity=40, piety=40)
    wonder = await make(session, "Glass Spire", EntityType.STRUCTURE, world_id, location_id=town.id)
    await add_flag(session, wonder.id, EntityFlag.WONDER, 1)
    sick = await make(session, "Arn", EntityType.MORTAL, world_id, hp=100, strength=60, agility=60)
    session.add(ConditionRow(bearer_node_id=sick.id, kind=ConditionKind.CHRONIC_ILLNESS, severity=2, source=HarmCause.ACCIDENT, since_epoch=1))
    await session.flush()
    rules = Rules()
    ctx = make_ctx(session, rules, epoch=5)
    await run_guarded(Phase("modifier_upkeep", modifier_upkeep), ctx)
    readings: dict[str, int | None] = {}

    async def read(ctx: TickContext) -> None:
        readings["prosperity"] = stat(town, "prosperity")
        readings["strength"] = stat(sick, "strength")

    await run_guarded(Phase("test_reader", read), ctx)
    assert readings["prosperity"] == 40 + rules.modifiers.wonder_prosperity
    assert readings["strength"] == round(60 * rules.modifiers.illness_strength_pct / 100)
    await run_guarded(Phase("modifier_upkeep", modifier_upkeep), make_ctx(session, rules, epoch=6))
    assert len((await ModifierIndex.load(session, epoch=6)).contributions(town.id, "prosperity")) == 1
