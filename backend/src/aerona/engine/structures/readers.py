from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.structure import STANDING_STATES, StructureKind
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

K = StructureKind


@dataclass(frozen=True)
class Working:
    structure: EntityRow
    profile: StructureProfileRow

    @property
    def strength(self) -> float:
        return self.profile.effect_pct / PERCENT


async def working(session: AsyncSession, kinds: Iterable[StructureKind], *, world_id: int | None = None, host_id: int | None = None) -> list[Working]:
    return list(await working_rows(session, tuple(kinds), world_id, host_id))


@memoized(EntityRow, NodeRow, StructureProfileRow)
async def working_rows(session: AsyncSession, kinds: tuple[StructureKind, ...], world_id: int | None, host_id: int | None) -> tuple[Working, ...]:
    statement = (
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(
            EntityRow.status == EntityStatus.CANON,
            StructureProfileRow.kind.in_(list(kinds)),
            StructureProfileRow.construction_state.in_(list(STANDING_STATES)),
            StructureProfileRow.effect_pct > 0,
        )
        .order_by(EntityRow.id)
    )
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    if host_id is not None:
        statement = statement.where(StructureProfileRow.host_entity_id == host_id)
    return tuple(Working(entity, profile) for entity, profile in (await session.execute(statement)).all())


async def strength_at(session: AsyncSession, host_id: int | None, kinds: Iterable[StructureKind]) -> float:
    if host_id is None:
        return 0.0
    return max((item.strength for item in await working(session, kinds, host_id=host_id)), default=0.0)


async def regions_of(session: AsyncSession, kinds: Iterable[StructureKind], atlas: RegionAtlas | None = None) -> dict[int, list[Working]]:
    atlas = atlas or await RegionAtlas.load(session)
    found: dict[int, list[Working]] = defaultdict(list)
    for item in await working(session, kinds):
        region = atlas.top_region(item.structure.id)
        if region is not None:
            found[region].append(item)
    return found


def region_strength(found: dict[int, list[Working]], region: int | None) -> float:
    if region is None:
        return 0.0
    return max((item.strength for item in found.get(region, [])), default=0.0)


OUTPUT_KINDS = {
    K.MILL: "mill_output_pct",
    K.FORGE: "forge_output_pct",
    K.TANNERY: "tannery_output_pct",
    K.MINE: "mine_output_pct",
    K.QUARRY: "quarry_output_pct",
    K.SHIPYARD: "shipyard_output_pct",
    K.WORKSHOP: "workshop_output_pct",
    K.ALCHEMIST_LAB: "alchemist_output_pct",
    K.MARKET: "workshop_output_pct",
    K.WAREHOUSE: "workshop_output_pct",
    K.GRANARY: "workshop_output_pct",
}


def output_bonus(rules: Rules, kind: StructureKind) -> int:
    return int(getattr(rules.structure_functions, OUTPUT_KINDS.get(kind, "workshop_output_pct")))


async def workshop_output(session: AsyncSession, rules: Rules, workshop: WorkshopRow | None) -> float:
    if workshop is None or workshop.structure_entity_id is None:
        return 1.0
    profile = await session.get(StructureProfileRow, workshop.structure_entity_id)
    if profile is None:
        return 1.0
    if profile.effect_pct <= 0:
        return 0.0
    return 1 + profile.effect_pct / PERCENT * output_bonus(rules, profile.kind) / PERCENT


async def palace_legitimacy(session: AsyncSession, rules: Rules, seats: Iterable[int | None]) -> int:
    table = rules.structure_functions
    best = 0
    for seat in sorted({item for item in seats if item is not None}):
        for item in await working(session, [K.PALACE], host_id=seat):
            splendor = stat(item.structure, "splendor") or 0
            best = max(best, round_half_up(item.strength * (table.palace_legitimacy + splendor / table.palace_splendor_divisor)))
    return best


async def rite_keeping(session: AsyncSession, rules: Rules, host_id: int | None) -> float:
    if host_id is None:
        return 0.0
    table = rules.structure_functions
    pct = {K.NECROPOLIS: table.necropolis_rite_pct, K.TOMB: table.tomb_rite_pct, K.TEMPLE: table.temple_rite_pct}
    found = await working(session, list(pct), host_id=host_id)
    return min(1.0, max((item.strength * pct[item.profile.kind] / PERCENT for item in found), default=0.0))


async def gate_opened(session: AsyncSession, rules: Rules, world_ids: Iterable[int | None]) -> bool:
    for world_id in {item for item in world_ids if item is not None}:
        if any(item.profile.effect_pct >= rules.structure_functions.gate_open_pct for item in await working(session, [K.COSMIC_GATE], world_id=world_id)):
            return True
    return False


async def kind_of(session: AsyncSession, structure_id: int) -> StructureKind | None:
    profile = await session.get(StructureProfileRow, structure_id)
    return profile.kind if profile is not None else None
