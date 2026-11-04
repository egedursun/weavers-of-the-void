from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, NaturalLaw
from aerona.domain.models.entity_stats import CultStats, ItemStats, LawStats, PeopleStats, ResourceStats, SpeciesStats
from aerona.engine.economy.resources import set_resource_yield
from aerona.engine.economy.stocks import holding
from aerona.engine.phases.curses import curse_decay, cursed_items, lift_curses
from aerona.engine.phases.grudges import divine_grudges
from aerona.engine.phases.heroism import EncounterOutcome, encounter, glory_hunts, send_hero_to_hunt, sworn_hunts
from aerona.engine.phases.magic import magic_storms, price_of_magic, wizards
from aerona.engine.phases.monsters import monster_raids
from aerona.engine.phases.prosperity import prosperity_reversion, reverted
from aerona.engine.phases.resources import resource_economy, resource_regeneration
from aerona.engine.phases.settlements import architecture, settlement_laws
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, add_flag, bond, entity, knowledge, mortal, natural_law, settlement, son_draft, tuned_rules


async def keys(session: AsyncSession) -> list[str | None]:
    return list(await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)))


async def test_divine_grudges_leak_to_worshippers(session: AsyncSession, world: CoreWorld) -> None:
    rival = await SonRepository(session).create(son_draft("Varos", world.world.id, (Domain.WAR, Domain.FIRE)))
    await SonRepository(session).change_relation(world.son.id, rival.id, -90)
    cult = await entity(session, "Ash Circle", EntityType.CULT, CultStats(followers=300), world_id=world.world.id, location_id=world.regions[1].id)
    await bond(session, cult.id, rival.id, BondKind.WORSHIPS)
    ctx = await manual_context(session, "grudges", tuned_rules(world_engine={"god_grudge_spill_chance": 100}))
    await divine_grudges(ctx)
    assert await BondRepository(session).exists_between(world.people.id, cult.id, BondKind.ENEMY)
    assert "grudges.holy_war" in await keys(session)


async def test_monster_raid_hurts_and_protector_fights(session: AsyncSession, world: CoreWorld) -> None:
    set_stats(world.species, danger=90)
    town = await settlement(session, "Brookhold", world, world.regions[2], population=1000, prosperity=50, defense=30)
    ctx = await manual_context(session, "raid", tuned_rules(world_engine={"raid_danger_divisor": 10}))
    await monster_raids(ctx)
    assert (stat(town, "population") or 0) < 1000
    assert stat(town, "defense") == 30 + ctx.rules.world_effects.raid_defense_gain
    assert await BondRepository(session).exists_between(world.species.id, town.id, BondKind.HUNTS)


async def test_heroes_win_lose_and_rewind(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "heroes")
    hero = await mortal(session, "Brannoc", world, world.regions[2].id, strength=100, agility=100, intellect=100)
    sword = await entity(session, "Brightfang", EntityType.ITEM, ItemStats(damage=100, might=10), world_id=world.world.id, location_id=world.regions[2].id)
    await bond(session, hero.id, sword.id, BondKind.OWNS)
    set_stats(world.species, strength=1, agility=1, danger=10)
    result = await encounter(ctx, hero, world.species, "in a test")
    assert result is not None and result.outcome is EncounterOutcome.KILLED
    assert world.species.status is EntityStatus.DEAD
    assert hero.title == f"{world.species.name} Slayer"
    assert result.legend is not None
    beast = await entity(
        session, "Hourwyrm", EntityType.SPECIES, SpeciesStats(strength=1, agility=1, danger=6), world_id=world.world.id, location_id=world.regions[2].id
    )
    await EntityRepository(session).add_trait(beast.id, CreatureTrait.TIME_REWINDER)
    rewind = await encounter(ctx, hero, beast, "again")
    assert rewind is not None and rewind.outcome is EncounterOutcome.REWOUND
    assert await has_flag(session, beast.id, EntityFlag.TIME_RETURNED)
    weak = await mortal(session, "Pip", world, world.regions[2].id, strength=1, agility=1, intellect=1)
    titan = await entity(
        session, "Titanback", EntityType.SPECIES, SpeciesStats(strength=100, agility=100, danger=100), world_id=world.world.id, location_id=world.regions[2].id
    )
    loss = await encounter(ctx, weak, titan, "foolishly")
    assert loss is not None and loss.outcome is EncounterOutcome.FELL
    assert weak.status is EntityStatus.DEAD
    assert await send_hero_to_hunt(ctx, hero.id, titan.id) is not None


async def test_sworn_and_glory_hunts(session: AsyncSession, world: CoreWorld) -> None:
    hunter = await mortal(session, "Kesk", world, world.regions[2].id, strength=90, agility=90)
    await bond(session, hunter.id, world.species.id, BondKind.HUNTS)
    ctx = await manual_context(session, "hunts", tuned_rules(world_engine={"hunt_chance": 100}))
    await sworn_hunts(ctx)
    assert not await BondRepository(session).active_between(hunter.id, world.species.id, [BondKind.HUNTS])
    set_stats(world.species, danger=90)
    await glory_hunts(ctx)
    texts = await keys(session)
    assert any(key in texts for key in ("heroism.victory", "heroism.defeat", "heroism.armor_save"))


async def test_curses_decay_lift_and_spread(session: AsyncSession, world: CoreWorld) -> None:
    await add_flag(session, world.people.id, EntityFlag.CURSED)
    ctx = await manual_context(session, "curses", tuned_rules(world_engine={"curse_lift_chance": 100, "cursed_item_contagion_chance": 100}))
    await curse_decay(ctx)
    assert stat(world.people, "population") == 6000 * ctx.rules.world_effects.curse_population_kept_pct // 100
    assert stat(world.people, "prosperity") == 55 - ctx.rules.world_effects.curse_stat_loss
    await lift_curses(ctx)
    assert not await has_flag(session, world.people.id, EntityFlag.CURSED)
    relic = await entity(session, "Black Crown", EntityType.ITEM, ItemStats(curse=90), world_id=world.world.id, location_id=world.regions[0].id)
    await bond(session, world.people.id, relic.id, BondKind.OWNS)
    await cursed_items(ctx)
    assert await has_flag(session, world.people.id, EntityFlag.CURSED)


async def test_resources_feed_owners_and_regrow(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    ore = await entity(
        session, "Brightvein", EntityType.RESOURCE, ResourceStats(abundance=50, value=80), world_id=world.world.id, location_id=world.regions[0].id
    )
    wood = await entity(session, "Greenwood", EntityType.RESOURCE, ResourceStats(abundance=50), world_id=world.world.id, location_id=world.regions[0].id)
    seam = await set_resource_yield(session, rules, ore.id, CommodityKind.ORE, MaterialKind.IRON)
    grove = await set_resource_yield(session, rules, wood.id, CommodityKind.TIMBER)
    for resource in (ore, wood):
        await bond(session, world.people.id, resource.id, BondKind.OWNS)
    reserve = seam.reserve
    ctx = await manual_context(session, "resources")
    await resource_economy(ctx)
    assert await holding(session, world.people.id, CommodityKind.ORE) > 0
    assert seam.reserve < reserve
    cut = grove.reserve
    assert cut < grove.initial_reserve and grove.regeneration > 0
    await resource_regeneration(ctx)
    assert grove.reserve > cut
    assert seam.regeneration == 0


async def test_prosperity_reverts_toward_equilibrium(session: AsyncSession, world: CoreWorld) -> None:
    assert reverted(90, 50, 10) == 86
    set_stats(world.people, prosperity=90)
    await prosperity_reversion(await manual_context(session, "prosperity"))
    assert stat(world.people, "prosperity") == 86


async def test_magic_storms_wizards_and_price(session: AsyncSession, world: CoreWorld) -> None:
    set_stats(world.regions[0], magic=95)
    relic = await entity(session, "Star Shard", EntityType.ITEM, ItemStats(might=10), world_id=world.world.id, location_id=world.regions[0].id)
    rules = tuned_rules(
        world_engine={"magic_storm_chance": 100, "magic_storm_curse_chance": 0, "sorcerer_act_chance": 100, "sorcerer_curse_chance": 100},
        rites={"invention_chance": 100},
        backlash={"per_power_pct": 0},
    )
    ctx = await manual_context(session, "magic", rules)
    await magic_storms(ctx)
    assert stat(relic, "might") == 10 + rules.world_effects.magic_storm_might_gain
    town = await settlement(session, "Brookhold", world, world.regions[0])
    foe = await settlement(session, "Grimhold", world, world.regions[1])
    await bond(session, town.id, foe.id, BondKind.ENEMY)
    mage = await mortal(session, "Vesna", world, town.id, intellect=90)
    lore = await knowledge(session, world, "Ember Lore", KnowledgeBranch.MAGIC)
    await bond(session, mage.id, lore.id, BondKind.KNOWS)
    dreamer = await SonRepository(session).create(son_draft("Morrow", world.world.id, (Domain.DREAM, Domain.SOUND)))
    await bond(session, mage.id, dreamer.id, BondKind.WORSHIPS)
    await wizards(ctx)
    assert await has_flag(session, mage.id, EntityFlag.WIZARD)
    assert await has_flag(session, foe.id, EntityFlag.CURSED)
    await natural_law(session, world, "Toll of Sorcery", NaturalLaw.MAGIC_PRICE)
    mages = await entity(
        session, "Starborn", EntityType.PEOPLE, PeopleStats(population=1000, magic=90), world_id=world.world.id, location_id=world.regions[1].id
    )
    await price_of_magic(await manual_context(session, "magic_price", rules))
    assert stat(mages, "population") == 1000 * rules.world_effects.magic_price_population_kept_pct // 100


async def test_laws_and_architecture_shape_walls(session: AsyncSession, world: CoreWorld) -> None:
    town = await settlement(session, "Brookhold", world, world.regions[0], defense=30, prosperity=50)
    await entity(session, "Fair Code", EntityType.LAW, LawStats(justice=90), world_id=world.world.id, location_id=town.id)
    ctx = await manual_context(session, "laws")
    await settlement_laws(ctx)
    assert stat(town, "defense") == 30 + ctx.rules.world_effects.law_just_defense_gain
    stone = await knowledge(session, world, "Stone Art", KnowledgeBranch.ARCHITECTURE)
    await bond(session, town.id, stone.id, BondKind.KNOWS)
    await architecture(ctx)
    assert stat(town, "defense") == 30 + ctx.rules.world_effects.law_just_defense_gain + ctx.rules.world_effects.architecture_defense_gain
