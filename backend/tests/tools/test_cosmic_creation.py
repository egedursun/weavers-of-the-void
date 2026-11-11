from sqlalchemy import func, select

from aerona.db.session import Database
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalaxyRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.rarity import Rarity
from aerona.engine.cosmos.ladder import ensure_ladder
from aerona.rules.registry import Rules
from tests.tools.factories import seed_realm, son_toolkit
from tests.tools.test_son_tools import ok, rejected

GALAXY = {"name": "Second Wheel", "galaxy_type": "spiral", "description": "A wide galaxy far from the first."}
CLUSTER = {"name": "Far Gathering", "kind": "filament", "description": "A long line of galaxies."}
DIMENSION = {"name": "Quiet Deep", "kind": "astral", "description": "A still place beside the first."}


async def laddered(database: Database, rarity: Rarity = Rarity.MYTHIC, essence: int | None = None) -> int:
    realm = await seed_realm(database, rarity=rarity)
    async with database.write() as session:
        await ensure_ladder(session, Rules())
        if essence is not None:
            son = await session.get(SonRow, realm.son_id)
            assert son is not None
            son.essence = essence
    return realm.son_id


async def essence_of(database: Database, son_id: int) -> int:
    async with database.read() as session:
        son = await session.get(SonRow, son_id)
        assert son is not None
        return son.essence


async def count(database: Database, table: type[GalaxyRow] | type[ClusterRow] | type[DimensionRow]) -> int:
    async with database.read() as session:
        return int(await session.scalar(select(func.count()).select_from(table)) or 0)


def test_each_greater_scale_costs_a_son_more() -> None:
    rules = Rules()
    assert rules.cosmic_costs.ignite_star * rules.son_tools.cosmic_hang_star_pct // 100 < rules.galaxies.create_essence
    assert rules.galaxies.create_essence < rules.clusters.create_essence < rules.dimensions.create_essence
    assert rules.son_tools.hang_star_ap < rules.son_tools.create_galaxy_ap < rules.son_tools.create_cluster_ap <= rules.son_tools.create_dimension_ap
    assert rules.cosmic_costs.create_galaxy < rules.cosmic_costs.create_cluster < rules.cosmic_costs.create_dimension
    assert min(rules.rarity_gates.galaxy_creation, rules.rarity_gates.cluster_creation, rules.rarity_gates.dimension_creation) >= rules.rarity_gates.birth_world


async def test_a_son_pays_for_a_galaxy_and_becomes_its_patron(database: Database) -> None:
    son_id = await laddered(database)
    before = await essence_of(database, son_id)
    toolkit = await son_toolkit(database, son_id, action_points=10)
    await ok(toolkit, "create_galaxy", GALAXY)
    assert before - await essence_of(database, son_id) == Rules().galaxies.create_essence
    async with database.read() as session:
        galaxy = await session.scalar(select(GalaxyRow).where(GalaxyRow.name == GALAXY["name"]))
        assert galaxy is not None
        assert galaxy.patron_son_id == son_id and galaxy.description == GALAXY["description"]


async def test_a_son_pays_for_a_cluster_and_a_dimension_it_then_rules(database: Database) -> None:
    son_id = await laddered(database, essence=Rules().clusters.create_essence + Rules().dimensions.create_essence)
    toolkit = await son_toolkit(database, son_id, action_points=10)
    await ok(toolkit, "create_cluster", CLUSTER)
    await ok(toolkit, "create_dimension", DIMENSION)
    assert await essence_of(database, son_id) == 0
    async with database.read() as session:
        dimension = await session.scalar(select(DimensionRow).where(DimensionRow.name == DIMENSION["name"]))
        assert dimension is not None and dimension.ruler_node_id == son_id
        assert await session.scalar(select(ClusterRow).where(ClusterRow.name == CLUSTER["name"])) is not None


async def test_a_son_short_of_essence_makes_nothing(database: Database) -> None:
    son_id = await laddered(database, essence=Rules().galaxies.create_essence - 1)
    galaxies = await count(database, GalaxyRow)
    toolkit = await son_toolkit(database, son_id, action_points=10)
    await rejected(toolkit, "create_galaxy", GALAXY)
    assert await count(database, GalaxyRow) == galaxies


async def test_a_son_below_the_gate_makes_no_galaxy(database: Database) -> None:
    son_id = await laddered(database, rarity=Rarity.LEGENDARY)
    galaxies = await count(database, GalaxyRow)
    toolkit = await son_toolkit(database, son_id, action_points=10)
    await rejected(toolkit, "create_galaxy", GALAXY)
    assert await count(database, GalaxyRow) == galaxies


async def test_a_son_cannot_spend_more_actions_than_a_galaxy_needs(database: Database) -> None:
    son_id = await laddered(database)
    galaxies = await count(database, GalaxyRow)
    toolkit = await son_toolkit(database, son_id, action_points=Rules().son_tools.create_galaxy_ap - 1)
    await rejected(toolkit, "create_galaxy", GALAXY)
    assert await count(database, GalaxyRow) == galaxies


def test_works_on_the_heavens_need_the_highest_sons_and_cost_less_than_making_a_galaxy() -> None:
    rules = Rules()
    gates = rules.rarity_gates
    assert min(gates.galactic_works, gates.dimensional_works) >= gates.cosmic_works >= gates.power_sites
    tools = rules.son_tools
    works = (tools.shape_structure_essence, tools.stir_galaxy_essence, tools.cosmic_feature_essence, tools.star_system_essence, tools.stir_dimension_essence)
    assert max(works) < rules.galaxies.create_essence
    assert tools.dimension_law_essence < rules.dimensions.create_essence


async def test_a_son_below_the_gate_cannot_stir_a_galaxy(database: Database) -> None:
    son_id = await laddered(database, rarity=Rarity.LEGENDARY)
    async with database.read() as session:
        galaxy = await session.scalar(select(GalaxyRow.id).limit(1))
    assert galaxy is not None
    toolkit = await son_toolkit(database, son_id, action_points=10)
    assert not toolkit.runtime.has("stir_galaxy")
    await rejected(toolkit, "stir_galaxy", {"galaxy_id": galaxy, "kind": "starburst", "reason": "the stars should burn brighter"})
