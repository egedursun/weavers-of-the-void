from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.referendums import ReferendumRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.referendums import Franchise, ReferendumResult, ReferendumSubject
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.polity.elections import VOTERS
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat_or

SALIENCE_PCT = total(
    ReferendumSubject,
    {
        ReferendumSubject.LAW: 50,
        ReferendumSubject.CONSTITUTION: 80,
        ReferendumSubject.INDEPENDENCE: 100,
        ReferendumSubject.UNION: 90,
        ReferendumSubject.TREATY: 50,
        ReferendumSubject.WAR: 100,
        ReferendumSubject.TRANSITION: 80,
        ReferendumSubject.RECALL: 60,
        ReferendumSubject.FAITH: 90,
    },
)


@dataclass
class ReferendumTally:
    called: int = 0
    held: int = 0
    passed: int = 0
    failed: int = 0
    voided: int = 0
    ignored: int = 0
    carried: int = 0


async def realm_of_holder(session: AsyncSession, holder: EntityRow) -> int | None:
    if holder.entity_type is EntityType.POLITY:
        return holder.id
    return await session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == holder.id).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )


async def franchise_at(session: AsyncSession, realm_id: int | None) -> Franchise:
    if realm_id is None:
        return Franchise.ALL
    for kind in (LawKind.FRANCHISE, LawKind.CONSTITUTION):
        value = await law_param(session, realm_id, kind, "voters")
        if value is not None and str(value) in {item.value for item in Franchise}:
            return Franchise(str(value))
    return Franchise.NOBLES


def voters_for(franchise: Franchise) -> frozenset[SocialClass]:
    return VOTERS[franchise.value]


async def towns_of(session: AsyncSession, holder: EntityRow) -> list[EntityRow]:
    if holder.entity_type is not EntityType.POLITY:
        return [holder]
    ids = await session.scalars(
        select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == holder.id).order_by(PolityMemberRow.member_entity_id)
    )
    return [town for town in [await session.get(EntityRow, town_id) for town_id in ids] if town is not None]


async def enfranchised_pct(ctx: TickContext, holder: EntityRow, franchise: Franchise) -> int:
    voters = voters_for(franchise)
    people = allowed = 0.0
    for town in await towns_of(ctx.session, holder):
        weight = float(max(1, stat_or(town, "population", 1)))
        shares = await class_shares(ctx.session, ctx.rules, town.id)
        people += weight
        allowed += weight * sum(share for social_class, share in shares.items() if social_class in voters) / PERCENT
    return round(allowed * PERCENT / people) if people else 0


async def pending(session: AsyncSession) -> list[ReferendumRow]:
    return list(await session.scalars(select(ReferendumRow).where(ReferendumRow.result == ReferendumResult.PENDING).order_by(ReferendumRow.id)))


async def realm_profile(session: AsyncSession, realm_id: int | None) -> PolityProfileRow | None:
    return await session.get(PolityProfileRow, realm_id) if realm_id is not None else None
