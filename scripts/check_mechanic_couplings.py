import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "src"))

from aerona.engine.interconnect.catalog import REGISTERED
from aerona.engine.interconnect.edges import edges_of
from aerona.engine.interconnect.registry import EdgeKind, Mechanic

MINIMUM = 2


def reach(mechanic: Mechanic) -> set[str]:
    declared = {coupling.target.value for coupling in mechanic.couplings}
    flowing = {
        subsystem.value
        for edge in edges_of(mechanic.key)
        if edge.kind is not EdgeKind.RULE_SWITCH
        for subsystem in (edge.source, edge.target)
    }
    return (declared | flowing) - {mechanic.subsystem.value}


def problems(mechanics: list[Mechanic]) -> list[str]:
    return [
        f"{mechanic.key} ({mechanic.subsystem.value}): couples to {len(reach(mechanic))} other subsystem(s); it needs {MINIMUM} or a stated reason"
        for mechanic in sorted(mechanics, key=lambda item: item.key)
        if len(reach(mechanic)) < MINIMUM and not mechanic.isolated_reason
    ]


def main() -> int:
    lines = problems(list(REGISTERED.values()))
    for line in lines:
        print(line)
    print(f"mechanic couplings: {len(REGISTERED)} mechanics, {len(lines)} problem(s)")
    return 1 if lines else 0


if __name__ == "__main__":
    raise SystemExit(main())
