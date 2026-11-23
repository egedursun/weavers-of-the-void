from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.land_memory import LAND_MEMORIES, SOURCE_KINDS
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.region import RegionMemoryRow
from aerona.db.tables.warfare import BattleRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.military import OutcomeClass
from aerona.domain.enums.region import MemoryOrigin, RegionMemoryKind
from aerona.domain.enums.war import BattleOutcome
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import flags_by_entity
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

DISASTER_MEMORIES: dict[EngineKind, RegionMemoryKind] = {
    EngineKind.FLOOD: RegionMemoryKind.DISASTER,
    EngineKind.EARTHQUAKE: RegionMemoryKind.DISASTER,
    EngineKind.DROUGHT: RegionMemoryKind.DISASTER,
    EngineKind.STORM: RegionMemoryKind.DISASTER,
    EngineKind.MAGIC_STORM: RegionMemoryKind.DISASTER,
    EngineKind.PLAGUE: RegionMemoryKind.PLAGUE,
    EngineKind.FAMINE: RegionMemoryKind.FAMINE,
}
SACKS = frozenset({BattleOutcome.SIEGE_BREACHED, BattleOutcome.SIEGE_STARVATION})
HOLY_STRUCTURES = frozenset({EngineKind.TEMPLE})


@dataclass(frozen=True)
class Remembered:
    region_id: int
    world_id: int
    kind: RegionMemoryKind
    magnitude: int
    epoch: int
    source_key: str
    title: str
    subject_id: int | None = None
    incident_id: int | None = None


def darkness_of(rules: Rules, kind: RegionMemoryKind) -> int:
    return LAND_MEMORIES[kind].darkness(rules)


def holiness_of(rules: Rules, kind: RegionMemoryKind) -> int:
    return LAND_MEMORIES[kind].holiness(rules)


def fades(rules: Rules, kind: RegionMemoryKind) -> bool:
    return LAND_MEMORIES[kind].weight is not None or darkness_of(rules, kind) > holiness_of(rules, kind)


def darkness(rules: Rules, rows: list[RegionMemoryRow]) -> int:
    return clamp_int(round_half_up(sum(row.magnitude * darkness_of(rules, row.kind) / PERCENT for row in rows)), 0, PERCENT)


def holiness(rules: Rules, rows: list[RegionMemoryRow]) -> int:
    return clamp_int(round_half_up(sum(row.magnitude * holiness_of(rules, row.kind) / PERCENT for row in rows)), 0, PERCENT)


async def memories_by_region(session: AsyncSession) -> dict[int, list[RegionMemoryRow]]:
    found: dict[int, list[RegionMemoryRow]] = defaultdict(list)
    for row in await session.scalars(select(RegionMemoryRow).order_by(RegionMemoryRow.id)):
        found[row.region_entity_id].append(row)
    return found


def _battle(rules: Rules, atlas: RegionAtlas, battle: BattleRow, names: dict[int, str]) -> Remembered | None:
    region = atlas.top_region(battle.place_entity_id)
    world = atlas.world_of(region) if region is not None else None
    if region is None or world is None:
        return None
    table = rules.terrain
    magnitude = round_half_up((battle.winner_losses + battle.loser_losses) / table.memory_battle_losses_per_point)
    kind = RegionMemoryKind.BATTLE
    if battle.outcome in SACKS:
        kind, magnitude = RegionMemoryKind.SACK, max(magnitude, table.memory_sack)
    if battle.outcome_class is OutcomeClass.MASSACRE:
        kind, magnitude = RegionMemoryKind.MASSACRE, magnitude + table.memory_massacre
    where = names.get(battle.place_entity_id or 0, "")
    title = names.get(battle.record_entity_id or 0) or (f"The battle at {where}" if where else "A battle")
    return Remembered(region, world, kind, clamp_int(magnitude, 0, PERCENT), battle.epoch, f"battle:{battle.id}", title, battle.record_entity_id)


async def gather(session: AsyncSession, rules: Rules, atlas: RegionAtlas, since_epoch: int) -> list[Remembered]:
    table = rules.terrain
    found: list[Remembered] = []
    battles = list(await session.scalars(select(BattleRow).where(BattleRow.epoch >= since_epoch).order_by(BattleRow.id)))
    named = {battle.place_entity_id for battle in battles} | {battle.record_entity_id for battle in battles}
    names = {row.id: row.name for row in await session.scalars(select(EntityRow).where(EntityRow.id.in_([item for item in named if item is not None])))}
    for battle in battles:
        memory = _battle(rules, atlas, battle, names)
        if memory is not None:
            found.append(memory)
    events = await session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.EVENT,
            EntityRow.engine_kind.in_(list(DISASTER_MEMORIES)),
            EntityRow.status != EntityStatus.REJECTED,
            EntityRow.birth_epoch >= since_epoch,
        )
        .order_by(EntityRow.id)
    )
    for event in events:
        region = atlas.top_region(event.location_id or event.id)
        if region is None or event.engine_kind is None or event.world_id is None:
            continue
        kind = DISASTER_MEMORIES[event.engine_kind]
        found.append(
            Remembered(
                region, event.world_id, kind, clamp_int(stat(event, "severity") or 0, 0, PERCENT), event.birth_epoch, f"event:{event.id}", event.name, event.id
            )
        )
    corpses = await session.scalars(
        select(EntityRow).where(EntityRow.engine_kind == EngineKind.DEAD_GOD, EntityRow.status == EntityStatus.CANON, EntityRow.birth_epoch >= since_epoch)
    )
    for corpse in corpses:
        region = atlas.top_region(corpse.id)
        if region is not None and corpse.world_id is not None:
            found.append(
                Remembered(
                    region,
                    corpse.world_id,
                    RegionMemoryKind.GOD_DEATH,
                    table.memory_god_death,
                    corpse.birth_epoch,
                    f"corpse:{corpse.id}",
                    corpse.name,
                    corpse.id,
                )
            )
    saints = await session.scalars(
        select(EntityRow).where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.mortal_role == MortalRole.SAINT,
            EntityRow.status == EntityStatus.DEAD,
            EntityRow.end_epoch >= since_epoch,
        )
    )
    for saint in saints:
        region = atlas.top_region(saint.location_id or saint.id)
        if region is not None and saint.world_id is not None:
            epoch = saint.end_epoch or saint.birth_epoch
            found.append(
                Remembered(
                    region,
                    saint.world_id,
                    RegionMemoryKind.SAINT_BURIAL,
                    table.memory_saint,
                    epoch,
                    f"saint:{saint.id}",
                    f"The grave of {saint.name}",
                    saint.id,
                )
            )
    miracles = await session.execute(
        select(IncidentRow.id, IncidentRow.place_entity_id, IncidentRow.epoch, IncidentRow.world_id, ChronicleRow.text)
        .join(ChronicleRow, ChronicleRow.id == IncidentRow.chronicle_id)
        .where(ChronicleRow.kind == ChronicleKind.MIRACLE, IncidentRow.epoch >= since_epoch, IncidentRow.place_entity_id.is_not(None))
        .order_by(IncidentRow.id)
    )
    for incident_id, place_id, epoch, world_id, text in miracles:
        region = atlas.top_region(place_id)
        world = world_id or (atlas.world_of(region) if region is not None else None)
        if region is not None and world is not None:
            found.append(Remembered(region, world, RegionMemoryKind.MIRACLE, table.memory_miracle, epoch, f"miracle:{incident_id}", text, None, incident_id))
    found.extend(await happenings(session, rules, atlas, since_epoch))
    return [memory for memory in found if memory.magnitude >= table.memory_min_magnitude]


async def happenings(session: AsyncSession, rules: Rules, atlas: RegionAtlas, since_epoch: int) -> list[Remembered]:
    rows = list(
        await session.scalars(select(IncidentRow).where(IncidentRow.kind.in_(sorted(SOURCE_KINDS)), IncidentRow.epoch >= since_epoch).order_by(IncidentRow.id))
    )
    parties: dict[int, list[int]] = defaultdict(list)
    if rows:
        for incident_id, node_id in await session.execute(
            select(IncidentParticipantRow.incident_id, IncidentParticipantRow.node_id)
            .where(IncidentParticipantRow.incident_id.in_([row.id for row in rows]))
            .order_by(IncidentParticipantRow.incident_id, IncidentParticipantRow.position, IncidentParticipantRow.node_id)
        ):
            parties[incident_id].append(node_id)
    found: list[Remembered] = []
    for row in rows:
        kind = SOURCE_KINDS[row.kind]
        spec = LAND_MEMORIES[kind]
        places = [row.place_entity_id, row.destination_entity_id, row.origin_entity_id, *parties.get(row.id, [])]
        region = next((top for place in places if place is not None and (top := atlas.top_region(place)) is not None), None)
        world = row.world_id or (atlas.world_of(region) if region is not None else None)
        if region is None or world is None:
            continue
        weight = spec.weight(rules) if spec.weight is not None else 0
        subject = next(iter(parties.get(row.id, [])), None)
        found.append(
            Remembered(region, world, kind, clamp_int(max(weight, row.magnitude), 0, PERCENT), row.epoch, f"incident:{row.id}", spec.label, subject, row.id)
        )
    return found


async def remember(session: AsyncSession, rules: Rules, atlas: RegionAtlas, since_epoch: int) -> list[RegionMemoryRow]:
    known = {(region, key) for region, key in await session.execute(select(RegionMemoryRow.region_entity_id, RegionMemoryRow.source_key))}
    made: list[RegionMemoryRow] = []
    for memory in await gather(session, rules, atlas, since_epoch):
        if (memory.region_id, memory.source_key) in known or held(memory.region_id):
            continue
        row = RegionMemoryRow(
            world_id=memory.world_id,
            region_entity_id=memory.region_id,
            kind=memory.kind,
            magnitude=memory.magnitude,
            epoch=max(0, memory.epoch),
            source_key=memory.source_key,
            subject_node_id=memory.subject_id,
            incident_id=memory.incident_id,
            title=memory.title,
            origin=MemoryOrigin.DERIVED,
        )
        session.add(row)
        made.append(row)
        known.add((memory.region_id, memory.source_key))
    await session.flush()
    return made


async def fade_memories(session: AsyncSession, rules: Rules, epoch: int) -> list[tuple[int, int, RegionMemoryKind]]:
    faded: list[tuple[int, int, RegionMemoryKind]] = []
    kept = set(await session.scalars(select(TraditionProfileRow.origin_incident_id).where(TraditionProfileRow.origin_incident_id.is_not(None))))
    for row in list(await session.scalars(select(RegionMemoryRow).where(RegionMemoryRow.held.is_(False), RegionMemoryRow.epoch < epoch))):
        if not fades(rules, row.kind) or (row.incident_id is not None and row.incident_id in kept):
            continue
        row.magnitude = max(0, row.magnitude - LAND_MEMORIES[row.kind].fade(rules))
        if row.magnitude <= 0:
            await session.delete(row)
            faded.append((row.region_entity_id, row.world_id, row.kind))
    await session.flush()
    return faded


async def derive_sacredness(
    session: AsyncSession, rules: Rules, atlas: RegionAtlas, grounds: dict[int, RegionEnvironmentRow], memories: dict[int, list[RegionMemoryRow]]
) -> int:
    table = rules.terrain
    added: dict[int, int] = defaultdict(int)
    temples = await session.scalars(
        select(EntityRow.id).where(
            EntityRow.entity_type == EntityType.STRUCTURE, EntityRow.engine_kind.in_(list(HOLY_STRUCTURES)), EntityRow.status == EntityStatus.CANON
        )
    )
    for temple_id in temples:
        region = atlas.top_region(temple_id)
        if region is not None:
            added[region] += table.sacred_temple
    sites = await flags_by_entity(session, EntityFlag.PILGRIMAGE_SITE)
    for site_id in sorted(sites):
        region = atlas.top_region(site_id)
        if region is not None:
            added[region] += table.sacred_pilgrimage_site
    corpses = await session.scalars(select(EntityRow.id).where(EntityRow.engine_kind == EngineKind.DEAD_GOD, EntityRow.status == EntityStatus.CANON))
    for corpse_id in corpses:
        region = atlas.top_region(corpse_id)
        if region is not None:
            added[region] += table.sacred_god_corpse
    for region_id in await session.scalars(
        select(PlaceEnvironmentRow.region_entity_id).where(PlaceEnvironmentRow.nexus.is_(True), PlaceEnvironmentRow.region_entity_id.is_not(None))
    ):
        if region_id is not None:
            added[region_id] += table.sacred_nexus
    changed = 0
    for region_id, ground in grounds.items():
        if "sacredness" in ground.locked:
            continue
        drawn = rules.land_memory.discovery_draw * sum(1 for row in memories.get(region_id, []) if row.kind is RegionMemoryKind.DISCOVERY)
        value = clamp_int(
            added.get(region_id, 0) + drawn + round_half_up(holiness(rules, memories.get(region_id, [])) * table.sacred_memory_pct / PERCENT), 0, PERCENT
        )
        if value != ground.sacredness:
            ground.sacredness = value
            changed += 1
    return changed
