from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.disease_agents import AGENT_OF_VECTOR, AGENTS
from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.disease_agents import DiseaseAgentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease import ClimateMoisture, OutbreakStatus, SpreadPath
from aerona.domain.enums.disease_agents import CureClass, DiseaseAgent
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import DiseaseStats
from aerona.engine.context import TickContext
from aerona.engine.disease.agents import AgentTally, apply_cure, cure_tried, keep_agents
from aerona.engine.primitives.stats import set_stats
from tests.engine.core.factories import CoreWorld, entity, settlement


async def sickness(session: AsyncSession, world: CoreWorld, vector: Transmission) -> EntityRow:
    disease = await entity(session, "Grey Cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    session.add(
        DiseaseProfileRow(
            disease_entity_id=disease.id,
            primary_route=vector,
            virulence=50,
            lethality=20,
            chronic_rate=10,
            incubation=1,
            affinity_moisture=ClimateMoisture.WET,
            immunity_epochs=2,
            mutation_rate=1,
            stigma=10,
            cure_level=9,
            locked=[],
        )
    )
    await session.flush()
    return disease


def test_every_agent_has_a_cure_and_every_vector_an_agent() -> None:
    assert all(spec.cures for spec in AGENTS.values())
    assert set(AGENT_OF_VECTOR) == set(Transmission)


async def test_a_disease_is_typed_by_its_vector_and_takes_its_agents_mutation(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    disease = await sickness(session, world, Transmission.INHALATION)
    await keep_agents(ctx, AgentTally())
    row = await session.get(DiseaseAgentRow, disease.id)
    profile = await session.get(DiseaseProfileRow, disease.id)
    assert row is not None and row.agent is DiseaseAgent.VIRUS
    assert profile is not None and profile.mutation_rate == ctx.rules.disease.mutation_virus_pct


async def test_a_rite_against_a_bacterium_fails_and_costs_trust_while_an_antimicrobial_eases_it(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    disease = await sickness(session, world, Transmission.WATER)
    town = await settlement(session, "Marrow", world, world.regions[0], piety=50)
    session.add(
        OutbreakRow(
            disease_entity_id=disease.id,
            region_entity_id=world.regions[0].id,
            path=SpreadPath.ORIGIN,
            severity=60,
            status=OutbreakStatus.ACTIVE,
            started_epoch=0,
            locked=[],
        )
    )
    await session.flush()
    await keep_agents(ctx, AgentTally())
    assert await apply_cure(ctx, town, disease.id, CureClass.RITE) is False
    assert await apply_cure(ctx, town, disease.id, CureClass.ANTIMICROBIAL) is True
    kinds = set(await session.scalars(select(IncidentRow.kind)))
    assert {"disease.wrong_cure", "disease.right_cure"} <= kinds


async def test_a_pious_community_answers_with_rites(world: CoreWorld, ctx: TickContext) -> None:
    set_stats(world.people, piety=ctx.rules.disease.rite_piety)
    row = DiseaseAgentRow(disease_entity_id=1, agent=DiseaseAgent.BACTERIUM, locked=[])
    assert cure_tried(ctx.rules, world.people, 9, row) is CureClass.RITE
