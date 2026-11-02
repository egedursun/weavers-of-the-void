import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.limits import MAX_STARS
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import Passion, Stat
from aerona.domain.enums.world import SonDistribution
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services.player import assignments
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, Recorder, add_world, bond, changed_tables, make_entity, make_son


async def test_assign_son_world_protects_from_distribution(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    other = await add_world(session, "Kesh")
    son = await make_son(session, "Velkar", world.world.id)
    await assignments.assign_son_world(scope, assignments.SonWorld(son_id=son.id, world_id=other.id))
    assert son.current_world_id == other.id
    assert son.manually_assigned_epoch == world.cosmos.epoch
    with pytest.raises(ValidationFailedError):
        await assignments.assign_son_world(scope, assignments.SonWorld(son_id=son.id, world_id=other.id))
    candidates = await assignments.distribution_candidates(scope)
    assert all(item.protected for item in candidates if item.son_id == son.id)
    await assignments.clear_son_protection(scope, assignments.SonTarget(son_id=son.id))
    assert son.manually_assigned_epoch is None


async def test_distribution_moves_lowest_scored_son(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, recorder: Recorder) -> None:
    other = await add_world(session, "Kesh")
    await make_entity(session, "Keshfolk", EntityType.PEOPLE, world_id=other.id)
    worshipped = await make_son(session, "Velkar", world.world.id)
    idle = await make_son(session, "Iolen", world.world.id)
    folk = await make_entity(session, "Orvfolk", EntityType.PEOPLE, world_id=world.world.id)
    await bond(session, folk.id, worshipped.id, BondKind.WORSHIPS)
    outcome = await assignments.distribute_now(scope, assignments.DistributeSons())
    assert outcome.values["moved"] == 1
    assert idle.current_world_id == other.id
    assert worshipped.current_world_id == world.world.id
    assert EventKind.SON_DISTRIBUTED in recorder.kinds()
    assert world.cosmos.son_distribution is SonDistribution.AUTO


async def test_move_entity_and_descendants(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    other = await add_world(session, "Kesh")
    target_region = await make_entity(session, "Kesh Vale", EntityType.REGION, world_id=other.id)
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    hero = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id, location_id=city.id)
    version = world.cosmos.map_version
    outcome = await assignments.move_entity(scope, assignments.MoveEntity(entity_id=city.id, location_id=target_region.id))
    assert city.world_id == other.id and city.location_id == target_region.id
    assert hero.world_id == other.id
    assert world.cosmos.map_version == version + 1
    assert "entities" in await changed_tables(session, outcome.ledger_entry_id)
    with pytest.raises(ValidationFailedError):
        await assignments.move_entity(scope, assignments.MoveEntity(entity_id=target_region.id, location_id=hero.id))


async def test_patron_rules(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    folk = await make_entity(session, "Orvfolk", EntityType.PEOPLE, world_id=world.world.id)
    await assignments.assign_patron(scope, assignments.AssignPatron(entity_id=folk.id, son_id=son.id))
    assert await BondRepository(session).patron(folk.id) == son.id
    await assignments.assign_patron(scope, assignments.AssignPatron(entity_id=folk.id, creator=True))
    assert await BondRepository(session).patron(folk.id) == world.creator.id
    await assignments.assign_patron(scope, assignments.AssignPatron(entity_id=folk.id))
    assert await EntityRepository(session).has_flag(folk.id, EntityFlag.GODLESS)
    with pytest.raises(ValidationFailedError):
        await assignments.assign_patron(scope, assignments.AssignPatron(entity_id=world.region.id, creator=True))


async def test_set_stat_clamps(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await assignments.set_stat(scope, assignments.SetStat(entity_id=city.id, stat="prosperity", value=250))
    assert city.stats.model_dump()["prosperity"] == 100
    await assignments.set_stat(scope, assignments.SetStat(entity_id=city.id, stat="sanity", value=-5))
    assert city.sanity == 0
    with pytest.raises(ValidationFailedError):
        await assignments.set_stat(scope, assignments.SetStat(entity_id=city.id, stat="mana", value=5))


async def test_set_tags_and_agent(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    city = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await assignments.set_tags(scope, assignments.SetTags(entity_id=city.id, add_flags=(EntityFlag.WONDER, EntityFlag.EMPIRE)))
    entities = EntityRepository(session)
    assert await entities.has_flag(city.id, EntityFlag.WONDER)
    with pytest.raises(ValidationFailedError):
        await assignments.set_tags(scope, assignments.SetTags(entity_id=city.id, add_flags=(EntityFlag.DEIFIED,)))
    await assignments.select_agent(scope, assignments.SelectAgent(entity_id=city.id))
    assert await entities.has_flag(city.id, EntityFlag.AGENT_SELECTED)
    with pytest.raises(ValidationFailedError):
        await assignments.select_agent(scope, assignments.SelectAgent(entity_id=world.region.id))


async def test_edit_son_rename_propagates_and_clamps(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    session.add(ChronicleRow(epoch=1, kind="world", text="Velkar walked the shore.", son_id=son.id))
    await session.flush()
    await assignments.edit_son(
        scope,
        assignments.EditSon(
            son_id=son.id,
            name="Thalor",
            passions={Passion.WRATH: 150},
            stats={Stat.ENDURANCE: 1},
            rarity=Rarity.EPIC,
            resources=assignments.SonResources(stars=9, essence=-3),
        ),
    )
    assert son.name == "Thalor"
    assert son.wrath == 100 and son.endurance == 1 and son.stars == MAX_STARS and son.essence == 0
    assert son.rarity is Rarity.EPIC
    texts = list(await session.scalars(select(ChronicleRow.text)))
    assert "Thalor walked the shore." in texts
    await make_son(session, "Iolen", world.world.id)
    with pytest.raises(ValidationFailedError):
        await assignments.edit_son(scope, assignments.EditSon(son_id=son.id, name="Iolen"))


async def test_add_star_requirements_and_ascension(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    world.creator.essence = 1000
    son = await make_son(session, "Velkar", world.world.id, rarity=Rarity.RARE)
    with pytest.raises(ValidationFailedError):
        await assignments.add_star(scope, assignments.SonTarget(son_id=son.id))
    son.level = 20
    son.fame = 100
    strength = son.strength
    await assignments.add_star(scope, assignments.SonTarget(son_id=son.id))
    assert son.stars == 2
    assert son.strength == strength + rules.god_actions.star_stat_gain
    son.stars = MAX_STARS
    outcome = await assignments.ascend(scope, assignments.SonTarget(son_id=son.id))
    assert son.rarity is Rarity.EPIC and son.stars == 1
    legend = await session.get(EntityRow, outcome.created_ids[0])
    assert legend is not None and legend.entity_type is EntityType.LEGEND and legend.pending_name
    assert await BondRepository(session).exists_between(legend.id, son.id, BondKind.TELLS_OF)
