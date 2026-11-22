from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.celestial import WorldMapRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.forecasting import ObservationMethodRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.sea_waves import SeaWaveCoastRow, SeaWaveRow, WaveWarningRow
from aerona.db.tables.water import CoastRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.folk_knowledge import FolkDomain
from aerona.domain.enums.forecasting import ObservationMethod
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.sea_waves import WaveOrigin
from aerona.domain.enums.water import CoastForm
from aerona.engine.context import TickContext
from aerona.engine.phases.disasters import apply_disaster
from aerona.engine.primitives.manual import manual_context
from aerona.engine.sea_waves.waves import raise_wave
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, settlement, surveyed, tuned_rules


@dataclass
class Blow:
    dead: list[EntityRow] = field(default_factory=list)


@dataclass
class Recorder:
    blows: dict[int, float] = field(default_factory=dict)

    async def __call__(self, ctx: TickContext, target: EntityRow, disaster: Disaster, severity: float) -> Blow:
        assert disaster is Disaster.FLOOD
        self.blows[target.id] = severity
        return Blow()


async def with_sea(session: AsyncSession, world: CoreWorld) -> None:
    row = await session.scalar(select(WorldMapRow).where(WorldMapRow.world_id == world.world.id))
    assert row is not None
    water = world.regions[2].id
    row.geometry = {"regions": [region | {"is_water": region["id"] == water} for region in row.geometry["regions"]]}
    await session.flush()


def rules_with(**values: int) -> Rules:
    return tuned_rules(sea_waves={"decay_per_hop": 15, "floor": 10, "harm_per_height": 5, "salt_height": 200, **values})


async def test_a_wave_strikes_every_coast_of_its_sea_lower_the_further_it_runs(session: AsyncSession, world: CoreWorld) -> None:
    await with_sea(session, world)
    ctx = await manual_context(session, "wave", rules_with())
    strike = Recorder()
    wave = await raise_wave(ctx, world.regions[1].id, WaveOrigin.QUAKE, 0.8, strike=strike, sure=True)
    assert wave is not None and wave.strength == 80 and wave.sea_region_id == world.regions[2].id
    coasts = {row.region_entity_id: row for row in await session.scalars(select(SeaWaveCoastRow).where(SeaWaveCoastRow.wave_id == wave.id))}
    near, far = coasts[world.regions[1].id], coasts[world.regions[3].id]
    assert near.height == 80 and far.height == 50 and far.delay == 2 and world.regions[0].id not in coasts
    assert abs(strike.blows[world.regions[1].id] - 0.8) < 1e-9
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "land.sea_wave")) is not None


async def test_a_warned_coast_suffers_less_and_a_high_wave_salts_the_land(session: AsyncSession, world: CoreWorld) -> None:
    await with_sea(session, world)
    await surveyed(session, world)
    ctx = await manual_context(session, "warned", rules_with(warning_death_cut_pct=50, salt_height=60, salt_fertility=10))
    near = world.regions[1].id
    session.add(WaveWarningRow(region_entity_id=near, method=ObservationMethod.SIGHT, epoch=ctx.epoch, until_epoch=ctx.epoch, locked=[]))
    ground = await session.get(RegionEnvironmentRow, near)
    assert ground is not None
    before = ground.soil_fertility
    strike = Recorder()
    await raise_wave(ctx, near, WaveOrigin.DIVINE, 1.0, strike=strike, sure=True)
    row = await session.scalar(select(SeaWaveCoastRow).where(SeaWaveCoastRow.region_entity_id == near))
    assert row is not None and row.warned and row.salted and abs(strike.blows[near] - 0.5) < 1e-9
    assert ground.soil_fertility == max(0, before - 10)


async def test_a_world_without_seas_sends_no_wave(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "dry", rules_with())
    assert await raise_wave(ctx, world.regions[1].id, WaveOrigin.QUAKE, 1.0, strike=Recorder(), sure=True) is None


async def test_a_weak_storm_drives_no_surge_and_a_strong_one_does(session: AsyncSession, world: CoreWorld) -> None:
    await with_sea(session, world)
    ctx = await manual_context(session, "surge", rules_with(storm_surge_chance_pct=100, storm_floor_pct=50))
    assert await raise_wave(ctx, world.regions[1].id, WaveOrigin.STORM, 0.3, strike=Recorder()) is None
    assert await raise_wave(ctx, world.regions[3].id, WaveOrigin.STORM, 1.0, strike=Recorder()) is not None


async def test_a_quake_beside_the_sea_raises_a_wave_through_the_disaster_itself(session: AsyncSession, world: CoreWorld) -> None:
    await with_sea(session, world)
    ctx = await manual_context(session, "quake", rules_with(quake_wave_chance_pct=100))
    region = await session.get(EntityRow, world.regions[3].id)
    assert region is not None
    await apply_disaster(ctx, region, Disaster.EARTHQUAKE, 1.0)
    wave = await session.scalar(select(SeaWaveRow))
    assert wave is not None and wave.origin is WaveOrigin.QUAKE and wave.origin_region_id == region.id


async def test_a_people_that_watches_the_waters_gives_a_warning_that_is_kept(session: AsyncSession, world: CoreWorld) -> None:
    await with_sea(session, world)
    ctx = await manual_context(session, "watch", rules_with(observation_floor=40))
    near = world.regions[1].id
    town = await settlement(session, "Watchharbour", world, world.regions[1])
    await BondRepository(session).connect(BondDraft(world.people.id, town.id, BondKind.LIVES_IN, 0, role=BondRole.HOMELAND))
    session.add(ObservationMethodRow(people_entity_id=world.people.id, domain=FolkDomain.WATERS, method=ObservationMethod.SIGHT, accuracy=70))
    await session.flush()
    await raise_wave(ctx, near, WaveOrigin.DIVINE, 1.0, strike=Recorder(), sure=True)
    row = await session.scalar(select(SeaWaveCoastRow).where(SeaWaveCoastRow.region_entity_id == near))
    warning = await session.scalar(select(WaveWarningRow).where(WaveWarningRow.region_entity_id == near))
    assert row is not None and row.warned
    assert warning is not None and warning.method is ObservationMethod.SIGHT and warning.by_node_id == world.people.id
    assert warning.until_epoch == ctx.epoch + ctx.rules.sea_waves.warning_epochs


async def test_a_world_mapped_without_open_water_still_sends_a_wave_along_its_coasts(session: AsyncSession, world: CoreWorld) -> None:
    for region in world.regions[:2]:
        session.add(CoastRow(region_entity_id=region.id, form=next(iter(CoastForm))))
    await session.flush()
    ctx = await manual_context(session, "coastal", rules_with())
    wave = await raise_wave(ctx, world.regions[0].id, WaveOrigin.QUAKE, 0.8, strike=Recorder(), sure=True)
    assert wave is not None and wave.sea_region_id is None
    struck = set(await session.scalars(select(SeaWaveCoastRow.region_entity_id).where(SeaWaveCoastRow.wave_id == wave.id)))
    assert struck == {world.regions[0].id, world.regions[1].id}
