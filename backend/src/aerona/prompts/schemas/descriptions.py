from aerona.catalog.climate import CLIMATES
from aerona.catalog.cosmography import DIMENSION_KINDS, WORLD_AGE_LABELS
from aerona.catalog.dominion import SCALE_POLES
from aerona.catalog.foreign_gods import FOREIGN_GOD_POWERS
from aerona.catalog.genesis import LAYER_KINDS
from aerona.catalog.knowledge import KNOWLEDGE_BRANCHES, NATURAL_LAWS, RESOURCE_MECHANICS
from aerona.catalog.powers import POWERS
from aerona.catalog.stars import STAR_TYPES
from aerona.catalog.worlds import WORLD_TYPES
from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.domain.enums.dominion import DivineScale
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.son import ExistenceMode
from aerona.prompts.data.foreign_gods import foreign_power_effect
from aerona.prompts.environment import template
from aerona.rules.registry import Rules


def image_prompt_rules() -> str:
    return template("shared/image_prompt_rules.md.j2").render().strip()


def rationale_rule(rules: Rules) -> str:
    return template("shared/rationale_rule.md.j2").render(rules=rules).strip()


def power_effects(rules: Rules) -> str:
    return " | ".join(f"{effect}: {spec.describe(rules)}" for effect, spec in POWERS.items())


def natural_laws() -> str:
    return "; ".join(f"{law}: {spec.effect}" for law, spec in NATURAL_LAWS.items())


def knowledge_branches() -> str:
    return "; ".join(f"{branch} ({spec.effect})" for branch, spec in KNOWLEDGE_BRANCHES.items())


def resource_mechanics() -> str:
    return " | ".join(f"{mechanic}: {spec.effect}" for mechanic, spec in RESOURCE_MECHANICS.items())


def foreign_god_powers(rules: Rules) -> str:
    return "; ".join(f"{effect} ({spec.label}: {foreign_power_effect(effect, rules)})" for effect, spec in FOREIGN_GOD_POWERS.items())


def star_type_catalogue() -> str:
    return "; ".join(f"{kind} ({spec.label}: {spec.description})" for kind, spec in STAR_TYPES.items())


def world_type_catalogue() -> str:
    return "; ".join(f"{kind} ({spec.label}: {spec.description})" for kind, spec in WORLD_TYPES.items())


def climate_era_catalogue() -> str:
    return "; ".join(f"{era} ({spec.label}: {spec.description})" for era, spec in CLIMATES.items())


def world_age_catalogue() -> str:
    return "; ".join(f"{age} ({label})" for age, label in WORLD_AGE_LABELS.items())


def layer_kind_catalogue() -> str:
    return "; ".join(f"{kind} ({DIMENSION_KINDS[kind].label}: {DIMENSION_KINDS[kind].description})" for kind in LAYER_KINDS)


def kind_category_catalogue() -> str:
    return "; ".join(f"{concept} ({spec.plural}: {', '.join(spec.category_labels)})" for concept, spec in CONCEPTS.items())


def design_budget(rules: Rules) -> str:
    table = rules.god_design
    poles = "; ".join(f"{scale}: {SCALE_POLES[scale][0]} at +3, {SCALE_POLES[scale][1]} at -3" for scale in DivineScale)
    return (
        f"Scales: {poles}. Each step toward a favoured end costs {table.scale_cost} budget and each step the other way gives it back; heat and cold cost nothing. "
        f"Each point of dominion costs {table.dominion_cost_pct}%, of magic {table.magic_cost_pct}%, of body {table.manifestation_cost_pct}%, each power {table.power_cost}. "
        f"Budget left over keeps more of the god's rolled stats, never less than {table.stats_floor_pct}% of them."
    )


def description_variables(rules: Rules) -> dict[str, object]:
    return {
        "rules": rules,
        "image_prompt_rules": image_prompt_rules(),
        "rationale_rule": rationale_rule(rules),
        "power_effects": power_effects(rules),
        "natural_laws": natural_laws(),
        "knowledge_branches": knowledge_branches(),
        "resource_mechanics": resource_mechanics(),
        "foreign_god_powers": foreign_god_powers(rules),
        "entity_type_keys": ", ".join(EntityType),
        "existence_states": ", ".join(ExistenceMode),
        "star_types": star_type_catalogue(),
        "world_types": world_type_catalogue(),
        "climate_eras": climate_era_catalogue(),
        "world_ages": world_age_catalogue(),
        "dimension_kinds": layer_kind_catalogue(),
        "design_budget": design_budget(rules),
        "kind_categories": kind_category_catalogue(),
    }
