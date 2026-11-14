from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import an
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.nature import SpeciesRelationRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.nature import Dormancy, Thermoregulation
from aerona.engine.nature.effects import folk_warmth
from aerona.engine.nature.microbes import keepers_in, live_cultures
from aerona.engine.nature.seasons import asleep, band_at, season_bands
from aerona.engine.nature.senses import sense_holder, senses_of

LIST_LINES = 3


async def mortal_nature_lines(scope: Scope, me: EntityRow) -> list[str]:
    session, rules = scope.session, scope.rules
    found = []
    holder = await sense_holder(session, me.id)
    keen = sorted(((acuity, sense) for sense, acuity in (await senses_of(session, holder)).items()), reverse=True) if holder is not None else []
    if keen:
        found.append("your people's keenest senses: " + ", ".join(f"{sense.value.replace('_', ' ')} {acuity}" for acuity, sense in keen[:LIST_LINES]))
    if await folk_warmth(session, me.id) is Thermoregulation.ECTOTHERM:
        band = await band_at(session, rules, scope.epoch, me.id)
        found.append(f"your people are cold-blooded; this season the land is {band.value if band is not None else 'of no known warmth'}")
    if me.location_id is not None:
        for row in await live_cultures(session, await keepers_in(session, me.location_id)):
            found.append(f"{an(row.kind.value)} culture is kept here (record {row.id}, quality {row.quality})")
    return found


async def son_nature_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    session = scope.session
    bands = await season_bands(session, scope.rules, scope.epoch)
    kinds = select(EntityRow.id).where(EntityRow.world_id == son.current_world_id, EntityRow.status == EntityStatus.CANON)
    found = []
    sleeping = []
    for profile in await session.scalars(
        select(SpeciesProfileRow)
        .where(SpeciesProfileRow.dormancy != Dormancy.NONE, SpeciesProfileRow.species_entity_id.in_(kinds))
        .order_by(SpeciesProfileRow.species_entity_id)
    ):
        lands = await session.scalars(select(SpeciesRangeRow.region_entity_id).where(SpeciesRangeRow.species_entity_id == profile.species_entity_id))
        if any(asleep(profile.dormancy, bands.get(region)) for region in lands):
            sleeping.append(await named(scope, profile.species_entity_id))
    if sleeping:
        found.append("kinds asleep this season: " + ", ".join(sleeping[:LIST_LINES]))
    for row in await session.scalars(
        select(SpeciesRelationRow)
        .where(SpeciesRelationRow.first_species_id.in_(kinds))
        .order_by(SpeciesRelationRow.strength.desc(), SpeciesRelationRow.id)
        .limit(LIST_LINES)
    ):
        found.append(f"{await named(scope, row.first_species_id)} and {await named(scope, row.second_species_id)} are bound by {row.kind.value}")
    return found
