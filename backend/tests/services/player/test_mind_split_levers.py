import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.mind import IdeaRow, MindRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import Attribute, Facet, IdeaKind, IdeaState
from aerona.domain.models.entity_stats import BeastStats
from aerona.engine.mind.split import attributes_of, facets_of
from aerona.engine.primitives.stats import stat
from aerona.services.player import mind
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_sets_and_holds_attributes_and_facets(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    hero = await make_entity(session, "Teodra", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    await mind.set_attributes(scope, mind.SetAttributes(node_id=hero.id, values={Attribute.ANALYTICAL_ABILITY: 90, Attribute.MEMORY: 70}))
    found = await attributes_of(session, hero.id)
    assert found[Attribute.ANALYTICAL_ABILITY] == 90 and stat(hero, "intellect") == 80
    await mind.set_facets(scope, mind.SetFacets(node_id=hero.id, values={Facet.CAUTION: -45}))
    assert (await facets_of(session, hero.id))[Facet.CAUTION] == -45
    held = await session.get(MindRow, hero.id)
    assert held is not None and {"attributes", "facets"} <= set(held.locked)


async def test_a_beast_has_attributes_but_no_temperament(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    beast = await make_entity(
        session, "Graw", EntityType.BEAST, world_id=world.world.id, location_id=world.region.id, stats=BeastStats(hp=60, strength=70, agility=50, cunning=40)
    )
    await mind.set_attributes(scope, mind.SetAttributes(node_id=beast.id, values={Attribute.STRENGTH: 95}))
    assert (await attributes_of(session, beast.id))[Attribute.STRENGTH] == 95
    with pytest.raises(ValidationFailedError):
        await mind.set_facets(scope, mind.SetFacets(node_id=beast.id, values={Facet.ANGER: 20}))


async def test_the_god_plants_settles_and_takes_away_an_idea(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    pupil = await make_entity(session, "Kesh", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    planted = await mind.implant_idea(scope, mind.ImplantIdea(node_id=pupil.id, idea=IdeaKind.CRAFT_DEVOTION, progress=40))
    row = await session.get(IdeaRow, planted.values["idea_id"])
    assert row is not None and row.state is IdeaState.INCUBATING and row.progress == 40
    with pytest.raises(ValidationFailedError):
        await mind.implant_idea(scope, mind.ImplantIdea(node_id=pupil.id, idea=IdeaKind.CRAFT_DEVOTION))
    await mind.set_attributes(scope, mind.SetAttributes(node_id=pupil.id, values={Attribute.FOCUS: 50}, lock=False))
    await mind.edit_idea(scope, mind.EditIdea(idea_id=row.id, state=IdeaState.INTERNALISED))
    assert row.state is IdeaState.INTERNALISED and row.finished_epoch is not None
    assert (await attributes_of(session, pupil.id))[Attribute.FOCUS] == 56
    await mind.remove_idea(scope, mind.IdeaTarget(idea_id=row.id))
    assert await session.get(IdeaRow, row.id) is None
