import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.foreign_gods import OuterBargainRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.entity import CivilizationTier, EntityStatus, EntityType
from aerona.domain.enums.horror import HorrorTarget
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import JourneyIntent, RouteClosure, TravelMethod
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import OuterBeingStats, PeopleStats, SpeciesStats
from aerona.domain.models.profiles import TravelResource
from aerona.engine.context import TickContext
from aerona.engine.cosmos.actions import bargain_with_outer, cleanse_leak, seal_gate
from aerona.engine.cosmos.horror_model import HORROR_PRESETS
from aerona.engine.cosmos.resources import define_cosmic_resource
from aerona.engine.phases.civilization import set_tier
from aerona.engine.phases.creatures import cross_species, force_mutation
from aerona.engine.phases.horror import order_horror_event, set_son_sanity
from aerona.engine.phases.sky import SkyOrder, order_sky_event
from aerona.engine.phases.travel import send_expedition, sever_by_hand, stitch_by_hand
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_son, make_world, teach, tick, tuned


async def test_seal_gate_and_cleanse(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "pantheon", outer_expel_chance=100))
    other = await make_world(session, "Velmor")
    other.leakage = 30
    route = await make_route(session, cosmos.home.id, other.id)
    await seal_gate(ctx, route.id, "Aeron")
    assert not route.active and route.closure is RouteClosure.SEALED
    assert other.leakage == 30 - rules.pantheon.seal_leak_reduction
    being = await make_entity(session, "Unspoken", EntityType.OUTER_BEING, OuterBeingStats(influence=40), world_id=other.id)
    text = await cleanse_leak(ctx, other.id, "Aeron")
    assert "pushed outside" in text and being.status is EntityStatus.DESTROYED
    with pytest.raises(ValidationFailedError):
        await cleanse_leak(ctx, cosmos.home.id, "Aeron")


async def test_bargain_with_outer(ctx: TickContext, cosmos: Cosmos) -> None:
    son = await make_son(ctx.session, "Velan", cosmos.home.id)
    sibling = await make_son(ctx.session, "Morak", cosmos.home.id)
    being = await make_entity(ctx.session, "Unspoken", EntityType.OUTER_BEING, OuterBeingStats(influence=40), world_id=cosmos.home.id)
    gain = await bargain_with_outer(ctx, son.id, being.id, "a key to every gate")
    pantheon = ctx.rules.pantheon
    assert gain == pantheon.bargain_essence_base + round(40 / pantheon.bargain_influence_divisor)
    assert await ctx.session.scalar(select(OuterBargainRow)) is not None
    assert await SonRepository(ctx.session).relation(son.id, sibling.id) == -pantheon.bargain_sibling_relation_loss


async def test_manual_services(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    other = await make_world(session, "Velmor")
    region = await make_region(session, "Port", other.id)
    people = await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=8000), world_id=cosmos.home.id)
    await teach(session, people, KnowledgeBranch.GATE_LORE)
    route = await make_route(session, cosmos.home.id, other.id, TravelMethod.ANCIENT_GATE)
    with pytest.raises(ValidationFailedError):
        await send_expedition(session, rules, people.id, route.id, JourneyIntent.COLONY, population=500)
    await set_tier(session, rules, people.id, CivilizationTier.CITY_STATE, lock=False)
    journey = await send_expedition(session, rules, people.id, route.id, JourneyIntent.COLONY, population=500)
    assert isinstance(journey, JourneyRow)
    assert "storm" in await sever_by_hand(session, rules, route.id, "Aeron", duration=2)
    assert "reopened the severed route" in await stitch_by_hand(session, rules, route.id, "Aeron")
    beast = await make_entity(session, "Graveling", EntityType.SPECIES, SpeciesStats(strength=50, danger=40), world_id=other.id, location_id=region.id)
    deer = await make_entity(session, "Glimdeer", EntityType.SPECIES, SpeciesStats(strength=20, danger=10), world_id=other.id, location_id=region.id)
    mutant = await force_mutation(session, rules, beast.id)
    chimera = await cross_species(session, rules, beast.id, deer.id)
    assert mutant.id != chimera.id
    eclipse = await order_sky_event(session, rules, SkyEventKind.ECLIPSE, SkyOrder(world_id=other.id, by="Aeron"))
    assert eclipse.world_id == other.id
    row, eye = await order_horror_event(session, rules, other.id, HORROR_PRESETS["minds_marked"])
    assert row.target is HorrorTarget.MINDS and other.name in eye
    son = await make_son(session, "Velan", cosmos.home.id)
    assert (await set_son_sanity(session, son.id, 150)).sanity == 100
    resource = await define_cosmic_resource(session, TravelResource(name="Starglass", rule="Melt to fold."))
    assert resource.name == "Starglass"
    with pytest.raises(ValidationFailedError):
        await define_cosmic_resource(session, TravelResource(name="Other"))
