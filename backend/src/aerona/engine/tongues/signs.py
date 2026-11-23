from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.tongues import SIGN_CAUSES
from aerona.constants.units import PERCENT
from aerona.db.tables.couplings import SignOriginRow
from aerona.db.tables.culture import SpeakerCohortRow
from aerona.db.tables.entities import EntityRow
from aerona.rules.registry import Rules

ROUTE_CAUSES = tuple(cause for cause, spec in SIGN_CAUSES.items() if spec.spreads_on_routes)


async def route_signs(session: AsyncSession, holder_id: int) -> set[int]:
    signed = select(SignOriginRow.language_entity_id).where(SignOriginRow.cause.in_(ROUTE_CAUSES))
    known = select(SpeakerCohortRow.language_entity_id).where(
        SpeakerCohortRow.community_entity_id == holder_id, SpeakerCohortRow.share > 0, SpeakerCohortRow.language_entity_id.in_(signed)
    )
    founded = select(SignOriginRow.language_entity_id).where(SignOriginRow.community_entity_id == holder_id, SignOriginRow.cause.in_(ROUTE_CAUSES))
    return set(await session.scalars(known)) | set(await session.scalars(founded))


async def shared_sign(session: AsyncSession, ends: tuple[int, int]) -> EntityRow | None:
    common = await route_signs(session, ends[0]) & await route_signs(session, ends[1])
    return await session.get(EntityRow, min(common)) if common else None


async def sign_ease(session: AsyncSession, rules: Rules, ends: tuple[int, int]) -> float:
    return 1 + rules.tongues.trade_sign_ease_pct / PERCENT if await shared_sign(session, ends) is not None else 1.0
