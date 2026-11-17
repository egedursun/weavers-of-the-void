from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole, ModifierOp, ModifierSource
from aerona.engine.phases.interconnect import modifier_upkeep
from aerona.engine.primitives.modifiers import Contribution, ModifierDraft, ModifierIndex, add_modifier, combine, remove_modifiers
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx


def _contribution(modifier_id: int, op: ModifierOp, magnitude: float, group: str | None = None) -> Contribution:
    return Contribution(modifier_id, op, magnitude, ModifierSource.BLESSING, None, "test.reason", group)


def test_adds_sum_before_multipliers_apply() -> None:
    breakdown = combine(10, [_contribution(1, ModifierOp.ADD, 5), _contribution(2, ModifierOp.MULTIPLY, 2), _contribution(3, ModifierOp.ADD, -3)])
    assert breakdown.value == (10 + 5 - 3) * 2
    assert [item.modifier_id for item in breakdown.applied] == [1, 2, 3]


def test_a_stacking_group_keeps_only_its_strongest_add_and_multiplier() -> None:
    contributions = [
        _contribution(1, ModifierOp.ADD, 4, "festival"),
        _contribution(2, ModifierOp.ADD, -6, "festival"),
        _contribution(3, ModifierOp.MULTIPLY, 1.1, "festival"),
        _contribution(4, ModifierOp.MULTIPLY, 0.7, "festival"),
        _contribution(5, ModifierOp.ADD, 1),
    ]
    breakdown = combine(20, contributions)
    assert breakdown.value == (20 - 6 + 1) * 0.7
    assert {item.modifier_id for item in breakdown.ignored} == {1, 3}


async def test_index_reads_only_modifiers_active_this_epoch(session: AsyncSession, world_id: int) -> None:
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, piety=40)
    await add_modifier(session, ModifierDraft(folk.id, "piety", ModifierOp.ADD, 10, ModifierSource.BLESSING, "blessing.piety", start_epoch=5))
    await add_modifier(session, ModifierDraft(folk.id, "piety", ModifierOp.ADD, 30, ModifierSource.CURSE, "later", start_epoch=20))
    await add_modifier(session, ModifierDraft(folk.id, "piety", ModifierOp.ADD, 50, ModifierSource.CURSE, "over", start_epoch=1, end_epoch=4))
    index = await ModifierIndex.load(session, epoch=10)
    assert index.effective(folk.id, "piety", 40) == 50
    assert index.keys_of(folk.id) == ["piety"]


async def test_upkeep_expires_and_decays_modifiers(session: AsyncSession, world_id: int) -> None:
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, piety=40)
    await add_modifier(session, ModifierDraft(folk.id, "piety", ModifierOp.ADD, 10, ModifierSource.PLAYER, "gone", start_epoch=1, end_epoch=3))
    decaying = await add_modifier(session, ModifierDraft(folk.id, "piety", ModifierOp.ADD, 10, ModifierSource.PLAYER, "fading", start_epoch=1, decay_pct=50))
    await add_modifier(session, ModifierDraft(folk.id, "piety", ModifierOp.MULTIPLY, 1.004, ModifierSource.PLAYER, "tiny", start_epoch=1, decay_pct=10))
    await modifier_upkeep(make_ctx(session, Rules(), epoch=5))
    await session.flush()
    rows = list(await session.scalars(select(ModifierRow).order_by(ModifierRow.id)))
    assert [row.id for row in rows] == [decaying.id]
    assert rows[0].magnitude == 5


async def test_removing_modifiers_by_source(session: AsyncSession, world_id: int) -> None:
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900, piety=40)
    await add_modifier(session, ModifierDraft(folk.id, "piety", ModifierOp.ADD, 10, ModifierSource.CURSE, "curse", start_epoch=1))
    await add_modifier(session, ModifierDraft(folk.id, "piety", ModifierOp.ADD, 3, ModifierSource.BLESSING, "blessing", start_epoch=1))
    assert await remove_modifiers(session, source_kind=ModifierSource.CURSE) == 1
    assert len(list(await session.scalars(select(ModifierRow)))) == 1


async def test_every_chronicle_line_records_an_incident(session: AsyncSession, world_id: int) -> None:
    folk = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=900)
    city = await make(session, "Stone Gate", EntityType.SETTLEMENT, world_id, population=800)
    ctx = make_ctx(session, Rules(), epoch=7)
    first = await record(
        ctx,
        "player.history",
        roles={IncidentRole.ACTOR: folk.id, IncidentRole.TARGET: city.id},
        facts={"account": "Reed Folk marched on Stone Gate."},
        magnitude=40,
    )
    second = await record(ctx, "player.history", roles={IncidentRole.SUBJECT: city.id}, facts={"account": "Stone Gate burned."}, cause=first.incident_id)
    incident = await session.get(IncidentRow, second.incident_id)
    assert incident is not None and incident.kind == "player.history" and incident.cause_incident_id == first.incident_id
    assert incident.chronicle_id == second.row.id
    participants = list(await session.scalars(select(IncidentParticipantRow).where(IncidentParticipantRow.incident_id == first.incident_id)))
    assert sorted((row.node_id, row.role) for row in participants) == sorted([(folk.id, IncidentRole.ACTOR), (city.id, IncidentRole.TARGET)])
