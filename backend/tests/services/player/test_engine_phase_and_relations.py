from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.limits import RELATION_MAX
from aerona.engine import pipeline
from aerona.engine.services.community_relations import blood_feud_pairs, relation, relation_history, relation_list
from aerona.rules.registry import Rules
from aerona.services.engine_phases import PhaseStage, list_phases
from aerona.services.player import engine_control, relations
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def _pair(session: AsyncSession, world: PlayerWorld) -> tuple[EntityRow, EntityRow]:
    first = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    second = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    return first, second


def test_every_pipeline_phase_is_listed_with_its_switch_state() -> None:
    listed = list_phases(Rules())
    assert [info.name for info in listed] == [phase.name for phase in pipeline.all_phases()]
    assert all(info.enabled for info in listed)
    assert {info.stage for info in listed} == set(PhaseStage)
    assert next(info for info in listed if info.name == "advance_epoch").runnable is False
    assert next(info for info in listed if info.name == "advance_epoch").essential
    assert next(info for info in listed if info.name == "campaigns").heavy


def test_a_switched_off_phase_is_listed_as_disabled() -> None:
    rules = Rules()
    rules = replace(rules, engine_phases=replace(rules.engine_phases, creatures=0))
    assert next(info for info in list_phases(rules) if info.name == "creatures").enabled is False


def test_the_new_actions_are_registered() -> None:
    assert {"engine:run_phase", "relation:set", "feud:start"} <= set(ACTIONS_BY_ID)


async def test_a_named_phase_runs_now_even_when_switched_off(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await engine_control.run_phase(scope, engine_control.RunPhase(phase="diplomacy"))
    assert outcome.action == "engine:run_phase"
    assert "diplomacy" in outcome.message
    assert (await session.scalars(select(ActionRecordRow))).all()


async def test_an_unknown_or_unrunnable_phase_is_refused(scope: PlayerScope) -> None:
    with pytest.raises(NotFoundError):
        await engine_control.run_phase(scope, engine_control.RunPhase(phase="no_such_step"))
    with pytest.raises(ValidationFailedError):
        await engine_control.run_phase(scope, engine_control.RunPhase(phase="advance_epoch"))


async def test_relation_can_be_set_listed_and_its_history_read(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    first, second = await _pair(session, world)
    outcome = await relations.set_community_relation(scope, relations.SetRelation(first_id=first.id, second_id=second.id, value=40))
    assert outcome.values["value"] == 40
    assert await relation(session, rules, first.id, second.id) == 40
    history = await relation_history(session, first.id, second.id, 5)
    assert history and history[-1].event == relations.SET_REASON
    listing = await relation_list(session, rules, first.id)
    assert [view.entity_id for view in listing] == [second.id]
    with pytest.raises(ValidationFailedError):
        await relations.set_community_relation(scope, relations.SetRelation(first_id=first.id, second_id=second.id, value=RELATION_MAX + 1))
    with pytest.raises(ValidationFailedError):
        await relations.set_community_relation(scope, relations.SetRelation(first_id=first.id, second_id=first.id, value=1))
    assert (await session.scalar(select(MemoryRow))) is not None


async def test_a_blood_feud_can_be_declared_once_and_lowers_the_relation(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    first, second = await _pair(session, world)
    before = await relation(session, rules, first.id, second.id)
    await relations.declare_feud(scope, relations.DeclareFeud(first_id=first.id, second_id=second.id))
    assert (first.id, second.id) in await blood_feud_pairs(session)
    assert await relation(session, rules, first.id, second.id) < before
    with pytest.raises(ValidationFailedError):
        await relations.declare_feud(scope, relations.DeclareFeud(first_id=first.id, second_id=second.id))


async def test_relations_need_two_communities(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    with pytest.raises(ValidationFailedError):
        await relations.declare_feud(scope, relations.DeclareFeud(first_id=town.id, second_id=world.region.id))
