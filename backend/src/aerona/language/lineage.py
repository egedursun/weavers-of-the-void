from collections.abc import Callable, Mapping

from aerona.language.phonology import Phonology
from aerona.language.signature import LanguageSignature, derive_signature
from aerona.rules.registry import Rules


def ancestor_chain(language_id: int, parent_of: Mapping[int, int | None], depth: int) -> list[int]:
    chain: list[int] = []
    seen = {language_id}
    current = parent_of.get(language_id)
    while current is not None and len(chain) < depth and current not in seen:
        chain.append(current)
        seen.add(current)
        current = parent_of.get(current)
    return chain


def phonology_lineage(language_id: int, parent_of: Mapping[int, int | None], rules: Rules) -> list[int]:
    return [language_id, *ancestor_chain(language_id, parent_of, rules.language.ancestry_depth)]


def resolve_signature(
    language_id: int,
    parent_of: Mapping[int, int | None],
    stored: Mapping[int, LanguageSignature],
    phonology_of: Callable[[int], Phonology],
    rules: Rules,
) -> LanguageSignature | None:
    if language_id in stored:
        return stored[language_id]
    lineage = [language_id, *ancestor_chain(language_id, parent_of, len(parent_of) + 1)]
    resolved: dict[int, LanguageSignature | None] = {}
    for position in range(len(lineage) - 1, -1, -1):
        current = lineage[position]
        if current in stored:
            resolved[current] = stored[current]
            continue
        parent = resolved.get(lineage[position + 1]) if position + 1 < len(lineage) else None
        resolved[current] = derive_signature(str(current), phonology_of(current), parent, rules)
    return resolved[language_id]
