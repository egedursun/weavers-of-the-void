import asyncio
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from aerona.db.session import Database
from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from aerona.services.player.catalog import ACTIONS, action, run_ledgered
from aerona.services.player.scope import PlayerScope
from tests.engine.integration import factories
from tests.services.player import every_lever
from tests.services.player.every_lever import LEVERS, Lever, payload_for

LEVER_CACHE = Path(tempfile.gettempdir()) / "aerona-levers"
SYNC_ACTIONS = sorted(spec.id for spec in ACTIONS if spec.sync is not None)


def template_digest(schema_template: Path) -> str:
    digest = hashlib.sha256(schema_template.name.encode())
    for module in (factories, every_lever):
        digest.update(Path(module.__file__ or "").read_bytes())
    return digest.hexdigest()[:24]


async def seed(path: Path) -> None:
    database = Database(f"sqlite+aiosqlite:///{path}")
    try:
        async with database.write() as session:
            await factories.seed_rich_cosmos(session)
        await simulate(database, 2)
    finally:
        await database.dispose()


@pytest.fixture(scope="session")
def lever_template(schema_template: Path) -> Path:
    cached = LEVER_CACHE / f"{template_digest(schema_template)}.db"
    if not cached.exists():
        LEVER_CACHE.mkdir(parents=True, exist_ok=True)
        building = LEVER_CACHE / f"{cached.stem}.{os.getpid()}.building"
        shutil.copyfile(schema_template, building)
        asyncio.run(seed(building))
        os.replace(building, cached)
    return cached


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
