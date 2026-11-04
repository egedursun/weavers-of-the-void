from typing import Any

import pytest
from sqlalchemy import select

from aerona.agents.tool_ports import AgentReadViews
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.session import Database
from aerona.db.tables.agency import AgentTurnRow
from aerona.db.tables.body import BodyRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import ChronicleRow, LexemeRow, ThreadLinkRow, ThreadRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.society import ResurrectionOrderRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import CreatureTrait, NaturalLaw
from aerona.domain.enums.son import PowerEffect, SonStatus
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import StarType
from aerona.domain.models.entity_stats import CultStats
from aerona.domain.models.phonology import Phonology
from aerona.domain.models.profiles import TravelResource
from aerona.rules.registry import Rules
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.son import lines
from tests.engine.core.factories import tuned_rules
from tests.tools.factories import DESCRIPTION, add_world, connect, make_entity, seed_realm, son_toolkit
from tests.tools.test_son_tools import entity, ok, rejected, son

LINE_TO_PEOPLE = "born of their songs"


def related(target_id: int) -> list[dict[str, Any]]:
    return [{"target_kind": "entity", "target_id": target_id, "kind": "related", "description": LINE_TO_PEOPLE}]


def creation(name: str, target_id: int, power: int = 2, **extra: Any) -> dict[str, Any]:
    return {"name": name, "description": DESCRIPTION, "power_level": power, "links": related(target_id), **extra}


async def keys(database: Database) -> list[str]:
    async with database.read() as session:
        return [key for key in await session.scalars(select(ChronicleRow.template_key).order_by(ChronicleRow.id)) if key]


async def incoming(database: Database, target_id: int, kind: BondKind) -> list[int]:
    async with database.read() as session:
        return [bond.source_node_id for bond in await BondRepository(session).incoming(target_id, kind)]


async def outgoing(database: Database, source_id: int, kind: BondKind) -> list[int]:
    async with database.read() as session:
        return [bond.target_node_id for bond in await BondRepository(session).outgoing(source_id, kind)]


async def set_status(database: Database, entity_id: int, status: EntityStatus) -> None:
    async with database.write() as session:
        row = await session.get(EntityRow, entity_id)
        assert row is not None
        await EntityRepository(session).set_status(row, status, 2)


async def test_state_rejections_name_the_reason(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        records = {
            status: (
                await make_entity(session, f"Rec {status.value}", EntityType.FACTION, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
            ).id
            for status in (EntityStatus.DEAD, EntityStatus.DESTROYED, EntityStatus.REJECTED, EntityStatus.FULFILLED)
        }
    for status, entity_id in records.items():
        await set_status(database, entity_id, status)
    toolkit = await son_toolkit(database, realm.son_id, action_points=6)
    texts = {status: await rejected(toolkit, "curse", {"entity_id": entity_id, "curse": "may it wither"}) for status, entity_id in records.items()}
    assert "is dead" in texts[EntityStatus.DEAD]
    assert "was destroyed" in texts[EntityStatus.DESTROYED]
    assert "rejected by Fate" in texts[EntityStatus.REJECTED]
    assert "has been fulfilled" in texts[EntityStatus.FULFILLED]
    assert "There is no record numbered #424242" in await rejected(toolkit, "curse", {"entity_id": 424242, "curse": "may it wither"})


async def test_losing_a_god_war_wounds_drains_and_puts_the_son_to_sleep(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        me = await session.get(SonRow, realm.son_id)
        god = await session.get(ForeignGodRow, realm.god_id)
        assert me is not None and god is not None
        me.strength, me.will, me.hp, me.essence = 1, 1, 3, 100
        god.power, god.stance = 100, 10
        god.strength, god.will = 100, 100
    rules = tuned_rules(son_tools={"foreign_war_die": 1})
    toolkit = await son_toolkit(database, realm.son_id, action_points=6, rules=rules)
    text = await ok(toolkit, "war_on_foreign_god", {"god_id": realm.god_id, "reason": "he drowned my faithful"})
    after = await son(database, realm.son_id)
    async with database.read() as session:
        fallen = await session.get(ForeignGodRow, realm.god_id)
    assert after.hp == 0 and after.status is SonStatus.ASLEEP and after.sleep_epochs_left == rules.son_tools.foreign_war_sleep_epochs
    assert fallen is not None and fallen.stance == 10 - rules.son_tools.foreign_war_attitude_loss
    assert after.essence == 100 - rules.son_tools.foreign_war_cost - rules.son_tools.foreign_war_essence_loss
    assert "but lost" in text and "fell asleep" in text and "Remaining actions: 0" in text
    async with database.read() as session:
        turn = await session.get(AgentTurnRow, realm.son_id)
    assert turn is not None and turn.action_points_left == 0
    assert "pantheon.god_war" in await keys(database)


async def test_world_summary_and_memory_read_through_the_views_port(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        me = await session.get(SonRow, realm.son_id)
        assert me is not None
        me.plan = "Raise a salt kingdom before the third age."
    toolkit = await son_toolkit(database, realm.son_id, ports=ToolPorts(views=AgentReadViews()))
    summary = await ok(toolkit, "world_summary", {})
    assert "Kessar Folk" in summary
    memory = await ok(toolkit, "my_memory", {})
    assert "Raise a salt kingdom" in memory


async def test_gifting_a_worshipping_community_follows_the_acceptance_roll(database: Database) -> None:
    realm = await seed_realm(database)
    accepting = await son_toolkit(database, realm.son_id, action_points=3, rules=tuned_rules(son_tools={"transfer_base_pct": 100}))
    given = await ok(accepting, "give_gift", {"son_id": realm.sibling_id, "worshipper_id": realm.people_id, "words": "take my salt people"})
    assert "Kessar Folk now worships Veyra" in given
    assert realm.sibling_id in await outgoing(database, realm.people_id, BondKind.WORSHIPS)
    assert realm.son_id not in await outgoing(database, realm.people_id, BondKind.WORSHIPS)
    async with database.read() as session:
        warmth = await SonRepository(session).relation(realm.son_id, realm.sibling_id)
    assert warmth >= Rules().son_tools.gift_relation_base + Rules().son_tools.gift_worshipper_relation


async def test_a_refused_community_gift_stays_with_its_old_god(database: Database) -> None:
    other = await seed_realm(database)
    async with database.write() as session:
        sibling = await session.get(SonRow, other.sibling_id)
        assert sibling is not None
        sibling.charisma = 1
    refusing = await son_toolkit(database, other.son_id, action_points=3, rules=tuned_rules(son_tools={"transfer_base_pct": 0}))
    refused = await ok(refusing, "give_gift", {"son_id": other.sibling_id, "worshipper_id": other.cult_id, "words": "go to my sister"})
    assert "refused to leave you" in refused
    assert other.son_id in await outgoing(database, other.cult_id, BondKind.WORSHIPS)
    assert lines.GIFT_REFUSED.key in await keys(database)


async def test_creation_advances_an_open_thread_and_notes_a_closed_one(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        open_thread = ThreadRow(text="Who drowned the salt king?", epoch=1)
        closed = ThreadRow(text="The old feud", epoch=1, status=ThreadStatus.CLOSED, closed_epoch=2)
        session.add_all([open_thread, closed])
        await session.flush()
        open_id, closed_id = open_thread.id, closed.id
    toolkit = await son_toolkit(database, realm.son_id, action_points=4)
    await ok(toolkit, "tell_legend", creation("The Drowned King", realm.people_id, thread_id=open_id))
    noted = await ok(toolkit, "tell_legend", creation("The Second Tide", realm.people_id, thread_id=closed_id))
    assert f"thread#{closed_id} is not open" in noted
    async with database.read() as session:
        advanced = await session.get(ThreadRow, open_id)
        links = list(await session.scalars(select(ThreadLinkRow.thread_id)))
    assert advanced is not None and advanced.progress == 1 and links == [open_id]


async def test_required_location_is_inferred_from_linked_places_or_refused(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=4)
    place_link = [{"target_kind": "entity", "target_id": realm.cosmos.place_id, "kind": "related", "description": "they gather there"}]
    await ok(toolkit, "create_people", {"name": "Hollowfolk", "description": DESCRIPTION, "power_level": 2, "links": place_link})
    assert (await entity(database, toolkit.created_entity_ids[-1])).location_id == realm.cosmos.place_id
    lore_link = [{"target_kind": "entity", "target_id": realm.language_id, "kind": "related", "description": "they speak it"}]
    refused = await rejected(toolkit, "create_people", {"name": "Driftfolk", "description": DESCRIPTION, "power_level": 2, "links": lore_link})
    assert "location_id is required" in refused and "Ember Hollow" in refused


async def test_co_creation_splits_cost_and_rewards_the_covenanted_partner(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await connect(session, realm.son_id, realm.sibling_id, BondKind.ALLY, "salt and fire")
        partner_before = await session.get(SonRow, realm.sibling_id)
        assert partner_before is not None
        essence_before, xp_before, fame_before = partner_before.essence, partner_before.xp, partner_before.fame
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    text = await ok(toolkit, "create_artwork", creation("The Twin Flame", realm.people_id, co_creator_id=realm.sibling_id))
    created = toolkit.created_entity_ids[-1]
    partner = await son(database, realm.sibling_id)
    tools = Rules().son_tools
    assert "paid by Veyra" in text
    assert partner.essence < essence_before
    assert partner.xp == xp_before + tools.co_creator_xp_base + 2 * tools.co_creator_xp_per_power
    assert partner.fame == fame_before + tools.co_creator_renown
    assert created in await outgoing(database, realm.sibling_id, BondKind.PRODUCED)


async def test_cults_worship_their_maker_unless_another_son_is_named(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=4)
    await ok(toolkit, "found_cult", creation("Order of the Tide", realm.people_id, location_id=realm.cosmos.region_id))
    assert await outgoing(database, toolkit.created_entity_ids[-1], BondKind.WORSHIPS) == [realm.son_id]
    await ok(toolkit, "found_cult", creation("Order of the Flame", realm.people_id, location_id=realm.cosmos.region_id, worshipped_son_id=realm.sibling_id))
    assert await outgoing(database, toolkit.created_entity_ids[-1], BondKind.WORSHIPS) == [realm.sibling_id]
    await ok(toolkit, "found_faction", creation("Salt Guild", realm.people_id, location_id=realm.cosmos.region_id))
    assert await outgoing(database, toolkit.created_entity_ids[-1], BondKind.WORSHIPS) == []
    await ok(toolkit, "found_settlement", creation("Saltmoor", realm.people_id, location_id=realm.cosmos.region_id, worshipped_son_id=realm.sibling_id))
    assert await outgoing(database, toolkit.created_entity_ids[-1], BondKind.WORSHIPS) == [realm.sibling_id]


async def test_the_first_life_on_an_empty_world_rewards_the_son(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        empty = await add_world(session, "Silent Reach")
        shore = await make_entity(session, "Bare Shore", EntityType.REGION, world_id=empty.id)
        me = await session.get(SonRow, realm.son_id)
        assert me is not None
        me.current_world_id = empty.id
        shore_id = shore.id
    before = await son(database, realm.son_id)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    await ok(toolkit, "create_people", {**creation("First Folk", shore_id), "location_id": shore_id})
    after = await son(database, realm.son_id)
    empty_rules = Rules().empty_world
    assert after.fame >= before.fame + empty_rules.first_people_renown
    assert lines.FIRST_LIFE.key in await keys(database)


async def test_names_with_foreign_sounds_are_warned_not_refused(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        world = await session.get(WorldRow, realm.cosmos.world_id)
        assert world is not None
        world.phonology = Phonology(
            vowels=("a", "e"), consonants=("k", "l", "m", "n", "r", "s", "t"), syllable_patterns=("CV",), min_syllables=1, max_syllables=3
        )
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    text = await ok(toolkit, "tell_legend", creation("Quzbo", realm.people_id))
    assert "the sounds b, o, q, u, z in its name do not exist" in text


async def test_create_region_with_a_parent_and_water(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    await ok(toolkit, "create_region", creation("The Drowned Reach", realm.people_id, location_id=realm.cosmos.region_id, water=True))
    region = await entity(database, toolkit.created_entity_ids[-1])
    assert region.entity_type is EntityType.REGION and region.location_id == realm.cosmos.region_id and region.is_water


async def test_settlements_and_peoples_take_their_population_from_power(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=6)
    await ok(toolkit, "found_settlement", creation("Lowmoor", realm.people_id, power=1, location_id=realm.cosmos.region_id))
    small = await entity(database, toolkit.created_entity_ids[-1])
    await ok(toolkit, "found_settlement", creation("Highmoor", realm.people_id, power=4, location_id=realm.cosmos.region_id))
    large = await entity(database, toolkit.created_entity_ids[-1])
    assert 0 < small.stats.model_dump()["population"] < large.stats.model_dump()["population"]
    await ok(toolkit, "create_people", creation("Moorfolk", realm.people_id, power=3, location_id=realm.cosmos.place_id))
    people = await entity(database, toolkit.created_entity_ids[-1])
    assert people.location_id == realm.cosmos.place_id and people.stats.model_dump()["population"] > 0
    refused = await rejected(toolkit, "found_settlement", creation("Nowhere", realm.language_id))
    assert "location_id is required" in refused


async def test_species_traits_are_capped_and_mighty_beasts_are_megafauna(database: Database) -> None:
    realm = await seed_realm(database)
    rules = tuned_rules(son_tools={"creature_max_traits": 2, "megafauna_power": 3})
    toolkit = await son_toolkit(database, realm.son_id, action_points=4, rules=rules)
    traits = ["flying", "venomous", "soul_eater"]
    await ok(toolkit, "create_species", creation("Skyfang", realm.people_id, power=3, traits=traits, body_plan="avian", size_class="large", diet="carnivore"))
    beast = toolkit.created_entity_ids[-1]
    refused = await rejected(toolkit, "create_species", creation("Mudhopper", realm.people_id, power=1, size_class="small", diet="omnivore"))
    assert "body_plan" in refused
    await ok(toolkit, "create_species", creation("Mudhopper", realm.people_id, power=1, body_plan="amorphous", size_class="small", diet="omnivore"))
    small = toolkit.created_entity_ids[-1]
    async with database.read() as session:
        body = await session.get(BodyRow, small)
        assert body is not None and body.plan is BodyPlan.AMORPHOUS
        repository = EntityRepository(session)
        assert set(await repository.traits(beast)) == {CreatureTrait.FLYING, CreatureTrait.VENOMOUS}
        assert EntityFlag.MEGAFAUNA in await repository.flags(beast)
        assert EntityFlag.MEGAFAUNA not in await repository.flags(small)


async def test_a_new_mortal_has_a_title_and_an_age_inside_the_lifespan_window(database: Database) -> None:
    realm = await seed_realm(database)
    tools = Rules().son_tools
    toolkit = await son_toolkit(database, realm.son_id, action_points=6)
    await ok(
        toolkit, "create_mortal", creation("Orsa Venn", realm.people_id, title="the Keeper", location_id=realm.settlement_id, stats={"lifespan": 80, "age": 79})
    )
    forced = await entity(database, toolkit.created_entity_ids[-1])
    youngest, oldest = round(80 * tools.mortal_age_min_pct / 100), round(80 * tools.mortal_age_max_pct / 100)
    assert forced.title == "the Keeper" and youngest <= forced.stats.model_dump()["age"] <= oldest
    kept_age = youngest + 1
    await ok(toolkit, "create_mortal", creation("Tam Venn", realm.people_id, location_id=realm.settlement_id, stats={"lifespan": 80, "age": kept_age}))
    kept = await entity(database, toolkit.created_entity_ids[-1])
    assert kept.stats.model_dump()["age"] == kept_age


async def test_items_draw_might_from_their_source_and_find_an_owner(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=6)
    sourced = [{"target_kind": "entity", "target_id": realm.resource_id, "kind": "source_of"}]
    await ok(toolkit, "forge_item", {"name": "Brineknife", "description": DESCRIPTION, "power_level": 2, "links": sourced, "location_id": realm.settlement_id})
    knife = await entity(database, toolkit.created_entity_ids[-1])
    await ok(toolkit, "forge_item", {**creation("Plainknife", realm.people_id), "location_id": realm.settlement_id})
    plain = await entity(database, toolkit.created_entity_ids[-1])
    divisor = Rules().son_tools.item_resource_might_divisor
    assert knife.stats.model_dump()["might"] == plain.stats.model_dump()["might"] + round(30 / divisor)
    assert await incoming(database, knife.id, BondKind.OWNS) and await incoming(database, plain.id, BondKind.OWNS)


async def test_structures_need_a_place_and_stand_inside_it(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=4)
    await ok(toolkit, "build_structure", creation("Tide Pillar", realm.people_id, location_id=realm.settlement_id, structure_kind="shrine", material="stone"))
    built = toolkit.created_entity_ids[-1]
    assert (await entity(database, built)).location_id == realm.settlement_id
    async with database.read() as session:
        profile = await session.get(StructureProfileRow, built)
    assert profile is not None and profile.kind is StructureKind.SHRINE and profile.dedicated_son_id == realm.son_id
    assert "location_id is required" in await rejected(toolkit, "build_structure", creation("Lost Pillar", realm.language_id, structure_kind="shrine"))
    assert "structure_kind" in await rejected(toolkit, "build_structure", creation("Kindless Pillar", realm.people_id, location_id=realm.settlement_id))


async def test_a_son_commissions_a_typed_work_in_his_name(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=4)
    await ok(toolkit, "commission_structure", {"community_id": realm.settlement_id, "structure_kind": "shrine", "name": "Tide Shrine"})
    async with database.read() as session:
        profile = await session.scalar(select(StructureProfileRow).where(StructureProfileRow.kind == StructureKind.SHRINE))
    assert profile is not None and profile.dedicated_son_id == realm.son_id and profile.construction_state is ConstructionState.BUILDING


async def test_a_language_is_born_with_capped_first_words(database: Database) -> None:
    realm = await seed_realm(database)
    rules = tuned_rules(son_tools={"coin_word_max_words": 2})
    toolkit = await son_toolkit(database, realm.son_id, action_points=3, rules=rules)
    words = [{"word": "vel", "meaning": "wave"}, {"word": "sar", "meaning": "salt"}, {"word": "tor", "meaning": "stone"}]
    await ok(toolkit, "create_language", creation("Vellish", realm.people_id, words=words))
    language = toolkit.created_entity_ids[-1]
    async with database.read() as session:
        stored = list(await session.scalars(select(LexemeRow.word).where(LexemeRow.language_entity_id == language).order_by(LexemeRow.id)))
    assert stored == ["vel", "sar"]


async def test_unplaced_kinds_have_no_location_and_optional_kinds_keep_theirs(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=10)
    await ok(toolkit, "tell_legend", creation("The Salt Wyrm", realm.people_id))
    await ok(toolkit, "hang_celestial", creation("Lantern Moon", realm.people_id))
    legend, moon = toolkit.created_entity_ids[-2:]
    assert (await entity(database, legend)).location_id is None and (await entity(database, moon)).location_id is None
    await ok(toolkit, "create_artwork", creation("The Drowned Choir", realm.people_id, location_id=realm.settlement_id))
    await ok(toolkit, "decree_law", creation("Law of Salt", realm.people_id, location_id=realm.settlement_id))
    await ok(toolkit, "summon_spirit", creation("Whisper of Brine", realm.people_id, location_id=realm.cosmos.place_id))
    artwork, law, spirit = toolkit.created_entity_ids[-3:]
    assert (await entity(database, artwork)).location_id == realm.settlement_id
    assert (await entity(database, law)).location_id == realm.settlement_id
    assert (await entity(database, spirit)).entity_type is EntityType.SPIRIT and (await entity(database, spirit)).location_id == realm.cosmos.place_id


async def test_a_tradition_needs_a_celebrant(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    await ok(toolkit, "found_tradition", creation("Brine Rite", realm.people_id))
    assert await incoming(database, toolkit.created_entity_ids[-1], BondKind.CELEBRATES) == [realm.people_id]


async def test_inspired_knowledge_has_a_branch_and_capped_first_learners(database: Database) -> None:
    realm = await seed_realm(database)
    rules = tuned_rules(son_tools={"knowledge_first_learners": 1})
    toolkit = await son_toolkit(database, realm.son_id, action_points=3, rules=rules)
    learners = [realm.settlement_id, realm.faction_id]
    await ok(toolkit, "inspire_knowledge", creation("Salt Smelting", realm.people_id, branch="metallurgy", learner_ids=learners))
    knowledge = await entity(database, toolkit.created_entity_ids[-1])
    knowers = await incoming(database, knowledge.id, BondKind.KNOWS)
    assert knowledge.knowledge_branch is not None and knowledge.knowledge_branch.value == "metallurgy"
    assert realm.settlement_id in knowers and realm.faction_id not in knowers


async def test_a_seer_son_utters_prophecies_cheaply(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    plain = await ok(toolkit, "utter_prophecy", creation("The Seventh Tide", realm.people_id))
    assert "your power's discount" not in plain
    async with database.write() as session:
        session.add(SonPowerRow(son_id=realm.son_id, slot=0, name="Far Sight", description="Sees the tides to come.", effect=PowerEffect.SEER))
    seer = await son_toolkit(database, realm.son_id, action_points=3)
    cheap = await ok(seer, "utter_prophecy", creation("The Eighth Tide", realm.people_id))
    assert "your power's discount" in cheap


async def test_an_event_changes_stats_within_its_severity_and_records_the_cause(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=4)
    effects = [{"entity_id": realm.settlement_id, "stat": "prosperity", "percent": 10}]
    await ok(toolkit, "start_event", creation("The Salt Boom", realm.people_id, power=3, effects=effects, stats={"severity": 30}))
    event = toolkit.created_entity_ids[-1]
    assert (await entity(database, realm.settlement_id)).stats.model_dump()["prosperity"] == 55
    assert await incoming(database, realm.settlement_id, BondKind.CAUSED) == [event]
    too_strong = [{"entity_id": realm.settlement_id, "stat": "prosperity", "percent": 40}]
    bounded = await ok(toolkit, "start_event", creation("The Salt Bust", realm.people_id, power=3, effects=too_strong, stats={"severity": 30}))
    assert "40% to 30%" in bounded


async def test_a_vessel_with_a_target_world_opens_a_route_of_its_kind(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    text = await ok(toolkit, "create_vessel", creation("Starhorse", realm.people_id, target_world_id=realm.other_world_id, vessel_kind="mount"))
    vessel = toolkit.created_entity_ids[-1]
    async with database.read() as session:
        route = await session.scalar(select(RouteRow).where(RouteRow.vehicle_entity_id == vessel))
    assert route is not None and route.method is TravelMethod.COSMIC_MOUNT and "Velmor" in text


async def test_a_natural_law_carries_its_mechanic(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    await ok(toolkit, "decree_natural_law", creation("Law of Gentle Death", realm.people_id, mechanic="short_life"))
    assert (await entity(database, toolkit.created_entity_ids[-1])).natural_law is NaturalLaw.SHORT_LIFE


async def test_healing_restores_sanity_and_an_unclaimed_target_turns_to_the_son(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        town = await session.get(EntityRow, realm.settlement_id)
        mortal = await session.get(EntityRow, realm.mortal_id)
        assert town is not None and mortal is not None
        town.sanity, mortal.sanity = 30, 20
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    healed = await ok(toolkit, "miracle", {"entity_id": realm.settlement_id, "kind": "healing", "how": "a warm rain of salt"})
    gain = Rules().son_tools.healing_sanity
    assert (await entity(database, realm.settlement_id)).sanity == 30 + gain
    assert (await entity(database, realm.mortal_id)).sanity == 20 + gain
    assert "came to their senses" in healed
    assert await outgoing(database, realm.settlement_id, BondKind.WORSHIPS) == [realm.son_id]
    assert lines.MIRACLE.key in await keys(database)


async def test_a_failed_take_life_returns_part_of_the_essence(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        await EntityRepository(session).add_flag(realm.mortal_id, EntityFlag.IMMORTAL, 1)
        me = await session.get(SonRow, realm.son_id)
        assert me is not None
        me.essence = 100
    toolkit = await son_toolkit(database, realm.son_id, action_points=3, rules=tuned_rules(death={"take_life_refund_pct": 50}))
    text = await ok(toolkit, "take_life", {"entity_id": realm.mortal_id, "how": "a wave at midnight"})
    cost = int(text.split("cost ")[1].split(" ")[0])
    assert f"{round(cost / 2)} returned" in text
    assert (await son(database, realm.son_id)).essence == 100 - cost + round(cost / 2)
    assert (await entity(database, realm.mortal_id)).status is EntityStatus.CANON


async def test_scattering_bones_turns_the_resurrection_cults_hostile(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        dead = await session.get(SonRow, realm.sibling_id)
        assert dead is not None
        dead.status, dead.death_epoch = SonStatus.DEAD, 1
        cult = await make_entity(session, "Ashen Vigil", EntityType.CULT, world_id=realm.cosmos.world_id, location_id=realm.cosmos.region_id)
        cult.stats = CultStats(followers=100, zeal=60, influence=40, devotion=50)
        session.add(ResurrectionOrderRow(cult_entity_id=cult.id, son_id=dead.id))
        cult_id = cult.id
    toolkit = await son_toolkit(database, realm.son_id, action_points=3)
    await ok(toolkit, "scatter_bones", {"son_id": realm.sibling_id})
    loss = Rules().death.scatter_bones_devotion_loss
    assert (await entity(database, cult_id)).stats.model_dump()["devotion"] == max(0, 50 - loss)
    assert realm.son_id in await outgoing(database, cult_id, BondKind.ENEMY)
    assert "already plotted" in await rejected(toolkit, "scatter_bones", {"son_id": realm.sibling_id})


async def test_extinguishing_a_star_darkens_its_worlds_and_chills_the_siblings(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        star = StarRow(name="Ember Eye", star_type=StarType.RED_GIANT, brightness=60, x=2.0, y=2.0, created_epoch=1)
        session.add(star)
        await session.flush()
        world = await session.get(WorldRow, realm.cosmos.world_id)
        assert world is not None
        world.star_id, world.leakage = star.id, 10
        cosmos = await CosmosRepository(session).require_cosmos()
        doom_before = cosmos.doom_clock
        star_id = star.id
    before = await son(database, realm.son_id)
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    await ok(toolkit, "extinguish_star", {"star_id": star_id, "reason": "the light has grown cruel"})
    tools, pantheon = Rules().son_tools, Rules().pantheon
    after = await son(database, realm.son_id)
    async with database.read() as session:
        darkened = await session.get(WorldRow, realm.cosmos.world_id)
        cosmos = await CosmosRepository(session).require_cosmos()
        relation = await SonRepository(session).relation(realm.son_id, realm.sibling_id)
    assert darkened is not None and darkened.leakage == 10 + pantheon.extinguish_leak
    assert cosmos.doom_clock > doom_before
    assert after.fame == before.fame + tools.extinguish_star_renown
    assert relation == -tools.extinguish_star_relation
    assert "sky.star_extinguished" in await keys(database)


@pytest.mark.parametrize(("intent", "threshold", "won", "phrase"), [("alliance", -1000, True, "extended a hand"), ("threat", 1000, False, "with fury")])
async def test_talking_to_a_foreign_god_shifts_its_stance(database: Database, intent: str, threshold: int, won: bool, phrase: str) -> None:
    realm = await seed_realm(database)
    tools = Rules().son_tools
    rules = tuned_rules(son_tools={f"foreign_{intent}_threshold": threshold})
    toolkit = await son_toolkit(database, realm.son_id, action_points=3, rules=rules)
    async with database.read() as session:
        god = await session.get(ForeignGodRow, realm.god_id)
        assert god is not None
        stance, power = god.stance, god.power
    text = await ok(toolkit, "talk_to_foreign_god", {"god_id": realm.god_id, "intent": intent, "words": "hear me, old one"})
    async with database.read() as session:
        after = await session.get(ForeignGodRow, realm.god_id)
    assert after is not None and phrase in text
    if intent == "alliance":
        assert won and after.stance == stance + tools.foreign_alliance_attitude
    else:
        assert not won and after.stance == stance - tools.foreign_threat_fail_attitude and after.power == power


async def test_a_successful_threat_drains_the_god(database: Database) -> None:
    realm = await seed_realm(database)
    tools = Rules().son_tools
    toolkit = await son_toolkit(database, realm.son_id, action_points=3, rules=tuned_rules(son_tools={"foreign_threat_threshold": -1000}))
    await ok(toolkit, "talk_to_foreign_god", {"god_id": realm.god_id, "intent": "threat", "words": "kneel or burn"})
    async with database.read() as session:
        god = await session.get(ForeignGodRow, realm.god_id)
    assert god is not None and god.power == 40 - tools.foreign_threat_strength


async def test_an_opened_cosmic_bed_belongs_to_its_son(database: Database) -> None:
    realm = await seed_realm(database)
    async with database.write() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
        cosmos.travel_resource = TravelResource(name="Starsalt", rule="Folds space.")
    toolkit = await son_toolkit(database, realm.son_id, action_points=5)
    await ok(toolkit, "open_cosmic_bed", {"region_id": realm.cosmos.region_id, "reason": "the star-salt must flow"})
    bed = await entity(database, toolkit.created_entity_ids[-1])
    assert bed.creator_son_id == realm.son_id and bed.location_id == realm.cosmos.region_id


async def test_a_mad_son_cannot_hold_costly_deeds(database: Database) -> None:
    realm = await seed_realm(database)
    horror = Rules().cosmic_horror
    async with database.write() as session:
        me = await session.get(SonRow, realm.son_id)
        assert me is not None
        me.sanity = horror.son_madness_threshold - 1
    rules = tuned_rules(cosmic_horror={"mad_son_max_tool_actions": 0})
    toolkit = await son_toolkit(database, realm.son_id, action_points=3, rules=rules)
    refused = await rejected(toolkit, "tell_legend", creation("Mad Tale", realm.people_id))
    assert "too broken" in refused
    await ok(toolkit, "inspect_entity", {"id": realm.people_id})
