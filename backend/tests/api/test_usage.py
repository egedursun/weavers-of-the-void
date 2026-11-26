from sqlalchemy import delete

from aerona.agents.metrics import count_lifetime
from aerona.db.telemetry.tables import LlmCallRow
from aerona.domain.enums.telemetry import LlmCallKind, LlmCallStatus
from tests.api.conftest import ApiWorld

CALLS = (
    (1, "Son turn: Ithren", "opus", LlmCallKind.AGENT, LlmCallStatus.OK, 1200, 300),
    (1, "Son turn: Vael", "opus", LlmCallKind.AGENT, LlmCallStatus.ERROR, 40, 0),
    (2, "Fate", "haiku", LlmCallKind.STRUCTURED, LlmCallStatus.OK, 900, 100),
    (None, "Naming 100%", "haiku", LlmCallKind.STRUCTURED, LlmCallStatus.PARTIAL, 50, 25),
)


async def seed_calls(api: ApiWorld) -> None:
    async with api.services.application.telemetry.sessions() as session, session.begin():
        for epoch, job, model, kind, status, tokens_in, tokens_out in CALLS:
            session.add(
                LlmCallRow(
                    epoch=epoch,
                    job=job,
                    role=job.split(":", 1)[0],
                    model=model,
                    kind=kind,
                    status=status,
                    duration_ms=tokens_in,
                    attempts=2 if status is LlmCallStatus.ERROR else 1,
                    input_tokens=tokens_in,
                    output_tokens=tokens_out,
                    error="refused" if status is LlmCallStatus.ERROR else None,
                )
            )


async def test_usage_summary_breaks_tokens_down_by_every_facet(api: ApiWorld) -> None:
    await seed_calls(api)
    summary = (await api.http.get("/api/usage/summary")).json()
    assert summary["totals"]["calls"] == 4
    assert summary["totals"]["input_tokens"] == 2190
    assert summary["totals"]["output_tokens"] == 425
    assert summary["totals"]["errors"] == 1
    assert summary["totals"]["partial"] == 1
    assert summary["totals"]["retried"] == 1
    assert summary["totals"]["largest_call"] == 1500
    assert (summary["totals"]["median_call"], summary["totals"]["p95_call"]) == (1000, 1500)
    assert summary["tokenizer"] == "tiktoken o200k_base"
    assert summary["totals"]["epochs"] == 2
    assert "cost" not in str(summary)
    assert [point["epoch"] for point in summary["timeline"]] == [1, 2]
    assert [share["name"] for share in summary["steps"]] == ["Son turns", "Fate", "Naming 100%"]
    assert {share["kind"] for share in summary["kinds"]} == {"agent", "structured"}
    assert summary["facets"]["models"] == ["haiku", "opus"]
    assert (summary["facets"]["epoch_low"], summary["facets"]["epoch_high"]) == (1, 2)
    daily = (await api.http.get("/api/usage/summary", params={"bucket": "day"})).json()
    assert len(daily["timeline"]) == 1
    assert daily["timeline"][0]["start"] is not None
    filtered = (await api.http.get("/api/usage/summary", params={"model": "opus", "step": "Son turns", "status": ["ok"]})).json()
    assert filtered["totals"]["calls"] == 1
    assert filtered["facets"]["calls"] == 4
    assert filtered["facets"]["tokens"] == 2615


async def test_usage_calls_search_sort_and_page(api: ApiWorld) -> None:
    await seed_calls(api)
    heaviest = (await api.http.get("/api/usage/calls", params={"sort": "total_tokens", "limit": 2})).json()
    assert heaviest["total"] == 4
    assert [call["input_tokens"] for call in heaviest["items"]] == [1200, 900]
    second = (await api.http.get("/api/usage/calls", params={"sort": "total_tokens", "limit": 2, "offset": 2})).json()
    assert [call["input_tokens"] for call in second["items"]] == [50, 40]
    lightest = (await api.http.get("/api/usage/calls", params={"sort": "input_tokens", "descending": False})).json()
    assert lightest["items"][0]["job"] == "Son turn: Vael"
    found = (await api.http.get("/api/usage/calls", params={"search": "REFUSED"})).json()
    assert [call["job"] for call in found["items"]] == ["Son turn: Vael"]
    literal = (await api.http.get("/api/usage/calls", params={"search": "100%"})).json()
    assert [call["job"] for call in literal["items"]] == ["Naming 100%"]
    epochs = (await api.http.get("/api/usage/calls", params={"epoch_from": 2, "epoch_to": 2})).json()
    assert [call["model"] for call in epochs["items"]] == ["haiku"]
    assert "cost_usd" not in epochs["items"][0]
    assert (await api.http.get("/api/usage/calls", params={"sort": "price"})).status_code in {400, 422}


async def test_usage_export_writes_every_matching_call_as_csv(api: ApiWorld) -> None:
    await seed_calls(api)
    response = await api.http.get("/api/usage/calls/export", params={"model": "haiku", "sort": "input_tokens", "descending": False})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "token-usage.csv" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("call,time,epoch,step")
    assert [line.split(",")[3] for line in lines[1:]] == ["Naming 100%", "Fate"]
    assert "1.5" not in response.text


async def test_lifetime_usage_outlives_pruned_calls_and_ranks_follow_the_rules(api: ApiWorld) -> None:
    await seed_calls(api)
    async with api.services.application.telemetry.sessions() as session, session.begin():
        await count_lifetime(session, 2615)
        await count_lifetime(session, 1000)
    before = (await api.http.get("/api/usage/summary")).json()["lifetime"]
    async with api.services.application.telemetry.sessions() as session, session.begin():
        await session.execute(delete(LlmCallRow))
    after = (await api.http.get("/api/usage/summary")).json()["lifetime"]
    assert after["tokens"] == before["tokens"] >= 3615
    assert after["calls"] == before["calls"]
    assert before["pace_epochs"] == 2 and before["pace_tokens"] == (1540 + 1000) // 2
    rules = api.services.rules.current.metrics
    assert [rank["rarity"] for rank in after["ranks"]] == ["common", "uncommon", "rare", "epic", "legendary", "mythic"]
    assert [rank["floor"] for rank in after["ranks"]][1:] == [
        rules.rank_uncommon_tokens,
        rules.rank_rare_tokens,
        rules.rank_epic_tokens,
        rules.rank_legendary_tokens,
        rules.rank_mythic_tokens,
    ]
