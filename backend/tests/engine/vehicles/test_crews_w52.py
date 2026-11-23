import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.operations_lines import crew_lines
from aerona.agents.context.scope import load_scope
from aerona.catalog.operations import CREW_STATIONS
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.operations import ShipCrewRow
from aerona.db.tables.vehicles import VesselSectionRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.military import VesselStatus
from aerona.domain.enums.operations import CrewStation
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame, VehicleSection
from aerona.domain.models.entity_stats import VesselStats
from aerona.engine.context import TickContext
from aerona.engine.operations.control import set_crew
from aerona.engine.operations.crews import CREWS_FIXUP, backfill_crews, crew_power, fitted_stations, lives_saved, station_fits, storm_care
from aerona.engine.operations.sail import crews_of
from aerona.rules.registry import Rules
from aerona.services.integrity.w52_agent_f import misplaced_crews, strike_misplaced_crew
from tests.engine.core.factories import CoreWorld, entity

FLYING = frozenset({VehicleSection.COCKPIT, VehicleSection.ENGINE, VehicleSection.SENSORS, VehicleSection.NAVIGATION, VehicleSection.WARD})


async def vessel(
    session: AsyncSession, world: CoreWorld, name: str, crew: int, sections: frozenset[VehicleSection] = frozenset()
) -> tuple[EntityRow, VesselProfileRow]:
    body = await entity(session, name, EntityType.VESSEL, VesselStats(), world_id=world.world.id, location_id=world.regions[0].id)
    row = VesselProfileRow(entity_id=body.id, kind=VehicleKind.SHIP, crew=crew, cargo_capacity=50, condition=100, status=VesselStatus.AFLOAT, locked=[])
    session.add(row)
    for section in sorted(sections):
        session.add(VesselSectionRow(vessel_entity_id=body.id, section=section, locked=[]))
    await session.flush()
    return body, row


def test_every_station_has_its_catalogue_and_the_old_ones_need_no_section() -> None:
    assert set(CREW_STATIONS) == set(CrewStation)
    assert station_fits(CrewStation.GUNNERS, None, VehicleFrame.BOAT)
    assert not station_fits(CrewStation.PILOTS, None, VehicleFrame.BOAT)
    assert station_fits(CrewStation.ROWERS, None, VehicleFrame.GALLEY) and not station_fits(CrewStation.ROWERS, None, VehicleFrame.BOAT)
    assert station_fits(CrewStation.CASTERS, frozenset({VehicleSection.WARD}), VehicleFrame.BOAT)
    assert not station_fits(CrewStation.RIGGERS, frozenset({VehicleSection.ENGINE}), VehicleFrame.BOAT)


async def test_a_vessel_with_a_cockpit_engine_and_wards_is_crewed_by_its_sections_and_fights_harder_for_it(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    body, row = await vessel(session, world, "Kite", 60, FLYING)
    stations = await fitted_stations(session, body.id, row)
    assert {CrewStation.PILOTS, CrewStation.ENGINEERS, CrewStation.SENSOR_OPERATORS, CrewStation.CASTERS, CrewStation.NAVIGATORS} <= set(stations)
    assert CrewStation.RIGGERS not in stations and CrewStation.HANDLERS not in stations
    crews = await crews_of(ctx, body.id, row)
    assert set(crews) == set(stations)
    rules = Rules()
    for crew in crews.values():
        crew.skill = 100
    assert crew_power(rules, row, crews, stations) > 1 + rules.crews.pilots_effect / 100
    assert storm_care(rules, row, crews, stations, 100) > storm_care(rules, row, crews, stations, 0) == 0
    bare, bare_row = await vessel(session, world, "Plain", 60)
    plain = await crews_of(ctx, bare.id, bare_row)
    assert crew_power(rules, bare_row, plain, await fitted_stations(session, bare.id, bare_row)) < crew_power(rules, row, crews, stations)


async def test_medics_save_lives_and_a_station_no_section_calls_for_is_refused_and_struck(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    body, row = await vessel(session, world, "Lantern", 40, frozenset({VehicleSection.CREW_QUARTERS}))
    await set_crew(ctx, body.id, CrewStation.MEDICS, {"count": 10, "skill": 100})
    crews = await crews_of(ctx, body.id, row)
    assert lives_saved(Rules(), row, crews, await fitted_stations(session, body.id, row)) > 0
    with pytest.raises(ValidationFailedError):
        await set_crew(ctx, body.id, CrewStation.PILOTS, {"count": 3})
    session.add(ShipCrewRow(vessel_entity_id=body.id, station=CrewStation.HANDLERS, count=2, skill=40, locked=[]))
    await session.flush()
    assert await misplaced_crews(session) == [body.id]
    await strike_misplaced_crew(session, body.id)
    await session.flush()
    assert await misplaced_crews(session) == []


async def test_the_fixup_gives_old_vessels_the_crews_their_sections_call_for_once(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    body, _row = await vessel(session, world, "Old Kite", 50, FLYING)
    session.add(ShipCrewRow(vessel_entity_id=body.id, station=CrewStation.GUNNERS, count=20, skill=40, locked=[]))
    await session.flush()
    added = await backfill_crews(session)
    assert added >= 5 and await session.get(AppliedFixupRow, CREWS_FIXUP) is not None
    stations = set(await session.scalars(select(ShipCrewRow.station).where(ShipCrewRow.vessel_entity_id == body.id)))
    assert CrewStation.NAVIGATORS in stations and CrewStation.PILOTS in stations
    assert await backfill_crews(session) == 0


async def test_a_captain_reads_the_crew_and_the_stations_no_one_works(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    body, row = await vessel(session, world, "Wren", 30, FLYING)
    await set_crew(ctx, body.id, CrewStation.PILOTS, {"count": 4, "skill": 70})
    scope = await load_scope(session, Rules())
    lines = await crew_lines(scope, row)
    assert any("pilots 4 of skill 70" in line for line in lines)
    assert any("navigators" in line and "no one works" in line for line in lines)
