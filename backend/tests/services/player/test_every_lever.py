import shutil
from dataclasses import replace
from enum import Enum
from pathlib import Path
from typing import get_args

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.cosmos.orbits import DERIVED_WORLD_FIELDS
from aerona.engine.lore import control
from aerona.engine.phases.physics import derive_all
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from aerona.services.player.catalog import ACTIONS, action, run_ledgered
from aerona.services.player.scope import PlayerScope
from tests.services.player.every_lever import BRANCH_LEVERS, LEVERS, LORE_LEVERS, Lever, Pick, payload_for

SYNC_ACTIONS = sorted(spec.id for spec in ACTIONS if spec.sync is not None)


async def run(database: Database, action_id: str, lever: Lever) -> None:
    if lever.setup is not None:
        async with database.write() as session:
            await lever.setup(session)
    for number, (step, values) in enumerate(lever.before):
        async with database.write() as session:
            await run_ledgered(PlayerScope(session, Rules()), step, await payload_for(session, action(step).input_model, values, 1000 + number))
    if lever.then is not None:
        async with database.write() as session:
            await lever.then(session)
    async with database.write() as session:
        before = await derived_values(session)
        payload = await payload_for(session, action(action_id).input_model, lever.values, 1)
        await run_ledgered(PlayerScope(session, Rules()), action_id, payload)
        after = await derived_values(session)
    changed = {key: value for key, value in after.items() if key in before and before[key] != value}
    if changed:
        async with database.write() as session:
            await derive_all(await manual_context(session, "lever_heavens", Rules()), quiet=True)
            settled = await derived_values(session)
        assert {key: settled[key] for key in changed} == changed, f"{action_id} sets world values the heavens then undo"


async def derived_values(session: AsyncSession) -> dict[tuple[int, str], object]:
    fields = sorted(DERIVED_WORLD_FIELDS)
    rows = await session.execute(select(WorldRow.id, *(getattr(WorldRow, name) for name in fields)))
    return {(row[0], name): value for row in rows for name, value in zip(fields, row[1:], strict=True)}


def test_every_lever_case_names_a_real_action() -> None:
    assert set(LEVERS) <= set(SYNC_ACTIONS)


@pytest.mark.parametrize("action_id", SYNC_ACTIONS)
async def test_every_god_lever_runs_to_success(lever_template: Path, tmp_path: Path, action_id: str) -> None:
    path = tmp_path / "lever.db"
    shutil.copyfile(lever_template, path)
    database = Database(f"sqlite+aiosqlite:///{path}")
    try:
        await run(database, action_id, LEVERS.get(action_id, Lever()))
    finally:
        await database.dispose()


BRANCH_FIELDS = frozenset({"action", "mode", "op", "verb", "operation", "move"})


def branches() -> list[tuple[str, str, str]]:
    found = []
    for spec in ACTIONS:
        if spec.sync is None:
            continue
        for name, info in spec.input_model.model_fields.items():
            choices = [item for item in get_args(info.annotation) or (info.annotation,) if isinstance(item, type) and issubclass(item, Enum)]
            if name in BRANCH_FIELDS and choices:
                found.extend((spec.id, name, value.value) for value in choices[0])
    return sorted(found)


BRANCHES = branches()


def test_every_branching_lever_is_found() -> None:
    assert {action for action, _, _ in BRANCHES} >= {"route", "intervene", "faction:spy", "trade_route:found"}


@pytest.mark.parametrize(("action_id", "field_name", "value"), BRANCHES)
async def test_every_branch_of_a_god_lever_runs_to_success(lever_template: Path, tmp_path: Path, action_id: str, field_name: str, value: str) -> None:
    path = tmp_path / "branch.db"
    shutil.copyfile(lever_template, path)
    database = Database(f"sqlite+aiosqlite:///{path}")
    lever = BRANCH_LEVERS.get((action_id, value), LEVERS.get(action_id, Lever()))
    try:
        await run(database, action_id, replace(lever, values={**lever.values, field_name: value}))
    finally:
        await database.dispose()


LORE_KINDS = sorted(kind.value for kind in control.PROFILES)


@pytest.mark.parametrize("kind", LORE_KINDS)
async def test_every_kind_of_lore_record_can_be_edited(lever_template: Path, tmp_path: Path, kind: str) -> None:
    path = tmp_path / "lore.db"
    shutil.copyfile(lever_template, path)
    database = Database(f"sqlite+aiosqlite:///{path}")
    lever = LORE_LEVERS.get(kind, Lever(values={"entity_id": Pick(EntityType(kind))}))
    try:
        await run(database, "lore:edit", lever)
    finally:
        await database.dispose()


def test_every_editor_lever_edits_real_values() -> None:
    editors = sorted(spec.id for spec in ACTIONS if spec.sync is not None and "values" in spec.input_model.model_fields)
    bare = [name for name in editors if not LEVERS.get(name, Lever()).values.get("values")]
    assert bare == []
