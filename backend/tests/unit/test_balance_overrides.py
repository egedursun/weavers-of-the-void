import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from aerona.rules.registry import Rules

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "balance_sim.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("balance_sim_overrides", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_the_rules_a_balance_run_is_given_reach_the_simulation() -> None:
    sim = load()
    seen: list[Rules | None] = []

    async def simulate(_database: Any, _epochs: int, *, rules: Rules | None = None) -> list[Any]:
        seen.append(rules)
        return []

    async def seed(_session: Any) -> None:
        return None

    async def nothing(*_args: Any) -> dict[str, float]:
        return {}

    async def counted(_database: Any) -> int:
        return 0

    for name, stand_in in {"simulate": simulate, "seed_rich_cosmos": seed, "measure": nothing, "community_count": counted}.items():
        setattr(sim, name, stand_in)
    await sim.run(2, {"loops.delay_war_weariness": 2.0})
    assert len(seen) == 2 and all(rules is not None and rules.loops.delay_war_weariness == 2 for rules in seen)


def test_a_share_of_too_few_cases_counts_as_none() -> None:
    sim = load()
    assert sim.share(2, 3) == 0.0 and sim.share(2, 4) == 0.0 and sim.share(3, 6) == 50.0
