from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.evolution import NEUTRAL
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.disease_agents import DiseaseAgentRow
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.domain.enums.disease_agents import DiseaseAgent
from aerona.domain.enums.ecology import DomesticationStage
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.engine.disease.control import DiseaseDesign, create_disease
from aerona.engine.ecology.evolution import Selection, live_traits, pressures, tell_shifts
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld
from tests.engine.core.living_kinds import kind, told

RULES = Rules()
E = EvolvedTrait


def selected(*, kept: bool = False, stricken: bool = False, hunted: bool = False) -> tuple[Selection, SpeciesRangeRow]:
    row = SpeciesRangeRow(species_entity_id=1, region_entity_id=10, abundance=50, hunted=0)
    selection = Selection(
        stored={(1, 10): {}},
        hunted_by={1: {2}} if hunted else {},
        present={(1, 10), (2, 10)} if hunted else {(1, 10)},
        stricken={(1, 10)} if stricken else set(),
        kept={1} if kept else set(),
    )
    return selection, row


def test_fifteen_traits_and_the_new_three_answer_their_pressures() -> None:
    assert len(EvolvedTrait) == 15
    profile = SpeciesProfileRow(stage=DomesticationStage.WILD, water_need=0)
    sick, row = selected(stricken=True)
    assert pressures(RULES, sick, row, profile, None)[E.DISEASE_RESISTANCE] == RULES.trait_evolution.resistance_gain
    wild, row = selected()
    kept, kept_row = selected(kept=True)
    assert pressures(RULES, wild, row, profile, None)[E.DOCILITY] < 0 < pressures(RULES, kept, kept_row, profile, None)[E.DOCILITY]
    preyed, preyed_row = selected(hunted=True)
    assert pressures(RULES, preyed, preyed_row, profile, None)[E.LONGEVITY] < 0 < pressures(RULES, wild, row, profile, None)[E.LONGEVITY]


async def test_a_long_lived_line_lives_longer_and_a_resistant_reservoir_drives_its_disease_harder(session: AsyncSession, world: CoreWorld) -> None:
    region = world.regions[0]
    elder = await kind(session, world, "Old Tortoise", region, 40, lifespan_years=20)
    ctx = await manual_context(session, "evolution")
    disease = await create_disease(
        ctx, region.id, DiseaseDesign(name=None, values={"primary_route": "bite", "target_functions": ["vital"]}, hold=False), son_id=None
    )
    session.add(DiseaseAgentRow(disease_entity_id=disease.id, agent=DiseaseAgent.PARASITE, reservoir_species_id=elder.id, locked=[]))
    await session.flush()
    sickness = await session.get(DiseaseProfileRow, disease.id)
    profile = await session.get(SpeciesProfileRow, elder.id)
    assert sickness is not None and profile is not None
    before = sickness.virulence
    await live_traits(ctx, {(elder.id, E.LONGEVITY): NEUTRAL + 30, (elder.id, E.DISEASE_RESISTANCE): NEUTRAL + 20}, {elder.id: profile})
    assert profile.lifespan_years == 21
    assert sickness.virulence == min(100, before + RULES.trait_evolution.virulence_answer)


async def test_a_trait_that_crosses_a_band_is_told(session: AsyncSession, world: CoreWorld) -> None:
    beast = await kind(session, world, "Drifting Elk", world.regions[0], 40)
    ctx = await manual_context(session, "evolution")
    await tell_shifts(ctx, {(beast.id, E.DOCILITY): 40}, {(beast.id, E.DOCILITY): 80})
    assert await told(session, "life.trait_shifted")
