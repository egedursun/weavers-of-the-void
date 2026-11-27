from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.effect_packages import PACKAGES, PackageSpec, StageSpec
from aerona.db.tables.afflictions import AfflictionRow


def spec_of(row: AfflictionRow) -> PackageSpec:
    return PACKAGES[row.package]


def stage_of(row: AfflictionRow) -> StageSpec | None:
    stages = spec_of(row).stages
    return stages[row.stage - 1] if 1 <= row.stage <= len(stages) else None


async def active(session: AsyncSession, bearer_id: int) -> list[AfflictionRow]:
    rows = await session.scalars(
        select(AfflictionRow).where(AfflictionRow.bearer_node_id == bearer_id, AfflictionRow.cured_epoch.is_(None)).order_by(AfflictionRow.id)
    )
    return list(rows)


async def ageless(session: AsyncSession, bearer_id: int) -> bool:
    return any((stage := stage_of(row)) is not None and stage.ageless for row in await active(session, bearer_id))
