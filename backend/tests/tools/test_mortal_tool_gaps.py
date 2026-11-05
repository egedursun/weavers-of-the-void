from typing import Any

from aerona.db.repositories.entities import EntityRepository
from aerona.db.session import Database
from aerona.db.tables.agency import AgentTurnRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import CivilizationTier, EntityStatus
from aerona.rules.registry import Rules
from aerona.rules.snapshot import with_value
from aerona.tools.toolkit import TurnToolkit
from tests.tools.factories import DESCRIPTION, mortal_toolkit, seed_realm


async def call(toolkit: TurnToolkit, name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
    outcome = await toolkit.runtime.call(name, arguments)
    return outcome.is_error, outcome.text


async def set_tier(database: Database, entity_id: int, tier: CivilizationTier) -> None:
    async with database.write() as session:
        row = await session.get(EntityRow, entity_id)
        assert row is not None
        row.civ_tier = tier


async def created_power(database: Database, entity_id: int) -> int:
    async with database.read() as session:
        row = await session.get(EntityRow, entity_id)
        assert row is not None
        return row.power_level


async def test_route_search_is_hidden_below_its_tier_and_appears_at_it(database: Database) -> None:
    realm = await seed_realm(database)
    below = await mortal_toolkit(database, realm.people_id)
    assert "find_route" not in below.catalogue.names
    rejected, text = await call(below, "find_route", {})
    assert rejected and "not available" in text
    await set_tier(database, realm.people_id, CivilizationTier.CITY_STATE)
    at_tier = await mortal_toolkit(database, realm.people_id)
    assert "find_route" in at_tier.catalogue.names


async def test_raising_the_unlock_tier_in_the_rules_hides_the_tool_again(database: Database) -> None:
    realm = await seed_realm(database)
    await set_tier(database, realm.people_id, CivilizationTier.CITY_STATE)
    strict = with_value(Rules(), "civilization", "unlock_route_search_tier", int(CivilizationTier.COSMIC_POWER))
    toolkit = await mortal_toolkit(database, realm.people_id, rules=strict)
    assert "find_route" not in toolkit.catalogue.names


async def test_lending_follows_the_loan_tier_rule(database: Database) -> None:
    realm = await seed_realm(database)
    open_by_default = await mortal_toolkit(database, realm.people_id)
    assert "lend" in open_by_default.catalogue.names
    gated = with_value(Rules(), "civilization", "unlock_loan_tier", int(CivilizationTier.KINGDOM))
    hidden = await mortal_toolkit(database, realm.people_id, rules=gated)
    assert "lend" not in hidden.catalogue.names
    await set_tier(database, realm.people_id, CivilizationTier.KINGDOM)
    shown = await mortal_toolkit(database, realm.people_id, rules=gated)
    assert "lend" in shown.catalogue.names


async def test_a_mortal_inherits_the_tier_of_its_community_for_tool_gates(database: Database) -> None:
    realm = await seed_realm(database)
    gated = with_value(Rules(), "civilization", "unlock_exploration_tier", int(CivilizationTier.KINGDOM))
    hidden = await mortal_toolkit(database, realm.mortal_id, rules=gated)
    assert "explore_land" not in hidden.catalogue.names
    await set_tier(database, realm.settlement_id, CivilizationTier.KINGDOM)
    shown = await mortal_toolkit(database, realm.mortal_id, rules=gated)
    assert "explore_land" in shown.catalogue.names


async def test_a_spent_per_epoch_tool_is_withheld_from_a_resumed_turn(database: Database) -> None:
    realm = await seed_realm(database)
    capped = with_value(Rules(), "mortal_tools", "coin_word_per_epoch", 1)
    first = await mortal_toolkit(database, realm.people_id, action_points=5, rules=capped)
    rejected, text = await call(first, "coin_words", {"words": [{"word": "sela", "meaning": "salt"}]})
    assert not rejected, text
    rejected, text = await call(first, "coin_words", {"words": [{"word": "mora", "meaning": "home"}]})
    assert rejected and "mortal_tools.coin_word_per_epoch" in text
    resumed = await mortal_toolkit(database, realm.people_id, action_points=5, rules=capped)
    assert "coin_words" not in resumed.catalogue.names
    rejected, _ = await call(resumed, "coin_words", {"words": [{"word": "tare", "meaning": "wind"}]})
    assert rejected


async def test_a_higher_per_epoch_cap_allows_the_second_call(database: Database) -> None:
    realm = await seed_realm(database)
    roomy = with_value(Rules(), "mortal_tools", "coin_word_per_epoch", 2)
    toolkit = await mortal_toolkit(database, realm.people_id, action_points=5, rules=roomy)
    for word, meaning in (("sela", "salt"), ("mora", "home")):
        rejected, text = await call(toolkit, "coin_words", {"words": [{"word": word, "meaning": meaning}]})
        assert not rejected, text
    rejected, _ = await call(toolkit, "coin_words", {"words": [{"word": "tare", "meaning": "wind"}]})
    assert rejected


async def test_a_zero_per_epoch_cap_removes_the_tool(database: Database) -> None:
    realm = await seed_realm(database)
    off = with_value(Rules(), "mortal_tools", "coin_word_per_epoch", 0)
    toolkit = await mortal_toolkit(database, realm.people_id, rules=off)
    assert "coin_words" not in toolkit.catalogue.names


async def culture_power(database: Database, rules: Rules, creator_power: int) -> int:
    realm = await seed_realm(database)
    async with database.write() as session:
        row = await session.get(EntityRow, realm.mortal_id)
        assert row is not None
        row.power_level = creator_power
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=5, rules=rules)
    rejected, text = await call(
        toolkit,
        "create_culture",
        {"kind": "legend", "name": "The Drowned Bell", "description": DESCRIPTION, "related_ids": [realm.species_id], "legend_category": "relic"},
    )
    assert not rejected, text
    return await created_power(database, toolkit.created_entity_ids[-1])


async def test_mortal_creation_power_follows_the_creators_power_share(database: Database) -> None:
    rules = with_value(with_value(Rules(), "mortal_tools", "creation_power_pct", 50), "mortal_tools", "creation_power_cap", 30)
    assert await culture_power(database, rules, 10) == 5


async def test_mortal_creation_power_is_clamped_to_the_cap(database: Database) -> None:
    rules = with_value(with_value(Rules(), "mortal_tools", "creation_power_pct", 100), "mortal_tools", "creation_power_cap", 4)
    assert await culture_power(database, rules, 10) == 4


async def test_mortal_creation_power_never_falls_below_one(database: Database) -> None:
    rules = with_value(with_value(Rules(), "mortal_tools", "creation_power_pct", 1), "mortal_tools", "creation_power_cap", 30)
    assert await culture_power(database, rules, 3) == 1


async def test_a_mortal_who_loses_canon_mid_turn_is_refused_and_the_turn_is_exhausted(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await mortal_toolkit(database, realm.mortal_id, action_points=5)
    async with database.write() as session:
        row = await session.get(EntityRow, realm.mortal_id)
        assert row is not None
        await EntityRepository(session).set_status(row, EntityStatus.DEAD, 3, "died between calls")
    rejected, text = await call(toolkit, "adopt", {"child_id": realm.mortal_id, "reason": "a last wish"})
    assert rejected
    assert "Ilsa Morrow" in text
    async with database.read() as session:
        turn = await session.get(AgentTurnRow, realm.mortal_id)
        assert turn is not None and turn.action_points_left == 0
