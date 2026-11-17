from dataclasses import replace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.lore import MessageRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import ReputationLabel
from aerona.engine.gods.reputation import (
    ReputationAxes,
    TraceKind,
    compute_reputation,
    drift_son,
    leave_trace,
    push_reputation,
    read_passions,
    reputation_label,
)
from aerona.engine.phases.reputation import reputation
from aerona.rules.registry import Rules
from aerona.services.gods.reputation import read_cosmos_reputation, set_passions
from aerona.services.gods.reputation import read_passions as service_passions
from tests.engine.gods.factories import GodsWorld, chronicle_keys, make_context, make_son


def test_label_order(rules: Rules) -> None:
    assert reputation_label(rules, love=10, fear=10, forgotten=90, loyalty=50) is ReputationLabel.FORGOTTEN
    assert reputation_label(rules, love=10, fear=80, forgotten=0, loyalty=10) is ReputationLabel.HATED
    assert reputation_label(rules, love=60, fear=60, forgotten=0, loyalty=60) is ReputationLabel.RESPECTED
    assert reputation_label(rules, love=10, fear=60, forgotten=0, loyalty=60) is ReputationLabel.FEARED
    assert reputation_label(rules, love=70, fear=0, forgotten=0, loyalty=60) is ReputationLabel.LOVED
    assert reputation_label(rules, love=10, fear=0, forgotten=45, loyalty=60) is ReputationLabel.DISTANT
    assert reputation_label(rules, love=10, fear=0, forgotten=0, loyalty=60) is ReputationLabel.ACKNOWLEDGED


def _act(world: GodsWorld, son_id: int, kind: ActionKind, epoch: int) -> ActionRecordRow:
    return ActionRecordRow(epoch=epoch, actor_kind=ActorKind.CREATOR, actor_node_id=world.creator.id, kind=kind, target_node_id=son_id)


async def test_reputation_from_structured_actions(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id, loyalty=40)
    session.add_all(
        [_act(world, son.id, ActionKind.BLESS_ESSENCE, 2), _act(world, son.id, ActionKind.LIGHTNING, 2), _act(world, son.id, ActionKind.DRAIN_ESSENCE, 2)]
    )
    session.add(MessageRow(epoch=2, sender_node_id=world.creator.id, recipient_node_id=son.id, intent=MessageIntent.THREAT, text="obey"))
    await session.flush()
    table = rules.reputation
    result = await compute_reputation(session, rules, son, 2, world.creator)
    assert result.love == round(table.love_base + table.love_per_grace_event + 40 / table.love_loyalty_divisor)
    assert result.fear == table.fear_base + table.fear_per_punish_event + table.fear_per_threat
    assert result.last_contact == 2
    assert result.forgotten == max(0, table.attention_threshold - 60) // table.neglect_attention_divisor


async def test_unanswered_son_prayers_cut_love(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    baseline = await compute_reputation(session, rules, son, 2, world.creator)
    session.add(MessageRow(epoch=2, sender_node_id=son.id, recipient_node_id=world.creator.id, intent=MessageIntent.PRAYER, text="father"))
    await session.flush()
    later = await compute_reputation(session, rules, son, 2, world.creator)
    assert later.unanswered == 1
    assert later.love == baseline.love - rules.reputation.love_per_unanswered_prayer


async def test_drift_and_label_chronicle(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id, loyalty=10)
    son.reputation_label = ReputationLabel.ACKNOWLEDGED
    son.manual_fear = 60
    son.trace_fear = 40
    await drift_son(make_context(session, rules, 2, "reputation"), son, world.creator)
    assert son.reputation_label is ReputationLabel.HATED
    assert son.loyalty == 10 - rules.reputation.hated_loyalty_loss
    assert son.manual_fear == round(60 * rules.reputation.manual_push_keep_pct / 100)
    assert son.trace_fear == round(40 * rules.reputation.power_trace_keep_pct / 100)
    assert "gods.reputation.change" in await chronicle_keys(session)


async def test_push_reputation_cap(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    cap = rules.reputation.manual_push_cap
    await push_reputation(session, rules, son, ReputationAxes(love=cap + 30), 2)
    assert son.manual_love == cap
    with pytest.raises(ValidationFailedError):
        await push_reputation(session, rules, son, ReputationAxes(love=10), 2)


async def test_traces_hit_target_and_siblings(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    target = await make_son(session, "Velkar", world.world.id)
    sibling = await make_son(session, "Iolen", world.world.id)
    applied = await leave_trace(session, rules, TraceKind.DRAIN, target.id, 2)
    assert target.trace_love == -rules.reputation.drain_love_loss
    assert target.trace_fear == rules.reputation.drain_fear
    assert sibling.trace_fear == rules.reputation.drain_sibling_fear
    assert set(applied) == {target.id, sibling.id}


async def test_passions_from_action_kinds(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    assert await read_passions(session, rules, 2) == [CreatorPassion.SILENCE]
    session.add_all(
        [
            _act(world, world.creator.id, ActionKind.DISASTER, 2),
            _act(world, world.creator.id, ActionKind.DISASTER, 2),
            _act(world, world.creator.id, ActionKind.MIRACLE, 2),
        ]
    )
    await session.flush()
    assert await read_passions(session, rules, 2) == [CreatorPassion.CHAOS, CreatorPassion.MERCY]


async def test_manual_passions_and_phase(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    view = await set_passions(session, rules, [CreatorPassion.ORDER, CreatorPassion.ORDER, CreatorPassion.BEAUTY], automatic=False)
    assert view.passions == (CreatorPassion.ORDER, CreatorPassion.BEAUTY)
    assert "gods.reputation.passions" in await chronicle_keys(session)
    with pytest.raises(ValidationFailedError):
        await set_passions(session, rules, [], automatic=False)
    await make_son(session, "Velkar", world.world.id)
    await reputation(make_context(session, rules, 2, "reputation"))
    assert (await service_passions(session, rules)).automatic is False
    cosmos_view = await read_cosmos_reputation(session, rules)
    assert len(cosmos_view.sons) == 1
    await set_passions(session, rules, [], automatic=True)
    tuned = replace(rules)
    assert (await service_passions(session, tuned)).automatic
