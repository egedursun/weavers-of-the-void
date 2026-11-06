from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.ecology import BeastProfileRow, SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.polity import PolityTerritoryRow
from aerona.db.tables.region import RegionDangerRow, RegionMemoryRow
from aerona.db.write_guard import held as frozen
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.ecology import BeastTemper, DomesticationStage
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.environment import ScarKind, SoilKind, TerrainKind
from aerona.domain.enums.region import DangerHarm, DangerOrigin, DangerSource
from aerona.engine.ecology.ranges import wildness
from aerona.engine.environment.memory import darkness
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, fraction, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.primitives.thresholds import relative_threshold
from aerona.rules.registry import Rules

SNOW_TERRAIN = frozenset({TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS, TerrainKind.ICE_SHEET})
VOLCANIC_SOILS = frozenset({SoilKind.VOLCANIC, SoilKind.ASH})
HELD_BEASTS = frozenset({BeastTemper.BOUND, BeastTemper.TAMED})
DANGER_KEY = "danger"


HARM_WEIGHTS: dict[tuple[DangerSource, DangerHarm], Callable[[Rules], int]] = {
    (DangerSource.BEASTS, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.beasts_settlers,
    (DangerSource.BEASTS, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.beasts_livestock,
    (DangerSource.BEASTS, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.beasts_travellers,
    (DangerSource.BEASTS, DangerHarm.ARMIES): lambda rules: rules.regional_danger.beasts_armies,
    (DangerSource.BEASTS, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.beasts_ambush,
    (DangerSource.BEASTS, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.beasts_merchants,
    (DangerSource.BANDITS, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.bandits_settlers,
    (DangerSource.BANDITS, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.bandits_livestock,
    (DangerSource.BANDITS, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.bandits_travellers,
    (DangerSource.BANDITS, DangerHarm.ARMIES): lambda rules: rules.regional_danger.bandits_armies,
    (DangerSource.BANDITS, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.bandits_ambush,
    (DangerSource.BANDITS, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.bandits_merchants,
    (DangerSource.MONSTERS, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.monsters_settlers,
    (DangerSource.MONSTERS, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.monsters_livestock,
    (DangerSource.MONSTERS, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.monsters_travellers,
    (DangerSource.MONSTERS, DangerHarm.ARMIES): lambda rules: rules.regional_danger.monsters_armies,
    (DangerSource.MONSTERS, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.monsters_ambush,
    (DangerSource.MONSTERS, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.monsters_merchants,
    (DangerSource.PHENOMENA, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.phenomena_settlers,
    (DangerSource.PHENOMENA, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.phenomena_livestock,
    (DangerSource.PHENOMENA, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.phenomena_travellers,
    (DangerSource.PHENOMENA, DangerHarm.ARMIES): lambda rules: rules.regional_danger.phenomena_armies,
    (DangerSource.PHENOMENA, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.phenomena_ambush,
    (DangerSource.PHENOMENA, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.phenomena_merchants,
    (DangerSource.DISEASE, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.disease_settlers,
    (DangerSource.DISEASE, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.disease_livestock,
    (DangerSource.DISEASE, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.disease_travellers,
    (DangerSource.DISEASE, DangerHarm.ARMIES): lambda rules: rules.regional_danger.disease_armies,
    (DangerSource.DISEASE, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.disease_ambush,
    (DangerSource.DISEASE, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.disease_merchants,
    (DangerSource.AVALANCHE, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.avalanche_settlers,
    (DangerSource.AVALANCHE, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.avalanche_livestock,
    (DangerSource.AVALANCHE, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.avalanche_travellers,
    (DangerSource.AVALANCHE, DangerHarm.ARMIES): lambda rules: rules.regional_danger.avalanche_armies,
    (DangerSource.AVALANCHE, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.avalanche_ambush,
    (DangerSource.AVALANCHE, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.avalanche_merchants,
    (DangerSource.QUICKSAND, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.quicksand_settlers,
    (DangerSource.QUICKSAND, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.quicksand_livestock,
    (DangerSource.QUICKSAND, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.quicksand_travellers,
    (DangerSource.QUICKSAND, DangerHarm.ARMIES): lambda rules: rules.regional_danger.quicksand_armies,
    (DangerSource.QUICKSAND, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.quicksand_ambush,
    (DangerSource.QUICKSAND, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.quicksand_merchants,
    (DangerSource.VOLCANIC, DangerHarm.SETTLERS): lambda rules: rules.regional_danger.volcanic_settlers,
    (DangerSource.VOLCANIC, DangerHarm.LIVESTOCK): lambda rules: rules.regional_danger.volcanic_livestock,
    (DangerSource.VOLCANIC, DangerHarm.TRAVELLERS): lambda rules: rules.regional_danger.volcanic_travellers,
    (DangerSource.VOLCANIC, DangerHarm.ARMIES): lambda rules: rules.regional_danger.volcanic_armies,
    (DangerSource.VOLCANIC, DangerHarm.AMBUSH): lambda rules: rules.regional_danger.volcanic_ambush,
    (DangerSource.VOLCANIC, DangerHarm.MERCHANTS): lambda rules: rules.regional_danger.volcanic_merchants,
}


def harm_weight(rules: Rules, source: DangerSource, harm: DangerHarm) -> int:
    return HARM_WEIGHTS[source, harm](rules)


def weighted(rules: Rules, rows: Iterable[RegionDangerRow], harm: DangerHarm) -> int:
    return clamp_int(round_half_up(sum(row.strength * harm_weight(rules, row.source, harm) / PERCENT for row in rows)), 0, PERCENT)


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
    for row in await session.scalars(select(SpeciesRangeRow).order_by(SpeciesRangeRow.species_entity_id, SpeciesRangeRow.region_entity_id)):
        profile = profiles.get(row.species_entity_id)
        if (
            row.species_entity_id not in living
            or profile is None
            or profile.stage is not DomesticationStage.WILD
            or profile.aggression < table.beasts_aggression_min
        ):
            continue
        slot = scene.slot(row.region_entity_id, DangerSource.BEASTS)
        if slot is not None:
            slot.add(min(row.abundance, PERCENT) * profile.aggression / PERCENT * table.beasts_species_pct / PERCENT, row.species_entity_id)
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
        .where(TraditionProfileRow.kind == TraditionKind.HOSPITALITY_LAW, TraditionParticipationRow.last_celebrated_epoch >= epoch - 1)
    )
    welcomed: dict[int, int] = defaultdict(int)
    for community_id in welcoming:
        region = scene.atlas.top_region(community_id)
        if region is not None:
            welcomed[region] += 1
    for region_id, ground in scene.grounds.items():
        slot = scene.slot(region_id, DangerSource.BANDITS)
        if slot is None:
            continue
        if scene.atlas.communities_in(region_id):
            slot.add((PERCENT - control[region_id]) * table.bandits_lawless_pct / PERCENT)
        slot.add(ground.scars.get(ScarKind.BATTLEFIELD.value, 0) * table.bandits_battlefield_pct / PERCENT)
        slot.strength = max(0.0, slot.strength - welcomed[region_id] * rules.traditions.hospitality_danger)


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


async def derive(session: AsyncSession, rules: Rules, scene: DangerScene, epoch: int) -> dict[int, dict[DangerSource, Derived]]:
    await _beasts(session, rules, scene)
    await _monsters(session, rules, scene)
    await _bandits(session, rules, scene, epoch)
    _ground(rules, scene)
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
