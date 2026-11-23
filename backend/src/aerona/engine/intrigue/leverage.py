from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CaseWitnessRow, CrimeCaseRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import HookDemand
from aerona.domain.enums.justice import CaseStage, Deposition
from aerona.domain.enums.unions import UnionPurpose
from aerona.engine.context import TickContext
from aerona.engine.departures.book import note_resignation
from aerona.engine.intrigue.favours import call_favour, hook_on, owed_to, use_hook
from aerona.engine.mortal.kin import partners_of
from aerona.engine.mortal.kinship import marry
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.enactment import back_law, pledge_vote
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.relations.book import relation

HOLDER = "holder_entity_id"
WEALTH = "wealth"
HONOUR_AT = 0


async def wed(ctx: TickContext, holder: EntityRow, target: EntityRow) -> str | None:
    if holder.entity_type is not EntityType.MORTAL or target.entity_type is not EntityType.MORTAL:
        return None
    if await partners_of(ctx.session, holder.id) or await partners_of(ctx.session, target.id):
        return None
    await marry(ctx.session, holder, target, ctx.epoch, purpose=UnionPurpose.ALLIANCE, description="a match pressed by leverage")
    return f"{target.name} agreed to wed {holder.name}"


async def step_down(ctx: TickContext, holder: EntityRow, target: EntityRow) -> str | None:
    offices = [
        row
        for row in await ctx.session.scalars(select(OfficeRow).where(OfficeRow.holder_entity_id == target.id).order_by(OfficeRow.id))
        if HOLDER not in (row.locked or [])
    ]
    if not offices:
        return None
    for office in offices:
        note_resignation(ctx, target, office)
        office.holder_entity_id, office.since_epoch = None, ctx.epoch
    return f"{target.name} gave up {len(offices)} office{'s' if len(offices) != 1 else ''}"


async def support(ctx: TickContext, holder: EntityRow, target: EntityRow) -> str | None:
    given = await ctx.session.get(MortalProfileRow, target.id)
    taken = await ctx.session.get(MortalProfileRow, holder.id)
    amount = ctx.rules.intrigue.support_wealth
    if given is None or taken is None or given.wealth < amount or not move_amount(given, taken, WEALTH, amount):
        return None
    return f"{target.name} lent {holder.name} {amount} of their wealth"


async def pledge(ctx: TickContext, holder: EntityRow, target: EntityRow) -> str | None:
    voted = await pledge_vote(ctx, holder.id, target.id)
    return f"{target.name} pledged their vote on {voted} proposal{'s' if voted != 1 else ''} to {holder.name}" if voted else None


async def back(ctx: TickContext, holder: EntityRow, target: EntityRow) -> str | None:
    backed = await back_law(ctx, holder.id, target.id)
    return f"{target.name} put the weight of rule behind {holder.name}'s laws" if backed else None


async def comply(ctx: TickContext, holder_id: int, target_id: int, demand: HookDemand) -> str | None:
    holder = await living_entity(ctx.session, holder_id)
    target = await living_entity(ctx.session, target_id)
    if holder is None or target is None or held(target_id):
        return None
    return await DEEDS[demand](ctx, holder, target)


async def appoint_holder(ctx: TickContext, holder: EntityRow, target: EntityRow) -> str | None:
    book = await RealmBook.load(ctx.session)
    seat = next((realm for realm in book.realms.values() if realm.ruler_id == target.id), None)
    if seat is None:
        return None
    office = next((row for row in seat.offices if row.holder_entity_id is None and HOLDER not in (row.locked or [])), None)
    if office is None:
        return None
    office.holder_entity_id, office.since_epoch = holder.id, ctx.epoch
    return f"{target.name} appointed {holder.name} to a vacant office"


async def keep_silent(ctx: TickContext, holder: EntityRow, target: EntityRow) -> str | None:
    rows = await ctx.session.scalars(
        select(CaseWitnessRow)
        .join(CrimeCaseRow, CrimeCaseRow.id == CaseWitnessRow.case_id)
        .where(CaseWitnessRow.witness_entity_id == target.id, CrimeCaseRow.accused_entity_id == holder.id, CrimeCaseRow.stage != CaseStage.CLOSED)
        .order_by(CaseWitnessRow.case_id)
    )
    silenced = 0
    for row in list(rows):
        if not row.locked:
            row.testimony = Deposition.SILENT
            silenced += 1
    return f"{target.name} fell silent before {silenced} court{'s' if silenced != 1 else ''}" if silenced else None


async def extort(ctx: TickContext, holder: EntityRow, target: EntityRow) -> str | None:
    given = await ctx.session.get(MortalProfileRow, target.id)
    taken = await ctx.session.get(MortalProfileRow, holder.id)
    amount = ctx.rules.intrigue.support_wealth * 2
    if given is None or taken is None or given.wealth < amount or not move_amount(given, taken, WEALTH, amount):
        return None
    return f"{target.name} paid {holder.name} {amount} of their wealth"


Deed = Callable[[TickContext, EntityRow, EntityRow], Awaitable[str | None]]
DEEDS: Mapping[HookDemand, Deed] = total(
    HookDemand,
    {
        HookDemand.MARRIAGE: wed,
        HookDemand.STEP_DOWN: step_down,
        HookDemand.SUPPORT: support,
        HookDemand.VOTE: pledge,
        HookDemand.LAW: back,
        HookDemand.APPOINTMENT: appoint_holder,
        HookDemand.SILENCE: keep_silent,
        HookDemand.PAYMENT: extort,
    },
)


async def leaned_on(ctx: TickContext, holder_id: int, target_id: int, demand: HookDemand) -> bool:
    hook = await hook_on(ctx, holder_id, target_id)
    if hook is not None:
        return await use_hook(ctx, hook, demand)
    favour = await owed_to(ctx, holder_id, target_id)
    if favour is None:
        return False
    back = await relation(ctx.session, target_id, holder_id)
    return await call_favour(ctx, favour, honour=back is not None and back.friendship >= HONOUR_AT)


async def press(ctx: TickContext, holder_id: int, target_id: int, demand: HookDemand) -> str | None:
    if not await leaned_on(ctx, holder_id, target_id, demand):
        return None
    return await comply(ctx, holder_id, target_id, demand)
