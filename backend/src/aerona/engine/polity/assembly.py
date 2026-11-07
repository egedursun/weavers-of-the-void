from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.affairs import ResolutionRow, ResolutionVoteRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.economy import ROUTE_DANGER_COLUMNS, TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.statecraft import SphereRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.polity import LawKind, LegitimacyBasis
from aerona.domain.enums.statecraft import ResolutionKind, ResolutionState
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook, enact
from aerona.engine.polity.regard import shift_regard
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat
from aerona.engine.services.community_relations import relation

RESOLUTION_REASON = "a resolution of the assembly"
KIND_TEXT: dict[ResolutionKind, str] = {
    ResolutionKind.ROUTE_SECURITY: "guard the routes between its worlds",
    ResolutionKind.EMBARGO: "embargo a realm",
    ResolutionKind.VOID_BAN: "ban rites of the void",
    ResolutionKind.SANCTION: "sanction the world of a god",
}
STATE = "state"
WEIGHT_DIVISOR = 1000


@dataclass
class AssemblyTally:
    proposed: int = 0
    passed: int = 0
    rejected: int = 0
    lapsed: int = 0
    breaches: int = 0


async def assemblies(ctx: TickContext) -> list[EntityRow]:
    return list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(
                EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON, EntityRow.engine_kind == EngineKind.INTERWORLD_FEDERATION
            )
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


async def motion(ctx: TickContext, members: list[EntityRow]) -> tuple[ResolutionKind, int | None] | None:
    enemy = await enemy_of(ctx, members)
    if enemy is not None:
        return ResolutionKind.EMBARGO, enemy
    son = await meddling_son(ctx, members)
    if son is not None:
        return ResolutionKind.SANCTION, son
    if await outer_beings(ctx, members):
        return ResolutionKind.VOID_BAN, None
    if len({member.world_id for member in members}) > 1:
        return ResolutionKind.ROUTE_SECURITY, None
    return None


async def aye(ctx: TickContext, member: EntityRow, row: ResolutionRow) -> bool:
    if row.kind is ResolutionKind.EMBARGO and row.target_node_id is not None:
        return await relation(ctx.session, ctx.rules, member.id, row.target_node_id) <= 0
    if row.kind is ResolutionKind.SANCTION:
        worships = await active_bonds(ctx.session, [BondKind.WORSHIPS], sources=[member.id])
        return all(bond.target_node_id != row.target_node_id for bond in worships)
    if row.kind is ResolutionKind.VOID_BAN:
        return (stat(member, "piety") or 0) >= 40
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


async def enforce(ctx: TickContext, book: RealmBook, row: ResolutionRow, members: list[EntityRow], tally: AssemblyTally) -> None:
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
            verdict = "passed" if passed else "voted down"
            await note(
                ctx,
                f"{assembly.name} {verdict} a resolution to {KIND_TEXT[row.kind]}, {row.votes_for} for and {row.votes_against} against.",
                key=f"assembly.{'passed' if passed else 'rejected'}",
                ids=[assembly.id, *([row.target_node_id] if row.target_node_id is not None else [])],
                kind=ChronicleKind.CIVILIZATION,
            )
        if row.state is ResolutionState.PASSED and row.until_epoch is not None and ctx.epoch >= row.until_epoch:
            row.state = ResolutionState.LAPSED
            await lift(ctx, book, members)
            tally.lapsed += 1
        elif row.state is ResolutionState.PASSED:
            await enforce(ctx, book, row, members, tally)


async def tend_assemblies(ctx: TickContext, tally: AssemblyTally) -> None:
    book = await RealmBook.load(ctx.session)
    for assembly in await assemblies(ctx):
        if not held(assembly.id):
            await sit(ctx, book, assembly, tally)
