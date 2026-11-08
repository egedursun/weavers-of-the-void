from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.domain.enums.war import WarStatus
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.polity.treaties import champion_for, guard, keep_hostage, send_levies, tribute_terms
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx, tune


async def profile_of(session: AsyncSession, treaty_id: int) -> TreatyProfileRow:
    found = await session.get(TreatyProfileRow, treaty_id)
    assert found is not None
    return found


async def test_a_tribute_treaty_carries_the_standard_terms(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    terms = tribute_terms(ctx)
    assert terms["amount"] == ctx.rules.campaigns.tribute_flow and terms["epochs"] == ctx.rules.campaigns.tribute_epochs


async def test_a_hostage_lives_with_the_other_side_and_goes_home_when_the_term_ends(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, epoch=10)
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    town = await make(session, "Highwall", EntityType.SETTLEMENT, world_id, population=900)
    home = await make(session, "Lowfold", EntityType.SETTLEMENT, world_id, population=900)
    heir = await make(session, "Ivo", EntityType.MORTAL, world_id, location_id=home.id)
    clause = Clause(ClauseKind.HOSTAGE, home.id, town.id, {"mortal_id": heir.id})
    treaty = await sign(ctx, TreatyKind.PEACE, [(first.id, PartyRole.SIGNATORY), (second.id, PartyRole.SIGNATORY)], clauses=[clause], witnessed=False)
    profile = await profile_of(session, treaty.id)
    row = await session.scalar(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == treaty.id, TreatyClauseRow.kind == ClauseKind.HOSTAGE))
    assert row is not None
    assert await keep_hostage(ctx, profile, row)
    assert heir.location_id == town.id
    later = make_ctx(session, epoch=10 + ctx.rules.treaties.hostage_epochs)
    assert await keep_hostage(later, profile, row)
    assert heir.location_id == home.id


async def test_a_guarantor_answers_an_attack_on_the_land_it_guards(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, tune(Rules(), treaties={"guarantor_chance": 100}))
    ward = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    guardian = await make(session, "Sun Crown", EntityType.PEOPLE, world_id, population=20000)
    raider = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    treaty = await sign(ctx, TreatyKind.GUARANTEE, [(ward.id, PartyRole.SIGNATORY), (guardian.id, PartyRole.GUARANTOR)], witnessed=False)
    war = await open_war(ctx, raider, ward)
    war.status = WarStatus.ONGOING
    await session.flush()
    assert await guard(ctx, await profile_of(session, treaty.id)) == 1
    enemy = await session.scalar(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.source_node_id == guardian.id))
    assert enemy is not None and enemy.target_node_id == raider.id


async def test_a_champion_clause_and_a_vassals_levies_follow_their_lord(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    lord = await make(session, "Sun Crown", EntityType.PEOPLE, world_id, population=20000)
    vassal = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    foe = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    assert not await champion_for(ctx, lord.id, foe.id)
    await sign(
        ctx,
        TreatyKind.PEACE,
        [(lord.id, PartyRole.SIGNATORY), (foe.id, PartyRole.SIGNATORY)],
        clauses=[Clause(ClauseKind.CHAMPION, lord.id, foe.id)],
        witnessed=False,
    )
    assert await champion_for(ctx, lord.id, foe.id) and await champion_for(ctx, foe.id, lord.id)
    assert await send_levies(ctx, vassal.id, lord.id, 100) == 0
    war = await open_war(ctx, lord, foe)
    war.status = WarStatus.ONGOING
    await session.flush()
    assert await send_levies(ctx, None, lord.id, 100) == 0
    assert await send_levies(ctx, vassal.id, lord.id, 100) == 1
    joined = await session.get(WarSideRow, (war.id, vassal.id))
    assert joined is not None
