from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.catalog.life.polity import CRISIS_CAUSES
from aerona.catalog.life_traits import REGIONAL_STANDING_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow, PolityRegardRow
from aerona.db.write_guard import held
from aerona.domain.enums.intrigue import HookDemand
from aerona.domain.enums.life_traits import RegionalStandingTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.statecraft import CrisisDemand, CrisisSide, CrisisState
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.intrigue.leverage import leaned_on
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.recording.record import StepDraft, record

GREAT = having(REGIONAL_STANDING_TRAITS, RegionalStandingTrait.GREAT)
ESCALATION = "escalation"
STATE = "state"


@dataclass
class CrisisTally:
    opened: int = 0
    backed: int = 0
    escalated: int = 0
    backed_down: int = 0
    conceded: int = 0
    wars: int = 0


@dataclass(frozen=True)
class Verdict:
    crisis: CrisisRow
    state: CrisisState


async def open_between(ctx: TickContext, first: int, second: int) -> CrisisRow | None:
    found: CrisisRow | None = await ctx.session.scalar(
        select(CrisisRow)
        .where(
            CrisisRow.state == CrisisState.ESCALATING,
            or_(
                (CrisisRow.demander_entity_id == first) & (CrisisRow.target_entity_id == second),
                (CrisisRow.demander_entity_id == second) & (CrisisRow.target_entity_id == first),
            ),
        )
        .limit(1)
    )
    return found


def nearest_land(book: RealmBook, demander: Realm, target: Realm) -> int | None:
    best: tuple[int, int] | None = None
    for theirs in sorted(target.territory):
        for mine in demander.territory:
            hops = book.atlas.region_hops(mine, theirs)
            if hops is not None and (best is None or (hops, theirs) < best):
                best = (hops, theirs)
    if best is not None:
        return best[1]
    return min(target.territory) if target.territory else None


async def open_crisis(ctx: TickContext, demander: Realm, target: Realm, demand: CrisisDemand, *, subject_id: int | None, amount: int = 0) -> CrisisRow | None:
    if held(demander.entity.id) or held(target.entity.id) or demander.entity.id == target.entity.id:
        return None
    if await open_between(ctx, demander.entity.id, target.entity.id) is not None:
        return None
    row = CrisisRow(
        demander_entity_id=demander.entity.id,
        target_entity_id=target.entity.id,
        demand=demand,
        subject_node_id=subject_id,
        amount=amount,
        opened_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(
        ctx,
        f"statecraft.crisis_opened_{demand.value}",
        roles={IncidentRole.ACCUSER: demander.entity.id, IncidentRole.TARGET: target.entity.id},
        facts={"subject": subject_id, "amount": amount},
        steps=(StepDraft(StepAction.THREATEN, actor=demander.entity.id, target=target.entity.id),),
        place=target.profile.capital_entity_id,
    )
    return row


async def crisis_instead(ctx: TickContext, first_id: int, second_id: int, cause: WarCause) -> bool:
    demand = CRISIS_CAUSES.get(cause)
    if demand is None:
        return False
    book = await RealmBook.load(ctx.session)
    demander, target = book.realm_for(first_id), book.realm_for(second_id)
    if demander is None or target is None or demander.entity.id == target.entity.id:
        return False
    if await open_between(ctx, demander.entity.id, target.entity.id) is not None:
        return True
    if not ctx.rng(f"statecraft.crisis.{demander.entity.id}.{target.entity.id}.{ctx.epoch}").chance(ctx.rules.statecraft.crisis_pct):
        return False
    subject = (
        nearest_land(book, demander, target)
        if demand is CrisisDemand.CEDE_REGION
        else demander.profile.state_religion_id
        if demand is CrisisDemand.CONVERT
        else None
    )
    amount = round_half_up(target.profile.treasury * ctx.rules.statecraft.pay_share_pct / PERCENT) if demand is CrisisDemand.PAY else 0
    return await open_crisis(ctx, demander, target, demand, subject_id=subject, amount=amount) is not None


async def trust_of(ctx: TickContext, holder: int, subject: int) -> int:
    row = await ctx.session.get(PolityRegardRow, (holder, subject))
    return row.trust if row is not None else PERCENT // 2


async def called_in(ctx: TickContext, book: RealmBook, crisis: CrisisRow, realm: Realm) -> CrisisSide | None:
    if realm.ruler_id is None:
        return None
    for side, party in ((CrisisSide.DEMANDER, crisis.demander_entity_id), (CrisisSide.TARGET, crisis.target_entity_id)):
        asker = book.realms.get(party)
        if asker is not None and asker.ruler_id is not None and await leaned_on(ctx, asker.ruler_id, realm.ruler_id, HookDemand.SUPPORT):
            ctx.count("crisis_backing_called_in")
            return side
    return None


async def gather(ctx: TickContext, book: RealmBook, crisis: CrisisRow, tally: CrisisTally) -> None:
    table = ctx.rules.statecraft
    world = book.realms[crisis.demander_entity_id].entity.world_id
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        realm_id = realm.entity.id
        if realm_id in (crisis.demander_entity_id, crisis.target_entity_id) or realm.entity.world_id != world or held(realm_id):
            continue
        if await ctx.session.get(CrisisBackerRow, (crisis.id, realm_id)) is not None:
            continue
        for_demander = await trust_of(ctx, realm_id, crisis.demander_entity_id)
        for_target = await trust_of(ctx, realm_id, crisis.target_entity_id)
        side: CrisisSide | None = None
        swing = False
        if max(for_demander, for_target) >= table.backer_trust:
            side = CrisisSide.DEMANDER if for_demander > for_target else CrisisSide.TARGET
        elif realm.profile.standing in GREAT:
            side, swing = CrisisSide.DEMANDER, True
        else:
            side = await called_in(ctx, book, crisis, realm)
        if side is None:
            continue
        ctx.session.add(CrisisBackerRow(crisis_id=crisis.id, backer_entity_id=realm_id, side=side, promised=table.swing_promise if swing else 0, swing=swing))
        tally.backed += 1
    await ctx.session.flush()


async def power_of(ctx: TickContext, strength: MilitaryStrength, realm: Realm | None) -> float:
    core = await living_entity(ctx.session, realm.profile.core_entity_id) if realm is not None and realm.profile.core_entity_id is not None else None
    return await strength.power(core) if core is not None else 0.0


async def side_power(ctx: TickContext, book: RealmBook, strength: MilitaryStrength, crisis: CrisisRow, side: CrisisSide) -> float:
    lead = crisis.demander_entity_id if side is CrisisSide.DEMANDER else crisis.target_entity_id
    total = await power_of(ctx, strength, book.realms.get(lead))
    for backer in await ctx.session.scalars(select(CrisisBackerRow).where(CrisisBackerRow.crisis_id == crisis.id, CrisisBackerRow.side == side)):
        total += await power_of(ctx, strength, book.realms.get(backer.backer_entity_id))
    return total


async def weigh(ctx: TickContext, book: RealmBook, crisis: CrisisRow, tally: CrisisTally) -> Verdict | None:
    table = ctx.rules.statecraft
    if crisis.demander_entity_id not in book.realms or crisis.target_entity_id not in book.realms:
        return Verdict(crisis, CrisisState.BACKED_DOWN)
    await gather(ctx, book, crisis, tally)
    strength = await MilitaryStrength.load(ctx.session, ctx.rules)
    demanding = await side_power(ctx, book, strength, crisis, CrisisSide.DEMANDER)
    resisting = await side_power(ctx, book, strength, crisis, CrisisSide.TARGET)
    ratio = table.back_down_ratio_pct / PERCENT
    if demanding < resisting * ratio:
        return Verdict(crisis, CrisisState.BACKED_DOWN)
    if resisting < demanding * ratio:
        return Verdict(crisis, CrisisState.CONCEDED)
    if crisis.escalation + 1 >= table.crisis_steps:
        return Verdict(crisis, CrisisState.WAR)
    if ESCALATION not in crisis.locked:
        crisis.escalation += 1
        tally.escalated += 1
    return None


async def ripe_crises(ctx: TickContext, tally: CrisisTally) -> list[Verdict]:
    book = await RealmBook.load(ctx.session)
    verdicts: list[Verdict] = []
    for crisis in list(await ctx.session.scalars(select(CrisisRow).where(CrisisRow.state == CrisisState.ESCALATING).order_by(CrisisRow.id))):
        if STATE in crisis.locked or held(crisis.demander_entity_id) or held(crisis.target_entity_id):
            continue
        verdict = await weigh(ctx, book, crisis, tally)
        if verdict is not None:
            verdicts.append(verdict)
    return verdicts
