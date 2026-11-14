from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import ChemicalWorksRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.crafts import ChemicalProduct
from aerona.rules.registry import Rules


async def works_output(session: AsyncSession, community_id: int, product: ChemicalProduct) -> int:
    row = await session.get(ChemicalWorksRow, (community_id, product))
    return row.output if row is not None else 0


async def fertilised(session: AsyncSession, rules: Rules, community_id: int) -> float:
    return 1 + await works_output(session, community_id, ChemicalProduct.FERTILISER) * rules.chemistry.fertiliser_yield_pct / PERCENT / PERCENT


async def blasted(session: AsyncSession, rules: Rules, community_id: int) -> float:
    return 1 + await works_output(session, community_id, ChemicalProduct.EXPLOSIVE) * rules.chemistry.explosive_mining_pct / PERCENT / PERCENT


async def soap_relief(session: AsyncSession, rules: Rules) -> dict[int, int]:
    relief: dict[int, float] = defaultdict(float)
    rows = await session.execute(
        select(ChemicalWorksRow.output, EntityRow.location_id)
        .join(EntityRow, EntityRow.id == ChemicalWorksRow.settlement_entity_id)
        .where(ChemicalWorksRow.product == ChemicalProduct.SOAP)
    )
    for output, region in rows:
        if region is not None:
            relief[region] += output * rules.chemistry.soap_disease / PERCENT
    return {region: round(value) for region, value in relief.items()}
