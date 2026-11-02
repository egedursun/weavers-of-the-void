from aerona.catalog.foreign_gods import FOREIGN_GOD_POWERS
from aerona.catalog.knowledge import KNOWLEDGE_BRANCHES, NATURAL_LAWS, RESOURCE_MECHANICS
from aerona.catalog.powers import POWERS
from aerona.catalog.stars import STAR_TYPES
from aerona.catalog.worlds import WORLD_TYPES
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
    }
