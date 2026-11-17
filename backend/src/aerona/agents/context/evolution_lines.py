from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import CarrierRow, CureResearchRow, LineageMarkRow, PlagueResponseRow
from aerona.db.tables.sons import SonRow
from aerona.engine.disease.research import institutions


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
    return found
