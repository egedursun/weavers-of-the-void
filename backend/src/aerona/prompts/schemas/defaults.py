from aerona.catalog.bonds import BOND_KINDS
from aerona.domain.enums.bond import BondKind
from aerona.prompts.schemas.constraints import ITEMS, ArrayBounds, Constraint, EnumValues, NumberBounds, StringLength
from aerona.rules.registry import Rules

RELATED_DECISION_EXTRAS = ("close",)


def counts(path: tuple[str, ...], minimum: int, maximum: int) -> ArrayBounds:
    return ArrayBounds(path, minimum, max(1, minimum, maximum))


def suggestable_bond_kinds() -> tuple[str, ...]:
    return tuple(kind.value for kind, spec in BOND_KINDS.items() if spec.fate_suggestable)


def genesis_constraints(rules: Rules) -> list[Constraint]:
    genesis = rules.genesis
    return [
        counts(("regions",), genesis.regions_min, genesis.regions_max),
        NumberBounds(("cosmic_resource", "region_index"), 0, max(0, genesis.regions_max - 1)),
        NumberBounds(("relations", ITEMS, "value"), -genesis.initial_son_relation, genesis.initial_son_relation),
    ]


def awaken_constraints(rules: Rules) -> list[Constraint]:
    awakening = rules.awakening
    return [counts(("peoples", ITEMS, "language", "words"), awakening.words_min, awakening.words_max)]


def revelation_constraints(rules: Rules) -> list[Constraint]:
    return [NumberBounds(("power_level",), 1, rules.content.revelation_max_power)]


def judgment_constraints(rules: Rules) -> list[Constraint]:
    fate = rules.fate
    return [
        ArrayBounds(("advanced_threads",), max_items=fate.thread_advance_cap),
        NumberBounds(("rewards", ITEMS, "fame"), 1, max(1, fate.reward_cap)),
        ArrayBounds(("facts",), max_items=fate.canon_facts_max),
        ArrayBounds(("words",), max_items=fate.words_per_epoch_cap),
    ]


def chronicle_constraints(rules: Rules) -> list[Constraint]:
    minimum = rules.fate.summary_min_chars
    return [StringLength(("summary",), minimum), StringLength(("worlds", ITEMS, "summary"), minimum)]


def world_sections_constraints(rules: Rules) -> list[Constraint]:
    return [StringLength(("worlds", ITEMS, "summary"), rules.fate.summary_min_chars)]


def deepen_constraints(rules: Rules) -> list[Constraint]:
    narrative = rules.narrative
    return [
        counts(("rumours",), narrative.rumors_min, narrative.rumors_max),
        counts(("sayings",), narrative.quotes_min, narrative.quotes_max),
        counts(("details",), narrative.sensory_details_min, narrative.sensory_details_max),
    ]


def creator_epic_constraints(rules: Rules) -> list[Constraint]:
    narrative = rules.narrative
    return [counts(("sections",), narrative.epic_sections_min, narrative.epic_sections_max)]


def god_depth_constraints(rules: Rules) -> list[Constraint]:
    narrative = rules.narrative
    return [
        counts(("names",), narrative.god_names_min, narrative.god_names_max),
        counts(("secrets",), narrative.secrets_min, narrative.secrets_max),
        counts(("sayings",), narrative.quotes_min, narrative.quotes_max),
        counts(("rumours",), narrative.rumors_min, narrative.rumors_max),
    ]


def creator_depth_constraints(rules: Rules) -> list[Constraint]:
    narrative = rules.narrative
    return [
        *god_depth_constraints(rules),
        counts(("fears",), narrative.fears_min, narrative.fears_max),
        counts(("prohibitions",), narrative.taboos_min, narrative.taboos_max),
        counts(("gifts",), narrative.gifts_min, narrative.gifts_max),
    ]


def foreign_depth_constraints(rules: Rules) -> list[Constraint]:
    powers = rules.foreign_gods.powers_count
    return [*god_depth_constraints(rules), ArrayBounds(("powers",), min(1, powers), max(1, powers))]


def council_constraints(rules: Rules) -> list[Constraint]:
    return [ArrayBounds(("alliances",), max_items=rules.council.alliance_rupture_cap)]


def son_chat_constraints(rules: Rules) -> list[Constraint]:
    limit = rules.council.chat_loyalty_max_change
    return [NumberBounds(("loyalty_change",), -limit, limit)]


def translation_constraints(rules: Rules) -> list[Constraint]:
    return [ArrayBounds(("new_words",), max_items=rules.council.translate_new_words_max)]


def new_world_constraints(rules: Rules) -> list[Constraint]:
    birth = rules.world_birth
    physics = rules.world_physics
    last_region = max(0, birth.regions_max - 1)
    return [
        counts(("regions",), birth.regions_min, birth.regions_max),
        counts(("language", "words"), birth.words_min, birth.words_max),
        ArrayBounds(("unique_resource", "mechanics"), max_items=birth.resource_mechanics_max),
        ArrayBounds(("natives",), max_items=birth.natives_max),
        NumberBounds(("unique_resource", "region_index"), 0, last_region),
        NumberBounds(("cosmic_resource", "region_index"), 0, last_region),
        NumberBounds(("natives", ITEMS, "region_index"), 0, last_region),
        NumberBounds(("time_factor",), physics.time_factor_min / 100, physics.time_factor_max / 100),
    ]


def bond_suggest_constraints(rules: Rules) -> list[Constraint]:
    return [EnumValues(("bonds", ITEMS, "type"), suggestable_bond_kinds())]


def bond_name_related_constraints(rules: Rules) -> list[Constraint]:
    return [EnumValues(("decisions", ITEMS, "decision"), (*suggestable_bond_kinds(), BondKind.RELATED.value, *RELATED_DECISION_EXTRAS))]
