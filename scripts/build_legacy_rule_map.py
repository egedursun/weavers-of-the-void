import json
import sys
from collections import defaultdict
from pathlib import Path

from aerona.migration.legacy.vocabulary import SCHEMA_MAP_PATH
from aerona.rules.model import RuleDescriptor
from aerona.rules.registry import Rules
from aerona.rules.snapshot import catalog

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "docs" / "spec" / "rules-registry.json"
SEPARATOR = "."
INDENT = 2


def label_key(label: str) -> str:
    return " ".join(label.casefold().split())


def resolve(entry: dict[str, object], paths: set[str], labels: dict[str, list[RuleDescriptor]], keys: dict[str, list[RuleDescriptor]]) -> str | None:
    namespace, key = str(entry["namespace"]).lower(), str(entry["key"])
    direct = f"{namespace}{SEPARATOR}{key}"
    if direct in paths:
        return direct
    by_label = labels.get(label_key(str(entry.get("label", ""))), [])
    if len(by_label) == 1:
        return by_label[0].path
    same_key = [descriptor for descriptor in by_label if descriptor.key == key]
    if len(same_key) == 1:
        return same_key[0].path
    by_key = keys.get(key, [])
    if len(by_key) == 1:
        return by_key[0].path
    return None


def build() -> tuple[dict[str, str | None], list[str]]:
    descriptors = catalog(Rules())
    paths = {descriptor.path for descriptor in descriptors}
    labels: dict[str, list[RuleDescriptor]] = defaultdict(list)
    keys: dict[str, list[RuleDescriptor]] = defaultdict(list)
    for descriptor in descriptors:
        labels[label_key(descriptor.label)].append(descriptor)
        keys[descriptor.key].append(descriptor)
    mapping: dict[str, str | None] = {}
    for entry in json.loads(REGISTRY_PATH.read_text(encoding="utf-8")):
        legacy = f"{entry['old_namespace']}{SEPARATOR}{entry['old_key']}"
        mapping[legacy] = resolve(entry, paths, labels, keys)
    unmapped = sorted(legacy for legacy, target in mapping.items() if target is None)
    return dict(sorted(mapping.items())), unmapped


def main() -> int:
    mapping, unmapped = build()
    data = json.loads(SCHEMA_MAP_PATH.read_text(encoding="utf-8"))
    data["rules"] = mapping
    data["rules_unmapped"] = unmapped
    SCHEMA_MAP_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=INDENT) + "\n", encoding="utf-8")
    print(f"legacy rules: {len(mapping)} mapped entries, {len(unmapped)} without a current key")
    return 0


if __name__ == "__main__":
    sys.exit(main())
