from collections import defaultdict
from dataclasses import dataclass, field

from aerona.core.grammar import several
from aerona.domain.enums.bond import BondKind
from aerona.services.kinship.tree import KinTie, TracedFamily

ORDINALS = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth")
REMOVALS = ("once", "twice", "thrice")
NAMED_GREATS = 2
ROOT_WORD = "This mortal"
FALLBACK = "Kin by marriage"
PARTNER_WORDS = {BondKind.CONCUBINE_OF: "Concubine", BondKind.BETROTHED_TO: "Promised"}
CARE_WORDS = {
    BondKind.FOSTERED_BY: ("Fosterling", "Fosterer"),
    BondKind.GODPARENT_OF: ("Godparent", "Godchild"),
    BondKind.SWORN_KIN: ("Sworn kin", "Sworn kin"),
}
SPOUSE = "Spouse"
FORMER_SPOUSE = "Former spouse"


@dataclass
class KinGraph:
    parents: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    children: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    partners: dict[int, list[tuple[int, str]]] = field(default_factory=lambda: defaultdict(list))
    care: list[KinTie] = field(default_factory=list)


def graph_of(family: TracedFamily) -> KinGraph:
    graph = KinGraph()
    for tie in family.ties:
        if tie.kind is BondKind.PARENT_OF:
            graph.parents[tie.target_id].append(tie.source_id)
            graph.children[tie.source_id].append(tie.target_id)
        elif tie.kind in PARTNER_WORDS:
            graph.partners[tie.source_id].append((tie.target_id, PARTNER_WORDS[tie.kind]))
            graph.partners[tie.target_id].append((tie.source_id, PARTNER_WORDS[tie.kind]))
        else:
            graph.care.append(tie)
    for union in family.unions:
        word = SPOUSE if union.end_epoch is None else FORMER_SPOUSE
        graph.partners[union.first_id].append((union.second_id, word))
        graph.partners[union.second_id].append((union.first_id, word))
    return graph


def line_word(base: str, depth: int) -> str:
    if depth == 1:
        return base.capitalize()
    grand = f"grand{base}"
    if depth == 2:
        return grand.capitalize()
    greats = depth - 2
    if greats <= NAMED_GREATS:
        return f"Great-{'great-' * (greats - 1)}{grand}"
    return f"{ordinal(greats)} great-{grand}"


def ordinal(number: int) -> str:
    suffix = "th" if 11 <= number % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def lower(word: str) -> str:
    return word if word[:1].isdigit() else word[:1].lower() + word[1:]


def cousin(degree: int, removed: int) -> str:
    ordinal = ORDINALS[degree - 1] if degree <= len(ORDINALS) else f"{degree}th"
    base = f"{ordinal} cousin"
    if removed == 0:
        return base
    times = REMOVALS[removed - 1] if removed <= len(REMOVALS) else several(removed, "time", "times")
    return f"{base} {times} removed"


def ancestry(graph: KinGraph, start: int) -> dict[int, int]:
    steps = {start: 0}
    frontier = [start]
    depth = 0
    while frontier:
        depth += 1
        grown: list[int] = []
        for person in frontier:
            for parent in graph.parents.get(person, []):
                if parent not in steps:
                    steps[parent] = depth
                    grown.append(parent)
        frontier = grown
    return steps


def collateral(graph: KinGraph, root: int, person: int, from_root: int, from_person: int) -> str:
    if from_root == 1 and from_person == 1:
        common = set(graph.parents.get(root, [])) & set(graph.parents.get(person, []))
        return "Sibling" if len(common) >= 2 else "Half-sibling"
    if from_root == 1:
        return f"Sibling's {lower(line_word('child', from_person - 1))}"
    if from_person == 1:
        return f"{line_word('parent', from_root - 1)}'s sibling"
    return cousin(min(from_root, from_person) - 1, abs(from_root - from_person))


def blood_word(graph: KinGraph, root: int, root_up: dict[int, int], person: int) -> str | None:
    shared = [(root_up[ancestor], depth) for ancestor, depth in ancestry(graph, person).items() if ancestor in root_up]
    if not shared:
        return None
    from_root, from_person = min(shared, key=lambda pair: (pair[0] + pair[1], pair[0]))
    if from_person == 0:
        return line_word("parent", from_root)
    if from_root == 0:
        return line_word("child", from_person)
    return collateral(graph, root, person, from_root, from_person)


def partner_word(word: str) -> str:
    return lower(word)


def through_partner(graph: KinGraph, root: int, blood: dict[int, str], person: int) -> str | None:
    root_partners = {other for other, _ in graph.partners.get(root, [])}
    for other, word in graph.partners.get(person, []):
        if other == root:
            return word
        kin = blood.get(other)
        if kin is not None:
            return "Step-parent" if kin == "Parent" and word == SPOUSE else f"{kin}'s {partner_word(word)}"
    return next((f"Spouse's {partner_word(word)}" for other, word in graph.partners.get(person, []) if other in root_partners), None)


def through_step(graph: KinGraph, root: int, blood: dict[int, str], person: int) -> str | None:
    root_partners = {other for other, _ in graph.partners.get(root, [])}
    parents = graph.parents.get(person, [])
    if any(parent in root_partners for parent in parents):
        return "Stepchild"
    if any(child in root_partners for child in graph.children.get(person, [])):
        return "Spouse's parent"
    for parent in parents:
        for other, _ in graph.partners.get(parent, []):
            kin = blood.get(other)
            if kin is not None:
                return "Step-sibling" if kin == "Parent" else f"{kin}'s stepchild"
    return None


def by_spouse(graph: KinGraph, root: int, blood: dict[int, str], person: int) -> str | None:
    return through_partner(graph, root, blood, person) or through_step(graph, root, blood, person)


def by_care(graph: KinGraph, root: int, named: dict[int, str], person: int) -> str | None:
    for tie in graph.care:
        words = CARE_WORDS.get(tie.kind)
        if words is None or person not in (tie.source_id, tie.target_id):
            continue
        other = tie.target_id if tie.source_id == person else tie.source_id
        source_word, target_word = words
        word = source_word if tie.source_id == person else target_word
        if other == root:
            return word
        kin = named.get(other)
        if kin is not None:
            return f"{kin}'s {lower(word)}"
    return None


def relations_of(family: TracedFamily) -> dict[int, str]:
    graph = graph_of(family)
    root_up = ancestry(graph, family.root)
    blood: dict[int, str] = {}
    for person in family.people:
        if person.id == family.root:
            continue
        word = blood_word(graph, family.root, root_up, person.id)
        if word is not None:
            blood[person.id] = word
    named = {**blood, family.root: ROOT_WORD}
    for person in family.people:
        if person.id not in named:
            spouse_word = by_spouse(graph, family.root, blood, person.id)
            if spouse_word is not None:
                named[person.id] = spouse_word
    for person in family.people:
        if person.id not in named:
            named[person.id] = by_care(graph, family.root, named, person.id) or FALLBACK
    return named
