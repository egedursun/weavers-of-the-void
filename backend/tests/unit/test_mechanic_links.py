import time
from pathlib import Path

from aerona.engine.interconnect import explorer
from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.edges import GENERIC_CARRIERS, mechanic_reads, mechanic_writes
from aerona.engine.interconnect.registry import EdgeKind


def brute_flows(key: str) -> set[tuple[str, str, tuple[str, ...]]]:
    mine = REGISTERED[key]
    found: set[tuple[str, str, tuple[str, ...]]] = set()
    for other in REGISTERED.values():
        if other.key == key:
            continue
        out = sorted((mechanic_writes(mine) & mechanic_reads(other)) - GENERIC_CARRIERS)
        into = sorted((mechanic_writes(other) & mechanic_reads(mine)) - GENERIC_CARRIERS)
        if out:
            found.add(("out", other.key, tuple(out)))
        if into:
            found.add(("in", other.key, tuple(into)))
    return found


def test_a_mechanics_flow_links_are_exactly_the_carriers_it_shares() -> None:
    for key in sorted(REGISTERED)[:: max(1, len(REGISTERED) // 12)]:
        flows = {(link.direction, link.other, link.carriers) for link in explorer.links_of(key) if link.kind is EdgeKind.FLOW and link.other in REGISTERED}
        assert flows == brute_flows(key), key


def test_one_mechanics_links_are_found_without_building_every_edge() -> None:
    source = Path(explorer.__file__).read_text(encoding="utf-8")
    assert "cached_edges" not in source and "flow_edges" not in source
    explorer.links_of.cache_clear()
    explorer.flow_index()
    start = time.perf_counter()
    explorer.links_of(sorted(REGISTERED)[0])
    assert time.perf_counter() - start < 1.0
