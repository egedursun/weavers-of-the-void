from httpx import AsyncClient
from sqlalchemy import func, select

from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.rule_override import RuleOverrideRow
from tests.api.conftest import ApiWorld


async def test_rules_can_be_listed_updated_and_reset(client: AsyncClient) -> None:
    listing = await client.get("/api/rules")
    assert listing.status_code == 200
    rules = listing.json()
    assert len(rules) > 1000
    target = next(item for item in rules if item["namespace"] == "agents" and item["key"] == "concurrent_jobs")
    updated = await client.put("/api/rules/agents/concurrent_jobs", json={"value": target["minimum"]})
    assert updated.status_code == 200
    assert updated.json()["value"] == target["minimum"]
    below = await client.put("/api/rules/agents/concurrent_jobs", json={"value": target["minimum"] - 1})
    assert below.status_code == 400
    missing = await client.put("/api/rules/agents/not_a_rule", json={"value": 1})
    assert missing.status_code == 404
    reset = await client.delete("/api/rules/agents/concurrent_jobs")
    assert reset.json()["value"] == target["default"]


async def test_rule_update_that_breaks_ordering_is_rejected(client: AsyncClient) -> None:
    response = await client.put("/api/rules/core_rules/tier_uncommon", json={"value": 9})
    assert response.status_code == 400
    assert "tier_uncommon" in response.json()["error"]


async def test_batch_rule_update_reaches_the_world_snapshot(api: ApiWorld) -> None:
    rules = (await api.http.get("/api/rules")).json()
    target = next(item for item in rules if item["namespace"] == "costs" and item["key"] == "summon_son")
    wanted = target["default"] + 1
    response = await api.http.patch("/api/rules", json={"changes": {"costs.summon_son": wanted}})
    assert response.status_code == 200
    async with api.services.database.read() as session:
        cosmos = await CosmosRepository(session).require_cosmos()
    assert cosmos.rules_snapshot["costs"]["summon_son"] == wanted
    reset = await api.http.patch("/api/rules", json={"changes": {"costs.summon_son": None}})
    assert next(item for item in reset.json() if item["key"] == "summon_son" and item["namespace"] == "costs")["value"] == target["default"]
    assert (await api.http.patch("/api/rules", json={"changes": {"nonsense": 1}})).status_code == 400


async def test_batch_rule_update_is_atomic_and_checks_chains_on_the_result(api: ApiWorld) -> None:
    moved = await api.http.patch("/api/rules", json={"changes": {"campaigns.army_power_min": 10, "campaigns.army_power_max": 11}})
    assert moved.status_code == 200, moved.text
    values = {(item["namespace"], item["key"]): item["value"] for item in moved.json()}
    assert (values[("campaigns", "army_power_min")], values[("campaigns", "army_power_max")]) == (10, 11)
    broken = await api.http.patch("/api/rules", json={"changes": {"costs.summon_son": 1, "campaigns.army_power_max": 3}})
    assert broken.status_code == 400
    current = {(item["namespace"], item["key"]): item["value"] for item in (await api.http.get("/api/rules")).json()}
    assert current[("campaigns", "army_power_max")] == 11
    assert current[("costs", "summon_son")] == api.services.rules.current.costs.summon_son != 1


async def test_rule_maximum_is_advisory_and_carries_a_warning(client: AsyncClient) -> None:
    rules = (await client.get("/api/rules")).json()
    target = next(item for item in rules if item["namespace"] == "agents" and item["key"] == "concurrent_jobs")
    assert target["warning"] is None
    above = await client.put("/api/rules/agents/concurrent_jobs", json={"value": target["maximum"] + 5})
    assert above.status_code == 200
    assert above.json()["value"] == target["maximum"] + 5
    assert "advised maximum" in above.json()["warning"]
    listed = next(item for item in (await client.get("/api/rules")).json() if item["key"] == "concurrent_jobs" and item["namespace"] == "agents")
    assert listed["warning"] == above.json()["warning"]


async def test_integer_rules_round_fractions_and_infinite_values_are_refused(client: AsyncClient) -> None:
    rounded = await client.put("/api/rules/agents/concurrent_jobs", json={"value": 2.5})
    assert rounded.status_code == 200
    assert rounded.json()["value"] == 3
    huge = await client.put("/api/rules/agents/concurrent_jobs", json={"value": 1e300})
    assert huge.status_code == 400


async def test_storing_the_default_deletes_the_override(empty_api: ApiWorld) -> None:
    rules = (await empty_api.http.get("/api/rules")).json()
    target = next(item for item in rules if item["namespace"] == "costs" and item["key"] == "summon_son")
    await empty_api.http.put("/api/rules/costs/summon_son", json={"value": target["default"] + 1})
    async with empty_api.services.database.read() as session:
        assert await session.scalar(select(func.count()).select_from(RuleOverrideRow)) == 1
    stored = await empty_api.http.put("/api/rules/costs/summon_son", json={"value": target["default"]})
    assert stored.json()["value"] == target["default"]
    async with empty_api.services.database.read() as session:
        assert await session.scalar(select(func.count()).select_from(RuleOverrideRow)) == 0
    await empty_api.http.patch("/api/rules", json={"changes": {"costs.summon_son": target["default"] + 1}})
    await empty_api.http.patch("/api/rules", json={"changes": {"costs.summon_son": target["default"]}})
    async with empty_api.services.database.read() as session:
        assert await session.scalar(select(func.count()).select_from(RuleOverrideRow)) == 0


async def test_batch_accepts_values_above_the_maximum_and_reset_all_clears_every_override(empty_api: ApiWorld) -> None:
    rules = (await empty_api.http.get("/api/rules")).json()
    target = next(item for item in rules if item["namespace"] == "costs" and item["key"] == "summon_son")
    response = await empty_api.http.patch("/api/rules", json={"changes": {"costs.summon_son": target["maximum"] + 3}})
    assert response.status_code == 200
    changed = next(item for item in response.json() if item["namespace"] == "costs" and item["key"] == "summon_son")
    assert changed["warning"] is not None
    cleared = await empty_api.http.patch("/api/rules", json={"changes": {}, "reset_all": True})
    assert next(item for item in cleared.json() if item["namespace"] == "costs" and item["key"] == "summon_son")["value"] == target["default"]
    await empty_api.http.put("/api/rules/costs/summon_son", json={"value": target["default"] + 1})
    assert (await empty_api.http.delete("/api/rules")).status_code == 204
    after = next(item for item in (await empty_api.http.get("/api/rules")).json() if item["namespace"] == "costs" and item["key"] == "summon_son")
    assert after["value"] == target["default"]
    async with empty_api.services.database.read() as session:
        assert await session.scalar(select(func.count()).select_from(RuleOverrideRow)) == 0
