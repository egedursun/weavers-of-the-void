from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sea_waves import SeaWaveCoastRow, SeaWaveRow, WaveWarningRow
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.sea_waves.sea import coasts_of, sea_of

RECENT = 2


async def mortal_wave_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    atlas = await RegionAtlas.load(session)
    region = atlas.top_region(me.id)
    if region is None:
        return []
    found: list[str] = []
    waters = [other for other in atlas.neighbours(region) if atlas.is_water(other)]
    if waters and region in coasts_of(atlas, sea_of(atlas, waters[0])):
        found.append(f"you live on the coast of {await named(scope, region)}, beside the sea; you may warn it of waves (region {region})")
    struck = select(SeaWaveCoastRow).where(SeaWaveCoastRow.region_entity_id == region).order_by(SeaWaveCoastRow.id)
    for row in await session.scalars(struck):
        wave = await session.get(SeaWaveRow, row.wave_id)
        if wave is None or wave.epoch < scope.epoch - RECENT:
            continue
        warned = ", and you were warned" if row.warned else ""
        salted = ", salting the land" if row.salted else ""
        found.append(f"a wave raised by {spoken(wave.origin)} struck here {row.height} high, {row.dead} dead{warned}{salted}")
    for warning in await session.scalars(select(WaveWarningRow).where(WaveWarningRow.region_entity_id == region, WaveWarningRow.until_epoch >= scope.epoch)):
        found.append(f"this coast is warned of waves by {spoken(warning.method)} until epoch {warning.until_epoch}")
    return found
