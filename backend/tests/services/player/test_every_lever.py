import shutil
from pathlib import Path

import pytest

from aerona.db.session import Database
from aerona.rules.registry import Rules
from aerona.services.player.catalog import ACTIONS, action, run_ledgered
from aerona.services.player.scope import PlayerScope
from tests.services.player.every_lever import LEVERS, Lever, payload_for

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
        payload = await payload_for(session, action(action_id).input_model, lever.values, 1)
        await run_ledgered(PlayerScope(session, Rules()), action_id, payload)


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
