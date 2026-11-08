from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import bond, make


async def test_a_mortal_a_kind_and_any_other_thing_each_weigh_their_own_strength(session: AsyncSession, world_id: int) -> None:
    strength = await MilitaryStrength.load(session, Rules())
    weak = await make(session, "Tam", EntityType.MORTAL, world_id, strength=10, agility=10)
    strong = await make(session, "Bram", EntityType.MORTAL, world_id, strength=90, agility=90)
    assert await strength.power(strong) > await strength.power(weak) > 0
    tame = await make(session, "Hare", EntityType.SPECIES, world_id, danger=5, strength=5)
    fierce = await make(session, "Bear", EntityType.SPECIES, world_id, danger=80, strength=80)
    assert await strength.power(fierce) > await strength.power(tame)
    hall = await make(session, "Old Hall", EntityType.STRUCTURE, world_id, durability=70)
    assert await strength.power(hall) > 0


async def test_allies_lend_a_share_of_their_strength(session: AsyncSession, world_id: int) -> None:
    strength = await MilitaryStrength.load(session, Rules())
    first = await make(session, "Iron Folk", EntityType.PEOPLE, world_id, population=9000)
    second = await make(session, "Reed Folk", EntityType.PEOPLE, world_id, population=6000)
    assert await strength.ally_power(first) == 0
    await bond(session, first.id, second.id, BondKind.ALLY)
    assert await strength.ally_power(first) > 0 and await strength.ally_power(second) > 0
