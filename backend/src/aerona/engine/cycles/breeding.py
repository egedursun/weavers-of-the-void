from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.cycles import MortalCasteRow, PeopleReproductionRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.cycles import ReproductiveCaste, ReproductiveSystem
from aerona.domain.enums.demography import Sex
from aerona.engine.cycles.lineage import caste_of, reproduction_of, sexes_fixed
from aerona.rules.registry import Rules

SEXLESS = frozenset({ReproductiveSystem.AMBISEXUAL, ReproductiveSystem.CASTE, ReproductiveSystem.ASEXUAL})


async def reproduction_at(session: AsyncSession, community_id: int) -> PeopleReproductionRow | None:
    community = await session.get(EntityRow, community_id)
    return await reproduction_of(session, community) if community is not None else None


async def fixed_sexes_at(session: AsyncSession, community_id: int) -> bool:
    row = await reproduction_at(session, community_id)
    return row is None or sexes_fixed(row.system)


def system_growth(rules: Rules, row: PeopleReproductionRow | None) -> float:
    table = rules.reproduction_systems
    if row is None:
        return 1.0
    if row.system is ReproductiveSystem.CASTE:
        return max(0.0, row.breeder_pct / max(1, table.breeder_norm_pct))
    if row.system is ReproductiveSystem.ASEXUAL:
        return table.asexual_growth_pct / PERCENT
    if row.system is ReproductiveSystem.AMBISEXUAL:
        return table.ambisexual_growth_pct / PERCENT
    return 1.0


async def breeding_factor(session: AsyncSession, rules: Rules, community_id: int) -> float:
    return system_growth(rules, await reproduction_at(session, community_id))


async def soldier_factor(session: AsyncSession, rules: Rules, community: EntityRow) -> float:
    row = await reproduction_of(session, community)
    if row is None or row.system is not ReproductiveSystem.CASTE:
        return 1.0
    table = rules.reproduction_systems
    return max(0.1, 1 + (row.soldier_pct - table.soldier_norm_pct) * table.soldier_levy_weight / PERCENT / PERCENT)


def born_sex(rules: Rules, system: ReproductiveSystem, rng: SeededRandom) -> Sex:
    if system in SEXLESS or rng.chance(rules.fertility.other_sex_pct):
        return Sex.OTHER
    return Sex.FEMALE if rng.chance(PERCENT // 2) else Sex.MALE


def caste_for(row: PeopleReproductionRow, rng: SeededRandom) -> ReproductiveCaste:
    weights = {ReproductiveCaste.BREEDER: row.breeder_pct, ReproductiveCaste.SOLDIER: row.soldier_pct, ReproductiveCaste.WORKER: row.worker_pct}
    if not any(weights.values()):
        return ReproductiveCaste.WORKER
    castes = [caste for caste, weight in weights.items() if weight > 0]
    return rng.weighted(castes, [float(weights[caste]) for caste in castes])


async def bearer_among(session: AsyncSession, first: EntityRow, second: EntityRow, rng: SeededRandom, fallback: EntityRow) -> EntityRow:
    row = await reproduction_of(session, first)
    if row is None:
        return fallback
    if row.system is ReproductiveSystem.AMBISEXUAL:
        return first if rng.chance(PERCENT // 2) else second
    if row.system is ReproductiveSystem.CASTE:
        for mortal in (first, second):
            if await caste_of(session, mortal.id) is ReproductiveCaste.BREEDER:
                return mortal
    return fallback


async def assign_caste(session: AsyncSession, child: EntityRow, parent: EntityRow, rng: SeededRandom, epoch: int) -> MortalCasteRow | None:
    row = await reproduction_of(session, parent)
    if row is None or row.system is not ReproductiveSystem.CASTE or await session.get(MortalCasteRow, child.id) is not None:
        return None
    caste = MortalCasteRow(mortal_entity_id=child.id, caste=caste_for(row, rng), since_epoch=epoch, locked=[])
    session.add(caste)
    return caste
