import importlib.util
from pathlib import Path
from types import ModuleType

from aerona.rules.registry.loops import LoopRules

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "balance_sim.py"
SHORT_RUN = 6
LOOP_DELAY = 2


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("balance_sim", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_band_names_a_measured_metric() -> None:
    sim = load()
    bands = sim.load_bands()
    assert bands and all(band.low <= band.high and band.meaning for band in bands)


async def test_a_short_llm_free_run_stays_inside_the_balance_bands() -> None:
    sim = load()
    values = await sim.run(SHORT_RUN)
    assert {band.metric for band in sim.load_bands()} == set(values)
    assert sim.outside(values) == []


async def test_balancing_loops_with_their_delays_do_not_swing_out_of_the_bands() -> None:
    sim = load()
    delays = {f"loops.{name}": float(LOOP_DELAY) for name in LoopRules.__dataclass_fields__}
    values = await sim.run(SHORT_RUN, delays)
    assert sim.outside(values) == []
