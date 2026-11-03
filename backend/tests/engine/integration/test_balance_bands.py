import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[4] / "scripts" / "balance_sim.py"
SHORT_RUN = 6


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
