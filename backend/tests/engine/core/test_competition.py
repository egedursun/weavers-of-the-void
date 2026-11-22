from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.commerce import SupplyTierRow
from aerona.db.tables.competition import CartelRow, MarketStructureRow, PriceWarRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.governance import InsolvencyCaseRow, OrgMergerRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.orders import EconomicOrderRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.commerce import SupplyTier
from aerona.domain.enums.competition import EntryBarrier, MarketForm, PriceWarOutcome
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.governance import MergerKind, MergerStage
from aerona.domain.enums.orders import AllocationMode
from aerona.domain.enums.polity import LawKind
from aerona.domain.models.entity_stats import FactionStats, PolityStats
from aerona.engine.competition.cartels import tend_cartel, tend_cartels
from aerona.engine.competition.law import break_monopoly, merger_barred
from aerona.engine.competition.pricing import market_factors
from aerona.engine.competition.structure import survey_market, survey_markets
from aerona.engine.competition.wars import start_war, tend_war
from aerona.engine.context import TickContext
from aerona.engine.governance.insolvency import InsolvencyTally
from aerona.engine.governance.mergers import open_bid
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules

GRAIN = CommodityKind.GRAIN


async def seller(
    session: AsyncSession, world: CoreWorld, name: str, home: EntityRow, *, wealth: int = 60, kind: FactionKind = FactionKind.MERCHANT_GUILD
) -> EntityRow:
    org = await entity(session, name, EntityType.FACTION, FactionStats(strength=30, wealth=wealth, sway=20), world_id=world.world.id, location_id=home.id)
    session.add(FactionProfileRow(faction_entity_id=org.id, kind=kind, home_entity_id=home.id, treasury=0, influence_over={}, cohort_share={}, locked=[]))
    await session.flush()
    return org


async def tier(session: AsyncSession, market: EntityRow, holder: EntityRow, share: int) -> None:
    session.add(SupplyTierRow(market_entity_id=market.id, commodity=GRAIN, tier=SupplyTier.WHOLESALE, holder_node_id=holder.id, share=share, locked=[]))
    await session.flush()


async def market_with_sellers(session: AsyncSession, world: CoreWorld, *shares: int) -> tuple[EntityRow, list[EntityRow]]:
    market = await settlement(session, "Graincross", world, world.regions[0], population=4000)
    sellers = [await seller(session, world, f"House {index}", market) for index, _share in enumerate(shares)]
    for org, share in zip(sellers, shares, strict=True):
        await tier(session, market, org, share)
    return market, sellers


async def test_a_guild_monopoly_is_a_single_seller_behind_its_guild_right_and_raises_prices(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    market = await settlement(session, "Guildhold", world, world.regions[0], population=4000)
    guild = await seller(session, world, "The Grain Guild", market)
    profile = await session.get(FactionProfileRow, guild.id)
    assert profile is not None
    profile.monopoly = GRAIN.value
    row = await survey_market(ctx, market, GRAIN)
    assert row.form is MarketForm.ONE_SELLER and row.concentration == 100 and row.sellers == {str(guild.id): 100}
    assert row.barriers.get(EntryBarrier.GUILD_RIGHT.value) == ctx.rules.competition.guild_right_barrier
    assert (await market_factors(ctx, market.id))[GRAIN] > 1


async def test_few_sellers_form_a_compact_that_raises_prices_decays_and_is_exposed_under_a_ban(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "cartel", tuned_rules(competition={"cartel_form_chance_pct": 100, "cartel_discipline_decay": 10}))
    market, sellers = await market_with_sellers(session, world, 60, 40)
    row = await survey_market(ctx, market, GRAIN)
    assert row.form is MarketForm.FEW_SELLERS
    before = (await market_factors(ctx, market.id))[GRAIN]
    counts = await tend_cartels(ctx, [row])
    cartel = await session.scalar(select(CartelRow))
    assert counts["formed"] == 1 and cartel is not None and set(cartel.members) == {org.id for org in sellers}
    assert (await market_factors(ctx, market.id))[GRAIN] > before
    await enact(ctx, market, LawKind.COMPETITION_LAW, {"cartel_ban": 100})
    cartel.secrecy = 0
    assert await tend_cartel(ctx, cartel) == "exposed"
    assert cartel.exposed and cartel.broken_epoch == ctx.epoch


async def test_a_compact_breaks_when_its_discipline_falls_under_the_gain_of_cheating(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "cheat", tuned_rules(competition={"cartel_form_chance_pct": 100, "cheat_gain_threshold": 65}))
    market, _sellers = await market_with_sellers(session, world, 55, 45)
    row = await survey_market(ctx, market, GRAIN)
    await tend_cartels(ctx, [row])
    cartel = await session.scalar(select(CartelRow))
    assert cartel is not None
    assert await tend_cartel(ctx, cartel) == "broken"


async def test_a_compact_a_god_left_with_no_members_breaks_without_stopping_the_epoch(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "empty_compact")
    cartel = CartelRow(name="Empty compact", members=[], markets=[], commodity=GRAIN, locked=[])
    session.add(cartel)
    await session.flush()
    assert await tend_cartel(ctx, cartel) == "broken"
    assert cartel.broken_epoch == ctx.epoch


async def test_a_price_war_is_won_by_the_deeper_purse_and_the_beaten_go_before_the_court(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    market, (strong, weak) = await market_with_sellers(session, world, 60, 40)
    set_stats(strong, wealth=100)
    set_stats(weak, wealth=0)
    await survey_market(ctx, market, GRAIN)
    war = await start_war(ctx, strong.id, market.id, GRAIN, cut=30, targets=[weak.id])
    tally = InsolvencyTally()
    assert await tend_war(ctx, war, tally) == "won"
    assert war.outcome is PriceWarOutcome.WON and tally.filed == 1
    assert await session.scalar(select(InsolvencyCaseRow.id).where(InsolvencyCaseRow.debtor_node_id == weak.id)) is not None
    holders = set(await session.scalars(select(SupplyTierRow.holder_node_id).where(SupplyTierRow.market_entity_id == market.id)))
    assert holders == {strong.id}
    assert (await session.scalar(select(PriceWarRow))) is war


async def test_the_law_reviews_a_merger_of_two_sellers_of_one_market_and_bars_it(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    market, (first, second) = await market_with_sellers(session, world, 55, 45)
    await survey_market(ctx, market, GRAIN)
    merger = await open_bid(ctx, first.id, second, MergerKind.MERGER, 10)
    assert await merger_barred(ctx, merger) is None
    await enact(ctx, market, LawKind.COMPETITION_LAW, {"merger_review": 60})
    assert await merger_barred(ctx, merger) is not None
    assert merger.stage is MergerStage.BID and await session.get(OrgMergerRow, merger.id) is merger


async def test_the_law_breaks_a_single_seller_in_two(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "break", tuned_rules())
    market = await settlement(session, "Onehold", world, world.regions[0], population=4000)
    guild = await seller(session, world, "The Only House", market)
    profile = await session.get(FactionProfileRow, guild.id)
    assert profile is not None
    profile.monopoly, profile.treasury = GRAIN.value, 1000
    row = await survey_market(ctx, market, GRAIN)
    await enact(ctx, market, LawKind.COMPETITION_LAW, {"monopoly_break": 100})
    child = await break_monopoly(ctx, row)
    assert child is not None and profile.monopoly is None
    offshoot = await session.get(FactionProfileRow, child.id)
    assert offshoot is not None and offshoot.treasury == 500


async def test_a_state_that_commands_its_grain_is_the_one_buyer_and_lowers_its_price(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    market, _sellers = await market_with_sellers(session, world, 10, 10)
    realm = await entity(session, "The Grain Realm", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=market.id))
    session.add(EconomicOrderRow(polity_entity_id=realm.id, sector=GRAIN, allocation=AllocationMode.COMMAND, locked=[]))
    await session.flush()
    row = await survey_market(ctx, market, GRAIN)
    assert row.form is MarketForm.ONE_BUYER


async def test_a_barrier_fades_once_what_raised_it_is_gone_and_its_fall_is_told(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "fall", tuned_rules(competition={"barrier_decay_per_epoch": 100}))
    market = await settlement(session, "Fallhold", world, world.regions[0], population=4000)
    guild = await seller(session, world, "The Fading Guild", market)
    profile = await session.get(FactionProfileRow, guild.id)
    assert profile is not None
    profile.monopoly = GRAIN.value
    row = await survey_market(ctx, market, GRAIN)
    assert EntryBarrier.GUILD_RIGHT.value in row.barriers
    profile.monopoly = None
    await tier(session, market, guild, 50)
    await survey_market(ctx, market, GRAIN)
    assert EntryBarrier.GUILD_RIGHT.value not in row.barriers
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "market.barrier_fell")) is not None
    assert await session.scalar(select(MarketStructureRow.id)) == row.id


async def test_the_owners_of_a_towns_workshops_are_the_sellers_of_what_they_make(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    market = await settlement(session, "Forgeholm", world, world.regions[0], population=4000)
    first = await seller(session, world, "The Anvil House", market)
    second = await seller(session, world, "The Hammer House", market)
    for owner, kind, level in ((first, WorkshopKind.TANNERY, 3), (second, WorkshopKind.WEAVERY, 2), (market, WorkshopKind.FORGE, 1)):
        session.add(WorkshopRow(community_entity_id=market.id, kind=kind, level=level, built_epoch=0, owner_node_id=owner.id))
    await session.flush()
    assert await survey_markets(ctx) == 1
    row = await session.scalar(select(MarketStructureRow).where(MarketStructureRow.market_entity_id == market.id))
    assert row is not None and row.commodity is CommodityKind.CLOTH
    assert set(row.sellers) == {str(first.id), str(second.id)} and row.sellers[str(first.id)] > row.sellers[str(second.id)]
