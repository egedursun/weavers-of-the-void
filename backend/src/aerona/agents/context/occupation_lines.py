from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import OccupationRow
from aerona.db.tables.occupation_regimes import OccupationRegimeRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.occupation_regime.effects import active_measures, serving
from aerona.engine.primitives.distance import RegionAtlas


async def regime_line(scope: Scope, regime: OccupationRegimeRow) -> str:
    session = scope.session
    occupation = await session.get(OccupationRow, regime.region_entity_id)
    hold = f", control {occupation.control}, resistance {occupation.resistance}" if occupation is not None else ""
    measures = ", ".join(f"{spoken(row.measure)} {row.strength}" for row in await active_measures(session, regime.id)) or "no measures"
    helpers = ", ".join(
        [f"{await named(scope, row.collaborator_node_id)} in {spoken(row.kind)} (service {row.id})" for row in await serving(session, regime.id)]
    )
    region, occupier = await named(scope, regime.region_entity_id), await named(scope, regime.occupier_entity_id)
    ruled = f"under {spoken(regime.rule)} rule, taking {regime.tax_pct} of its taxes{hold}"
    return f"occupation {regime.id} of {region} by {occupier} {ruled}; {measures}; serving it: {helpers or 'no one'}"


async def mortal_occupation_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    ruled = set(await session.scalars(select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == me.id, OfficeRow.kind == OfficeKind.RULER)))
    home = await session.get(EntityRow, me.location_id) if me.location_id is not None else None
    region = (await RegionAtlas.load(session)).top_region(home.id) if home is not None else None
    query = select(OccupationRegimeRow).where(OccupationRegimeRow.ended_epoch.is_(None))
    return [
        await regime_line(scope, regime)
        for regime in await session.scalars(query.order_by(OccupationRegimeRow.id))
        if regime.occupier_entity_id in ruled or regime.region_entity_id == region
    ]
