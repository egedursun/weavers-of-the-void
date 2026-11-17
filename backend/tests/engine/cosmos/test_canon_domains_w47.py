import dataclasses
import typing

from aerona.api.schemas.catalogue import WorldTypeInfo
from aerona.catalog.worlds import WorldTypeSpec
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.foreign_gods import birth_local_gods
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region


async def local_god_domains(ctx: TickContext, cosmos: Cosmos, world_type: WorldType) -> set[Domain | None]:
    cosmos.home.world_type = world_type
    await make_region(ctx.session, "Harvest Reach", cosmos.home.id)
    await make_region(ctx.session, "Sound Hollow", cosmos.home.id)
    await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    (born,) = await birth_local_gods(ctx)
    return {born.domain_primary, born.domain_secondary}


async def test_a_local_god_takes_its_domains_from_the_world_canon_on_a_sand_world(ctx: TickContext, cosmos: Cosmos) -> None:
    assert await local_god_domains(ctx, cosmos, WorldType.SAND) == {Domain.SOUND, Domain.HARVEST}


async def test_a_local_god_takes_its_domains_from_the_world_canon_on_an_ocean_world(ctx: TickContext, cosmos: Cosmos) -> None:
    assert await local_god_domains(ctx, cosmos, WorldType.OCEAN) == {Domain.SOUND, Domain.HARVEST}


def test_no_kind_of_world_hands_its_gods_fixed_domains() -> None:
    hints = typing.get_type_hints(WorldTypeSpec)
    tied = [field.name for field in dataclasses.fields(WorldTypeSpec) if "Domain" in str(hints[field.name])]
    assert tied == []
    assert "domains" not in WorldTypeInfo.model_fields
