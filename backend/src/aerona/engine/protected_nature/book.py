from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.protected_nature import ProtectedAreaRow, SpeciesProtectionRow
from aerona.domain.enums.protected_nature import ProtectedUse, ProtectionMeasure
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

LIVELIHOODS = frozenset({ProtectedUse.LOGGING, ProtectedUse.FARMING, ProtectedUse.MINING, ProtectedUse.SETTLEMENT, ProtectedUse.FISHING, ProtectedUse.BUILDING})


@dataclass
class NatureTally:
    areas: int = 0
    lifted: int = 0
    poached: int = 0
    species: int = 0
    reintroduced: int = 0
    recovered: int = 0
    movements: int = 0


def uses_of(row: ProtectedAreaRow) -> set[ProtectedUse]:
    known = {item.value: item for item in ProtectedUse}
    return {known[value] for value in row.banned_uses or [] if value in known}


def measures_of(row: SpeciesProtectionRow) -> set[ProtectionMeasure]:
    known = {item.value: item for item in ProtectionMeasure}
    return {known[value] for value in row.measures or [] if value in known}


def effective(rules: Rules, row: ProtectedAreaRow) -> int:
    return clamp_int(row.strength + row.wardens * rules.protected_nature.warden_strength, 0, PERCENT)


async def open_areas(session: AsyncSession) -> list[ProtectedAreaRow]:
    return list(await session.scalars(select(ProtectedAreaRow).where(ProtectedAreaRow.lifted_epoch.is_(None)).order_by(ProtectedAreaRow.id)))


async def protections_of(session: AsyncSession, species_id: int) -> list[SpeciesProtectionRow]:
    query = select(SpeciesProtectionRow).where(SpeciesProtectionRow.species_entity_id == species_id)
    return list(await session.scalars(query.order_by(SpeciesProtectionRow.id)))


async def hunting_marks(session: AsyncSession, rules: Rules) -> dict[tuple[int, int | None], tuple[int, int]]:
    scale = rules.protected_nature.use_cut_per_strength_pct / max(1, rules.game_laws.protect_pct)
    marks: dict[tuple[int, int | None], tuple[int, int]] = {}
    for area in await open_areas(session):
        if ProtectedUse.HUNTING in uses_of(area):
            marks[(area.region_entity_id, None)] = (clamp_int(round(effective(rules, area) * scale), 0, PERCENT), area.poaching)
    return marks


async def spared_species(session: AsyncSession, rules: Rules) -> dict[int, float]:
    cut = rules.protected_nature.use_cut_per_strength_pct / PERCENT
    found: dict[int, float] = {}
    for row in await session.scalars(select(SpeciesProtectionRow).order_by(SpeciesProtectionRow.id)):
        if ProtectionMeasure.HUNTING_BAN in measures_of(row):
            found[row.species_entity_id] = max(found.get(row.species_entity_id, 0.0), cut)
    return found
