from sqlalchemy import select

from aerona.catalog.statecraft import DEMAND_TEXT
from aerona.db.tables.polity import TreatyProfileRow, VassalageRow
from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow
from aerona.db.write_guard import held
from aerona.domain.enums.intrigue import FavourOrigin
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import TreatyStatus
from aerona.domain.enums.statecraft import CrisisDemand, CrisisSide, CrisisState
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.intrigue.favours import owe
from aerona.engine.military.aims import cede
from aerona.engine.polity.accords import end_treaty
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.crises import CrisisTally, Verdict, ripe_crises
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import record
from aerona.engine.services.war import declare_war

LEGITIMACY = "legitimacy"


async def backers_of(ctx: TickContext, crisis: CrisisRow, side: CrisisSide) -> list[CrisisBackerRow]:
    return list(
        await ctx.session.scalars(
            select(CrisisBackerRow).where(CrisisBackerRow.crisis_id == crisis.id, CrisisBackerRow.side == side).order_by(CrisisBackerRow.backer_entity_id)
        )
    )


async def release(ctx: TickContext, overlord: Realm, vassal_id: int | None) -> bool:
    row = await ctx.session.get(VassalageRow, vassal_id) if vassal_id is not None else None
    if row is None or row.overlord_entity_id != overlord.entity.id or held(row.vassal_entity_id):
        return False
    treaty = await ctx.session.get(TreatyProfileRow, row.treaty_entity_id) if row.treaty_entity_id is not None else None
    if treaty is not None and treaty.status is TreatyStatus.IN_FORCE:
        await end_treaty(ctx, treaty, TreatyStatus.FULFILLED, "released at a power's demand")
    await ctx.session.delete(row)
    return True


async def concede(ctx: TickContext, book: RealmBook, crisis: CrisisRow, demander: Realm, target: Realm) -> bool:
    if crisis.demand is CrisisDemand.CEDE_REGION:
        winner = await living_entity(ctx.session, demander.profile.core_entity_id) if demander.profile.core_entity_id is not None else None
        loser = await living_entity(ctx.session, target.profile.core_entity_id) if target.profile.core_entity_id is not None else None
        return winner is not None and loser is not None and crisis.subject_node_id is not None and await cede(ctx, book, winner, loser, crisis.subject_node_id)
    if crisis.demand is CrisisDemand.RELEASE_VASSAL:
        return await release(ctx, target, crisis.subject_node_id)
    if crisis.demand is CrisisDemand.CONVERT:
        if crisis.subject_node_id is None or "state_religion_id" in target.profile.locked:
            return False
        target.profile.state_religion_id = crisis.subject_node_id
        return True
    paid = min(crisis.amount, max(0, target.profile.treasury))
    return paid > 0 and move_amount(target.profile, demander.profile, "treasury", paid)


async def reward_backers(ctx: TickContext, crisis: CrisisRow, demander: Realm) -> None:
    core = demander.profile.core_entity_id
    if core is None:
        return
    for backer in await backers_of(ctx, crisis, CrisisSide.DEMANDER):
        if backer.promised > 0:
            await owe(ctx, demander.entity.id, backer.backer_entity_id, FavourOrigin.WAR_SUPPORT, backer.promised)


def shame(realm: Realm, amount: int) -> None:
    if LEGITIMACY not in realm.profile.locked:
        realm.profile.legitimacy = clamp_int(realm.profile.legitimacy - amount, 0, 100)


async def go_to_war(ctx: TickContext, crisis: CrisisRow, demander: Realm, target: Realm) -> bool:
    first, second = demander.profile.core_entity_id, target.profile.core_entity_id
    if first is None or second is None:
        return False
    reason = f"the crisis over a demand to {DEMAND_TEXT[crisis.demand]} came to war"
    if not await declare_war(ctx, first, second, reason, cause=WarCause.DECLARED, world_cap=False, brokered=True):
        return False
    for side, foe in ((CrisisSide.DEMANDER, second), (CrisisSide.TARGET, first)):
        for backer in await backers_of(ctx, crisis, side):
            realm = await living_entity(ctx.session, backer.backer_entity_id)
            if realm is not None and not held(realm.id):
                await declare_war(ctx, realm.id, foe, reason, cause=WarCause.DECLARED, world_cap=False, brokered=True)
    return True


async def settle(ctx: TickContext, book: RealmBook, verdict: Verdict, tally: CrisisTally) -> None:
    crisis = verdict.crisis
    demander, target = book.realms.get(crisis.demander_entity_id), book.realms.get(crisis.target_entity_id)
    state = verdict.state
    if demander is None or target is None:
        state = CrisisState.BACKED_DOWN
    elif state is CrisisState.BACKED_DOWN:
        shame(demander, ctx.rules.statecraft.back_down_legitimacy)
        tally.backed_down += 1
    elif state is CrisisState.CONCEDED:
        await concede(ctx, book, crisis, demander, target)
        await reward_backers(ctx, crisis, demander)
        shame(target, ctx.rules.statecraft.back_down_legitimacy)
        tally.conceded += 1
    elif await go_to_war(ctx, crisis, demander, target):
        tally.wars += 1
    else:
        return
    crisis.state, crisis.resolved_epoch = state, ctx.epoch
    if demander is not None and target is not None:
        await record(
            ctx,
            f"statecraft.crisis_{state.value}_{crisis.demand.value}",
            roles={IncidentRole.ACCUSER: demander.entity.id, IncidentRole.TARGET: target.entity.id},
            facts={"escalation": crisis.escalation, "legitimacy_lost": ctx.rules.statecraft.back_down_legitimacy},
            place=target.profile.capital_entity_id,
        )


async def tend_crises(ctx: TickContext, tally: CrisisTally) -> None:
    verdicts = await ripe_crises(ctx, tally)
    book = await RealmBook.load(ctx.session)
    for verdict in verdicts:
        await settle(ctx, book, verdict, tally)
