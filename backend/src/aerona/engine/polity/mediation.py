from sqlalchemy import func, select

from aerona.catalog.life_traits import TREATY_KIND_TRAITS, having
from aerona.catalog.pacts import DECLARED_STANDINGS, PARTY_ROLES, PAUSED_STATES, PRINCIPAL_ROLES, STANDINGS
from aerona.constants.units import PERCENT, TENTHS
from aerona.db.tables.polity import TreatyPartyRow, TreatyProfileRow
from aerona.db.tables.statecraft import CrisisRow, PolityRegardRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.intrigue import FavourOrigin
from aerona.domain.enums.life_traits import TreatyKindTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import PartyRole, RegionalStanding, TreatyStatus
from aerona.domain.enums.statecraft import CrisisState
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.intrigue.favours import owe
from aerona.engine.polity.accords import end_treaty, parties_of
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.regard import alarm, realm_ids, shift_regard
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record

ALLIANCE_KINDS = having(TREATY_KIND_TRAITS, TreatyKindTrait.ALLIANCES)
STANDING = "standing"
STATUS = "status"


async def mediators_of(ctx: TickContext, treaty_id: int) -> list[int]:
    return [row.party_node_id for row in await parties_of(ctx.session, treaty_id) if PARTY_ROLES[row.role].settles]


async def principals_of(ctx: TickContext, treaty_id: int) -> list[int]:
    return [row.party_node_id for row in await parties_of(ctx.session, treaty_id) if row.role in PRINCIPAL_ROLES]


async def settle_dispute(ctx: TickContext, profile: TreatyProfileRow, obligor_id: int) -> bool:
    for mediator in await mediators_of(ctx, profile.treaty_entity_id):
        if held(mediator):
            continue
        await record(
            ctx,
            "treaty.mediated",
            roles={IncidentRole.MEDIATOR: mediator, IncidentRole.SUBJECT: profile.treaty_entity_id, IncidentRole.ACCUSED: obligor_id},
            facts={"standing": ctx.rules.treaties.mediator_standing},
        )
        return True
    return False


async def join_as_mediator(ctx: TickContext, profile: TreatyProfileRow, mediator_id: int) -> bool:
    if profile.status is not TreatyStatus.IN_FORCE or held(profile.treaty_entity_id, mediator_id):
        return False
    if mediator_id in {row.party_node_id for row in await parties_of(ctx.session, profile.treaty_entity_id)}:
        return False
    ctx.session.add(TreatyPartyRow(treaty_entity_id=profile.treaty_entity_id, party_node_id=mediator_id, role=PartyRole.MEDIATOR))
    await ctx.session.flush()
    await record(
        ctx,
        "treaty.mediated",
        roles={IncidentRole.MEDIATOR: mediator_id, IncidentRole.SUBJECT: profile.treaty_entity_id},
        facts={"standing": ctx.rules.treaties.mediator_standing},
    )
    return True


async def suspend_treaty(ctx: TickContext, profile: TreatyProfileRow, by_id: int, reason: str) -> bool:
    if profile.status is not TreatyStatus.IN_FORCE or STATUS in profile.locked or held(profile.treaty_entity_id):
        return False
    profile.status = TreatyStatus.SUSPENDED
    loss = ctx.rules.treaties.suspension_trust_loss
    suspender = await realm_ids(ctx, by_id)
    for party in await principals_of(ctx, profile.treaty_entity_id):
        other = await realm_ids(ctx, party)
        if other is not None and suspender is not None and other != suspender:
            await shift_regard(ctx, other, suspender, trust=-loss)
    await record(
        ctx,
        "treaty.suspended",
        roles={IncidentRole.ACTOR: by_id, IncidentRole.SUBJECT: profile.treaty_entity_id},
        facts={"trust_lost": loss},
    )
    return True


def leaderless(book: RealmBook, party_ids: list[int]) -> int | None:
    for party in party_ids:
        realm = book.realm_of(party)
        if realm is not None and realm.ruler_id is None:
            return party
    return None


async def tend_suspended(ctx: TickContext, book: RealmBook) -> dict[str, int]:
    counts = {"suspended": 0, "resumed": 0, "lapsed": 0}
    live = select(TreatyProfileRow).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE).order_by(TreatyProfileRow.treaty_entity_id)
    for profile in list(await ctx.session.scalars(live)):
        party = leaderless(book, await principals_of(ctx, profile.treaty_entity_id))
        if party is not None and await suspend_treaty(ctx, profile, party, "a party is without a ruler"):
            counts["suspended"] += 1
    paused = select(TreatyProfileRow).where(TreatyProfileRow.status.in_(list(PAUSED_STATES))).order_by(TreatyProfileRow.treaty_entity_id)
    for profile in list(await ctx.session.scalars(paused)):
        if STATUS in profile.locked or held(profile.treaty_entity_id):
            continue
        if profile.until_epoch is not None and ctx.epoch >= profile.until_epoch:
            await end_treaty(ctx, profile, TreatyStatus.EXPIRED, "it lapsed while suspended")
            counts["lapsed"] += 1
        elif leaderless(book, await principals_of(ctx, profile.treaty_entity_id)) is None:
            profile.status = TreatyStatus.IN_FORCE
            counts["resumed"] += 1
    return counts


async def trust_in(ctx: TickContext, holder: int, subject: int) -> int:
    row = await ctx.session.get(PolityRegardRow, (holder, subject))
    return row.trust if row is not None else PERCENT // 2


async def find_mediator(ctx: TickContext, book: RealmBook, crisis: CrisisRow) -> int | None:
    sides = {crisis.demander_entity_id, crisis.target_entity_id}
    world = book.realms[crisis.demander_entity_id].entity.world_id if crisis.demander_entity_id in book.realms else None
    best: tuple[int, int] | None = None
    for realm in book.realms.values():
        if realm.entity.id in sides or realm.entity.world_id != world or held(realm.entity.id):
            continue
        trust = min([await trust_in(ctx, side, realm.entity.id) for side in sorted(sides)])
        bonus = PERCENT if realm.profile.standing in DECLARED_STANDINGS else 0
        if trust >= PERCENT // 2 and (best is None or trust + bonus > best[0]):
            best = (trust + bonus, realm.entity.id)
    return best[1] if best is not None else None


async def mediate_crisis(ctx: TickContext, book: RealmBook, crisis: CrisisRow, mediator_id: int) -> bool:
    if crisis.state is not CrisisState.ESCALATING or STATUS in crisis.locked or held(crisis.demander_entity_id, crisis.target_entity_id, mediator_id):
        return False
    if mediator_id in (crisis.demander_entity_id, crisis.target_entity_id):
        return False
    crisis.state, crisis.mediator_entity_id, crisis.resolved_epoch = CrisisState.MEDIATED, mediator_id, ctx.epoch
    gain = ctx.rules.treaties.mediator_standing
    mediator = book.realms.get(mediator_id)
    for side in (crisis.demander_entity_id, crisis.target_entity_id):
        await shift_regard(ctx, side, mediator_id, trust=gain)
        realm = book.realms.get(side)
        if realm is not None and mediator is not None and realm.ruler_id is not None and mediator.ruler_id is not None:
            await owe(ctx, realm.ruler_id, mediator.ruler_id, FavourOrigin.RELIEF, gain)
    await record(
        ctx,
        "crisis.mediated",
        roles={IncidentRole.MEDIATOR: mediator_id, IncidentRole.ACCUSER: crisis.demander_entity_id, IncidentRole.TARGET: crisis.target_entity_id},
        facts={"demand": crisis.demand, "escalation": crisis.escalation},
    )
    return True


async def leave_alliances(ctx: TickContext, realm: Realm) -> int:
    core = realm.profile.core_entity_id
    if core is None:
        return 0
    joined = (
        select(TreatyProfileRow)
        .join(TreatyPartyRow, TreatyPartyRow.treaty_entity_id == TreatyProfileRow.treaty_entity_id)
        .where(TreatyPartyRow.party_node_id == core, TreatyProfileRow.status == TreatyStatus.IN_FORCE, TreatyProfileRow.kind.in_(list(ALLIANCE_KINDS)))
        .order_by(TreatyProfileRow.treaty_entity_id)
    )
    left = 0
    for profile in list(await ctx.session.scalars(joined)):
        if STATUS not in profile.locked and not held(profile.treaty_entity_id):
            await end_treaty(ctx, profile, TreatyStatus.EXPIRED, "a party declared itself neutral")
            left += 1
    return left


async def declare_neutral(ctx: TickContext, realm: Realm) -> bool:
    if realm.profile.standing is RegionalStanding.NEUTRAL or STANDING in realm.profile.locked or held(realm.entity.id):
        return False
    realm.profile.standing = RegionalStanding.NEUTRAL
    left = await leave_alliances(ctx, realm)
    await record(ctx, "polity.declared_neutral", roles={IncidentRole.SUBJECT: realm.entity.id}, facts={"alliances_left": left})
    return True


async def warring_realms(ctx: TickContext, book: RealmBook, world_id: int | None) -> int:
    ids = [realm.entity.id for realm in book.realms.values() if realm.entity.world_id == world_id]
    if not ids:
        return 0
    found = await ctx.session.scalar(
        select(func.count(func.distinct(WarSideRow.entity_id)))
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id.in_(ids), WarSideRow.left_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
    )
    return int(found or 0)


async def keep_neutrality(ctx: TickContext, book: RealmBook) -> dict[str, int]:
    counts = {"declared": 0, "traded": 0}
    table = ctx.rules.diplomacy
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if held(realm.entity.id):
            continue
        wars = await warring_realms(ctx, book, realm.entity.world_id)
        if not STANDINGS[realm.profile.standing].allies:
            members = book.members(realm)
            capital = next((member for member in members if member.id == realm.profile.capital_entity_id), members[0] if members else None)
            if capital is not None and wars and not held(capital.id):
                shift_stat(capital, "prosperity", table.neutral_trade_pct * wars / TENTHS, high=PERCENT)
                counts["traded"] += 1
            continue
        alone = realm.profile.standing is RegionalStanding.MINOR_POWER and wars >= 2
        if alone and ctx.rng(f"neutral.{realm.entity.id}.{ctx.epoch}").chance(table.neutral_declare_pct) and await declare_neutral(ctx, realm):
            counts["declared"] += 1
    return counts


async def breach_neutrality(ctx: TickContext, aggressor_id: int, target_id: int) -> bool:
    book = await RealmBook.load(ctx.session)
    target = book.realm_for(target_id)
    if target is None or STANDINGS[target.profile.standing].allies:
        return False
    aggressor = book.realm_for(aggressor_id)
    if aggressor is None:
        return False
    await alarm(ctx, aggressor.entity.id, ctx.rules.diplomacy.neutral_breach_alarm, book)
    return True
