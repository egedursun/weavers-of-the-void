from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import SonStatus
from aerona.engine.gods.lineage import bloodline
from aerona.engine.gods.power import drain_son
from aerona.engine.gods.queries import worship_targets
from aerona.engine.gods.worship import worships_creator
from aerona.engine.phases.god_power import god_power
from aerona.engine.primitives.faith import worship_creator
from aerona.rules.registry import Rules
from aerona.services.gods import god_power as service
from tests.engine.gods.factories import GodsWorld, bond, chronicle_keys, make_context, make_entity, make_son


def _certain(rules: Rules, **changes: int) -> Rules:
    return replace(rules, god_power=replace(rules.god_power, **changes))


async def test_drain_son_numbers_and_rotating_text(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id, essence=100)
    sibling = await make_son(session, "Iolen", world.world.id, loyalty=50)
    ctx = make_context(session, rules, 2, "manual")
    result = await drain_son(ctx, world.creator, son)
    table = rules.god_power
    assert result.drawn == 50
    assert result.gained == round(50 * table.drain_son_efficiency_pct / 100)
    assert son.loyalty == 60 - table.drain_son_loyalty_loss
    assert sibling.loyalty == 50 + table.drain_witness_loyalty
    await drain_son(ctx, world.creator, son)
    await drain_son(ctx, world.creator, son)
    keys = await chronicle_keys(session)
    assert keys[:3] == [line.key for line in god_lines.DRAIN_SON[:3]]
    last = await session.scalar(select(ChronicleRow.text).order_by(ChronicleRow.id.desc()).limit(1))
    assert last is not None and "3rd time this epoch" in last


async def test_spontaneous_rebellion_drain_and_return(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _certain(rules, auto_rebel_chance=100, auto_drain_chance=100, auto_return_chance=100)
    angry = await make_son(session, "Velkar", world.world.id, loyalty=5, wrath=90, essence=80)
    loyal = await make_son(session, "Iolen", world.world.id, loyalty=70)
    world.creator.mood_anger = 90
    await god_power(make_context(session, tuned, 3, "god_power"))
    keys = await chronicle_keys(session)
    assert god_lines.REBELLION.key in keys
    assert angry.rebel
    assert angry.essence < 80
    assert await SonRepository(session).relation(angry.id, loyal.id) == -rules.son_tools.rebel_sibling_relation
    angry.loyalty = 80
    await god_power(make_context(session, tuned, 4, "god_power"))
    assert not angry.rebel
    assert god_lines.REBELLION_ENDED.key in await chronicle_keys(session)


async def test_bloody_hand_curse_and_newborns(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _certain(rules, auto_curse_chance=100)
    prophet = await make_entity(session, "Seer", EntityType.MORTAL, world_id=world.world.id)
    await EntityRepository(session).add_flag(prophet.id, EntityFlag.PROPHET, 1)
    killer = await make_entity(session, "Brann", EntityType.MORTAL, world_id=world.world.id)
    child = await make_entity(session, "Brannling", EntityType.MORTAL, world_id=world.world.id)
    await bond(session, killer.id, prophet.id, BondKind.KILLED, 2)
    await bond(session, child.id, killer.id, BondKind.DESCENDS_FROM, 2)
    await god_power(make_context(session, tuned, 3, "god_power"))
    entities = EntityRepository(session)
    assert await entities.has_flag(killer.id, EntityFlag.BLOODLINE_CURSE)
    assert await entities.has_flag(child.id, EntityFlag.BLOODLINE_CURSE)
    assert {member.id for member in await bloodline(make_context(session, rules, 3), killer)} == {killer.id, child.id}
    grandchild = await make_entity(session, "Brannkin", EntityType.MORTAL, world_id=world.world.id)
    await bond(session, grandchild.id, child.id, BondKind.DESCENDS_FROM, 3)
    await god_power(make_context(session, tuned, 4, "god_power"))
    assert await entities.has_flag(grandchild.id, EntityFlag.BLOODLINE_CURSE)
    assert god_lines.BLOODLINE_NEWBORNS.key in await chronicle_keys(session)


async def test_spontaneous_prophet_and_conversion(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _certain(rules, auto_prophet_chance=100, prophet_convert_chance=100)
    world.creator.mood_contentment = 95
    people = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    mortal = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id)
    await bond(session, mortal.id, people.id, BondKind.LIVES_IN, 1)
    await worship_creator(session, mortal, 1, "vow")
    await god_power(make_context(session, tuned, 3, "god_power"))
    assert await EntityRepository(session).has_flag(mortal.id, EntityFlag.PROPHET)
    assert await worships_creator(session, people.id)
    assert god_lines.PROPHET_COMMUNITY.key in await chronicle_keys(session)


async def test_manual_god_power_actions(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id, rarity=Rarity.EPIC)
    people = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, people.id, son.id, BondKind.WORSHIPS)
    essence = world.creator.essence
    assert await service.demote_son(session, rules, son.id) is Rarity.RARE
    assert world.creator.essence == essence - rules.god_power.demote_cost
    names = await service.convert_to_creator(session, rules, people.id)
    assert names == ["Velkar"]
    assert await worship_targets(session, people.id) == [world.creator.id]
    with pytest.raises(ValidationFailedError):
        await service.convert_to_creator(session, rules, people.id)
    harvest = await service.harvest_community(session, rules, people.id)
    assert harvest.gained > 0
    mortal = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id)
    await service.choose_prophet(session, rules, mortal.id)
    with pytest.raises(ValidationFailedError):
        await service.choose_prophet(session, rules, mortal.id)
    drained = await service.drain_mortal(session, rules, mortal.id)
    assert drained.gained == round(20 / rules.god_power.drain_mortal_hp_per_essence)
    command = await service.absolute_command(session, rules, son.id, "  Guard the vale.  ")
    assert command == "Guard the vale." and son.order_absolute
    await service.force_rebellion(session, rules, son.id, "No more chains")
    await service.pardon_rebel(session, rules, son.id)
    assert not son.rebel


async def test_wrath_destroys_and_world_wrath(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _certain(rules, wrath_death_chance=100)
    city = await make_entity(session, "Ardun", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    citizen = await make_entity(session, "Citizen", EntityType.MORTAL, world_id=world.world.id, location_id=city.id)
    result = await service.wrath(session, tuned, city.id, "pride")
    assert result.died == 1
    assert city.status is EntityStatus.DESTROYED and citizen.status is EntityStatus.DEAD
    with pytest.raises(ValidationFailedError):
        await service.wrath(session, tuned, world.region.id)
    events = await service.world_wrath(session, rules, world.world.id, EngineKind.STORM)
    assert len(events) == 1


async def test_devour_and_resurrect_mortal(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    death, gained = await service.devour_son(session, rules, son.id, "insolence")
    assert son.status is SonStatus.DEAD and death.corpse is not None
    assert gained >= 100
    mortal = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id)
    await service.drain_mortal(session, rules, mortal.id, devour=True)
    assert mortal.status is EntityStatus.DEAD
    await service.resurrect_mortal(session, rules, mortal.id)
    assert mortal.status is EntityStatus.CANON
    assert await EntityRepository(session).has_flag(mortal.id, EntityFlag.RETURNED_FROM_DEATH)
