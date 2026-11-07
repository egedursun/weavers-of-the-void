from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.economy import LoanRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.renown import ReputationRow
from aerona.db.tables.warfare import CasusBelliRow, WarProductionRow, WarSideRow
from aerona.domain.enums.economy import CommodityKind, LoanStatus
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.military import PeaceTermKind, UnitKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.enums.war import CasusBelliKind, WarSide
from aerona.engine.military import orders
from aerona.engine.military.clash import night_honour
from aerona.engine.military.support import reluctance, support_aim
from aerona.engine.military.terms import fights_on, separate_peace, terror, war_between
from aerona.engine.military.war_costs import peace_budget, term_cost
from aerona.engine.military.war_lines import keep_war_lines, war_output
from aerona.engine.primitives.stats import stat
from aerona.engine.renown.book import acclaim
from aerona.engine.services.casus_belli import gather_casus_belli
from aerona.engine.services.war import OngoingWar, open_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx
from tests.engine.warfare.test_battle_depth_rp2 import side as battle_side
from tests.engine.warfare.test_battle_depth_rp2 import unit as battle_unit

RULES = Rules()


async def pair(session: AsyncSession, world_id: int) -> tuple:
    first = await make(session, "Oron Folk", EntityType.PEOPLE, world_id, population=8000)
    second = await make(session, "Ilsa Folk", EntityType.PEOPLE, world_id, population=8000)
    return first, second


async def test_a_defaulted_debt_becomes_a_casus_belli_that_ripens_and_lapses(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    lender, borrower = await pair(session, world_id)
    session.add(
        LoanRow(
            lender_entity_id=lender.id,
            borrower_entity_id=borrower.id,
            principal=100,
            interest_pct=10,
            issued_epoch=1,
            due_epoch=5,
            status=LoanStatus.DEFAULTED,
            purpose="war",
        )
    )
    await session.flush()
    tally = await gather_casus_belli(ctx)
    row = await session.scalar(select(CasusBelliRow).where(CasusBelliRow.holder_entity_id == lender.id))
    assert tally.found.get(CasusBelliKind.DEBT_DEFAULT.value) == 1 and row is not None and row.target_entity_id == borrower.id
    assert row.justification == 0
    await gather_casus_belli(ctx)
    assert row.justification == RULES.war_conduct.justify_gain
    later = ctx.epoch + RULES.war_conduct.casus_belli_epochs + 1
    lapsed = await gather_casus_belli(make_ctx(session, epoch=later))
    renewed = list(await session.scalars(select(CasusBelliRow).where(CasusBelliRow.holder_entity_id == lender.id)))
    assert lapsed.lapsed == 1 and [(item.since_epoch, item.justification) for item in renewed] == [(later, 0)]


async def test_a_war_on_a_ripe_casus_belli_is_justified_and_one_without_is_not(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    attacker, defender = await pair(session, world_id)
    cause = CasusBelliRow(holder_entity_id=attacker.id, target_entity_id=defender.id, kind=CasusBelliKind.VENDETTA, justification=80, since_epoch=1, locked=[])
    session.add(cause)
    await session.flush()
    war = await open_war(ctx, attacker, defender)
    assert war.justified and war.casus_belli_id == cause.id and cause.used_war_id == war.id
    third = await make(session, "Kel Folk", EntityType.PEOPLE, world_id, population=8000)
    unjust = await open_war(ctx, attacker, third)
    side = await session.get(WarSideRow, (unjust.id, attacker.id))
    assert not unjust.justified and side is not None
    assert side.support == RULES.war_conduct.support_start - RULES.war_conduct.unjustified_support


async def test_war_support_is_lower_for_an_unjustified_attacker_than_for_its_defender(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    attacker, defender = await pair(session, world_id)
    war = await open_war(ctx, attacker, defender)
    attacking = await session.get(WarSideRow, (war.id, attacker.id))
    defending = await session.get(WarSideRow, (war.id, defender.id))
    assert attacking is not None and defending is not None
    aim_attacker = await support_aim(ctx, war, attacking, dead=0, maimed=0, occupied=0)
    aim_defender = await support_aim(ctx, war, defending, dead=0, maimed=0, occupied=0)
    assert aim_attacker < aim_defender
    assert await support_aim(ctx, war, defending, dead=4000, maimed=0, occupied=2) < aim_defender


async def test_war_score_pays_for_demands_by_kind_and_size(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    attacker, defender = await pair(session, world_id)
    war = await open_war(ctx, attacker, defender)
    war.score = 3
    table = RULES.war_conduct
    assert await peace_budget(ctx, war, attacker.id) == table.base_budget + 3 * table.score_unit
    assert await peace_budget(ctx, war, defender.id) == table.base_budget
    assert await term_cost(ctx, PeaceTermKind.VASSALAGE, {}, None) > await term_cost(ctx, PeaceTermKind.MARRIAGE, {}, None)
    assert await term_cost(ctx, PeaceTermKind.CESSION, {}, defender.id) > await term_cost(ctx, PeaceTermKind.CESSION, {}, None)


async def test_a_worn_ally_makes_a_separate_peace_and_a_beaten_side_with_support_fights_on(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    attacker, defender = await pair(session, world_id)
    ally = await make(session, "Vey Folk", EntityType.PEOPLE, world_id, population=4000)
    war = await open_war(ctx, attacker, defender)
    row = WarSideRow(war_id=war.id, entity_id=ally.id, side=WarSide.ATTACKER, joined_epoch=ctx.epoch, weariness=RULES.war_conduct.separate_peace_at, locked=[])
    session.add(row)
    await session.flush()
    assert await separate_peace(ctx, OngoingWar(war, attacker.id, defender.id), row) and row.left_epoch == ctx.epoch
    beaten = await session.get(WarSideRow, (war.id, defender.id))
    assert beaten is not None
    beaten.support, beaten.weariness = 90, 0
    assert await fights_on(ctx, war, defender) and beaten.weariness == RULES.war_conduct.refusal_weariness
    beaten.support = 10
    assert not await fights_on(ctx, war, defender)


async def test_a_massacre_hardens_a_people_that_does_not_shun_war(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    attacker, defender = await pair(session, world_id)
    war = await open_war(ctx, attacker, defender)
    side = await session.get(WarSideRow, (war.id, defender.id))
    assert side is not None
    before = side.support
    assert not await terror(ctx, war.id, attacker, defender, "massacre")
    assert side.support == before + RULES.war_conduct.harden_support


async def test_a_war_line_grows_more_efficient_and_cuts_civilian_goods(session: AsyncSession, world_id: int) -> None:
    rules = replace(RULES, war_conduct=replace(RULES.war_conduct, efficiency_gain=10, efficiency_cap=30))
    ctx = make_ctx(session, rules)
    attacker, defender = await pair(session, world_id)
    await open_war(ctx, attacker, defender)
    counts = await keep_war_lines(ctx)
    line = await session.get(WarProductionRow, attacker.id)
    assert counts["opened"] == 2 and line is not None and line.efficiency == 0
    for _ in range(4):
        await keep_war_lines(ctx)
    assert line.efficiency == 30
    assert await war_output(ctx, attacker.id, line.commodity) == 1.3
    assert await war_output(ctx, attacker.id, CommodityKind.CLOTH) == 1 - rules.war_conduct.civilian_cut_pct / 100


async def test_low_war_support_raises_fewer_levies(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    attacker, defender = await pair(session, world_id)
    war = await open_war(ctx, attacker, defender)
    side = await session.get(WarSideRow, (war.id, attacker.id))
    assert side is not None
    table = RULES.war_conduct
    assert reluctance(table.low_support_levy_pct, table.support_neutral, table.support_neutral) == 0
    assert reluctance(table.low_support_levy_pct, 0, table.support_neutral) == table.low_support_levy_pct / 100
    assert reluctance(table.low_support_levy_pct, side.support, table.support_neutral) > 0


async def test_steep_tolls_give_a_casus_belli_and_tribute_costs_by_its_amount(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    issuer, partner = await pair(session, world_id)
    session.add(
        TradePolicyRow(
            issuer_node_id=issuer.id,
            kind=TradePolicyKind.TARIFF,
            partner_node_id=partner.id,
            rate_pct=RULES.war_conduct.toll_dispute_pct,
            since_epoch=1,
            locked=[],
        )
    )
    await session.flush()
    tally = await gather_casus_belli(ctx)
    assert tally.found.get(CasusBelliKind.TRADE_DISPUTE.value) == 1
    small = await term_cost(ctx, PeaceTermKind.TRIBUTE, {"amount": 10, "epochs": 3}, None)
    large = await term_cost(ctx, PeaceTermKind.TRIBUTE, {"amount": 1000, "epochs": 3}, None)
    assert large > small


async def test_executing_a_captive_of_the_enemy_is_terror(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    captor, home = await pair(session, world_id)
    war = await open_war(ctx, captor, home)
    assert await war_between(ctx, captor.id, home.id) == war.id
    assert await war_between(ctx, captor.id, captor.id) == war.id
    side = await session.get(WarSideRow, (war.id, home.id))
    assert side is not None
    before = side.support
    await terror(ctx, war.id, captor, home, "execution of a captive")
    assert side.support != before


async def test_a_night_raid_shames_a_people_that_prizes_honour(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session)
    raider_folk, foe_folk = await pair(session, world_id)
    session.add_all(
        [CultureValueRow(entity_id=raider_folk.id, axis=ValueAxis.HONOUR, value=80), CultureValueRow(entity_id=foe_folk.id, axis=ValueAxis.HONOUR, value=80)]
    )
    army = await orders.raise_standing_army(ctx, raider_folk.id, 200)
    await session.flush()
    raider = battle_side("Raiders", [battle_unit(UnitKind.LEVY, 50, ident=1)], ident=raider_folk.id)
    raider.entity = raider_folk
    raider.stacks[0].row.army_entity_id = army.id
    foe = battle_side("Foe", [battle_unit(UnitKind.LEVY, 50, ident=2)], ident=foe_folk.id)
    foe.entity = foe_folk
    morale = stat(army, "morale") or 0
    assert await night_honour(ctx, raider, foe) == 1 and (stat(army, "morale") or 0) < morale
    views = list(
        await session.scalars(select(ReputationRow).where(ReputationRow.subject_node_id == raider_folk.id, ReputationRow.axis == ReputationAxis.TRICKERY))
    )
    assert views and views[0].value > 0


async def test_a_first_unheard_ill_repute_makes_no_empty_reputation(session: AsyncSession, world_id: int) -> None:
    first, second = await pair(session, world_id)
    assert await acclaim(session, first.id, second.id, ReputationAxis.HONOUR, amount=-10, epoch=1) is None
    assert await session.scalar(select(ReputationRow).where(ReputationRow.subject_node_id == first.id)) is None
