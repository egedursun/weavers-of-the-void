from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.monetary import MonetaryAuthorityRow, MonetaryRateRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import CurrencyIssuer
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.monetary import MonetaryAim
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.finance.credit import interest_for
from aerona.engine.monetary.authorities import MonetaryTally, establish, price_factor
from aerona.engine.monetary.policy import tend_authority
from aerona.engine.monetary.rescue import rescue_bank, spread_run
from aerona.engine.monetary.tend import apply_legacy
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules
from tests.engine.warfare.factories import society


async def minted(
    session: AsyncSession, world: CoreWorld, name: str = "Ravenmark", *, trust: int = 80, debased: int | None = None
) -> tuple[EntityRow, CurrencyRow]:
    town = await settlement(session, f"{name} Town", world, world.regions[0], population=5000)
    await society(session, town.id)
    currency = CurrencyRow(
        issuer_entity_id=town.id, name=name, purity=100, supply=1000, trust=trust, minted_epoch=0, debased_epoch=debased, issuer_kind=CurrencyIssuer.COMMUNITY
    )
    session.add(currency)
    await session.flush()
    row = await session.get(CommunitySocietyRow, town.id)
    assert row is not None
    row.currency_id = currency.id
    await session.flush()
    return town, currency


async def bank_at(session: AsyncSession, world: CoreWorld, town: EntityRow, name: str, wealth: int) -> EntityRow:
    return await entity(session, name, EntityType.FACTION, FactionStats(strength=20, wealth=wealth, sway=10), world_id=world.world.id, location_id=town.id)


async def test_each_currency_gets_an_authority_and_a_debased_one_funds_the_state(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town, sound = await minted(session, world)
    _other, debased = await minted(session, world, "Ashmark", debased=0)
    tally = MonetaryTally()
    await apply_legacy(ctx, tally)
    rows = {row.currency_id: row for row in await session.scalars(select(MonetaryAuthorityRow))}
    assert tally.founded == 2 and rows[sound.id].aim is MonetaryAim.STABLE_VALUE and rows[debased.id].aim is MonetaryAim.FUND_THE_STATE
    assert rows[sound.id].independence == 0 and rows[sound.id].holder_node_id == town.id and rows[sound.id].issuer_node_id == town.id


async def test_the_rate_is_felt_an_epoch_later_and_moves_interest_and_prices(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town, currency = await minted(session, world, trust=40)
    authority = await establish(ctx, currency)
    tally = MonetaryTally()
    await tend_authority(ctx, authority, tally)
    neutral = ctx.rules.monetary.neutral_rate
    assert authority.rate == neutral + ctx.rules.monetary.rate_step and authority.effective_rate == neutral
    assert tally.rates_moved == 1 and await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "money.rate_set")) is not None
    authority.rate = neutral + 10
    await tend_authority(ctx, authority, tally)
    assert authority.effective_rate == neutral + 10
    assert await interest_for(ctx, town.id, 10) == 10 + 10 * ctx.rules.monetary.rate_to_interest_pct // 100
    assert await price_factor(ctx, currency.id) < 1
    assert len(list(await session.scalars(select(MonetaryRateRow)))) == 2


async def test_funding_the_state_raises_supply_lowers_trust_and_fills_the_treasury(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    _town, currency = await minted(session, world)
    authority = await establish(ctx, currency)
    authority.aim = MonetaryAim.FUND_THE_STATE
    await tend_authority(ctx, authority, MonetaryTally())
    assert currency.supply == 1000 + 1000 * ctx.rules.monetary.state_issue_pct // 100
    assert currency.trust == 80 - ctx.rules.monetary.state_issue_trust_loss
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "money.printed_for_state")) is not None


async def test_a_peg_holds_while_reserves_last_and_then_breaks_with_a_shock(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    _town, anchor = await minted(session, world, "Goldmark", trust=90)
    _home, currency = await minted(session, world, "Tinmark", trust=60)
    authority = await establish(ctx, currency)
    authority.aim, authority.peg_currency_id, authority.reserves = MonetaryAim.PEG, anchor.id, 1000
    tally = MonetaryTally()
    await tend_authority(ctx, authority, tally)
    assert tally.pegs_held == 1 and currency.trust == 90 and authority.reserves < 1000
    currency.trust, authority.reserves = 30, 10
    before = authority.rate
    await tend_authority(ctx, authority, tally)
    assert tally.pegs_broken == 1 and authority.aim is MonetaryAim.STABLE_VALUE and authority.rate > before
    assert authority.peg_broken_epoch == ctx.epoch


async def test_a_lender_of_last_resort_saves_a_bank_and_without_one_the_fall_runs_on_others(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    town, currency = await minted(session, world)
    authority = await establish(ctx, currency)
    failing = await bank_at(session, world, town, "The Failing House", 1)
    other = await bank_at(session, world, town, "The Standing House", 80)
    assert not await rescue_bank(ctx, failing)
    before = authority.reserve_requirement_pct
    struck = await spread_run(ctx, failing, [failing, other])
    assert struck == [other.id] and stat(other, "wealth") == 80 - 80 * ctx.rules.monetary.run_spread_pct // 100
    assert authority.lender_of_last_resort and authority.reserve_requirement_pct == before + ctx.rules.monetary.run_reserve_step
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "money.lender_of_last_resort")) is not None
    authority.reserves = 1000
    assert await rescue_bank(ctx, failing)
    assert stat(failing, "wealth") == ctx.rules.monetary.rescue_wealth and authority.reserves == 1000 - ctx.rules.monetary.rescue_cost


async def test_a_ruler_at_war_bends_a_dependent_authority_but_not_an_independent_one(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "bend", tuned_rules(monetary={"bend_chance_pct": 100}))
    town, currency = await minted(session, world)
    foe = await settlement(session, "Foehold", world, world.regions[0])
    await BondRepository(session).connect(BondDraft(town.id, foe.id, BondKind.ENEMY, ctx.epoch, "at war"))
    authority = await establish(ctx, currency)
    tally = MonetaryTally()
    await tend_authority(ctx, authority, tally)
    assert tally.bent == 1 and authority.aim is MonetaryAim.FUND_THE_STATE
    bank = await bank_at(session, world, town, "The Free Bank", 50)
    authority.aim, authority.independence, authority.holder_node_id = MonetaryAim.STABLE_VALUE, 100, bank.id
    await tend_authority(ctx, authority, tally)
    assert authority.aim is MonetaryAim.STABLE_VALUE and tally.bent == 1
