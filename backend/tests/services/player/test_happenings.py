import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.happenings import EventCasualtyRow, EventFootprintRow, EventProfileRow, RegionGeomorphRow
from aerona.domain.enums.demography import AgeBand, Sex
from aerona.domain.enums.entity import EngineKind, EntityStatus
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TemperatureBand, TerrainKind
from aerona.domain.enums.happening import EventPhase
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.society import SocialClass
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import happenings
from aerona.services.player.catalog import ACTIONS_BY_ID
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld

LEVERS = (
    "event:create",
    "event:edit",
    "event:phase",
    "event:release",
    "event:footprint",
    "event:casualties",
    "event:end",
    "land:stir",
    "land:river",
    "land:shape",
    "land:release",
)


async def _undo(session: AsyncSession, entry_id: int | None, epoch: int) -> list[str]:
    assert entry_id is not None
    changes = await changes_of(session, entry_id)
    report = await UndoRun(session, epoch, changes, label_names(changes, await node_names(session, changes))).run()
    return report.conflicts


async def _ground(session: AsyncSession, world: PlayerWorld) -> RegionEnvironmentRow:
    row = RegionEnvironmentRow(
        entity_id=world.region.id,
        world_id=world.world.id,
        biome_mix=[0, 0, 0, 0, 100, 0, 0, 0, 0, 0],
        dominant_terrain=TerrainKind.PLAIN,
        elevation_mean=20,
        roughness=30,
        latitude=30,
        moisture=50,
        base_forest=20,
        forest_cover=20,
        base_wetland=10,
        wetland=10,
        river_class=RiverClass.RIVER,
        coast_kind=CoastKind.NONE,
        soil=SoilKind.LOAM,
        soil_fertility=60,
        soil_base=60,
        temperature=50,
        temperature_band=TemperatureBand.TEMPERATE,
        rainfall=50,
        seasonality=20,
        disease_load=10,
        magic_density=10,
        defensibility=20,
    )
    session.add(row)
    await session.flush()
    return row


def test_every_event_and_land_lever_is_in_the_catalog() -> None:
    assert [lever for lever in LEVERS if lever not in ACTIONS_BY_ID] == []


async def test_an_event_is_created_held_released_and_ended(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await _ground(session, world)
    outcome = await happenings.create_event(
        scope, happenings.CreateEvent(kind=EngineKind.FESTIVAL_OF_NOTE, where_id=world.region.id, name="the Feast of Lanterns", severity=40, start_year=5)
    )
    event_id = outcome.created_ids[0]
    event = await session.get(EntityRow, event_id)
    profile = await session.get(EventProfileRow, event_id)
    assert event is not None and event.engine_kind is EngineKind.FESTIVAL_OF_NOTE
    assert profile is not None and profile.start_year == 5 and profile.incident_id is not None
    footprint = list(await session.scalars(select(EventFootprintRow.region_entity_id).where(EventFootprintRow.event_entity_id == event_id)))
    assert footprint == [world.region.id]
    await happenings.set_event_phase(scope, happenings.EventPhaseCommand(event_id=event_id, phase=EventPhase.PEAK, hold=True))
    assert profile.phase is EventPhase.PEAK and "phase" in profile.locked
    await happenings.release_event(scope, happenings.EventRelease(event_id=event_id, field="phase"))
    assert "phase" not in profile.locked
    await happenings.edit_event(scope, happenings.EditEvent(event_id=event_id, values={"end_year": 9, "severity": 70}))
    assert profile.end_year == 9 and "end_year" in profile.locked
    with pytest.raises(ValidationFailedError):
        await happenings.edit_event(scope, happenings.EditEvent(event_id=event_id, values={"end_year": 1}))
    await happenings.set_event_casualties(
        scope,
        happenings.EventCasualties(
            event_id=event_id, community_id=world.region.id, age_band=AgeBand.ADULT, sex=Sex.MALE, social_class=SocialClass.FARMER, count=12
        ),
    )
    assert sum(row.count for row in await session.scalars(select(EventCasualtyRow).where(EventCasualtyRow.event_entity_id == event_id))) == 12
    await happenings.end_event(scope, happenings.EventTarget(event_id=event_id))
    assert profile.end_epoch is not None and profile.phase is EventPhase.AFTERMATH


async def test_creating_an_event_is_undoable(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await _ground(session, world)
    outcome = await happenings.create_event(scope, happenings.CreateEvent(kind=EngineKind.RIOT, where_id=world.region.id, severity=30))
    event_id = outcome.created_ids[0]
    assert await _undo(session, outcome.ledger_entry_id, world.cosmos.epoch) == []
    session.expire_all()
    assert await session.scalar(select(EventProfileRow).where(EventProfileRow.entity_id == event_id)) is None
    assert await session.scalar(select(EntityRow.status).where(EntityRow.id == event_id)) is EntityStatus.REJECTED


async def test_a_land_is_parched_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    ground = await _ground(session, world)
    await happenings.shape_land(scope, happenings.ShapeLand(region_id=world.region.id, desertification=80, desertified=True))
    shape = await session.get(RegionGeomorphRow, world.region.id)
    assert shape is not None and shape.desertified and set(shape.locked) == {"desertification", "desertified"}
    assert ground.dominant_terrain is TerrainKind.DESERT
    await happenings.release_land(scope, happenings.ReleaseLand(region_id=world.region.id, field="desertified"))
    assert shape.locked == ["desertification"]
    with pytest.raises(ValidationFailedError):
        await happenings.shape_land(scope, happenings.ShapeLand(region_id=world.region.id))


async def test_only_volcanic_disasters_are_stirred(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    ground = await _ground(session, world)
    with pytest.raises(ValidationFailedError):
        await happenings.stir_land(scope, happenings.StirLand(region_id=world.region.id, disaster=Disaster.FLOOD))
    outcome = await happenings.stir_land(scope, happenings.StirLand(region_id=world.region.id, disaster=Disaster.ERUPTION, severity=70))
    event = await session.get(EntityRow, outcome.created_ids[0])
    assert event is not None and event.engine_kind is EngineKind.ERUPTION and ground.soil is SoilKind.ASH


async def test_a_river_without_a_neighbour_cannot_move(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await _ground(session, world)
    with pytest.raises(ValidationFailedError):
        await happenings.move_river(scope, happenings.MoveRiver(from_region_id=world.region.id))
