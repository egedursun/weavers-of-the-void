from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.pacts import STANDINGS
from aerona.db.tables.affairs import ResolutionRow
from aerona.db.tables.polity import TreatyProfileRow
from aerona.db.tables.statecraft import CrisisRow, PolityRegardRow
from aerona.domain.enums.polity import PartyRole, RegionalStanding, TreatyKind, TreatyStatus
from aerona.domain.enums.statecraft import CrisisDemand, CrisisState, ResolutionKind
from aerona.engine.context import TickContext
from aerona.engine.polity.accords import judge_mediators, sign
from aerona.engine.polity.assembly import AssemblyTally, gathered_enforce
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.mediation import declare_neutral, join_as_mediator, mediate_crisis, settle_dispute, suspend_treaty, tend_suspended
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.factories import CoreWorld
from tests.engine.diplomacy.pacts_world import crown


async def treaty(ctx: TickContext, kind: TreatyKind, first: int, second: int, until: int | None = None) -> TreatyProfileRow:
    made = await sign(ctx, kind, [(first, PartyRole.SIGNATORY), (second, PartyRole.SIGNATORY)], until=until, witnessed=False, derive=False)
    profile = await ctx.session.get(TreatyProfileRow, made.id)
    assert profile is not None
    return profile


async def test_a_third_power_settles_a_crisis_and_is_trusted_and_owed(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    (first, _), (second, _), (third, _) = [await crown(session, world, name) for name in ("Reed", "Fen", "Ash")]
    crisis = CrisisRow(demander_entity_id=first.id, target_entity_id=second.id, demand=CrisisDemand.PAY, opened_epoch=1, locked=[])
    session.add(crisis)
    await session.flush()
    assert await mediate_crisis(ctx, await RealmBook.load(session), crisis, third.id)
    assert crisis.state is CrisisState.MEDIATED and crisis.mediator_entity_id == third.id
    assert await session.get(PolityRegardRow, (first.id, third.id)) is not None


async def test_a_mediator_settles_a_dispute_and_answers_for_a_broken_treaty(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    (first, _), (second, _), (third, _) = [await crown(session, world, name) for name in ("Reed", "Fen", "Ash")]
    profile = await treaty(ctx, TreatyKind.PEACE, first.id, second.id)
    assert await join_as_mediator(ctx, profile, third.id)
    assert not await join_as_mediator(ctx, profile, third.id)
    assert await settle_dispute(ctx, profile, first.id)
    assert await judge_mediators(ctx, profile, kept=False, broken=True) == 2


async def test_a_suspended_treaty_rests_without_breach_and_lapses_at_its_term(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    (first, _), (second, _) = [await crown(session, world, name) for name in ("Reed", "Fen")]
    profile = await treaty(ctx, TreatyKind.PEACE, first.id, second.id, until=ctx.epoch)
    assert await suspend_treaty(ctx, profile, first.id, "held in abeyance")
    assert profile.status is TreatyStatus.SUSPENDED and profile.ended_epoch is None
    counts = await tend_suspended(ctx, await RealmBook.load(session))
    assert counts["lapsed"] == 1 and profile.status is TreatyStatus.EXPIRED


async def test_a_neutral_realm_leaves_its_alliances_and_joins_none(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    (first, _), (second, _) = [await crown(session, world, name) for name in ("Reed", "Fen")]
    alliance = await treaty(ctx, TreatyKind.ALLIANCE_DEFENSIVE, first.id, second.id)
    realm = (await RealmBook.load(session)).realms[first.id]
    assert await declare_neutral(ctx, realm)
    assert realm.profile.standing is RegionalStanding.NEUTRAL and alliance.status is TreatyStatus.EXPIRED
    assert not STANDINGS[RegionalStanding.NEUTRAL].allies
    assert not await declare_neutral(ctx, realm)


async def test_council_aid_restores_a_stricken_member(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    (first, town) = await crown(session, world, "Reed")
    before = stat_or(town, "prosperity", 0)
    row = ResolutionRow(assembly_entity_id=first.id, kind=ResolutionKind.AID, target_node_id=town.id, proposed_epoch=1, locked=[])
    assert await gathered_enforce(ctx, row, [town], AssemblyTally(), 15)
    assert stat_or(town, "prosperity", 0) > before
