from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import CelestialStats
from aerona.engine.gods.mood import MoodInputs, passion_matches
from aerona.engine.phases.sons import star_bonus
from aerona.engine.phases.travel import road_risk
from aerona.engine.services.war import declare_war, open_war
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx


async def test_a_war_inherits_the_typed_cause_of_its_hostility(session: AsyncSession, world_id: int) -> None:
    ctx = make_ctx(session, Rules())
    rebels = await make(session, "Ash Rebels", EntityType.FACTION, world_id, strength=50, wealth=20, sway=30)
    city = await make(session, "Stone Gate", EntityType.SETTLEMENT, world_id, population=4000, defense=20)
    assert await declare_war(ctx, rebels.id, city.id, "uprising", cause=WarCause.UPRISING, world_cap=False)
    war = await open_war(ctx, rebels, city)
    assert war.cause is WarCause.UPRISING


def test_the_epoch_star_bonus_scales_with_its_influence() -> None:
    rules = Rules()
    transition = rules.world_epoch_transition

    def star(influence: int | None) -> EntityRow:
        return EntityRow(entity_type=EntityType.CELESTIAL, stats=CelestialStats(brightness=50, influence=influence))

    assert star_bonus(rules, star(transition.star_influence_pivot)) == transition.star_domain_essence_bonus
    assert star_bonus(rules, star(0)) == 0
    assert star_bonus(rules, star(100)) > transition.star_domain_essence_bonus


def test_a_dangerous_destination_world_raises_road_risk() -> None:
    rules = Rules()
    route = RouteRow(danger=20)
    assert road_risk(rules, route, set(), None, world_danger=80) > road_risk(rules, route, set(), None)


def test_passions_count_only_the_events_they_love() -> None:
    rules = Rules()
    base = MoodInputs(wars=0, godless=0, communities=5, rebels=0, doom_clock=0, cult=0, new_life=3, actions=1, active_sons=2, unanswered_weight=0.0, battles=4)
    assert passion_matches(rules, replace(base, passions=(CreatorPassion.WAR,))) == 4
    assert passion_matches(rules, replace(base, passions=(CreatorPassion.CREATION,))) == 3
    assert passion_matches(rules, replace(base, passions=(CreatorPassion.KNOWLEDGE,), discoveries=2)) == 2
    assert passion_matches(rules, base) == 0
