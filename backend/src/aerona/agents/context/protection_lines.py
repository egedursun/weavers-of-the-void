from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.protected_nature import ProtectedAreaRow, SpeciesProtectionRow
from aerona.engine.primitives.distance import RegionAtlas


async def mortal_protection_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    region = (await RegionAtlas.load(session)).top_region(me.location_id) if me.location_id is not None else None
    if region is None:
        return []
    found: list[str] = []
    areas = select(ProtectedAreaRow).where(ProtectedAreaRow.region_entity_id == region, ProtectedAreaRow.lifted_epoch.is_(None))
    for area in await session.scalars(areas.order_by(ProtectedAreaRow.id)):
        barred = ", ".join(spoken(use) for use in area.banned_uses or []) or "nothing"
        found.append(f"your land is protected by {spoken(area.basis)} against {barred}, strength {area.strength}, poaching {area.poaching}")
    kinds = sorted(set(await session.scalars(select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id == region))))
    if kinds:
        for row in await session.scalars(
            select(SpeciesProtectionRow).where(SpeciesProtectionRow.species_entity_id.in_(kinds)).order_by(SpeciesProtectionRow.id)
        ):
            measures = ", ".join(spoken(measure) for measure in row.measures or []) or "no measures"
            found.append(f"{await named(scope, row.species_entity_id)} (kind {row.species_entity_id}) is protected: {measures}")
    return found
