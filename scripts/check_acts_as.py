import sys

from aerona.catalog.structure_effects import EFFECTS, STRUCTURE_OWN_EFFECTS
from aerona.catalog.structures import ACTS_AS
from aerona.domain.enums.structure import EffectTarget, StructureKind
from aerona.engine.structures.own_effects import APPLIERS


def findings() -> list[str]:
    found: list[str] = []
    for kind in StructureKind:
        effects = STRUCTURE_OWN_EFFECTS.get(kind, ())
        if kind in ACTS_AS and not effects:
            found.append(f"{kind.value} acts as {ACTS_AS[kind].value} but has no effect of its own; give it own effects in catalog/structure_effects.py")
        for effect in effects:
            spec = EFFECTS.get(effect)
            if spec is None or spec.target not in APPLIERS:
                found.append(f"{kind.value}: own effect {effect.value} is read by no phase; give its target an applier in engine/structures/own_effects.py")
    unread = [target.value for target in EffectTarget if target not in APPLIERS]
    found.extend(f"effect target {target} has no applier" for target in unread)
    return found


def main() -> int:
    found = findings()
    for line in found:
        print(line)
    print(f"structures without their own behaviour: {len(found)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
