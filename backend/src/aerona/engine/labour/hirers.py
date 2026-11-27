from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.labour import FORM_STRENGTH, STANDING_STRENGTH, TRADE_CLASS
from aerona.catalog.needs import WORKSHOP_JOBS
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.labour import WorkerBodyRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import riches_of
from aerona.engine.industry.owners import company_owner
from aerona.engine.labour.bodies import trade_workers
from aerona.engine.minds.profiles import MADE_ORIGINS
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity

MADE_MIND_SUBSTITUTE = 30
SHARE_WEIGHT_PCT = 40
SOLIDARITY_WEIGHT_PCT = 30
FUND_EPOCHS_CAP = 3
FUND_EPOCH_STRENGTH = 10
RICHES_WEIGHT_PCT = 60


async def works_of(session: AsyncSession, community_id: int, trades: list[Job]) -> list[WorkshopRow]:
    kinds = sorted(kind for kind, job in WORKSHOP_JOBS.items() if job in trades)
    if not kinds:
        return []
    query = select(WorkshopRow).where(WorkshopRow.community_entity_id == community_id, WorkshopRow.kind.in_(kinds))
    return list(await session.scalars(query.order_by(WorkshopRow.level.desc(), WorkshopRow.id)))


async def hirer_of(session: AsyncSession, community: EntityRow, trade: Job) -> EntityRow:
    for work in await works_of(session, community.id, [trade]):
        owner = await living_entity(session, work.owner_node_id)
        if owner is not None:
            return owner
    company = await living_entity(session, await company_owner(session, community))
    return company if company is not None else community


async def own_side(session: AsyncSession, body_id: int, hirer_id: int) -> bool:
    if hirer_id == body_id or await session.get(FactionMembershipRow, (body_id, hirer_id)) is not None:
        return True
    governance = await session.get(OrgGovernanceRow, body_id)
    profile = await session.get(FactionProfileRow, body_id)
    return hirer_id in {governance.head_node_id if governance is not None else None, profile.leader_entity_id if profile is not None else None}


async def made_minds_at(session: AsyncSession, community_id: int) -> int:
    here = select(EntityRow.id).where(EntityRow.location_id == community_id, EntityRow.status == EntityStatus.CANON)
    found = await session.scalars(select(MindProfileRow.node_id).where(MindProfileRow.node_id.in_(here), MindProfileRow.origin.in_(sorted(MADE_ORIGINS))))
    return len(list(found))


async def substitutes_pct(session: AsyncSession, community_id: int) -> int:
    society = await session.get(CommunitySocietyRow, community_id)
    bound = round_half_up(society.share(SocialClass.SERF_OR_SLAVE)) if society is not None else 0
    made = MADE_MIND_SUBSTITUTE if await made_minds_at(session, community_id) else 0
    return clamp_int(bound + made, 0, PERCENT)


async def worker_strength(ctx: TickContext, body: WorkerBodyRow, community_id: int, trade: Job) -> int:
    workers = await trade_workers(ctx.session, community_id, [trade])
    share = body.members * PERCENT // workers if workers else 0
    paying = body.fund // max(1, body.members * ctx.rules.labour.strike_pay) if body.members and ctx.rules.labour.strike_pay else FUND_EPOCHS_CAP
    strength = (
        min(share, PERCENT) * SHARE_WEIGHT_PCT // PERCENT
        + body.solidarity * SOLIDARITY_WEIGHT_PCT // PERCENT
        + min(paying, FUND_EPOCHS_CAP) * FUND_EPOCH_STRENGTH
        + STANDING_STRENGTH[body.standing]
        + FORM_STRENGTH[body.form]
    )
    return clamp_int(strength, 0, PERCENT)


async def hirer_strength(ctx: TickContext, hirer: EntityRow, community_id: int) -> int:
    substitutes = await substitutes_pct(ctx.session, community_id)
    strength = riches_of(hirer) * RICHES_WEIGHT_PCT // PERCENT + substitutes * ctx.rules.labour.substitute_strength_pct // PERCENT
    return clamp_int(strength, 0, PERCENT)


async def shift_contentment(ctx: TickContext, community_id: int, trade: Job, amount: int) -> None:
    society = await ctx.session.get(CommunitySocietyRow, community_id)
    if society is None or not amount:
        return
    column = f"satisfaction_{TRADE_CLASS[trade].value}"
    setattr(society, column, clamp_int(int(getattr(society, column)) + amount, 0, PERCENT))
