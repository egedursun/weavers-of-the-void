from typing import Any

import pytest

from aerona.epoch import retry
from aerona.services import agent_ports
from aerona.services.agent_ports import AgentDeepener, AgentFateControls, AgentNamer, AgentNarrator, AgentPowerWriter


class Calls:
    def __init__(self) -> None:
        self.seen: list[tuple[str, tuple[Any, ...]]] = []

    def stand_in(self, name: str, result: Any = None) -> Any:
        async def call(*args: Any) -> Any:
            self.seen.append((name, args[1:]))
            return result

        return call


class NamedResult:
    named = 4


FATE = ("retry_fate", "rejudge_debt", "rejudge_limbo", "retry_voices", "retry_births")


async def test_every_agent_port_reaches_its_own_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = Calls()
    runtime: Any = object()
    monkeypatch.setattr(agent_ports, "deepen_entity", calls.stand_in("deepen_entity"))
    monkeypatch.setattr(agent_ports, "deepen_foreign_god", calls.stand_in("deepen_foreign_god"))
    monkeypatch.setattr(agent_ports, "name_pending_records", calls.stand_in("name_pending_records", NamedResult()))
    monkeypatch.setattr(agent_ports, "complete_son_powers", calls.stand_in("complete_son_powers"))
    monkeypatch.setattr(agent_ports, "backfill_epoch", calls.stand_in("backfill_epoch"))
    for name in FATE:
        monkeypatch.setattr(retry, name, calls.stand_in(name, {name: 1}))
    monkeypatch.setattr(retry, "audit_epoch_chronicle", calls.stand_in("audit_epoch_chronicle", {"epoch": 7}))
    deepener = AgentDeepener(runtime)
    await deepener.deepen_entity(11)
    await deepener.deepen_foreign_god(12)
    assert await AgentNamer(runtime).name_pending() == 4
    await AgentPowerWriter(runtime).write_powers(13)
    await AgentNarrator(runtime).narrate(14)
    fate = AgentFateControls(runtime)
    for name in FATE:
        assert await getattr(fate, name)() == {name: 1}
    assert await fate.audit_chronicle(7) == {"epoch": 7}
    assert calls.seen == [
        ("deepen_entity", (11,)),
        ("deepen_foreign_god", (12,)),
        ("name_pending_records", ()),
        ("complete_son_powers", (13,)),
        ("backfill_epoch", (14,)),
        *((name, ()) for name in FATE),
        ("audit_epoch_chronicle", (7,)),
    ]
