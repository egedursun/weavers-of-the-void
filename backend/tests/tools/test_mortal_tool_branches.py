from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.session import Database
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.epochs import DeferredStepRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.routes import HorizonIntuitionRow
from aerona.db.tables.society import ResurrectionOrderRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import ArmyRow, CaptiveRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import CaptiveStatus
from aerona.domain.models.entity_stats import FactionStats, MortalStats
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats
from aerona.engine.services.war import open_war
from aerona.rules.registry import Rules
from aerona.tools.mortal import lines
from tests.engine.core.factories import tuned_rules
from tests.tools.factories import connect, make_entity, mortal_toolkit, seed_realm
from tests.tools.test_mortal_tools import LONG, bonds_between, entity, ok, teach


async def keys(database: Database) -> list[str]:
    async with database.read() as session:
        return [key for key in await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)) if key]


async def has_flag(database: Database, entity_id: int, flag: EntityFlag) -> bool:
    async with database.read() as session:
        return await EntityRepository(session).has_flag(entity_id, flag)


async def test_a_named_mortal_founds_only_a_dialect_of_its_tongue(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await connect(session, realm.mortal_id, realm.language_id, BondKind.SPEAKS)
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=3)
    await ok(toolkit, "found_language", {"name": "Morrish", "description": LONG, "words": [{"word": "mor", "meaning": "home"}]})
    dialect = await entity(database, toolkit.created_entity_ids[-1])
    assert dialect.stats.model_dump()["spread"] == Rules().mortal_tools.dialect_spread
    assert dialect.subtype is not None and "Kessari" in dialect.subtype
    assert await bonds_between(database, dialect.id, realm.language_id, BondKind.DESCENDS_FROM) == 1
    assert await bonds_between(database, realm.mortal_id, realm.language_id, BondKind.SPEAKS) == 0


async def test_confiscating_a_resource_sets_its_owner_against_the_claimant(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await connect(session, realm.faction_id, realm.resource_id, BondKind.OWNS)
        await weaken(session, realm.faction_id)
    sure = replace(Rules(), mortal_tools=replace(Rules().mortal_tools, seize_defense=0, seize_die=1, seizure_relation_loss=200))
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=3, rules=sure)
    claimed = await ok(toolkit, "claim_resource", {"resource_id": realm.resource_id})
    assert "Red Oars" in claimed
    assert await bonds_between(database, realm.faction_id, realm.people_id, BondKind.ENEMY) == 1
    assert await bonds_between(database, realm.faction_id, realm.resource_id, BondKind.OWNS) == 0
    assert "tools.mortal.claimed" in await keys(database)


async def test_a_caught_saboteur_earns_enmity(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        town = await session.get(EntityRow, realm.settlement_id)
        assert town is not None
        town.stats = town.stats.model_copy(update={"defense": 100})
    rules = tuned_rules(mortal_tools={"sabotage_die": 1, "sabotage_caught_margin": 0})
    toolkit = await mortal_toolkit(database, realm.faction_id, rules=rules)
    text = await ok(toolkit, "sabotage", {"target_id": realm.settlement_id, "kind": "arson", "how": "torches at the granary"})
    assert "caught" in text.lower()
    assert await bonds_between(database, realm.settlement_id, realm.faction_id, BondKind.ENEMY) == 1
    assert lines.SABOTAGE_CAUGHT.key in await keys(database)


async def test_poison_can_kill_a_named_mortal(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        mortal = await session.get(EntityRow, realm.mortal_id)
        assert mortal is not None
        mortal.stats = MortalStats(hp=2, strength=10, agility=10, intellect=0, charisma=10, age=30, lifespan=70)
    rules = tuned_rules(mortal_tools={"sabotage_die": 1})
    toolkit = await mortal_toolkit(database, realm.faction_id, rules=rules)
    text = await ok(toolkit, "sabotage", {"target_id": realm.mortal_id, "kind": "poison", "how": "a drop in the wine"})
    assert "Ilsa Morrow" in text
    assert (await entity(database, realm.mortal_id)).status is EntityStatus.DEAD


async def test_a_people_can_worship_the_creator_directly(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=3)
    await ok(toolkit, "worship", {"son_id": 0, "offering": "the first salt of the year"})
    assert await bonds_between(database, realm.people_id, realm.cosmos.creator_id, BondKind.WORSHIPS) == 1
    assert lines.WORSHIP_CREATOR.key in await keys(database)


async def test_a_worshipper_performs_a_resurrection_rite_for_its_dead_god(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        dead = await session.get(SonRow, realm.son_id)
        assert dead is not None
        dead.status, dead.death_epoch = SonStatus.DEAD, 2
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=3)
    text = await ok(toolkit, "resurrection_rite", {"son_id": realm.son_id, "kind": "prayer"})
    assert "Thalor" in text
    async with database.read() as session:
        order = await session.scalar(select(ResurrectionOrderRow).where(ResurrectionOrderRow.son_id == realm.son_id))
    assert order is not None
    assert "death.rite_per_epoch" in (await toolkit.runtime.call("resurrection_rite", {"son_id": realm.son_id, "kind": "prayer"})).text


async def test_an_adventurer_seizes_an_item_from_its_owner(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        item = await make_entity(session, "Bell of Brine", EntityType.ITEM, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
        await connect(session, realm.people_id, item.id, BondKind.OWNS)
        people = await session.get(EntityRow, realm.people_id)
        assert people is not None
        people.stats = people.stats.model_copy(update={"martiality": 0})
        item_id = item.id
    rules = tuned_rules(mortal_tools={"seize_item_die": 1})
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=3, rules=rules)
    await ok(toolkit, "go_on_adventure", {"target_id": item_id, "goal": "to ring it at dawn"})
    assert await bonds_between(database, realm.mortal_id, item_id, BondKind.OWNS) == 1
    assert await bonds_between(database, realm.people_id, item_id, BondKind.OWNS) == 0
    assert await bonds_between(database, realm.people_id, realm.mortal_id, BondKind.ENEMY) == 1
    assert lines.SEIZED.key in await keys(database)


async def defier(database: Database, realm_son: int, strength: int) -> None:
    async with database.write() as session:
        son = await session.get(SonRow, realm_son)
        assert son is not None
        son.strength, son.will, son.level, son.existence = strength, strength, 1, 10


async def test_a_mortal_who_crushes_a_fading_god_becomes_a_godslayer(database: Database) -> None:
    realm = await seed_realm(database)
    await defier(database, realm.son_id, 1)
    rules = tuned_rules(mortal_tools={"defy_god_die": 1, "godslayer_margin": 0, "godslayer_max_existence": 100})
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=3, rules=rules)
    text = await ok(toolkit, "challenge_god", {"son_id": realm.son_id, "reason": "he drowned my father"})
    me = await entity(database, realm.mortal_id)
    async with database.read() as session:
        slain = await session.get(SonRow, realm.son_id)
    assert slain is not None and slain.status is SonStatus.DEAD
    assert me.title == lines.GODSLAYER_TITLE and lines.GODSLAYER_TITLE in text
    assert me.stats.model_dump()["charisma"] == 50 + rules.mortal_tools.godslayer_charisma
    assert lines.GODSLAYER.key in await keys(database)


async def test_a_mortal_who_wins_without_crushing_wounds_the_god(database: Database) -> None:
    realm = await seed_realm(database)
    await defier(database, realm.son_id, 1)
    async with database.read() as session:
        before = await session.get(SonRow, realm.son_id)
        assert before is not None
        hp_before, fame_before = before.hp, before.fame
    rules = tuned_rules(mortal_tools={"defy_god_die": 1, "godslayer_margin": 1000})
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=3, rules=rules)
    await ok(toolkit, "challenge_god", {"son_id": realm.son_id, "reason": "he drowned my father"})
    async with database.read() as session:
        wounded = await session.get(SonRow, realm.son_id)
    assert wounded is not None and wounded.status is SonStatus.ACTIVE and wounded.hp < hp_before
    assert wounded.fame == max(0, fame_before - rules.mortal_tools.god_wound_renown_loss)
    assert lines.GOD_WOUNDED.key in await keys(database)


async def test_a_defeated_defier_dies_or_is_cursed(database: Database) -> None:
    realm = await seed_realm(database)
    await defier(database, realm.son_id, 100)
    cursed = tuned_rules(mortal_tools={"defy_god_die": 1, "defy_god_death_chance": 0})
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=3, rules=cursed)
    await ok(toolkit, "challenge_god", {"son_id": realm.son_id, "reason": "he drowned my father"})
    assert await has_flag(database, realm.mortal_id, EntityFlag.CURSED)
    assert lines.DEFIER_CURSED.key in await keys(database)
    async with database.write() as session:
        bold = await make_entity(session, "Bran Holt", EntityType.MORTAL, world_id=realm.cosmos.world_id, location_id=realm.settlement_id)
        son = await session.get(SonRow, realm.son_id)
        assert son is not None
        bold_id, fame_before = bold.id, son.fame
    killed = tuned_rules(mortal_tools={"defy_god_die": 1, "defy_god_death_chance": 100})
    doomed = await mortal_toolkit(database, bold_id, action_points=3, rules=killed)
    await ok(doomed, "challenge_god", {"son_id": realm.son_id, "reason": "for my brother"})
    async with database.read() as session:
        son_after = await session.get(SonRow, realm.son_id)
    assert (await entity(database, bold_id)).status is EntityStatus.DEAD
    assert son_after is not None and son_after.fame == fame_before + killed.mortal_tools.god_crush_renown
    assert lines.DEFIER_DIED.key in await keys(database)


async def test_a_searching_people_senses_an_unknown_world_for_the_epoch_end(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        people = await session.get(EntityRow, realm.people_id)
        assert people is not None
        people.civ_tier = 3
    await teach(database, realm, realm.people_id, KnowledgeBranch.SKY_NAVIGATION, "Star Sailing")
    rules = tuned_rules(mortal_tools={"route_threshold": 100000, "unknown_world_threshold": 0})
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=3, rules=rules)
    text = await ok(toolkit, "find_route", {"how": "reading the old star charts"})
    assert "sensed" in text.lower() or "world" in text.lower()
    async with database.read() as session:
        intuition = await session.scalar(select(HorizonIntuitionRow))
        deferred = await session.scalar(select(DeferredStepRow))
    assert intuition is not None and intuition.mortal_entity_id == realm.people_id
    assert deferred is not None and deferred.payload == {"intuition_id": intuition.id}
    assert lines.ROUTE_SENSED.key in await keys(database)


async def test_pioneers_settle_the_discovered_land(database: Database) -> None:
    realm = await seed_realm(database)
    rules = tuned_rules(exploration={"tool_success_threshold": 0})
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=3, rules=rules)
    text = await ok(toolkit, "explore_land", {"kind": "place", "name": "Glimmer Cave", "description": LONG, "settle": True})
    land_id, settlement_id = toolkit.created_entity_ids[0], toolkit.created_entity_ids[-1]
    settlement = await entity(database, settlement_id)
    assert settlement.entity_type is EntityType.SETTLEMENT and settlement.location_id == land_id
    assert await has_flag(database, settlement_id, EntityFlag.PIONEER)
    assert (await entity(database, realm.people_id)).stats.model_dump()["population"] < 6000
    assert settlement.name in text


async def ruin_setup(database: Database, realm_world: int, region: int) -> tuple[int, int, int]:
    async with database.write() as session:
        ruin = await make_entity(session, "Old Brinewall", EntityType.SETTLEMENT, world_id=realm_world, location_id=region)
        await EntityRepository(session).add_flag(ruin.id, EntityFlag.RUIN, 1)
        lost = await make_entity(session, "Salt Glyphs", EntityType.KNOWLEDGE, world_id=realm_world, knowledge_branch=KnowledgeBranch.MAGIC)
        await EntityRepository(session).add_flag(lost.id, EntityFlag.LOST, 1)
        relic = await make_entity(session, "Drowned Crown", EntityType.ITEM, world_id=realm_world, location_id=ruin.id)
        return ruin.id, lost.id, relic.id


async def test_searching_ruins_finds_knowledge_an_item_or_a_curse(database: Database) -> None:
    realm = await seed_realm(database)
    ruin, lost, relic = await ruin_setup(database, realm.cosmos.world_id, realm.cosmos.region_id)
    knowledge_rules = tuned_rules(mortal_tools={"relic_knowledge_threshold": -1000})
    await ok(await mortal_toolkit(database, realm.people_id, rules=knowledge_rules), "search_ruins", {"target_id": ruin, "how": "digging below"})
    assert await bonds_between(database, realm.people_id, lost, BondKind.KNOWS) == 1
    assert not await has_flag(database, lost, EntityFlag.LOST)
    item_rules = tuned_rules(mortal_tools={"relic_knowledge_threshold": 1000, "relic_item_threshold": -1000})
    await ok(await mortal_toolkit(database, realm.settlement_id, rules=item_rules), "search_ruins", {"target_id": ruin, "how": "sifting the sand"})
    assert await bonds_between(database, realm.settlement_id, relic, BondKind.OWNS) == 1
    curse_rules = tuned_rules(mortal_tools={"relic_knowledge_threshold": 1000, "relic_item_threshold": 1000, "relic_curse_threshold": 1000})
    await ok(await mortal_toolkit(database, realm.faction_id, rules=curse_rules), "search_ruins", {"target_id": ruin, "how": "breaking the seals"})
    assert await has_flag(database, realm.faction_id, EntityFlag.CURSED)
    recorded = await keys(database)
    assert {lines.RUIN_KNOWLEDGE.key, lines.RUIN_ITEM.key, lines.RUIN_CURSE.key} <= set(recorded)


async def hold(database: Database, captive: int, captor: int) -> None:
    async with database.write() as session:
        session.add(CaptiveRow(captive_entity_id=captive, captor_entity_id=captor, status=CaptiveStatus.HELD, taken_epoch=1))


async def captive_status(database: Database) -> CaptiveStatus:
    async with database.read() as session:
        row = await session.scalar(select(CaptiveRow).order_by(CaptiveRow.id.desc()))
        assert row is not None
        return row.status


async def test_a_captive_escapes_or_is_wounded_trying(database: Database) -> None:
    realm = await seed_realm(database)
    await hold(database, realm.mortal_id, realm.faction_id)
    failing = tuned_rules(mortal_tools={"escape_min_pct": 0, "escape_max_pct": 0})
    await ok(await mortal_toolkit(database, realm.mortal_id, rules=failing), "escape", {"how": "through the drain"})
    assert await captive_status(database) is CaptiveStatus.HELD
    assert (await entity(database, realm.mortal_id)).stats.model_dump()["hp"] == 40 - failing.mortal_tools.escape_caught_wound
    succeeding = tuned_rules(mortal_tools={"escape_min_pct": 100, "escape_max_pct": 100})
    await ok(await mortal_toolkit(database, realm.mortal_id, rules=succeeding), "escape", {"how": "over the wall"})
    assert await captive_status(database) is CaptiveStatus.ESCAPED
    assert {lines.ESCAPE_FAILED.key, lines.ESCAPED.key} <= set(await keys(database))


async def test_a_rescue_frees_the_captive_or_makes_the_captor_an_enemy(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        captor = await session.get(EntityRow, realm.faction_id)
        assert captor is not None
        captor.stats = FactionStats(strength=100, wealth=40, sway=40)
    await hold(database, realm.mortal_id, realm.faction_id)
    rules = tuned_rules(mortal_tools={"rescue_die": 1})
    await ok(await mortal_toolkit(database, realm.people_id, rules=rules), "rescue_captive", {"captive_id": realm.mortal_id, "plan": "a night raid"})
    assert await captive_status(database) is CaptiveStatus.HELD
    assert await bonds_between(database, realm.faction_id, realm.people_id, BondKind.ENEMY) == 1
    async with database.write() as session:
        captor = await session.get(EntityRow, realm.faction_id)
        assert captor is not None
        captor.stats = FactionStats(strength=0, wealth=40, sway=40)
    await ok(await mortal_toolkit(database, realm.settlement_id, rules=rules), "rescue_captive", {"captive_id": realm.mortal_id, "plan": "a bribe at the gate"})
    assert await captive_status(database) is CaptiveStatus.RESCUED
    assert {lines.RESCUE_FAILED.key, lines.RESCUED.key} <= set(await keys(database))


async def test_a_new_army_protects_its_people_and_joins_their_war(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        people = await session.get(EntityRow, realm.people_id)
        faction = await session.get(EntityRow, realm.faction_id)
        assert people is not None and faction is not None
        war = await open_war(await manual_context(session, "test_war", Rules()), people, faction)
        war_id = war.id
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=4)
    await ok(toolkit, "raise_army", {"name": "Salt Spears", "percent": 10})
    army_id = toolkit.created_entity_ids[-1]
    army = await entity(database, army_id)
    stats = army.stats.model_dump()
    tools = Rules().mortal_tools
    assert stats["size"] >= tools.army_min_soldiers and 0 <= stats["morale"] <= 100 and stats["experience"] == tools.army_experience
    assert await bonds_between(database, army_id, realm.people_id, BondKind.PROTECTS) == 1
    async with database.read() as session:
        row = await session.get(ArmyRow, army_id)
        part_of = await BondRepository(session).outgoing(army_id, BondKind.PART_OF)
    assert row is not None and row.war_id == war_id and part_of
    assert lines.ARMY.key in await keys(database)


async def weaken(session: AsyncSession, entity_id: int) -> None:
    faction = await session.get(EntityRow, entity_id)
    assert faction is not None
    set_stats(faction, strength=0, wealth=0, sway=0)
