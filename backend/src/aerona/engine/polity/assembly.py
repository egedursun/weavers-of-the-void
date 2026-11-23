from dataclasses import dataclass

from sqlalchemy import or_, select

from aerona.catalog.pacts import RESOLUTIONS
from aerona.constants.units import PERCENT
from aerona.db.faction_kinds import of_kinds
from aerona.db.tables.affairs import ResolutionRow, ResolutionVoteRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.economy import ROUTE_DANGER_COLUMNS, TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.statecraft import SphereRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind, LegitimacyBasis
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.statecraft import ResolutionKind, ResolutionState
from aerona.engine.context import TickContext
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook, enact
from aerona.engine.polity.regard import shift_regard
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import shift_stat, stat, stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.community_relations import change_relation, relation

RESOLUTION_REASON = "a resolution of the assembly"
STATE = "state"
WEIGHT_DIVISOR = 1000


@dataclass
class AssemblyTally:
    proposed: int = 0
    passed: int = 0
    rejected: int = 0
    lapsed: int = 0
    breaches: int = 0
    quarantined: int = 0


async def assemblies(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON, of_kinds([FactionKind.INTERWORLD_FEDERATION]))
            .order_by(EntityRow.id)
        )
    )


async def members_of(ctx: TickContext, assembly_id: int) -> list[EntityRow]:
    found = [await ctx.session.get(EntityRow, bond.source_node_id) for bond in await active_bonds(ctx.session, [BondKind.MEMBER_OF], targets=[assembly_id])]
    return sorted((row for row in found if row is not None and row.status is EntityStatus.CANON), key=lambda row: row.id)


async def standing(ctx: TickContext, assembly_id: int) -> list[ResolutionRow]:
    return list(
        await ctx.session.scalars(
            select(ResolutionRow)
            .where(ResolutionRow.assembly_entity_id == assembly_id, ResolutionRow.state.in_([ResolutionState.PROPOSED, ResolutionState.PASSED]))
            .order_by(ResolutionRow.id)
        )
    )


async def enemy_of(ctx: TickContext, members: list[EntityRow]) -> int | None:
    ids = [member.id for member in members]
    bond = await ctx.session.scalar(
        select(BondRow)
        .where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(ids), BondRow.source_node_id.not_in(ids))
        .order_by(BondRow.id)
        .limit(1)
    )
    return bond.source_node_id if bond is not None else None


async def meddling_son(ctx: TickContext, members: list[EntityRow]) -> int | None:
    ids = [member.id for member in members]
    son = await ctx.session.scalar(
        select(BondRow.incited_by_son_id)
        .where(BondRow.kind == BondKind.ENEMY, BondRow.incited_by_son_id.is_not(None), BondRow.target_node_id.in_(ids))
        .order_by(BondRow.id)
        .limit(1)
    )
    return int(son) if son is not None else None


async def outer_beings(ctx: TickContext, members: list[EntityRow]) -> bool:
    worlds = {member.world_id for member in members if member.world_id is not None}
    found = await ctx.session.scalar(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.status == EntityStatus.CANON, EntityRow.world_id.in_(list(worlds)))
        .limit(1)
    )
    return found is not None


async def plagued_world(ctx: TickContext, members: list[EntityRow]) -> int | None:
    worlds = sorted({member.world_id for member in members if member.world_id is not None})
    if len(worlds) < 2:
        return None
    found = await ctx.session.scalar(
        select(EntityRow.world_id)
        .join(OutbreakRow, OutbreakRow.region_entity_id == EntityRow.id)
        .where(OutbreakRow.status == OutbreakStatus.ACTIVE, EntityRow.world_id.in_(worlds))
        .order_by(EntityRow.world_id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def quarrel(ctx: TickContext, members: list[EntityRow]) -> tuple[int, int] | None:
    worst: tuple[float, int, int] | None = None
    for first in members:
        for second in members:
            if first.id >= second.id:
                continue
            value = await relation(ctx.session, ctx.rules, first.id, second.id)
            if value < 0 and (worst is None or value < worst[0]):
                worst = (value, first.id, second.id)
    return (worst[1], worst[2]) if worst is not None else None


def stricken(members: list[EntityRow]) -> int | None:
    poor = [member for member in members if stat_or(member, "prosperity", PERCENT) < PERCENT // 4]
    return min(poor, key=lambda member: (stat_or(member, "prosperity", 0), member.id)).id if poor else None


async def gathered_motion(ctx: TickContext, members: list[EntityRow]) -> tuple[ResolutionKind, int | None] | None:
    plague = await plagued_world(ctx, members)
    if plague is not None:
        return ResolutionKind.QUARANTINE, plague
    pair = await quarrel(ctx, members)
    if pair is not None:
        return ResolutionKind.ARBITRATION, pair[0]
    needy = stricken(members)
    return (ResolutionKind.AID, needy) if needy is not None else None


async def motion(ctx: TickContext, members: list[EntityRow]) -> tuple[ResolutionKind, int | None] | None:
    enemy = await enemy_of(ctx, members)
    if enemy is not None:
        return ResolutionKind.EMBARGO, enemy
    son = await meddling_son(ctx, members)
    if son is not None:
        return ResolutionKind.SANCTION, son
    if await outer_beings(ctx, members):
        return ResolutionKind.VOID_BAN, None
    found = await gathered_motion(ctx, members)
    if found is not None:
        return found
    return (ResolutionKind.ROUTE_SECURITY, None) if len({member.world_id for member in members}) > 1 else None


async def aye(ctx: TickContext, member: EntityRow, row: ResolutionRow) -> bool:
    if row.kind is ResolutionKind.EMBARGO and row.target_node_id is not None:
        return await relation(ctx.session, ctx.rules, member.id, row.target_node_id) <= 0
    if row.kind is ResolutionKind.SANCTION:
        worships = await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[member.id])
        return all(bond.target_node_id != row.target_node_id for bond in worships)
    if row.kind is ResolutionKind.VOID_BAN:
        return (stat(member, "piety") or 0) >= 40
    if row.kind is ResolutionKind.QUARANTINE:
        return member.world_id != row.target_node_id
    if row.kind is ResolutionKind.AID and row.target_node_id is not None and member.id != row.target_node_id:
        return await relation(ctx.session, ctx.rules, member.id, row.target_node_id) >= 0
    return True


async def follow_powers(ctx: TickContext, book: RealmBook, member: EntityRow, votes: dict[int, bool]) -> bool | None:
    realm = book.realm_for(member.id)
    if realm is None:
        return None
    power = await ctx.session.scalar(
        select(SphereRow.power_entity_id).where(SphereRow.client_entity_id == realm.entity.id).order_by(SphereRow.strength.desc()).limit(1)
    )
    lord = book.realms.get(power) if power is not None else None
    core = lord.profile.core_entity_id if lord is not None else None
    return votes.get(core) if core is not None else None


async def vote(ctx: TickContext, book: RealmBook, row: ResolutionRow, members: list[EntityRow]) -> None:
    cast: dict[int, bool] = {}
    for member in members:
        found = await ctx.session.get(ResolutionVoteRow, (row.id, member.id))
        weight = max(1, int(stat(member, "population") or 0) // WEIGHT_DIVISOR)
        if found is not None and found.locked:
            cast[member.id] = found.aye
            continue
        choice = await aye(ctx, member, row)
        if found is None:
            found = ResolutionVoteRow(resolution_id=row.id, member_node_id=member.id)
            ctx.session.add(found)
        found.aye, found.weight = choice, weight
        cast[member.id] = choice
    for member in members:
        follows = await follow_powers(ctx, book, member, cast)
        found = await ctx.session.get(ResolutionVoteRow, (row.id, member.id))
        if follows is not None and found is not None and not found.locked:
            found.aye = follows
    await ctx.session.flush()
    rows = list(await ctx.session.scalars(select(ResolutionVoteRow).where(ResolutionVoteRow.resolution_id == row.id)))
    if "votes_for" not in row.locked:
        row.votes_for = sum(item.weight for item in rows if item.aye)
    if "votes_against" not in row.locked:
        row.votes_against = sum(item.weight for item in rows if not item.aye)


async def issuers(ctx: TickContext, book: RealmBook, members: list[EntityRow]) -> list[int]:
    return sorted({(realm.entity.id if (realm := book.realm_for(member.id)) is not None else member.id) for member in members})


async def embargo(ctx: TickContext, book: RealmBook, members: list[EntityRow], partners: list[int]) -> None:
    for issuer in await issuers(ctx, book, members):
        if held(issuer):
            continue
        for partner in partners:
            exists = await ctx.session.scalar(
                select(TradePolicyRow.id)
                .where(
                    TradePolicyRow.issuer_node_id == issuer,
                    TradePolicyRow.kind == TradePolicyKind.EMBARGO,
                    TradePolicyRow.partner_node_id == partner,
                    TradePolicyRow.reason == RESOLUTION_REASON,
                )
                .limit(1)
            )
            if exists is None and partner != issuer:
                ctx.session.add(
                    TradePolicyRow(
                        issuer_node_id=issuer, kind=TradePolicyKind.EMBARGO, partner_node_id=partner, since_epoch=ctx.epoch, reason=RESOLUTION_REASON, locked=[]
                    )
                )


async def sanctioned_realms(ctx: TickContext, book: RealmBook, son_id: int | None) -> list[int]:
    son = await ctx.session.get(SonRow, son_id) if son_id is not None else None
    if son is None or son.current_world_id is None:
        return []
    return sorted(realm.entity.id for realm in book.realms.values() if realm.entity.world_id == son.current_world_id)


async def guard_routes(ctx: TickContext, members: list[EntityRow]) -> None:
    ids = [member.id for member in members]
    routes = await ctx.session.scalars(
        select(TradeRouteProfileRow).where(TradeRouteProfileRow.first_market_id.in_(ids), TradeRouteProfileRow.second_market_id.in_(ids))
    )
    for route in routes:
        if held(route.route_entity_id):
            continue
        for column in ROUTE_DANGER_COLUMNS:
            setattr(route, column, clamp_int(getattr(route, column) - ctx.rules.affairs.route_safety, 0, 100))


async def ban_void(ctx: TickContext, book: RealmBook, members: list[EntityRow]) -> None:
    laws = await LawBook.load(ctx.session)
    for issuer in await issuers(ctx, book, members):
        realm = book.realms.get(issuer)
        if realm is None or held(issuer):
            continue
        current = laws.in_force(issuer, LawKind.RITE_RESTRICTIONS)
        level = ctx.rules.affairs.void_ban_level
        if current is None:
            await enact(ctx, realm.entity, LawKind.RITE_RESTRICTIONS, {"level": level}, basis=LegitimacyBasis.COUNCIL)
        elif "params" not in (current.locked or []) and int(current.params.get("level", 0)) < level:
            current.params = {**current.params, "level": level}


async def close_to(ctx: TickContext, row: ResolutionRow, members: list[EntityRow]) -> int:
    away = [member.id for member in members if member.world_id != row.target_node_id]
    there = select(EntityRow.id).where(EntityRow.world_id == row.target_node_id)
    routes = await ctx.session.scalars(
        select(TradeRouteProfileRow)
        .where(
            or_(
                TradeRouteProfileRow.first_market_id.in_(there) & TradeRouteProfileRow.second_market_id.in_(away),
                TradeRouteProfileRow.second_market_id.in_(there) & TradeRouteProfileRow.first_market_id.in_(away),
            ),
            TradeRouteProfileRow.status == TradeRouteStatus.OPEN,
        )
        .order_by(TradeRouteProfileRow.route_entity_id)
    )
    closed = 0
    for route in list(routes):
        if held(route.route_entity_id) or "status" in route.locked:
            continue
        route.status, route.blockaded_by_entity_id = TradeRouteStatus.BLOCKADED, row.assembly_entity_id
        closed += 1
    return closed


async def reopen(ctx: TickContext, row: ResolutionRow) -> None:
    if row.kind is not ResolutionKind.QUARANTINE:
        return
    for route in await ctx.session.scalars(
        select(TradeRouteProfileRow).where(
            TradeRouteProfileRow.blockaded_by_entity_id == row.assembly_entity_id, TradeRouteProfileRow.status == TradeRouteStatus.BLOCKADED
        )
    ):
        if not held(route.route_entity_id) and "status" not in route.locked:
            route.status, route.blockaded_by_entity_id = TradeRouteStatus.OPEN, None


async def arbitrate(ctx: TickContext, row: ResolutionRow, members: list[EntityRow], amount: int) -> None:
    pair = await quarrel(ctx, members)
    if pair is None or row.target_node_id not in pair:
        return
    first, second = pair
    await change_relation(ctx, first, second, amount, MemoryKind.FREED_US, note="a dispute settled by the council")
    await change_relation(ctx, second, first, amount, MemoryKind.FREED_US, note="a dispute settled by the council")


async def gathered_enforce(ctx: TickContext, row: ResolutionRow, members: list[EntityRow], tally: AssemblyTally, effect: int) -> bool:
    if row.kind is ResolutionKind.QUARANTINE:
        if ctx.rng(f"assembly.quarantine.{row.id}.{ctx.epoch}").chance(effect):
            tally.quarantined += await close_to(ctx, row, members)
        return True
    if row.kind is ResolutionKind.ARBITRATION:
        await arbitrate(ctx, row, members, effect)
        return True
    if row.kind is ResolutionKind.AID:
        needy = next((member for member in members if member.id == row.target_node_id), None)
        if needy is not None and not held(needy.id):
            shift_stat(needy, "prosperity", effect, high=PERCENT)
        return True
    return False


async def enforce(ctx: TickContext, book: RealmBook, row: ResolutionRow, members: list[EntityRow], tally: AssemblyTally) -> None:
    effect = RESOLUTIONS[row.kind].effect(ctx.rules)
    if await gathered_enforce(ctx, row, members, tally, effect):
        return
    if not ctx.rng(f"assembly.enforce.{row.id}.{ctx.epoch}").chance(effect):
        return
    if row.kind is ResolutionKind.EMBARGO and row.target_node_id is not None:
        target = book.realm_for(row.target_node_id)
        await embargo(ctx, book, members, [target.entity.id if target is not None else row.target_node_id])
    elif row.kind is ResolutionKind.SANCTION:
        await embargo(ctx, book, members, await sanctioned_realms(ctx, book, row.target_node_id))
    elif row.kind is ResolutionKind.ROUTE_SECURITY:
        await guard_routes(ctx, members)
    else:
        await ban_void(ctx, book, members)
    if row.kind is ResolutionKind.EMBARGO and row.target_node_id is not None:
        for member in members:
            if await ctx.session.scalar(
                select(BondRow.id)
                .where(
                    BondRow.kind == BondKind.TRADES_WITH,
                    BondRow.state == BondState.ACTIVE,
                    BondRow.source_node_id == member.id,
                    BondRow.target_node_id == row.target_node_id,
                )
                .limit(1)
            ):
                await breach(ctx, book, member, members)
                tally.breaches += 1


async def breach(ctx: TickContext, book: RealmBook, member: EntityRow, members: list[EntityRow]) -> None:
    offender = book.realm_for(member.id)
    if offender is None:
        return
    for other in members:
        judge = book.realm_for(other.id)
        if judge is not None and judge.entity.id != offender.entity.id:
            await shift_regard(ctx, judge.entity.id, offender.entity.id, trust=-ctx.rules.affairs.resolution_breach_trust)


async def lift(ctx: TickContext, book: RealmBook, members: list[EntityRow]) -> None:
    bound = await issuers(ctx, book, members)
    for policy in await ctx.session.scalars(
        select(TradePolicyRow).where(
            TradePolicyRow.reason == RESOLUTION_REASON, TradePolicyRow.kind == TradePolicyKind.EMBARGO, TradePolicyRow.issuer_node_id.in_(bound)
        )
    ):
        if not policy.locked and not held(policy.issuer_node_id):
            await ctx.session.delete(policy)


async def sit(ctx: TickContext, book: RealmBook, assembly: EntityRow, tally: AssemblyTally) -> None:
    members = [member for member in await members_of(ctx, assembly.id) if not held(member.id)]
    if not members:
        return
    rows = await standing(ctx, assembly.id)
    if not rows and ctx.rng(f"assembly.motion.{assembly.id}.{ctx.epoch}").chance(ctx.rules.affairs.resolution_pct):
        found = await motion(ctx, members)
        if found is not None:
            row = ResolutionRow(assembly_entity_id=assembly.id, kind=found[0], target_node_id=found[1], proposed_epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
            await ctx.session.flush()
            rows = [row]
            tally.proposed += 1
    for row in rows:
        if STATE in row.locked:
            if row.state is ResolutionState.PASSED:
                await enforce(ctx, book, row, members, tally)
            continue
        if row.state is ResolutionState.PROPOSED:
            await vote(ctx, book, row, members)
            passed = row.votes_for > row.votes_against
            row.state = ResolutionState.PASSED if passed else ResolutionState.REJECTED
            row.until_epoch = ctx.epoch + ctx.rules.affairs.resolution_epochs if passed else ctx.epoch
            tally.passed += passed
            tally.rejected += not passed
            ballots = list(await ctx.session.scalars(select(ResolutionVoteRow).where(ResolutionVoteRow.resolution_id == row.id)))
            await record(
                ctx,
                f"assembly.{'passed' if passed else 'rejected'}_{row.kind.value}",
                roles={
                    IncidentRole.AUTHORITY: assembly.id,
                    IncidentRole.TARGET: row.target_node_id,
                    IncidentRole.MEMBER: [ballot.member_node_id for ballot in ballots],
                },
                facts={"votes_for": row.votes_for, "votes_against": row.votes_against},
                steps=tuple(
                    StepDraft(
                        StepAction.VOTE,
                        actor=ballot.member_node_id,
                        amount=ballot.weight,
                        unit=FactUnit.COUNT,
                        outcome=StepOutcome.ACCEPTED if ballot.aye else StepOutcome.REFUSED,
                    )
                    for ballot in ballots
                ),
            )
        if row.state is ResolutionState.PASSED and row.until_epoch is not None and ctx.epoch >= row.until_epoch:
            row.state = ResolutionState.LAPSED
            await lift(ctx, book, members)
            await reopen(ctx, row)
            tally.lapsed += 1
        elif row.state is ResolutionState.PASSED:
            await enforce(ctx, book, row, members, tally)


async def tend_assemblies(ctx: TickContext, tally: AssemblyTally) -> None:
    book = await RealmBook.load(ctx.session)
    for assembly in await assemblies(ctx):
        if not held(assembly.id):
            await sit(ctx, book, assembly, tally)
