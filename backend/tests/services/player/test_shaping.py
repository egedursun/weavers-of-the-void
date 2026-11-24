import shutil
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

from aerona.agents.summoner import Parentage, applied, designed
from aerona.db.session import Database
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import MortalStats
from aerona.domain.models.son_design import SonDesign
from aerona.prompts.schemas.shared import PassionsOutput, SonProfileOutput
from aerona.rules.registry import Rules
from aerona.services.player.catalog import action, run_ledgered
from aerona.services.player.scope import PlayerScope
from tests.services.player.every_lever import Pick, payload_for


async def shaped(lever_template: Path, tmp_path: Path, action_id: str, values: dict[str, Any]) -> tuple[Database, int]:
    path = tmp_path / "shape.db"
    shutil.copyfile(lever_template, path)
    database = Database(f"sqlite+aiosqlite:///{path}")
    async with database.write() as session:
        payload = await payload_for(session, action(action_id).input_model, values, 1)
        outcome = await run_ledgered(PlayerScope(session, Rules()), action_id, payload)
    created = outcome.created_ids[0]
    return database, created


async def test_a_shaped_mortal_keeps_every_chosen_value(lever_template: Path, tmp_path: Path) -> None:
    database, created = await shaped(
        lever_template,
        tmp_path,
        "mortal:shape",
        {"community_id": Pick(EntityType.SETTLEMENT), "name": "Ardel Vasse", "role": "sage", "sex": "bearer", "strength": 81, "age": 30},
    )
    try:
        async with database.read() as session:
            mortal = await session.get(EntityRow, created)
            assert mortal is not None and mortal.name == "Ardel Vasse"
            assert isinstance(mortal.stats, MortalStats)
            assert (mortal.stats.strength, mortal.stats.age, mortal.stats.sex) == (81, 30, "bearer")
    finally:
        await database.dispose()


@pytest.mark.parametrize("kind", ["celestial", "spirit", "natural_law", "cult"])
async def test_every_shaped_record_kind_is_made_with_its_name(lever_template: Path, tmp_path: Path, kind: str) -> None:
    values: dict[str, Any] = {"entity_type": kind, "name": f"Shaped {kind}", "world_id": Pick("world")}
    if kind == "cult":
        values["god_id"] = Pick("son")
    database, created = await shaped(lever_template, tmp_path, "record:shape", values)
    try:
        async with database.read() as session:
            made = await session.get(EntityRow, created)
            assert made is not None and made.entity_type.value == kind and made.name == f"Shaped {kind}"
            if kind == "cult":
                worship = await session.scalar(select(BondRow).where(BondRow.source_node_id == created, BondRow.kind == BondKind.WORSHIPS))
                assert worship is not None
    finally:
        await database.dispose()


async def test_a_named_village_and_region_take_their_names(lever_template: Path, tmp_path: Path) -> None:
    database, created = await shaped(lever_template, tmp_path, "people:village", {"people_id": Pick(EntityType.PEOPLE), "name": "Lowmeadow"})
    try:
        async with database.read() as session:
            town = await session.get(EntityRow, created)
            assert town is not None and town.name == "Lowmeadow"
    finally:
        await database.dispose()


def test_a_son_design_overrides_what_the_model_wrote() -> None:
    output = SonProfileOutput.model_construct(
        name="Model Name",
        title="t",
        domain_1=Domain.EARTH,
        domain_2=Domain.SEA,
        appearance="a",
        temperament="b",
        obsession="c",
        fear="d",
        speech_style="e",
        secret="f",
        passions=PassionsOutput(loyalty=10, ambition=10, wrath=10, mercy=10),
    )
    design = SonDesign(name="Chosen", domain_1=Domain.SKY, temperament="calm", wrath=90)
    result = applied(output, design)
    assert (result.name, result.domain_1, result.temperament, result.passions.wrath) == ("Chosen", Domain.SKY, "calm", 90)
    assert result.domain_2 is Domain.SEA and result.passions.loyalty == 10
    assert "Chosen" in (designed(Parentage(), design).inspiration or "")
