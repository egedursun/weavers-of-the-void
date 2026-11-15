from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.ecology import SpeciesProfileRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.biology import BiologyVariant
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import NaturalTrait
from aerona.domain.enums.ecology import Diet, Sociality
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.folkways import DecisionBias
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.world_view import BindingNeed
from aerona.engine.body.variant_control import edit_biology, restore_biology, set_variant
from aerona.engine.body.variants import BiologyTally, bias_target, biology_of, folk_biology, keep_biology
from aerona.engine.context import TickContext
from aerona.engine.cosmos.world_view_control import edit_view
from aerona.engine.cosmos.world_views import ViewTally, keep_views
from aerona.engine.economy.household import eat
from aerona.engine.primitives.manual import manual_context
from aerona.services.integrity.biology import seed_missing_biology
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "biology_variants", rules=tuned_rules())


async def winged_hive(session: AsyncSession, world: CoreWorld) -> None:
    session.add(
        PeopleBiologyRow(
            people_entity_id=world.people.id,
            maturity_years=15,
            adult_years=40,
            elder_years=60,
            fertility_pct=100,
            acclimatised=TemperatureBand.TEMPERATE,
            staple=CommodityKind.GRAIN,
            body_plan=BodyPlan.AVIAN,
            traits=[NaturalTrait.HIVE_MINDED.value],
            locked=[],
        )
    )
    await session.flush()


async def test_a_people_takes_the_variants_its_body_shows_and_the_god_can_reshape_hold_and_restore_them(session: AsyncSession, world: CoreWorld) -> None:
    await winged_hive(session, world)
    ctx = await at(session, 2)
    tally = BiologyTally()
    await keep_biology(ctx, tally)
    row = await session.get(BiologyRow, world.people.id)
    assert row is not None and tally.seeded >= 1 and row.variants == ["aerial", "hive"]
    assert row.food_need_pct == 130 and row.fertility_pct == 144 and row.morale_loss_pct == 50 and row.storm_harm_pct == 150
    await set_variant(ctx, world.people.id, BiologyVariant.UNDEAD, True)
    view = await biology_of(session, world.people.id)
    assert BiologyVariant.UNDEAD in view.variants and view.fertility_pct == 0 and not view.ages and not view.breathes and "variants" in row.locked
    await edit_biology(ctx, world.people.id, {"food_need_pct": 90}, [])
    await keep_biology(await at(session, 3), BiologyTally())
    assert row.food_need_pct == 90 and "food_need_pct" in row.locked and row.variants == ["aerial", "hive", "undead"]
    await restore_biology(ctx, world.people.id)
    assert row.variants == ["aerial", "hive"] and row.food_need_pct == 130 and row.locked == []


async def test_integrity_seeds_missing_biologies_drops_unknown_variants_and_follows_the_variants_in_every_free_value(
    session: AsyncSession, world: CoreWorld
) -> None:
    await winged_hive(session, world)
    ctx = await at(session, 2)
    await keep_biology(ctx, BiologyTally())
    row = await session.get(BiologyRow, world.people.id)
    assert row is not None
    row.variants = ["aerial", "hive", "glass"]
    row.death_pct = 7
    session.add(SpeciesProfileRow(species_entity_id=world.species.id, sociality=Sociality.HIVE, diet=Diet.PHOTOSYNTHETIC))
    await session.flush()
    assert await seed_missing_biology(session, ctx.rules, 3) >= 2
    assert row.variants == ["aerial", "hive"] and row.death_pct == 120
    species = await session.get(BiologyRow, world.species.id)
    assert species is not None and species.variants == ["hive", "plant_like"] and species.food_need_pct == 40


async def test_a_body_that_needs_no_food_eats_nothing_and_a_body_that_needs_no_air_is_not_bound_to_it(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Coghold", world, world.regions[0], population=1000)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, unrest=0, locked=[]))
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.GRAIN, quantity=500, quality=50))
    await winged_hive(session, world)
    ctx = await at(session, 2)
    await keep_biology(ctx, BiologyTally())
    await set_variant(ctx, world.people.id, BiologyVariant.CONSTRUCT, True)
    assert (await folk_biology(session, town)).food_need_pct == 0
    meal = await eat(ctx, town, (CommodityKind.GRAIN,))
    grain = await session.scalar(select(CommunityStockRow.quantity).where(CommunityStockRow.community_entity_id == town.id))
    assert meal.fed_pct == 100 and grain == 500
    await keep_views(ctx, ViewTally())
    await edit_view(ctx, world.world.id, {"need": BindingNeed.AIR.value}, [])
    tally = ViewTally()
    await keep_views(await at(session, 3), tally)
    assert tally.short == 0 and tally.met >= 1


async def test_a_mortal_reads_the_biology_of_its_people_and_its_mind_leans_as_its_body_does(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Hivewall", world, world.regions[0], population=1000)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    someone = await mortal(session, "Ashe", world, town.id)
    await bond(session, someone.id, town.id, BondKind.LIVES_IN)
    await winged_hive(session, world)
    ctx = await at(session, 2)
    await keep_biology(ctx, BiologyTally())
    await set_variant(ctx, world.people.id, BiologyVariant.CONSTRUCT, True)
    view = await folk_biology(session, someone)
    assert BiologyVariant.CONSTRUCT in view.variants and view.morale_loss_pct == 0 and view.disaster(Disaster.PLAGUE) == 0
    bias_pct = ctx.rules.biology_variants.bias_pct
    assert bias_target(view, DecisionBias.LOSS_AVERSION, 90, bias_pct) == 50
    assert bias_target(view, DecisionBias.LITERALISM, 50, bias_pct) == 90
    assert bias_target(view, DecisionBias.GROUPTHINK, 50, bias_pct) == 100
    assert bias_target(view, DecisionBias.OVERCONFIDENCE, 80, bias_pct) == 50
