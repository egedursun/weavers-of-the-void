from aerona.agents.celestial_deepener import deepen_celestial
from aerona.agents.runtime import AgentRuntime
from aerona.db.base import Base
from aerona.db.session import Database
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalaxyRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.cosmography import ClusterKind, DimensionKind, GalaxyType
from aerona.engine.cosmos.ladder import ClusterDraft, DimensionDraft, GalaxyDraft, create_cluster, create_dimension, create_galaxy
from aerona.prompts import PromptId
from aerona.prompts.contexts.narrative import CelestialKind
from aerona.rules.registry import Rules
from tests.agents.fakes import FakeModel
from tests.agents.test_roles import payload
from tests.agents.world import AgentWorld

DEEPENED_ELSEWHERE = {EntityRow, SonRow, ForeignGodRow, CreatorRow}


async def test_a_world_and_its_star_are_deepened(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld) -> None:
    deep = payload(PromptId.DEEPEN_CELESTIAL_USER, history="The sea came first.")
    model.script(type(deep), deep)
    depth = await deepen_celestial(runtime, CelestialKind.WORLD, world.core.world.id)
    assert depth.history == "The sea came first."
    model.script(type(deep), deep)
    star_id = world.core.world.star_id
    assert star_id is not None
    await deepen_celestial(runtime, CelestialKind.STAR, star_id)
    async with database.read() as session:
        stored_world = await session.get(WorldRow, world.core.world.id)
        stored_star = await session.get(StarRow, star_id)
    assert stored_world is not None and stored_world.depth is not None
    assert stored_star is not None and stored_star.depth is not None and stored_star.depth.rumours


async def test_every_scale_of_the_heavens_is_deepened(runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld, rules: Rules) -> None:
    async with database.write() as session:
        dimension = await create_dimension(session, rules, DimensionDraft("Reach", DimensionKind.ASTRAL, 1))
        cluster = await create_cluster(session, rules, ClusterDraft("Gathering", ClusterKind.LOCAL_GROUP, 1, dimension_id=dimension.id))
        galaxy = await create_galaxy(session, rules, GalaxyDraft("Wheel", GalaxyType.SPIRAL, 1, cluster_id=cluster.id))
        targets = (
            (CelestialKind.DIMENSION, DimensionRow, dimension.id),
            (CelestialKind.CLUSTER, ClusterRow, cluster.id),
            (CelestialKind.GALAXY, GalaxyRow, galaxy.id),
        )
    for kind, table, node_id in targets:
        deep = payload(PromptId.DEEPEN_CELESTIAL_USER, history=f"The {kind.value} came first.")
        model.script(type(deep), deep)
        depth = await deepen_celestial(runtime, kind, node_id)
        assert depth.history == f"The {kind.value} came first."
        async with database.read() as session:
            row = await session.get(table, node_id)
        assert row is not None and row.depth is not None and row.depth.rumours


def test_every_kind_that_has_depth_can_be_deepened() -> None:
    tables = {mapper.class_ for mapper in Base.registry.mappers if "depth" in mapper.columns and issubclass(mapper.class_, NodeRow)}
    deepened = {WorldRow, StarRow, GalaxyRow, ClusterRow, DimensionRow, *DEEPENED_ELSEWHERE}
    assert tables <= deepened, sorted(table.__name__ for table in tables - deepened)
    assert {kind.value for kind in CelestialKind} == {"world", "star", "galaxy", "cluster", "dimension"}
