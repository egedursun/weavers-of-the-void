from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import ProphecyConditionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, HouseProfileRow, OfficeRow
from aerona.db.tables.sons import SonPowerRow
from aerona.domain.enums.culture import LegendArchetype, ProphecyConsequence, ProphecyPredicate, ProphecyState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import ClaimBasis, OfficeKind
from aerona.domain.enums.son import PowerEffect
from aerona.domain.enums.war import WarStatus
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import HouseStats, PolityStats, ProphecyStats
from aerona.engine.lore.prophecy import OUTCOMES, Foretelling, args_of, derive, fail, met, press, seer_power, threatened_ruler
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, entity, mortal, settlement, tuned_rules

P = ProphecyPredicate


async def realm(session: AsyncSession, world: CoreWorld) -> tuple[EntityRow, EntityRow, EntityRow, EntityRow]:
    polity = await entity(session, "Kingdom of Vale", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    house = await entity(session, "House Varn", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    town = await settlement(session, "Brookhold", world, world.regions[0])
    ruler = await mortal(session, "Ana", world, town.id)
    session.add(HouseProfileRow(house_entity_id=house.id, traits=[], seats=[], locked=[]))
    session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[], since_epoch=1))
    await session.flush()
    return polity, house, town, ruler


def condition(predicate: ProphecyPredicate, args: dict[str, int | str], **values: object) -> ProphecyConditionRow:
    fields: dict[str, object] = {"audience": [], "pressure": 20, "state": ProphecyState.PENDING, "locked": []} | values
    return ProphecyConditionRow(prophecy_entity_id=0, predicate=predicate, args=args, **fields)


async def foretold(session: AsyncSession, world: CoreWorld, certainty: int = 90) -> EntityRow:
    return await entity(session, f"The Telling of {certainty}", EntityType.PROPHECY, ProphecyStats(certainty=certainty), world_id=world.world.id)


async def test_each_foretelling_reads_its_own_arguments(session: AsyncSession, world: CoreWorld) -> None:
    assert args_of(Foretelling(P.DIES, subject_id=3, within_epochs=0)) == {"entity": 3, "epochs": 1}
    assert args_of(Foretelling(P.FALLS, subject_id=4)) == {"settlement": 4}
    assert args_of(Foretelling(P.BORN_IN, subject_id=5)) == {"house": 5}
    assert args_of(Foretelling(P.SKY_EVENT)) == {"kind": SkyEventKind.ECLIPSE.value}
    assert args_of(Foretelling(P.WAR_BETWEEN, subject_id=1, second_id=2)) == {"first": 1, "second": 2}
    assert args_of(Foretelling(P.RULER_OF, subject_id=6, archetype=LegendArchetype.CHOSEN_ONE)) == {"polity": 6, "archetype": "chosen_one"}
    assert args_of(Foretelling(P.WITHIN_EPOCHS, subject_id=7))["place"] == 7


async def test_deaths_falls_births_skies_and_wars_come_to_pass(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    _, house, town, ruler = await realm(session, world)
    assert not await met(ctx, P.DIES, {"entity": ruler.id}, 0)
    ruler.status, ruler.end_epoch = EntityStatus.DEAD, ctx.epoch
    assert await met(ctx, P.DIES, {"entity": ruler.id}, 0)
    assert not await met(ctx, P.FALLS, {"settlement": town.id}, ctx.epoch + 1)
    assert await met(ctx, P.FALLS, {"settlement": 999999}, 0)
    assert not await met(ctx, P.BORN_IN, {"house": house.id}, 0)
    child = await mortal(session, "Bo", world, town.id)
    session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=child.id, joined_epoch=1, by_marriage=False))
    await session.flush()
    assert await met(ctx, P.BORN_IN, {"house": house.id}, 0)
    assert not await met(ctx, P.SKY_EVENT, {"kind": SkyEventKind.ECLIPSE.value}, 0)
    session.add(SkyEventRow(kind=SkyEventKind.ECLIPSE, epoch=ctx.epoch + 1, world_id=world.world.id))
    await session.flush()
    assert await met(ctx, P.SKY_EVENT, {"kind": SkyEventKind.ECLIPSE.value}, ctx.epoch)
    other = await settlement(session, "Fernwick", world, world.regions[0])
    assert not await met(ctx, P.WAR_BETWEEN, {"first": town.id, "second": other.id}, 0)
    war = await open_war(ctx, town, other)
    war.status = WarStatus.MOBILIZING
    assert not await met(ctx, P.WAR_BETWEEN, {"first": town.id, "second": other.id}, 0)
    war.status = WarStatus.ONGOING
    assert await met(ctx, P.WAR_BETWEEN, {"first": town.id, "second": other.id}, 0)


async def test_a_ruler_must_match_the_house_archetype_or_mark_foretold(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    polity, house, _, ruler = await realm(session, world)
    assert await met(ctx, P.RULER_OF, {"polity": polity.id}, 0)
    assert not await met(ctx, P.RULER_OF, {"polity": polity.id}, 5)
    assert not await met(ctx, P.RULER_OF, {"polity": polity.id, "house": house.id}, 0)
    assert not await met(ctx, P.RULER_OF, {"polity": polity.id, "chosen": 1}, 0)
    assert not await met(ctx, P.RULER_OF, {"polity": polity.id, "archetype": LegendArchetype.CHOSEN_ONE.value}, 0)
    await add_flag(session, ruler.id, EntityFlag.CHOSEN, 1)
    assert await met(ctx, P.RULER_OF, {"polity": polity.id, "chosen": 1}, 0)
    assert await met(ctx, P.RULER_OF, {"polity": polity.id, "archetype": LegendArchetype.CHOSEN_ONE.value}, 0)


async def test_what_a_prophecy_names_decides_what_it_foretells(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    polity, house, town, ruler = await realm(session, world)
    prophecy = await foretold(session, world)
    assert (await derive(ctx, prophecy, [house]))[0] is P.BORN_IN
    session.add(ClaimRow(claimant_entity_id=ruler.id, house_entity_id=house.id, polity_entity_id=polity.id, basis=ClaimBasis.INHERITANCE))
    await session.flush()
    assert await derive(ctx, prophecy, [house]) == (P.RULER_OF, {"polity": polity.id, "house": house.id})
    assert await derive(ctx, prophecy, [polity]) == (P.RULER_OF, {"polity": polity.id, "chosen": 1})
    assert (await derive(ctx, prophecy, [town, world.people]))[0] is P.WAR_BETWEEN
    assert (await derive(ctx, prophecy, [town]))[0] is P.FALLS
    assert (await derive(ctx, prophecy, [ruler]))[0] is P.DIES
    assert (await derive(ctx, prophecy, []))[0] is P.WITHIN_EPOCHS


async def test_every_consequence_reaches_its_target(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    polity, house, town, ruler = await realm(session, world)
    session.add(CultureValueRow(entity_id=world.people.id, axis=ValueAxis.SUPERSTITION, value=0))
    session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=ruler.id, joined_epoch=1, by_marriage=False))
    await session.flush()
    heard = condition(P.WITHIN_EPOCHS, {}, audience=[world.people.id])
    assert await OUTCOMES[ProphecyConsequence.OMEN](ctx, heard, None) is not None
    assert await OUTCOMES[ProphecyConsequence.OMEN](ctx, condition(P.WITHIN_EPOCHS, {}), None) is None
    importance = ruler.importance or 0
    assert await OUTCOMES[ProphecyConsequence.RULE](ctx, heard, ruler) is not None and (ruler.importance or 0) > importance
    defense = stat(town, "defense") or 0
    assert await OUTCOMES[ProphecyConsequence.FALL](ctx, heard, town) is not None and (stat(town, "defense") or 0) < defense
    hp = stat(ruler, "hp") or 0
    assert await OUTCOMES[ProphecyConsequence.DEATH](ctx, heard, ruler) is not None and (stat(ruler, "hp") or 0) < hp
    assert await OUTCOMES[ProphecyConsequence.DEATH](ctx, heard, town) is None
    assert await OUTCOMES[ProphecyConsequence.WAR](ctx, heard, town) is not None
    assert await OUTCOMES[ProphecyConsequence.BIRTH](ctx, heard, ruler) is not None
    assert await OUTCOMES[ProphecyConsequence.BIRTH](ctx, heard, town) is None
    assert await OUTCOMES[ProphecyConsequence.RULE](ctx, heard, None) is None
    assert polity.id


async def test_a_pressing_prophecy_strains_foretold_enemies_and_doomed_towns(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    _, _, town, _ = await realm(session, world)
    prophecy = await foretold(session, world)
    other = await settlement(session, "Fernwick", world, world.regions[0])
    assert await press(ctx, prophecy, condition(P.WAR_BETWEEN, {"first": town.id, "second": other.id})) == "the foretold enemies eye each other"
    set_stats(town, defense=50)
    assert await press(ctx, prophecy, condition(P.FALLS, {"settlement": town.id})) == f"{town.name} loses heart"
    assert (stat(town, "defense") or 0) < 50
    doubtful = await foretold(session, world, certainty=0)
    assert await press(ctx, doubtful, condition(P.FALLS, {"settlement": town.id})) is None


async def test_a_ruler_who_fears_a_named_house_moves_against_its_child(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", rules=tuned_rules(prophecy={"paranoia_chance": 100}))
    polity, house, town, _ = await realm(session, world)
    child = await mortal(session, "Bo", world, town.id)
    session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=child.id, joined_epoch=1, by_marriage=False))
    await session.flush()
    hp = stat(child, "hp") or 0
    row = condition(P.RULER_OF, {"polity": polity.id, "house": house.id})
    assert await threatened_ruler(ctx, row) is not None and (stat(child, "hp") or 0) < hp
    assert await threatened_ruler(ctx, condition(P.RULER_OF, {"polity": polity.id})) is None


async def test_a_failed_prophecy_shames_its_seer_and_cools_superstition(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test")
    _, _, town, seer = await realm(session, world)
    seer.importance = 10
    session.add(CultureValueRow(entity_id=world.people.id, axis=ValueAxis.SUPERSTITION, value=30))
    await session.flush()
    row = condition(P.FALLS, {"settlement": town.id}, audience=[world.people.id], seer_entity_id=seer.id)
    assert await fail(ctx, row) == 1
    assert row.state is ProphecyState.FAILED and (seer.importance or 0) < 10


async def test_a_seer_power_counts_once_the_son_reaches_its_level(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", rules=Rules())
    assert not await seer_power(ctx, world.son)
    session.add(SonPowerRow(son_id=world.son.id, slot=0, name="Far Sight", description="Sees ahead.", effect=PowerEffect.SEER))
    await session.flush()
    world.son.level = 100
    assert await seer_power(ctx, world.son)
