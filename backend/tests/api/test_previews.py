from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agency import AgentTurnRow, TurnCounterRow
from aerona.db.tables.lore import MessageRow
from aerona.domain.enums.agent import MessageIntent, ToolBlock, TurnCounter
from aerona.domain.enums.rarity import Rarity
from aerona.domain.models.turn import TurnContext
from aerona.prompts.contexts.opportunities import CreatorHintKind
from tests.api.conftest import ApiWorld, seeded


async def test_son_tools_split_by_rarity_gate(api: ApiWorld) -> None:
    son = seeded(api).core.son
    async with api.services.database.write() as session:
        son.rarity = Rarity.COMMON
        session.add(son)
    body = (await api.http.get(f"/api/sons/{son.id}/tools")).json()
    assert body["son_id"] == son.id
    assert body["available"]
    assert all(tool["description"] for tool in body["available"])
    assert any(item["reason"] == ToolBlock.RARITY for item in body["blocked"])
    assert {item["name"] for item in body["available"]}.isdisjoint({item["name"] for item in body["blocked"]})
    assert (await api.http.get("/api/sons/999999/tools")).status_code == 404


async def test_son_opportunity_lines_render_server_text(api: ApiWorld) -> None:
    son = seeded(api).core.son
    response = await api.http.get(f"/api/sons/{son.id}/opportunities")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["subject_id"] == son.id
    for line in body["lines"]:
        assert line["text"].strip()
        assert not line["text"].startswith("- ")
        assert isinstance(line["tools"], list)
    assert (await api.http.get("/api/sons/999999/opportunities")).status_code == 404


async def test_entity_opportunities_and_agent_context(api: ApiWorld) -> None:
    creation = seeded(api).creation
    lines = await api.http.get(f"/api/entities/{creation.id}/opportunities")
    assert lines.status_code == 200, lines.text
    context = await api.http.get(f"/api/entities/{creation.id}/agent-context")
    assert context.status_code == 200, context.text
    body = context.json()
    assert body["entity_id"] == creation.id
    assert creation.name in body["system_prompt"] or body["system_prompt"]
    assert body["user_prompt"]
    assert body["action_points"] > 0
    assert (await api.http.get("/api/entities/999999/agent-context")).status_code == 404


async def test_creator_hint_lines_follow_warning_percentage(api: ApiWorld) -> None:
    async with api.services.database.write() as session:
        creator = await CosmosRepository(session).require_creator()
        creator.essence = 100000
    body = (await api.http.get("/api/opportunities/creator")).json()
    kinds = {line["kind"] for line in body["lines"]}
    assert CreatorHintKind.RICH_ESSENCE in kinds
    assert CreatorHintKind.DOOM not in kinds


async def test_reset_counters_clears_epoch_counters(api: ApiWorld) -> None:
    son = seeded(api).core.son
    async with api.services.database.write() as session:
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        session.add(TurnCounterRow(agent_node_id=son.id, epoch=epoch, counter=TurnCounter.GIFTS, value=2))
        session.add(
            AgentTurnRow(agent_node_id=son.id, agent_kind="son", epoch=epoch, action_points_left=3, context=TurnContext().with_creation(1), finished=False)
        )
    shown = (await api.http.get(f"/api/sons/{son.id}/tools")).json()
    assert {"counter": "gifts", "value": 2} in shown["counters"]
    reset = await api.http.post(f"/api/sons/{son.id}/reset-counters", json={})
    assert reset.status_code == 200, reset.text
    assert reset.json()["values"]["cleared"] == 1
    assert (await api.http.get(f"/api/sons/{son.id}/tools")).json()["counters"] == []


async def test_force_rebellion_marks_the_son(api: ApiWorld) -> None:
    son = seeded(api).core.son
    response = await api.http.post(f"/api/sons/{son.id}/rebellion", json={"manifesto": "No more tribute."})
    assert response.status_code == 200, response.text
    again = await api.http.post(f"/api/sons/{son.id}/rebellion", json={"manifesto": "No more tribute."})
    assert again.status_code == 400
    blank = await api.http.post(f"/api/sons/{son.id}/rebellion", json={"manifesto": " "})
    assert blank.status_code == 400


async def test_dream_inbox_lists_both_directions(api: ApiWorld) -> None:
    world = seeded(api)
    async with api.services.database.write() as session:
        epoch = (await CosmosRepository(session).require_cosmos()).epoch
        session.add(
            MessageRow(epoch=epoch, sender_node_id=world.core.son.id, recipient_node_id=world.creation.id, intent=MessageIntent.DREAM, text="Salt rises.")
        )
        session.add(
            MessageRow(epoch=epoch, sender_node_id=world.creation.id, recipient_node_id=world.core.son.id, intent=MessageIntent.DREAM, text="I saw a tower.")
        )
    body = (await api.http.get(f"/api/entities/{world.creation.id}/dreams")).json()
    assert [item["text"] for item in body["received"]] == ["Salt rises."]
    assert [item["text"] for item in body["sent"]] == ["I saw a tower."]
    assert body["received"][0]["is_read"] is False


async def test_doom_line_appears_only_past_the_warning_percentage(api: ApiWorld) -> None:
    rules = api.services.rules.current
    threshold = max(1, rules.balance.apocalypse_threshold)
    warning = rules.opportunities.apocalypse_warning_pct
    async with api.services.database.write() as session:
        (await CosmosRepository(session).require_cosmos()).doom_clock = 1 if warning > 1 else 0
    quiet = (await api.http.get("/api/opportunities/creator")).json()
    assert CreatorHintKind.DOOM not in {line["kind"] for line in quiet["lines"]}
    async with api.services.database.write() as session:
        (await CosmosRepository(session).require_cosmos()).doom_clock = threshold
    loud = (await api.http.get("/api/opportunities/creator")).json()
    doom = [line for line in loud["lines"] if line["kind"] == CreatorHintKind.DOOM]
    assert doom
    assert str(threshold) in doom[0]["text"]


async def test_foreign_god_detail_carries_server_costs(api: ApiWorld) -> None:
    listing = (await api.http.get("/api/foreign-gods")).json()
    if not listing:
        return
    body = (await api.http.get(f"/api/foreign-gods/{listing[0]['id']}")).json()
    assert body["kill_cost"] > 0
    assert body["drain_gain"] >= body["drain_amount"]
