import sqlite3
from pathlib import Path

from sqlalchemy import inspect, select

from aerona.agents.metrics import call_row, call_status
from aerona.db.telemetry.setup import setup_telemetry, telemetry_url
from aerona.db.telemetry.tables import LiveEventRow, LlmCallRow
from aerona.domain.enums.telemetry import LlmCallKind, LlmCallStatus
from aerona.llm.records import AgentRun, CallKind, CallOutcome, CallRecord

OLD_CALLS_TABLE = (
    "CREATE TABLE llm_calls (id INTEGER PRIMARY KEY, epoch INTEGER, job VARCHAR(120) NOT NULL, role VARCHAR(80), model VARCHAR(80) NOT NULL, "
    "kind VARCHAR(40) NOT NULL CHECK (kind IN ('agent', 'structured')), status VARCHAR(40) NOT NULL CHECK (status IN ('ok', 'error')), "
    "duration_ms BIGINT NOT NULL, attempts INTEGER NOT NULL, turns INTEGER, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL, "
    "cost_usd FLOAT NOT NULL, actions INTEGER, error TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL)"
)
OLD_CALL_ROW = (
    "INSERT INTO llm_calls (job, model, kind, status, duration_ms, attempts, input_tokens, output_tokens, cost_usd) "
    "VALUES ('fate', 'haiku', 'structured', 'ok', 10, 1, 0, 0, 0.0)"
)


async def test_telemetry_lives_in_its_own_file(tmp_path: Path) -> None:
    url = telemetry_url(tmp_path)
    assert url.endswith("telemetry.db")
    database = await setup_telemetry(url)
    try:
        async with database.engine.connect() as connection:
            names = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
        assert names == {"llm_calls", "live_events", "usage_totals"}
        async with database.sessions() as session, session.begin():
            session.add(
                LlmCallRow(job="son turn", model="haiku", kind=LlmCallKind.AGENT, status=LlmCallStatus.OK, duration_ms=1200, input_tokens=10, output_tokens=5)
            )
            session.add(LiveEventRow(timestamp_ms=1, kind="job.started", data={"id": "x"}))
        assert (tmp_path / "telemetry.db").exists()
    finally:
        await database.dispose()


async def test_an_old_call_table_is_rebuilt_to_accept_partial_calls(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.db"
    with sqlite3.connect(path) as connection:
        connection.execute(OLD_CALLS_TABLE)
        connection.execute(OLD_CALL_ROW)
    database = await setup_telemetry(telemetry_url(tmp_path))
    try:
        async with database.sessions() as session, session.begin():
            session.add(LlmCallRow(job="son turn", model="haiku", kind=LlmCallKind.AGENT, status=LlmCallStatus.PARTIAL, duration_ms=5))
        async with database.sessions() as session:
            statuses = list(await session.scalars(select(LlmCallRow.status).order_by(LlmCallRow.id)))
        assert statuses == [LlmCallStatus.OK, LlmCallStatus.PARTIAL]
        async with database.engine.connect() as connection:
            columns = await connection.run_sync(lambda sync: {column["name"] for column in inspect(sync).get_columns("llm_calls")})
        assert "cost_usd" not in columns
    finally:
        await database.dispose()


def test_an_unfinished_agent_session_is_recorded_as_partial() -> None:
    finished = CallRecord(label="son turn", kind=CallKind.AGENT, model="haiku")
    AgentRun(text="", usage=finished.usage, completed=True, stop_reason=None)
    unfinished = CallRecord(label="son turn", kind=CallKind.AGENT, model="haiku")
    AgentRun(text="", usage=unfinished.usage, completed=False, stop_reason=None)
    failed = CallRecord(label="son turn", kind=CallKind.AGENT, model="haiku", outcome=CallOutcome.TIMEOUT)
    assert [call_status(record) for record in (finished, unfinished, failed)] == [LlmCallStatus.OK, LlmCallStatus.PARTIAL, LlmCallStatus.ERROR]
    assert call_row(unfinished, 3, 2).status is LlmCallStatus.PARTIAL
