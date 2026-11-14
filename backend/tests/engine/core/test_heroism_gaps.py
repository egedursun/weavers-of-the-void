from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.models.entity_stats import ItemStats, SpeciesStats
from aerona.engine.mythic.ballads import legend_carrier
from aerona.engine.phases.curses import curse_decay, cursed_items
from aerona.engine.phases.heroism import EncounterOutcome, encounter
from aerona.engine.phases.monsters import monster_raids
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import set_stats, stat
from tests.engine.core.factories import CoreWorld, add_flag, bond, entity, mortal, settlement, tuned_rules


async def keys(session: AsyncSession) -> list[str | None]:
    return list(await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)))


async def weak_beast(session: AsyncSession, world: CoreWorld, name: str, danger: int = 10) -> EntityRow:
    return await entity(
        session, name, EntityType.SPECIES, SpeciesStats(strength=1, agility=1, danger=danger), world_id=world.world.id, location_id=world.regions[2].id
    )


async def test_protector_intercepts_a_monster_raid(session: AsyncSession, world: CoreWorld) -> None:
    set_stats(world.species, strength=1, agility=1, danger=90)
    town = await settlement(session, "Brookhold", world, world.regions[2], population=1000, prosperity=50, defense=30)
    guard = await mortal(session, "Brannoc", world, world.regions[2].id, strength=100, agility=100, intellect=100)
    await bond(session, guard.id, town.id, BondKind.PROTECTS)
    ctx = await manual_context(session, "raid", tuned_rules(world_engine={"raid_danger_divisor": 10}))
    await monster_raids(ctx)
    assert stat(town, "population") == 1000
    assert stat(town, "defense") == 30
    assert "monsters.raid" not in await keys(session)
    assert "heroism.victory" in await keys(session)
    assert await BondRepository(session).exists_between(guard.id, world.species.id, BondKind.BEAT) or world.species.status is EntityStatus.DEAD


async def test_megafauna_slayer_changes_the_age(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "megafauna")
    hero = await mortal(session, "Brannoc", world, world.regions[2].id, strength=100, agility=100, intellect=100)
    await add_flag(session, world.species.id, EntityFlag.MEGAFAUNA)
    set_stats(world.species, strength=1, agility=1, danger=10)
    result = await encounter(ctx, hero, world.species, "in a test")
    assert result is not None and result.outcome is EncounterOutcome.KILLED
    assert world.species.status is EntityStatus.DEAD
    assert hero.title == f"{world.species.name} Slayer"
    assert await has_flag(session, hero.id, EntityFlag.AGE_CHANGER)
    assert hero.power_level == min(ctx.rules.world_hunt.power_cap, 3 + ctx.rules.world_hunt.megafauna_slayer_power_gain)
    epics = list(await session.scalars(select(EntityRow).where(EntityRow.name == f"The Fall of {world.species.name}")))
    assert len(epics) == 1 and epics[0].entity_type is EntityType.LEGEND
    kinds = list(await session.scalars(select(ChronicleRow.kind).where(ChronicleRow.template_key == "heroism.age_change")))
    assert kinds == [ChronicleKind.AGE_CHANGE]


async def test_weapon_gains_might_and_becomes_legendary_after_enough_victories(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "weapon")
    hunt = ctx.rules.world_hunt
    hero = await mortal(session, "Brannoc", world, world.regions[2].id, strength=100, agility=100, intellect=100)
    sword = await entity(
        session, "Brightfang", EntityType.ITEM, ItemStats(damage=100, might=10), world_id=world.world.id, location_id=world.regions[2].id, power_level=3
    )
    await bond(session, hero.id, sword.id, BondKind.OWNS)
    first = await weak_beast(session, world, "Gnarlfang")
    second = await weak_beast(session, world, "Mirewolf")
    await encounter(ctx, hero, first, "first hunt")
    assert stat(sword, "might") == 10 + hunt.weapon_might_gain
    assert not await has_flag(session, sword.id, EntityFlag.LEGENDARY)
    assert "heroism.legendary_weapon" not in await keys(session)
    await encounter(ctx, hero, second, "second hunt")
    assert stat(sword, "might") == 10 + 2 * hunt.weapon_might_gain
    assert await has_flag(session, sword.id, EntityFlag.LEGENDARY)
    assert sword.power_level == min(hunt.power_cap, 4)
    assert "heroism.legendary_weapon" in await keys(session)
    assert await BondRepository(session).exists_between(sword.id, second.id, BondKind.BEAT) or await BondRepository(session).exists_between(
        sword.id, second.id, BondKind.KILLED
    )


async def test_armor_turns_a_lost_fight_into_a_wound(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "armor", tuned_rules(world_hunt={"armor_save_base_pct": 100}))
    hunt = ctx.rules.world_hunt
    weak = await mortal(session, "Pip", world, world.regions[2].id, strength=1, agility=1, intellect=1, hp=100)
    plate = await entity(
        session, "Ironplate", EntityType.ITEM, ItemStats(damage=0, protection=80, might=0), world_id=world.world.id, location_id=world.regions[2].id
    )
    await bond(session, weak.id, plate.id, BondKind.OWNS)
    titan = await entity(
        session, "Titanback", EntityType.SPECIES, SpeciesStats(strength=100, agility=100, danger=100), world_id=world.world.id, location_id=world.regions[2].id
    )
    result = await encounter(ctx, weak, titan, "foolishly")
    assert result is not None and result.outcome is EncounterOutcome.WOUNDED
    assert weak.status is EntityStatus.CANON
    assert 0 < (stat(weak, "hp") or 0) < 100
    assert stat(plate, "protection") == 80 - hunt.armor_save_wear
    assert "heroism.armor_save" in await keys(session)
    assert "heroism.defeat" not in await keys(session)


async def test_unarmoured_hero_dies_when_armor_is_too_weak(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "armor", tuned_rules(world_hunt={"armor_save_base_pct": 100}))
    weak = await mortal(session, "Pip", world, world.regions[2].id, strength=1, agility=1, intellect=1)
    scrap = await entity(
        session, "Scrap", EntityType.ITEM, ItemStats(damage=0, protection=ctx.rules.world_hunt.armor_save_min_protection - 1), world_id=world.world.id
    )
    await bond(session, weak.id, scrap.id, BondKind.OWNS)
    titan = await entity(
        session, "Titanback", EntityType.SPECIES, SpeciesStats(strength=100, agility=100, danger=100), world_id=world.world.id, location_id=world.regions[2].id
    )
    result = await encounter(ctx, weak, titan, "foolishly")
    assert result is not None and result.outcome is EncounterOutcome.FELL
    assert weak.status is EntityStatus.DEAD
    assert "heroism.defeat" in await keys(session)


async def test_legend_carrier_prefers_location_then_lives_in_then_descent(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "carrier")
    town = await settlement(session, "Brookhold", world, world.regions[1])
    in_town = await mortal(session, "Dorn", world, town.id)
    assert (await legend_carrier(ctx, in_town)) is town
    wanderer = await mortal(session, "Wren", world, world.regions[2].id)
    assert await legend_carrier(ctx, wanderer) is None
    await bond(session, wanderer.id, world.people.id, BondKind.DESCENDS_FROM)
    carrier = await legend_carrier(ctx, wanderer)
    assert carrier is not None and carrier.id == world.people.id
    await bond(session, wanderer.id, town.id, BondKind.LIVES_IN)
    carrier = await legend_carrier(ctx, wanderer)
    assert carrier is not None and carrier.id == town.id


async def test_cursed_mortal_dies_of_the_curse_and_the_curser_is_the_killer(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "curse", tuned_rules(world_engine={"curse_hp_loss": 10}))
    victim = await mortal(session, "Vesna", world, world.regions[0].id, hp=25)
    await add_flag(session, victim.id, EntityFlag.CURSED)
    await bond(session, world.son.id, victim.id, BondKind.CURSED)
    await curse_decay(ctx)
    assert victim.status is EntityStatus.CANON and stat(victim, "hp") == 15
    await curse_decay(ctx)
    assert stat(victim, "hp") == 5
    await curse_decay(ctx)
    assert cast(EntityStatus, victim.status) is EntityStatus.DEAD
    assert await BondRepository(session).exists_between(world.son.id, victim.id, BondKind.KILLED)
    assert "mortal.death.cause" in await keys(session)


async def test_curse_hp_loss_of_zero_leaves_a_cursed_mortal_alive(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "curse", tuned_rules(world_engine={"curse_hp_loss": 0}))
    victim = await mortal(session, "Vesna", world, world.regions[0].id, hp=5)
    await add_flag(session, victim.id, EntityFlag.CURSED)
    await curse_decay(ctx)
    assert victim.status is EntityStatus.CANON and stat(victim, "hp") == 5


async def test_cursed_item_damages_its_owner_stats_hp_and_life(session: AsyncSession, world: CoreWorld) -> None:
    effects_rules = tuned_rules(world_engine={"cursed_item_contagion_chance": 0})
    ctx = await manual_context(session, "relic", effects_rules)
    effects = ctx.rules.world_effects
    relic = await entity(session, "Black Crown", EntityType.ITEM, ItemStats(curse=90), world_id=world.world.id, location_id=world.regions[0].id)
    town = await settlement(session, "Brookhold", world, world.regions[0], prosperity=60, defense=40)
    await bond(session, town.id, relic.id, BondKind.OWNS)
    await cursed_items(ctx)
    stat_damage = round_half_up(90 / effects.item_curse_stat_divisor)
    assert stat(town, "prosperity") == 60 - stat_damage
    assert stat(town, "defense") == 40 - stat_damage

    doomed = await mortal(session, "Corwen", world, world.regions[0].id, hp=10)
    jinx = await entity(session, "Jinx Ring", EntityType.ITEM, ItemStats(curse=100), world_id=world.world.id, location_id=world.regions[0].id)
    await bond(session, doomed.id, jinx.id, BondKind.OWNS)
    await cursed_items(ctx)
    assert doomed.status is EntityStatus.DEAD
    assert "mortal.death.cause" in await keys(session)
    assert "curses.spread" not in await keys(session)


async def test_cursed_item_drains_the_hp_of_a_non_mortal_owner(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "relic", tuned_rules(world_engine={"cursed_item_contagion_chance": 0}))
    relic = await entity(session, "Black Crown", EntityType.ITEM, ItemStats(curse=90), world_id=world.world.id, location_id=world.regions[0].id)
    await bond(session, world.species.id, relic.id, BondKind.OWNS)
    await cursed_items(ctx)
    assert stat(world.species, "hp") == 80 - round_half_up(90 / ctx.rules.world_effects.item_curse_hp_divisor)


async def test_cursed_item_wounds_a_mortal_owner_without_killing_a_healthy_one(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "relic", tuned_rules(world_engine={"cursed_item_contagion_chance": 100}))
    owner = await mortal(session, "Corwen", world, world.regions[0].id, hp=60)
    relic = await entity(session, "Black Crown", EntityType.ITEM, ItemStats(curse=90), world_id=world.world.id, location_id=world.regions[0].id)
    await bond(session, owner.id, relic.id, BondKind.OWNS)
    await cursed_items(ctx)
    assert owner.status is EntityStatus.CANON
    assert 0 < (stat(owner, "hp") or 0) < 60
    assert await has_flag(session, owner.id, EntityFlag.CURSED)
    assert "curses.spread" in await keys(session)
