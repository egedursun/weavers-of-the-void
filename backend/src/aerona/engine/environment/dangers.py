from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.beast_tempers import HELD_TEMPERS
from aerona.catalog.terrain import terrains
from aerona.catalog.wind_belts import CURRENTS
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmography import PhenomenonFootprintRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.polity import PolityTerritoryRow
from aerona.db.tables.region import RegionDangerRow, RegionMemoryRow
from aerona.db.write_guard import held as frozen
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.ecology import BeastTemper, DomesticationStage
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.environment import CoastKind, ScarKind, SoilKind, TerrainKind, TerrainTrait
from aerona.domain.enums.region import DangerHarm, DangerOrigin, DangerSource
from aerona.engine.cosmos.kinds import PHENOMENON_MECHANICS
from aerona.engine.cosmos.placement import cosmography_of
from aerona.engine.cycles.hospitality import circuit_stops
from aerona.engine.ecology.ranges import wildness
from aerona.engine.environment.memory import darkness
from aerona.engine.environment.profile import RIVER_RANK
from aerona.engine.nature.symbiosis import mimics_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, fraction, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.primitives.thresholds import relative_threshold
from aerona.rules.registry import Rules

SNOW_TERRAIN = terrains(TerrainTrait.COLD, without=(TerrainTrait.OPEN,))
SLOPES = terrains(TerrainTrait.ROUGH, TerrainTrait.HIGH)
HIGH_GROUND = terrains(TerrainTrait.HIGH)
OPEN_GROUND = terrains(TerrainTrait.OPEN)
WET_GROUND = terrains(TerrainTrait.WET)
VOLCANIC_SOILS = frozenset({SoilKind.VOLCANIC, SoilKind.TEPHRA})
HELD_BEASTS = HELD_TEMPERS
DANGER_KEY = "danger"


HARM_WEIGHTS: dict[tuple[DangerSource, DangerHarm], Callable[[Rules], int]] = {
    (DangerSource.BEASTS, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.beasts_settlers,
    (DangerSource.BEASTS, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.beasts_livestock,
    (DangerSource.BEASTS, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.beasts_travellers,
    (DangerSource.BEASTS, DangerHarm.ARMIES): lambda rules: rules.regional_danger.beasts_armies,
    (DangerSource.BEASTS, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.beasts_ambush,
    (DangerSource.BEASTS, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.beasts_merchants,
    (DangerSource.BEASTS, DangerHarm.CROPS): lambda rules: rules.regional_danger.beasts_crops,
    (DangerSource.BEASTS, DangerHarm.VESSELS): lambda rules: rules.regional_danger.beasts_vessels,
    (DangerSource.BEASTS, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.beasts_structures,
    (DangerSource.BEASTS, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.beasts_pilgrims,
    (DangerSource.BEASTS, DangerHarm.WORKERS): lambda rules: rules.regional_danger.beasts_workers,
    (DangerSource.BANDITS, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.bandits_settlers,
    (DangerSource.BANDITS, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.bandits_livestock,
    (DangerSource.BANDITS, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.bandits_travellers,
    (DangerSource.BANDITS, DangerHarm.ARMIES): lambda rules: rules.regional_danger.bandits_armies,
    (DangerSource.BANDITS, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.bandits_ambush,
    (DangerSource.BANDITS, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.bandits_merchants,
    (DangerSource.BANDITS, DangerHarm.CROPS): lambda rules: rules.regional_danger.bandits_crops,
    (DangerSource.BANDITS, DangerHarm.VESSELS): lambda rules: rules.regional_danger.bandits_vessels,
    (DangerSource.BANDITS, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.bandits_structures,
    (DangerSource.BANDITS, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.bandits_pilgrims,
    (DangerSource.BANDITS, DangerHarm.WORKERS): lambda rules: rules.regional_danger.bandits_workers,
    (DangerSource.MONSTERS, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.monsters_settlers,
    (DangerSource.MONSTERS, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.monsters_livestock,
    (DangerSource.MONSTERS, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.monsters_travellers,
    (DangerSource.MONSTERS, DangerHarm.ARMIES): lambda rules: rules.regional_danger.monsters_armies,
    (DangerSource.MONSTERS, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.monsters_ambush,
    (DangerSource.MONSTERS, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.monsters_merchants,
    (DangerSource.MONSTERS, DangerHarm.CROPS): lambda rules: rules.regional_danger.monsters_crops,
    (DangerSource.MONSTERS, DangerHarm.VESSELS): lambda rules: rules.regional_danger.monsters_vessels,
    (DangerSource.MONSTERS, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.monsters_structures,
    (DangerSource.MONSTERS, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.monsters_pilgrims,
    (DangerSource.MONSTERS, DangerHarm.WORKERS): lambda rules: rules.regional_danger.monsters_workers,
    (DangerSource.PHENOMENA, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.phenomena_settlers,
    (DangerSource.PHENOMENA, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.phenomena_livestock,
    (DangerSource.PHENOMENA, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.phenomena_travellers,
    (DangerSource.PHENOMENA, DangerHarm.ARMIES): lambda rules: rules.regional_danger.phenomena_armies,
    (DangerSource.PHENOMENA, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.phenomena_ambush,
    (DangerSource.PHENOMENA, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.phenomena_merchants,
    (DangerSource.PHENOMENA, DangerHarm.CROPS): lambda rules: rules.regional_danger.phenomena_crops,
    (DangerSource.PHENOMENA, DangerHarm.VESSELS): lambda rules: rules.regional_danger.phenomena_vessels,
    (DangerSource.PHENOMENA, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.phenomena_structures,
    (DangerSource.PHENOMENA, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.phenomena_pilgrims,
    (DangerSource.PHENOMENA, DangerHarm.WORKERS): lambda rules: rules.regional_danger.phenomena_workers,
    (DangerSource.DISEASE, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.disease_settlers,
    (DangerSource.DISEASE, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.disease_livestock,
    (DangerSource.DISEASE, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.disease_travellers,
    (DangerSource.DISEASE, DangerHarm.ARMIES): lambda rules: rules.regional_danger.disease_armies,
    (DangerSource.DISEASE, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.disease_ambush,
    (DangerSource.DISEASE, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.disease_merchants,
    (DangerSource.DISEASE, DangerHarm.CROPS): lambda rules: rules.regional_danger.disease_crops,
    (DangerSource.DISEASE, DangerHarm.VESSELS): lambda rules: rules.regional_danger.disease_vessels,
    (DangerSource.DISEASE, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.disease_structures,
    (DangerSource.DISEASE, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.disease_pilgrims,
    (DangerSource.DISEASE, DangerHarm.WORKERS): lambda rules: rules.regional_danger.disease_workers,
    (DangerSource.AVALANCHE, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.avalanche_settlers,
    (DangerSource.AVALANCHE, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.avalanche_livestock,
    (DangerSource.AVALANCHE, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.avalanche_travellers,
    (DangerSource.AVALANCHE, DangerHarm.ARMIES): lambda rules: rules.regional_danger.avalanche_armies,
    (DangerSource.AVALANCHE, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.avalanche_ambush,
    (DangerSource.AVALANCHE, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.avalanche_merchants,
    (DangerSource.AVALANCHE, DangerHarm.CROPS): lambda rules: rules.regional_danger.avalanche_crops,
    (DangerSource.AVALANCHE, DangerHarm.VESSELS): lambda rules: rules.regional_danger.avalanche_vessels,
    (DangerSource.AVALANCHE, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.avalanche_structures,
    (DangerSource.AVALANCHE, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.avalanche_pilgrims,
    (DangerSource.AVALANCHE, DangerHarm.WORKERS): lambda rules: rules.regional_danger.avalanche_workers,
    (DangerSource.QUICKSAND, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.quicksand_settlers,
    (DangerSource.QUICKSAND, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.quicksand_livestock,
    (DangerSource.QUICKSAND, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.quicksand_travellers,
    (DangerSource.QUICKSAND, DangerHarm.ARMIES): lambda rules: rules.regional_danger.quicksand_armies,
    (DangerSource.QUICKSAND, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.quicksand_ambush,
    (DangerSource.QUICKSAND, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.quicksand_merchants,
    (DangerSource.QUICKSAND, DangerHarm.CROPS): lambda rules: rules.regional_danger.quicksand_crops,
    (DangerSource.QUICKSAND, DangerHarm.VESSELS): lambda rules: rules.regional_danger.quicksand_vessels,
    (DangerSource.QUICKSAND, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.quicksand_structures,
    (DangerSource.QUICKSAND, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.quicksand_pilgrims,
    (DangerSource.QUICKSAND, DangerHarm.WORKERS): lambda rules: rules.regional_danger.quicksand_workers,
    (DangerSource.VOLCANIC, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.volcanic_settlers,
    (DangerSource.VOLCANIC, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.volcanic_livestock,
    (DangerSource.VOLCANIC, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.volcanic_travellers,
    (DangerSource.VOLCANIC, DangerHarm.ARMIES): lambda rules: rules.regional_danger.volcanic_armies,
    (DangerSource.VOLCANIC, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.volcanic_ambush,
    (DangerSource.VOLCANIC, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.volcanic_merchants,
    (DangerSource.VOLCANIC, DangerHarm.CROPS): lambda rules: rules.regional_danger.volcanic_crops,
    (DangerSource.VOLCANIC, DangerHarm.VESSELS): lambda rules: rules.regional_danger.volcanic_vessels,
    (DangerSource.VOLCANIC, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.volcanic_structures,
    (DangerSource.VOLCANIC, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.volcanic_pilgrims,
    (DangerSource.VOLCANIC, DangerHarm.WORKERS): lambda rules: rules.regional_danger.volcanic_workers,
    (DangerSource.LANDSLIDE, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.landslide_settlers,
    (DangerSource.LANDSLIDE, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.landslide_livestock,
    (DangerSource.LANDSLIDE, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.landslide_travellers,
    (DangerSource.LANDSLIDE, DangerHarm.ARMIES): lambda rules: rules.regional_danger.landslide_armies,
    (DangerSource.LANDSLIDE, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.landslide_ambush,
    (DangerSource.LANDSLIDE, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.landslide_merchants,
    (DangerSource.LANDSLIDE, DangerHarm.CROPS): lambda rules: rules.regional_danger.landslide_crops,
    (DangerSource.LANDSLIDE, DangerHarm.VESSELS): lambda rules: rules.regional_danger.landslide_vessels,
    (DangerSource.LANDSLIDE, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.landslide_structures,
    (DangerSource.LANDSLIDE, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.landslide_pilgrims,
    (DangerSource.LANDSLIDE, DangerHarm.WORKERS): lambda rules: rules.regional_danger.landslide_workers,
    (DangerSource.EXPOSURE, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.exposure_settlers,
    (DangerSource.EXPOSURE, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.exposure_livestock,
    (DangerSource.EXPOSURE, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.exposure_travellers,
    (DangerSource.EXPOSURE, DangerHarm.ARMIES): lambda rules: rules.regional_danger.exposure_armies,
    (DangerSource.EXPOSURE, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.exposure_ambush,
    (DangerSource.EXPOSURE, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.exposure_merchants,
    (DangerSource.EXPOSURE, DangerHarm.CROPS): lambda rules: rules.regional_danger.exposure_crops,
    (DangerSource.EXPOSURE, DangerHarm.VESSELS): lambda rules: rules.regional_danger.exposure_vessels,
    (DangerSource.EXPOSURE, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.exposure_structures,
    (DangerSource.EXPOSURE, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.exposure_pilgrims,
    (DangerSource.EXPOSURE, DangerHarm.WORKERS): lambda rules: rules.regional_danger.exposure_workers,
    (DangerSource.CURRENTS, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.currents_settlers,
    (DangerSource.CURRENTS, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.currents_livestock,
    (DangerSource.CURRENTS, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.currents_travellers,
    (DangerSource.CURRENTS, DangerHarm.ARMIES): lambda rules: rules.regional_danger.currents_armies,
    (DangerSource.CURRENTS, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.currents_ambush,
    (DangerSource.CURRENTS, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.currents_merchants,
    (DangerSource.CURRENTS, DangerHarm.CROPS): lambda rules: rules.regional_danger.currents_crops,
    (DangerSource.CURRENTS, DangerHarm.VESSELS): lambda rules: rules.regional_danger.currents_vessels,
    (DangerSource.CURRENTS, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.currents_structures,
    (DangerSource.CURRENTS, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.currents_pilgrims,
    (DangerSource.CURRENTS, DangerHarm.WORKERS): lambda rules: rules.regional_danger.currents_workers,
    (DangerSource.TOXIC_GROUND, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.toxic_ground_settlers,
    (DangerSource.TOXIC_GROUND, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.toxic_ground_livestock,
    (DangerSource.TOXIC_GROUND, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.toxic_ground_travellers,
    (DangerSource.TOXIC_GROUND, DangerHarm.ARMIES): lambda rules: rules.regional_danger.toxic_ground_armies,
    (DangerSource.TOXIC_GROUND, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.toxic_ground_ambush,
    (DangerSource.TOXIC_GROUND, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.toxic_ground_merchants,
    (DangerSource.TOXIC_GROUND, DangerHarm.CROPS): lambda rules: rules.regional_danger.toxic_ground_crops,
    (DangerSource.TOXIC_GROUND, DangerHarm.VESSELS): lambda rules: rules.regional_danger.toxic_ground_vessels,
    (DangerSource.TOXIC_GROUND, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.toxic_ground_structures,
    (DangerSource.TOXIC_GROUND, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.toxic_ground_pilgrims,
    (DangerSource.TOXIC_GROUND, DangerHarm.WORKERS): lambda rules: rules.regional_danger.toxic_ground_workers,
    (DangerSource.LIGHTNING, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.lightning_settlers,
    (DangerSource.LIGHTNING, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.lightning_livestock,
    (DangerSource.LIGHTNING, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.lightning_travellers,
    (DangerSource.LIGHTNING, DangerHarm.ARMIES): lambda rules: rules.regional_danger.lightning_armies,
    (DangerSource.LIGHTNING, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.lightning_ambush,
    (DangerSource.LIGHTNING, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.lightning_merchants,
    (DangerSource.LIGHTNING, DangerHarm.CROPS): lambda rules: rules.regional_danger.lightning_crops,
    (DangerSource.LIGHTNING, DangerHarm.VESSELS): lambda rules: rules.regional_danger.lightning_vessels,
    (DangerSource.LIGHTNING, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.lightning_structures,
    (DangerSource.LIGHTNING, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.lightning_pilgrims,
    (DangerSource.LIGHTNING, DangerHarm.WORKERS): lambda rules: rules.regional_danger.lightning_workers,
    (DangerSource.SINKHOLE, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.sinkhole_settlers,
    (DangerSource.SINKHOLE, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.sinkhole_livestock,
    (DangerSource.SINKHOLE, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.sinkhole_travellers,
    (DangerSource.SINKHOLE, DangerHarm.ARMIES): lambda rules: rules.regional_danger.sinkhole_armies,
    (DangerSource.SINKHOLE, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.sinkhole_ambush,
    (DangerSource.SINKHOLE, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.sinkhole_merchants,
    (DangerSource.SINKHOLE, DangerHarm.CROPS): lambda rules: rules.regional_danger.sinkhole_crops,
    (DangerSource.SINKHOLE, DangerHarm.VESSELS): lambda rules: rules.regional_danger.sinkhole_vessels,
    (DangerSource.SINKHOLE, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.sinkhole_structures,
    (DangerSource.SINKHOLE, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.sinkhole_pilgrims,
    (DangerSource.SINKHOLE, DangerHarm.WORKERS): lambda rules: rules.regional_danger.sinkhole_workers,
    (DangerSource.ROCKFALL, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.rockfall_settlers,
    (DangerSource.ROCKFALL, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.rockfall_livestock,
    (DangerSource.ROCKFALL, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.rockfall_travellers,
    (DangerSource.ROCKFALL, DangerHarm.ARMIES): lambda rules: rules.regional_danger.rockfall_armies,
    (DangerSource.ROCKFALL, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.rockfall_ambush,
    (DangerSource.ROCKFALL, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.rockfall_merchants,
    (DangerSource.ROCKFALL, DangerHarm.CROPS): lambda rules: rules.regional_danger.rockfall_crops,
    (DangerSource.ROCKFALL, DangerHarm.VESSELS): lambda rules: rules.regional_danger.rockfall_vessels,
    (DangerSource.ROCKFALL, DangerHarm.STRUCTURES): lambda rules: rules.regional_danger.rockfall_structures,
    (DangerSource.ROCKFALL, DangerHarm.PILGRIMS): lambda rules: rules.regional_danger.rockfall_pilgrims,
    (DangerSource.ROCKFALL, DangerHarm.WORKERS): lambda rules: rules.regional_danger.rockfall_workers,
}


def harm_weight(rules: Rules, source: DangerSource, harm: DangerHarm) -> int:
    return HARM_WEIGHTS[source, harm](rules)


def reaches(rules: Rules, source: DangerSource) -> list[DangerHarm]:
    return [harm for harm in DangerHarm if harm_weight(rules, source, harm) > 0]


def row_weight(rules: Rules, row: RegionDangerRow, harm: DangerHarm) -> int:
    if row.harmed and harm.value not in row.harmed:
        return 0
    return harm_weight(rules, row.source, harm)


def weighted(rules: Rules, rows: Iterable[RegionDangerRow], harm: DangerHarm) -> int:
    return clamp_int(round_half_up(sum(row.strength * row_weight(rules, row, harm) / PERCENT for row in rows)), 0, PERCENT)


def total(rules: Rules, rows: Iterable[RegionDangerRow]) -> int:
    return clamp_int(round_half_up(sum(row.strength for row in rows) * rules.regional_danger.total_pct / PERCENT), 0, PERCENT)


async def dangers_by_region(session: AsyncSession, region_ids: Iterable[int] | None = None) -> dict[int, list[RegionDangerRow]]:
    statement = select(RegionDangerRow).order_by(RegionDangerRow.id)
    if region_ids is not None:
        statement = statement.where(RegionDangerRow.region_entity_id.in_(list(region_ids)))
    found: dict[int, list[RegionDangerRow]] = defaultdict(list)
    for row in await session.scalars(statement):
        found[row.region_entity_id].append(row)
    return found


async def harm_of(session: AsyncSession, rules: Rules, region_id: int | None, harm: DangerHarm) -> int:
    if region_id is None:
        return 0
    rows = await session.scalars(select(RegionDangerRow).where(RegionDangerRow.region_entity_id == region_id))
    return weighted(rules, rows, harm)


async def weighted_dangers(session: AsyncSession, rules: Rules, harm: DangerHarm) -> dict[int, int]:
    return {region_id: weighted(rules, rows, harm) for region_id, rows in (await dangers_by_region(session)).items()}


def sync_stat(rules: Rules, region: EntityRow, rows: Iterable[RegionDangerRow]) -> None:
    set_stats(region, **{DANGER_KEY: total(rules, rows)})


@dataclass
class Derived:
    strength: float = 0.0
    node_id: int | None = None
    node_weight: float = 0.0

    def add(self, amount: float, node_id: int | None = None) -> None:
        self.strength += amount
        if node_id is not None and amount > self.node_weight:
            self.node_id, self.node_weight = node_id, amount


@dataclass
class DangerScene:
    atlas: RegionAtlas
    grounds: dict[int, RegionEnvironmentRow]
    regions: dict[int, EntityRow]
    memories: dict[int, list[RegionMemoryRow]]
    derived: dict[int, dict[DangerSource, Derived]] = field(default_factory=dict)

    def slot(self, region_id: int | None, source: DangerSource) -> Derived | None:
        if region_id is None or region_id not in self.grounds:
            return None
        return self.derived.setdefault(region_id, {}).setdefault(source, Derived())


async def _beasts(session: AsyncSession, rules: Rules, scene: DangerScene) -> None:
    table = rules.regional_danger
    profiles = {row.species_entity_id: row for row in await session.scalars(select(SpeciesProfileRow))}
    living = set(await session.scalars(select(EntityRow.id).where(EntityRow.entity_type == EntityType.SPECIES, EntityRow.status == EntityStatus.CANON)))
    ranges = list(await session.scalars(select(SpeciesRangeRow).order_by(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id)))
    present = {(row.species_entity_id, row.region_entity_id) for row in ranges if row.abundance > 0}
    mimics = await mimics_of(session)
    for row in ranges:
        profile = profiles.get(row.species_entity_id)
        if row.species_entity_id not in living or profile is None or profile.stage is not DomesticationStage.WILD:
            continue
        aggression = profile.aggression
        copied = mimics.get(row.species_entity_id)
        model = profiles.get(copied[0]) if copied is not None and (copied[0], row.region_entity_id) in present else None
        if copied is not None and model is not None:
            aggression = max(aggression, round(model.aggression * rules.symbiosis.mimic_alarm_pct / PERCENT * copied[1] / PERCENT))
        if aggression < table.beasts_aggression_min:
            continue
        slot = scene.slot(row.region_entity_id, DangerSource.BEASTS)
        if slot is not None:
            slot.add(min(row.abundance, PERCENT) * aggression / PERCENT * table.beasts_species_pct / PERCENT, row.species_entity_id)
    beasts = await session.execute(
        select(BeastProfileRow.beast_entity_id, BeastProfileRow.lair_place_id, BeastProfileRow.temper)
        .join(EntityRow, EntityRow.id == BeastProfileRow.beast_entity_id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(BeastProfileRow.beast_entity_id)
    )
    for beast_id, lair_id, temper in beasts:
        if temper in HELD_BEASTS:
            continue
        slot = scene.slot(scene.atlas.top_region(lair_id or beast_id), DangerSource.BEASTS)
        if slot is not None:
            slot.add(table.beasts_named_sleeping if temper is BeastTemper.SLEEPING else table.beasts_named_awake, beast_id)
    for region_id, ground in scene.grounds.items():
        wild = wildness(ground, False, rules) or 0
        slot = scene.slot(region_id, DangerSource.BEASTS)
        if slot is not None:
            slot.add(wild * table.beasts_wildness_pct / PERCENT)


async def _monsters(session: AsyncSession, rules: Rules, scene: DangerScene) -> None:
    engine = rules.world_engine
    species = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.SPECIES, EntityRow.status == EntityStatus.CANON)))
    threshold = relative_threshold(species, DANGER_KEY, fraction(engine.monster_top_pct), engine.monster_min_danger, engine.monster_always_danger)
    for creature in species:
        danger = stat(creature, DANGER_KEY) or 0
        if danger < threshold(creature):
            continue
        slot = scene.slot(scene.atlas.top_region(creature.id), DangerSource.MONSTERS)
        if slot is not None:
            slot.add(danger * rules.regional_danger.monsters_danger_pct / PERCENT, creature.id)


async def _bandits(session: AsyncSession, rules: Rules, scene: DangerScene, epoch: int) -> None:
    table = rules.regional_danger
    outlaws = await session.scalars(
        select(EntityRow.id).where(
            EntityRow.entity_type == EntityType.MORTAL, EntityRow.mortal_role == MortalRole.BANDIT, EntityRow.status == EntityStatus.CANON
        )
    )
    for outlaw in outlaws:
        slot = scene.slot(scene.atlas.top_region(outlaw), DangerSource.BANDITS)
        if slot is not None:
            slot.add(table.bandits_per_outlaw, outlaw)
    control: dict[int, int] = defaultdict(int)
    for region_id, held in await session.execute(select(PolityTerritoryRow.region_entity_id, PolityTerritoryRow.control)):
        control[region_id] = max(control[region_id], held)
    welcoming = await session.scalars(
        select(TraditionParticipationRow.community_entity_id)
        .join(TraditionProfileRow, TraditionProfileRow.tradition_entity_id == TraditionParticipationRow.tradition_entity_id)
        .where(TraditionProfileRow.kind == TraditionFunction.HOSPITALITY, TraditionParticipationRow.last_celebrated_epoch >= epoch - 1)
    )
    welcomed: dict[int, int] = defaultdict(int)
    for community_id in welcoming:
        region = scene.atlas.top_region(community_id)
        if region is not None:
            welcomed[region] += 1
    circuits: dict[int, int] = defaultdict(int)
    for stop in await circuit_stops(session):
        region = scene.atlas.top_region(stop)
        if region is not None:
            circuits[region] += 1
    for region_id, ground in scene.grounds.items():
        slot = scene.slot(region_id, DangerSource.BANDITS)
        if slot is None:
            continue
        if scene.atlas.communities_in(region_id):
            slot.add((PERCENT - control[region_id]) * table.bandits_lawless_pct / PERCENT)
        slot.add(ground.scars.get(ScarKind.BATTLEFIELD.value, 0) * table.bandits_battlefield_pct / PERCENT)
        welcome = welcomed[region_id] * rules.traditions.hospitality_danger + circuits[region_id] * rules.ceremonial_circuits.hospitality_danger
        slot.strength = max(0.0, slot.strength - welcome)


def _ground(rules: Rules, scene: DangerScene) -> None:
    table = rules.regional_danger
    scars = rules.scars
    for region_id, ground in scene.grounds.items():
        scar = ground.scars
        phenomena = scene.slot(region_id, DangerSource.PHENOMENA)
        if phenomena is not None:
            phenomena.add(scar.get(ScarKind.HAUNTED.value, 0) * scars.haunted_danger_pct / PERCENT)
            phenomena.add(scar.get(ScarKind.LEAK_WOUND.value, 0) * scars.leak_wound_danger_pct / PERCENT)
            phenomena.add(scar.get(ScarKind.BLIGHTED.value, 0) * table.phenomena_blighted_pct / PERCENT)
            phenomena.add(max(0, ground.magic_density - table.phenomena_magic_above) * table.phenomena_magic_pct / PERCENT)
            phenomena.add(darkness(rules, scene.memories.get(region_id, [])) * table.phenomena_darkness_pct / PERCENT)
            phenomena.strength *= 1 - ground.sacredness * table.phenomena_sacred_pct / PERCENT / PERCENT
        disease = scene.slot(region_id, DangerSource.DISEASE)
        if disease is not None:
            disease.add(ground.disease_load * table.disease_load_pct / PERCENT)
            disease.add(scar.get(ScarKind.PLAGUE_GROUND.value, 0) * table.disease_plague_ground_pct / PERCENT)
        avalanche = scene.slot(region_id, DangerSource.AVALANCHE)
        if avalanche is not None and ground.temperature < table.avalanche_cold_below:
            if ground.dominant_terrain in SNOW_TERRAIN:
                avalanche.add(table.avalanche_terrain)
            avalanche.add(ground.roughness * table.avalanche_roughness_pct / PERCENT)
        quicksand = scene.slot(region_id, DangerSource.QUICKSAND)
        if quicksand is not None:
            if ground.dominant_terrain is TerrainKind.MARSH:
                quicksand.add(table.quicksand_marsh)
            if ground.dominant_terrain is TerrainKind.DESERT:
                quicksand.add(table.quicksand_desert)
            quicksand.add(ground.wetland * table.quicksand_wetland_pct / PERCENT)
        volcanic = scene.slot(region_id, DangerSource.VOLCANIC)
        if volcanic is not None:
            if ground.dominant_terrain is TerrainKind.VOLCANIC:
                volcanic.add(table.volcanic_terrain)
            elif ground.soil in VOLCANIC_SOILS:
                volcanic.add(table.volcanic_soil)
            volcanic.add(scar.get(ScarKind.CRATER.value, 0) * table.volcanic_crater_pct / PERCENT)


def landslide(rules: Rules, ground: RegionEnvironmentRow) -> float:
    table = rules.regional_danger
    if ground.dominant_terrain not in SLOPES:
        return 0.0
    loose = ground.scars.get(ScarKind.ERODED.value, 0) + ground.scars.get(ScarKind.DEFORESTED.value, 0)
    wet = ground.rainfall / PERCENT
    return table.landslide_base + ground.roughness * table.landslide_roughness_pct / PERCENT * wet + loose * table.landslide_eroded_pct / PERCENT


def exposure(rules: Rules, ground: RegionEnvironmentRow) -> float:
    table = rules.regional_danger
    beyond = max(0, table.exposure_cold_below - ground.temperature, ground.temperature - table.exposure_heat_above)
    return table.exposure_base + beyond * table.exposure_extreme_pct / PERCENT if beyond > 0 else 0.0


def currents(rules: Rules, ground: RegionEnvironmentRow) -> float:
    table = rules.regional_danger
    river = RIVER_RANK[ground.river_class] * table.currents_river_step
    coast = table.currents_coast if ground.coast_kind is not CoastKind.NONE else 0
    if not river and not coast:
        return 0.0
    return float(table.currents_base + river + coast + max(0, CURRENTS[ground.current].danger(rules)))


def toxic_ground(rules: Rules, ground: RegionEnvironmentRow) -> float:
    table = rules.regional_danger
    fumes = table.toxic_ground_base if ground.dominant_terrain is TerrainKind.VOLCANIC else 0
    marsh = ground.wetland * table.toxic_ground_marsh_pct / PERCENT if ground.dominant_terrain in WET_GROUND else 0
    return fumes + marsh + ground.scars.get(ScarKind.POISONED.value, 0) * table.toxic_ground_poisoned_pct / PERCENT


def lightning(rules: Rules, ground: RegionEnvironmentRow) -> float:
    table = rules.regional_danger
    return float(table.lightning_harm) if ground.rainfall > table.lightning_rain_above and ground.dominant_terrain in OPEN_GROUND else 0.0


def sinkhole(rules: Rules, ground: RegionEnvironmentRow) -> float:
    return float(rules.regional_danger.sinkhole_harm) if ground.dominant_terrain is TerrainKind.KARST else 0.0


def rockfall(rules: Rules, ground: RegionEnvironmentRow) -> float:
    table = rules.regional_danger
    if ground.dominant_terrain not in HIGH_GROUND:
        return 0.0
    return table.rockfall_harm + ground.roughness * table.rockfall_roughness_pct / PERCENT


RISING: Mapping[DangerSource, Callable[[Rules, RegionEnvironmentRow], float]] = {
    DangerSource.LANDSLIDE: landslide,
    DangerSource.EXPOSURE: exposure,
    DangerSource.CURRENTS: currents,
    DangerSource.TOXIC_GROUND: toxic_ground,
    DangerSource.LIGHTNING: lightning,
    DangerSource.SINKHOLE: sinkhole,
    DangerSource.ROCKFALL: rockfall,
}
PROTECTION: Mapping[DangerSource, Callable[[Rules], int]] = {
    DangerSource.LANDSLIDE: lambda rules: rules.regional_danger.landslide_protection_cut_pct,
    DangerSource.EXPOSURE: lambda rules: rules.regional_danger.exposure_protection_cut_pct,
    DangerSource.CURRENTS: lambda rules: rules.regional_danger.currents_protection_cut_pct,
    DangerSource.TOXIC_GROUND: lambda rules: rules.regional_danger.toxic_ground_protection_cut_pct,
    DangerSource.LIGHTNING: lambda rules: rules.regional_danger.lightning_protection_cut_pct,
    DangerSource.SINKHOLE: lambda rules: rules.regional_danger.sinkhole_protection_cut_pct,
    DangerSource.ROCKFALL: lambda rules: rules.regional_danger.rockfall_protection_cut_pct,
}


def _rising(rules: Rules, scene: DangerScene) -> None:
    for region_id, ground in scene.grounds.items():
        for source, rise in RISING.items():
            slot = scene.slot(region_id, source)
            if slot is not None:
                slot.add(rise(rules, ground) * (PERCENT - ground.built * PROTECTION[source](rules) / PERCENT) / PERCENT)


async def _cosmic(session: AsyncSession, rules: Rules, scene: DangerScene) -> None:
    statement = (
        select(PhenomenonFootprintRow.region_entity_id, PhenomenonFootprintRow.intensity, PhenomenonProfileRow.kind, PhenomenonProfileRow.entity_id)
        .join(PhenomenonProfileRow, PhenomenonProfileRow.entity_id == PhenomenonFootprintRow.phenomenon_entity_id)
        .join(EntityRow, EntityRow.id == PhenomenonProfileRow.entity_id)
        .where(EntityRow.status == EntityStatus.CANON)
    )
    for region_id, intensity, kind, entity_id in await session.execute(statement):
        slot = scene.slot(region_id, DangerSource.PHENOMENA)
        if slot is not None:
            slot.add(PHENOMENON_MECHANICS[kind].danger(rules) * intensity / PERCENT, entity_id)
    for rift in await session.scalars(select(RiftRow).where(RiftRow.state.in_(list(OPEN_RIFT_STATES)))):
        slot = scene.slot(rift.region_entity_id, DangerSource.PHENOMENA)
        if slot is not None:
            slot.add(rift.size * rules.rifts.danger_pct / PERCENT)
    ladder = await cosmography_of(session)
    for region_id, ground in sorted(scene.grounds.items()):
        place = ladder.place_world_id(ground.world_id)
        heavens = ladder.pull(rules, place).danger
        slot = scene.slot(region_id, DangerSource.PHENOMENA) if heavens > 0 else None
        if slot is not None:
            slot.add(heavens, place.dimension_id)


async def derive(session: AsyncSession, rules: Rules, scene: DangerScene, epoch: int) -> dict[int, dict[DangerSource, Derived]]:
    await _beasts(session, rules, scene)
    await _cosmic(session, rules, scene)
    await _monsters(session, rules, scene)
    await _bandits(session, rules, scene, epoch)
    _ground(rules, scene)
    _rising(rules, scene)
    return scene.derived


def settle_row(rules: Rules, row: RegionDangerRow, derived: Derived, epoch: int) -> bool:
    strength = clamp_int(round_half_up(derived.strength), 0, PERCENT)
    if row.held:
        return True
    if row.origin is not DangerOrigin.DERIVED:
        faded = row.strength - rules.regional_danger.curse_fade
        if faded > strength:
            row.strength = faded
            row.updated_epoch = epoch
            return True
        row.origin = DangerOrigin.DERIVED
        row.son_id = None
    if strength <= 0:
        return False
    if row.strength != strength or row.source_node_id != derived.node_id:
        row.strength = strength
        row.source_node_id = derived.node_id
        row.updated_epoch = epoch
    return True


async def write_dangers(session: AsyncSession, rules: Rules, scene: DangerScene, epoch: int) -> int:
    existing = await dangers_by_region(session)
    written = 0
    for region_id in sorted(scene.grounds):
        region = scene.regions.get(region_id)
        if region is None or frozen(region_id):
            continue
        rows = {row.source: row for row in existing.get(region_id, [])}
        derived = scene.derived.get(region_id, {})
        kept: list[RegionDangerRow] = []
        for source in DangerSource:
            found = derived.get(source, Derived())
            row = rows.get(source)
            if row is None:
                strength = clamp_int(round_half_up(found.strength), 0, PERCENT)
                if strength <= 0:
                    continue
                row = RegionDangerRow(
                    world_id=scene.grounds[region_id].world_id,
                    region_entity_id=region_id,
                    source=source,
                    strength=strength,
                    origin=DangerOrigin.DERIVED,
                    source_node_id=found.node_id,
                    held=False,
                    since_epoch=epoch,
                    updated_epoch=epoch,
                )
                session.add(row)
                kept.append(row)
                written += 1
                continue
            if settle_row(rules, row, found, epoch):
                kept.append(row)
            else:
                await session.delete(row)
        sync_stat(rules, region, kept)
    await session.flush()
    return written


async def ease_danger(session: AsyncSession, rules: Rules, region_id: int, source: DangerSource, amount: int) -> int:
    row = await session.scalar(select(RegionDangerRow).where(RegionDangerRow.region_entity_id == region_id, RegionDangerRow.source == source))
    if row is None or row.held:
        return 0
    eased = min(row.strength, amount)
    row.strength -= eased
    region = await session.get(EntityRow, region_id)
    if region is not None:
        rows = list(await session.scalars(select(RegionDangerRow).where(RegionDangerRow.region_entity_id == region_id)))
        sync_stat(rules, region, rows)
    return eased
