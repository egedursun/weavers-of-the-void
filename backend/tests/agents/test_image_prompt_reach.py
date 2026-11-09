from sqlalchemy import select

from aerona.agents.image_prompter import COSMIC_TABLES, missing_cosmos_prompts
from aerona.agents.runtime import AgentRuntime
from aerona.db.session import Database
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalaxyRow
from aerona.domain.enums.cosmography import ClusterKind, DimensionKind, GalaxyType
from aerona.domain.enums.node import NodeKind
from aerona.engine.cosmos.ladder import ClusterDraft, DimensionDraft, GalaxyDraft, create_cluster, create_dimension, create_galaxy
from aerona.prompts import PromptId, output_model
from aerona.prompts.catalog import render
from aerona.prompts.contexts.imagery import CosmosImagePromptsContext, CosmosSubject
from aerona.prompts.data.images import COSMOS_DIRECTION, CosmosSubjectKind
from aerona.rules.registry import Rules
from aerona.services.images.records import PROMPT_TABLES
from tests.agents.fakes import FakeModel
from tests.agents.world import AgentWorld

PROMPTED_ELSEWHERE = frozenset({NodeKind.ENTITY})


def test_every_kind_that_takes_an_image_can_be_given_a_prompt() -> None:
    missing = [
        kind.value
        for kind in PROMPT_TABLES
        if kind not in PROMPTED_ELSEWHERE
        and (
            kind.value not in {item.value for item in CosmosSubjectKind}
            or COSMIC_TABLES.get(CosmosSubjectKind(kind.value)) is not PROMPT_TABLES[kind]
            or CosmosSubjectKind(kind.value) not in COSMOS_DIRECTION
        )
    ]
    assert missing == []


def test_the_prompt_guides_every_cosmic_kind() -> None:
    rules = Rules()
    subjects = [
        CosmosSubject(number=index + 1, kind=kind, type_label="Kind", name=f"Name {index}", description="An account.")
        for index, kind in enumerate(CosmosSubjectKind)
    ]
    text = render(PromptId.COSMOS_IMAGE_PROMPTS_USER, CosmosImagePromptsContext(rules=rules, world_name="W", cosmology="C", tone="T", subjects=subjects))
    assert all(COSMOS_DIRECTION[subject.kind] in text and f"no {subject.number}:" in text for subject in subjects)


async def test_galaxies_clusters_and_dimensions_get_image_prompts(
    runtime: AgentRuntime, model: FakeModel, database: Database, world: AgentWorld, rules: Rules
) -> None:
    async with database.write() as session:
        dimension = await create_dimension(session, rules, DimensionDraft("Reach", DimensionKind.ASTRAL, 1))
        cluster = await create_cluster(session, rules, ClusterDraft("Gathering", ClusterKind.LOCAL_GROUP, 1, dimension_id=dimension.id))
        galaxy = await create_galaxy(session, rules, GalaxyDraft("Wheel", GalaxyType.SPIRAL, 1, cluster_id=cluster.id))
        ids = [dimension.id, cluster.id, galaxy.id]
    output = output_model(PromptId.COSMOS_IMAGE_PROMPTS_USER)
    model.script(
        output, output.model_validate({"prompts": [{"number": number, "prompt": f"A wide view of subject {number} at its own scale"} for number in (1, 2, 3)]})
    )
    assert await missing_cosmos_prompts(runtime, ids) == 3
    async with database.read() as session:
        prompts = [
            await session.scalar(select(table.image_prompt).where(table.id == node_id))
            for table, node_id in ((DimensionRow, ids[0]), (ClusterRow, ids[1]), (GalaxyRow, ids[2]))
        ]
    assert all(prompts)
