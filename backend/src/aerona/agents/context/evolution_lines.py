from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.catalog.disease_agents import AGENTS, CURE_LABELS
from aerona.catalog.spread_paths import SPREAD_PATHS
from aerona.core.grammar import an, spoken
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.disease_agents import DiseaseAgentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import CarrierRow, CureResearchRow, LineageMarkRow, PlagueResponseRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.disease import OutbreakStatus
from aerona.engine.disease.research import institutions
from aerona.engine.primitives.queries import top_region


async def son_evolution_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for mark in await session.scalars(select(LineageMarkRow).where(LineageMarkRow.source_node_id == son.id).order_by(LineageMarkRow.species_entity_id)):
        species = await session.get(EntityRow, mark.species_entity_id)
        if species is not None:
            word = "blessed" if mark.blessing else "tainted"
            found.append(f"You {word} the line of {species.name}; its young carry the {spoken(mark.package)}")
    return found


async def mortal_evolution_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for carrier in await session.scalars(select(CarrierRow).where(CarrierRow.mortal_entity_id == me.id, CarrierRow.identified.is_(True))):
        disease = await session.get(EntityRow, carrier.disease_entity_id)
        if disease is not None:
            found.append(f"physicians found that you carry {disease.name} without falling ill")
    home = me.location_id
    if home is None:
        return found
    for response in await session.scalars(
        select(PlagueResponseRow).where(PlagueResponseRow.community_entity_id == home).order_by(PlagueResponseRow.disease_entity_id)
    ):
        disease = await session.get(EntityRow, response.disease_entity_id)
        if disease is not None:
            found.append(f"your community answers {disease.name}: {spoken(response.response)} ({response.strength})")
    seats = [row for row in await institutions(session) if row.location_id == home]
    for seat in seats:
        for research in await session.scalars(select(CureResearchRow).where(CureResearchRow.institution_entity_id == seat.id)):
            disease = await session.get(EntityRow, research.disease_entity_id)
            if disease is None:
                continue
            state = (
                f"found in epoch {research.cured_epoch}" if research.cured_epoch is not None else f"{research.points} of {scope.rules.cure_research.threshold}"
            )
            found.append(f"{seat.name} seeks a cure for {disease.name}: {state}")
    found.extend(await agent_lines(scope, me))
    return found


async def agent_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    region = await top_region(session, me)
    if region is None:
        return []
    found: list[str] = []
    sick = await session.execute(
        select(OutbreakRow.disease_entity_id, OutbreakRow.path)
        .where(OutbreakRow.region_entity_id == region.id, OutbreakRow.status == OutbreakStatus.ACTIVE)
        .order_by(OutbreakRow.id)
    )
    paths = {disease_id: path for disease_id, path in sick}
    for disease_id in sorted(paths):
        disease = await session.get(EntityRow, disease_id)
        agent = await session.get(DiseaseAgentRow, disease_id)
        if disease is None or agent is None:
            continue
        found.append(f"{disease.name} came here: {SPREAD_PATHS[paths[disease_id]].label.lower()}")
        if not agent.identified:
            found.append(f"no healer yet knows what {disease.name} is")
            continue
        cures = ", ".join(CURE_LABELS[cure].lower() for cure in sorted(AGENTS[agent.agent].cures))
        found.append(f"{disease.name} is {an(AGENTS[agent.agent].label.lower())}; cures that work on it: {cures}")
    return found
