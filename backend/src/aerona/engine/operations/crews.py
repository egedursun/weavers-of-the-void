from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.operations import CLASSIC_STATIONS, CREW_STATIONS, FIGHTING_STATIONS, STORM_CARE
from aerona.catalog.vehicles import FRAMES
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.operations import ShipCrewRow
from aerona.domain.enums.operations import CrewStation
from aerona.domain.enums.vehicles import VehicleFrame, VehicleSection
from aerona.engine.vehicles.sections import design_sections, vessel_sections
from aerona.rules.registry import Rules

ROWED = frozenset({VehicleFrame.GALLEY, VehicleFrame.LONGSHIP})
CREWS_FIXUP = "crews.w52"
CARE_CAP = 0.9


async def present_sections(session: AsyncSession, vessel_id: int, row: VesselProfileRow) -> frozenset[VehicleSection] | None:
    own = await vessel_sections(session, vessel_id)
    if own:
        return frozenset(own)
    if row.design_id is not None:
        drawn = await design_sections(session, row.design_id)
        if drawn:
            return frozenset(drawn)
    return None


def station_fits(station: CrewStation, sections: frozenset[VehicleSection] | None, frame: VehicleFrame) -> bool:
    spec = CREW_STATIONS[station]
    if sections is None:
        return station in CLASSIC_STATIONS and (station is not CrewStation.ROWERS or frame in ROWED)
    return not spec.sections or bool(spec.sections & sections)


async def fitted_stations(session: AsyncSession, vessel_id: int, row: VesselProfileRow) -> list[CrewStation]:
    sections = await present_sections(session, vessel_id, row)
    return [station for station in CrewStation if station_fits(station, sections, row.frame)]


def manned(row: VesselProfileRow, crews: dict[CrewStation, ShipCrewRow], station: CrewStation, fitted: list[CrewStation]) -> float:
    crew = crews.get(station)
    if crew is None or crew.count <= 0 or station not in fitted:
        return 0.0
    weight = max(1, sum(CREW_STATIONS[item].share for item in fitted))
    needed = max(1, FRAMES[row.frame].crew * CREW_STATIONS[station].share // weight)
    return min(1.0, crew.count / needed) * crew.skill / PERCENT


def effect_of(rules: Rules, row: VesselProfileRow, crews: dict[CrewStation, ShipCrewRow], station: CrewStation, fitted: list[CrewStation]) -> float:
    return CREW_STATIONS[station].effect(rules) * manned(row, crews, station, fitted) / PERCENT


def crew_power(rules: Rules, row: VesselProfileRow, crews: dict[CrewStation, ShipCrewRow], fitted: list[CrewStation]) -> float:
    return 1 + sum(effect_of(rules, row, crews, station, fitted) for station in fitted if station in FIGHTING_STATIONS)


def storm_care(rules: Rules, row: VesselProfileRow, crews: dict[CrewStation, ShipCrewRow], fitted: list[CrewStation], accuracy: int) -> float:
    hands = sum(effect_of(rules, row, crews, station, fitted) for station in STORM_CARE)
    course = effect_of(rules, row, crews, CrewStation.NAVIGATORS, fitted) * accuracy / PERCENT
    return min(CARE_CAP, hands + course)


def lives_saved(rules: Rules, row: VesselProfileRow, crews: dict[CrewStation, ShipCrewRow], fitted: list[CrewStation]) -> float:
    return min(CARE_CAP, effect_of(rules, row, crews, CrewStation.MEDICS, fitted))


async def backfill_crews(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, CREWS_FIXUP) is not None:
        return 0
    added = 0
    for row in list(await session.scalars(select(VesselProfileRow).order_by(VesselProfileRow.entity_id))):
        fitted = await fitted_stations(session, row.entity_id, row)
        have = set(await session.scalars(select(ShipCrewRow.station).where(ShipCrewRow.vessel_entity_id == row.entity_id)))
        if not have:
            continue
        weight = max(1, sum(CREW_STATIONS[station].share for station in fitted))
        for station in fitted:
            if station in have:
                continue
            session.add(
                ShipCrewRow(
                    vessel_entity_id=row.entity_id, station=station, count=row.crew * CREW_STATIONS[station].share // weight, skill=row.seamanship, locked=[]
                )
            )
            added += 1
    session.add(AppliedFixupRow(key=CREWS_FIXUP, result={"crews": added}))
    await session.flush()
    return added
