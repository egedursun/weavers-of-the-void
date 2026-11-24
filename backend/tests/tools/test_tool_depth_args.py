from dataclasses import replace
from typing import Any

import pytest
from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.geology import UndergroundStratum
from aerona.tools.mortal.registry import mortal_specs
from aerona.tools.son.registry import son_specs
from tests.tools.every_mortal_tool import MORTAL_CASES
from tests.tools.every_setup import deep_ways
from tests.tools.every_son_tool import SON_CASES
from tests.tools.every_tool import Case, complete
from tests.tools.factories import Realm, mortal_toolkit, son_toolkit
from tests.tools.test_every_tool import PORTS, staged

BELOW = UndergroundStratum.CAVERN_UPPER

LAND = "works the land, its soil, water or sky, which lie at the surface"
WHOLE = "acts on the whole region, every level of it alike"
ROUTE = "names a route or a region as a whole for a public work"
SURFACE: dict[str, str] = {
    "clear_remnants": LAND,
    "reintroduce": "returns a kind to the wild range of the land",
    "dig_deeper": "digs down from the surface of the land the digger stands on",
    "drill_reservoir": LAND,
    "divert_river": LAND,
    "open_ground": LAND,
    "change_gear": LAND,
    "warn_coast": LAND,
    "cleanse_land": LAND,
    "commemorate": WHOLE,
    "begin_works": ROUTE,
    "dredge": LAND,
    "send_dispatch": "sends word toward a region, read by whoever rules it",
    "open_cosmic_bed": LAND,
    "sow_crop": LAND,
    "lay_enchantment": WHOLE,
    "designate_keystone": LAND,
    "tend_soil_stock": LAND,
    "stock_depot": "supplies an army's depot, kept per region at the surface",
    "lay_bare_fossils": LAND,
    "turn_wind": LAND,
    "move_ice": LAND,
    "wake_spirit": WHOLE,
    "hallow_wild": LAND,
    "shape_weather": LAND,
    "raise_phenomenon": WHOLE,
    "open_breach": WHOLE,
    "forge_ley_line": "joins the surface density of two lands",
    "carry_species": "carries a kind into the wild range of the land",
    "open_rift": WHOLE,
    "turn_region_climate": LAND,
    "call_impact": LAND,
    "wound_land": LAND,
    "heal_land": LAND,
    "reshape_land": LAND,
    "mark_land": WHOLE,
    "sanctify_region": WHOLE,
    "quell_danger": WHOLE,
    "curse_region": WHOLE,
    "redirect_river": LAND,
    "tend_land": LAND,
}


def region_arguments() -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for spec in [*mortal_specs(), *son_specs()]:
        fields = spec.input_model.model_fields
        for name in fields:
            if name in {"region_id", "location_id"} or name.endswith("_region_id"):
                sibling = "stratum" if name in {"region_id", "location_id"} else f"{name.removesuffix('_region_id')}_stratum"
                found.append((spec.name, name, sibling))
    return found


def test_every_tool_that_places_a_thing_in_a_region_takes_its_level_or_says_why_it_cannot() -> None:
    fields = {spec.name: spec.input_model.model_fields for spec in [*mortal_specs(), *son_specs()]}
    missing = [f"{tool}.{name} lacks {sibling}" for tool, name, sibling in region_arguments() if sibling not in fields[tool] and tool not in SURFACE]
    assert missing == []


def test_the_surface_list_names_only_tools_that_exist_and_still_lack_a_level() -> None:
    fields = {spec.name: spec.input_model.model_fields for spec in [*mortal_specs(), *son_specs()]}
    stale = [tool for tool in SURFACE if tool not in fields or "stratum" in fields[tool]]
    assert stale == []


def below(case: Case, key: str) -> Case:
    def arguments(realm: Realm, ids: dict[str, int]) -> dict[str, Any]:
        return {**case.arguments(realm, ids), key: realm.cosmos.region_id, "stratum": BELOW.value}

    async def setup(session: Any, realm: Realm) -> dict[str, int]:
        await deep_ways(session, realm)
        return dict(await case.setup(session, realm))

    return replace(case, arguments=arguments, setup=setup)


SON_BELOW = ("create_place", "create_people", "summon_spirit", "raise_beast", "found_settlement", "call_cosmic_being")
MORTAL_BELOW = ("found_settlement", "discover_resource")


async def placed_below(database: Database, before: set[int]) -> list[EntityRow]:
    async with database.read() as session:
        return [row for row in await session.scalars(select(EntityRow).where(EntityRow.stratum == BELOW).order_by(EntityRow.id)) if row.id not in before]


async def known(database: Database) -> set[int]:
    async with database.read() as session:
        return set(await session.scalars(select(EntityRow.id)))


@pytest.mark.parametrize("name", SON_BELOW)
async def test_a_son_tool_places_its_creation_beneath_the_region(database: Database, name: str) -> None:
    key = "region_id" if "region_id" in son_specs_by_name()[name].input_model.model_fields else "location_id"
    case = below(SON_CASES[name], key)
    realm, ids = await staged(database, case)
    before = await known(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=case.action_points, ports=PORTS)
    outcome = await toolkit.runtime.call(name, complete(son_specs_by_name()[name].input_model, case.arguments(realm, ids)))
    assert not outcome.is_error, outcome.text
    assert await placed_below(database, before)


@pytest.mark.parametrize("name", MORTAL_BELOW)
async def test_a_mortal_tool_places_its_work_beneath_the_region(database: Database, name: str) -> None:
    case = below(MORTAL_CASES[name], "location_id")
    realm, ids = await staged(database, case)
    before = await known(database)
    actor = case.actor(realm, ids) if case.actor is not None else realm.mortal_id
    toolkit = await mortal_toolkit(database, actor, action_points=case.action_points, ports=PORTS)
    outcome = await toolkit.runtime.call(name, complete(mortal_specs_by_name()[name].input_model, case.arguments(realm, ids)))
    assert not outcome.is_error, outcome.text
    assert await placed_below(database, before)


async def test_a_level_that_is_not_beneath_the_region_is_refused(database: Database) -> None:
    case = SON_CASES["create_place"]
    realm, ids = await staged(database, case)
    toolkit = await son_toolkit(database, realm.son_id, action_points=case.action_points, ports=PORTS)
    arguments = {**case.arguments(realm, ids), "location_id": realm.cosmos.region_id, "stratum": UndergroundStratum.DEEP_UNDERWORLD.value}
    outcome = await toolkit.runtime.call("create_place", complete(son_specs_by_name()["create_place"].input_model, arguments))
    assert outcome.is_error and "lies beneath" in outcome.text


def son_specs_by_name() -> dict[str, Any]:
    return {spec.name: spec for spec in son_specs()}


def mortal_specs_by_name() -> dict[str, Any]:
    return {spec.name: spec for spec in mortal_specs()}
