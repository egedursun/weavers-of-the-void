from aerona.catalog.body_plans import PLANS
from aerona.catalog.bonds import BOND_KINDS
from aerona.catalog.creatures import CREATURE_TRAITS
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.entity_types import ENTITY_TYPES, EntityTypeSpec
from aerona.catalog.interventions import DISASTERS, MIRACLES
from aerona.catalog.stars import STAR_TYPES
from aerona.catalog.structures import STRUCTURES
from aerona.catalog.tenets import TENET_EFFECTS
from aerona.catalog.worlds import WORLD_TYPES
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.culture import ArtMedium, IdeologyTenet, MagicSchool, MagicSource, ProphecyConsequence, ProphecyPredicate, RiteEffectKind
from aerona.domain.enums.ecology import BeastTemper, Diet, SizeClass, Sociality, YieldProduct
from aerona.domain.enums.economy import CommodityKind, MaterialFamily
from aerona.domain.enums.entity import LIVING_CREATION_TYPES, EntityType, LegendCategory
from aerona.domain.enums.faith import FuneralRite, JudgementDoctrine, RebirthPath
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.place import PlaceKind, SecretKind
from aerona.domain.enums.travel import VehicleKind
from aerona.prompts.contexts.blocks import SummarySection
from aerona.prompts.environment import normalize, string_template
from aerona.prompts.errors import UnknownToolError
from aerona.prompts.schemas.descriptions import knowledge_branches, natural_laws, resource_mechanics
from aerona.prompts.tools.context import ToolTextContext
from aerona.prompts.tools.ids import MortalToolId, SonToolId, ToolId
from aerona.prompts.tools.mortal import MORTAL_TOOL_TEXTS
from aerona.prompts.tools.son import CREATION_TOOLS, SON_TOOL_TEXTS
from aerona.prompts.tools.text import RenderedToolText, ToolText
from aerona.rules.registry import Rules

LAND_TYPES = frozenset({EntityType.REGION, EntityType.PLACE})
STATS_FIELD = "stats"


def text_of(tool_id: ToolId) -> ToolText:
    if isinstance(tool_id, SonToolId) and tool_id in SON_TOOL_TEXTS:
        return SON_TOOL_TEXTS[tool_id]
    if isinstance(tool_id, MortalToolId) and tool_id in MORTAL_TOOL_TEXTS:
        return MORTAL_TOOL_TEXTS[tool_id]
    raise UnknownToolError(str(tool_id))


def creation_entity(tool_id: ToolId) -> EntityTypeSpec | None:
    if isinstance(tool_id, SonToolId) and tool_id in CREATION_TOOLS:
        return ENTITY_TYPES[CREATION_TOOLS[tool_id]]
    return None


def stat_fields(entity: EntityTypeSpec, rules: Rules) -> dict[str, str]:
    fields: dict[str, str] = {}
    for stat in entity.stats:
        low, high = stat.bounds(rules)
        span = f"{low} to {high}" if high is not None else f"at least {low}"
        fields[f"{STATS_FIELD}.{stat.key}"] = f"{stat.label} ({span})"
    return fields


def template_variables(rules: Rules, context: ToolTextContext, entity: EntityTypeSpec | None) -> dict[str, object]:
    return {
        "rules": rules,
        "context": context,
        "entity": entity,
        "container_labels": sorted(ENTITY_TYPES[kind].label for kind in entity.containers) if entity else [],
        "living_types": LIVING_CREATION_TYPES,
        "land_types": LAND_TYPES,
        "domains": [DOMAIN_LABELS[domain] for domain in DOMAIN_LABELS],
        "summary_sections": [section.value for section in SummarySection],
        "weavable_bonds": [kind.value for kind, spec in BOND_KINDS.items() if spec.weavable],
        "miracles": "; ".join(f"{miracle} ({spec.label}: {spec.effect})" for miracle, spec in MIRACLES.items()),
        "disasters": "; ".join(f"{disaster} ({spec.label}: {spec.effect})" for disaster, spec in DISASTERS.items()),
        "natural_laws": natural_laws(),
        "resource_mechanics": resource_mechanics(),
        "knowledge_branches": knowledge_branches(),
        "body_plans": "; ".join(f"{plan} ({spec.label})" for plan, spec in PLANS.items() if plan is not BodyPlan.DIVINE_MANIFEST),
        "creature_traits": "; ".join(f"{trait} ({spec.effect})" for trait, spec in CREATURE_TRAITS.items()),
        "world_types": ", ".join(f"{kind} ({spec.label})" for kind, spec in WORLD_TYPES.items()),
        "curse_packages": "; ".join(
            f"{kind} ({spec.label}: {spec.description})" for kind, spec in PACKAGES.items() if Transmission.CURSE in spec.transmissions
        ),
        "star_types": ", ".join(f"{kind} ({spec.label})" for kind, spec in STAR_TYPES.items()),
        "vessel_kinds": [kind.value for kind in VehicleKind],
        "legend_categories": [category.value for category in LegendCategory],
        "commodities": [commodity.value for commodity in CommodityKind],
        "materials": [material.value for material in MaterialKind],
        "material_families": [family.value for family in MaterialFamily],
        "structure_kinds": ", ".join(f"{kind} ({spec.label})" for kind, spec in STRUCTURES.items()),
        "art_media": ", ".join(medium.value for medium in ArtMedium),
        "magic_schools": ", ".join(school.value for school in MagicSchool),
        "magic_sources": ", ".join(source.value for source in MagicSource),
        "rite_effects": ", ".join(effect.value for effect in RiteEffectKind),
        "ideology_tenets": ", ".join(tenet.value for tenet in IdeologyTenet),
        "prophecy_predicates": ", ".join(item.value for item in ProphecyPredicate),
        "prophecy_consequences": ", ".join(item.value for item in ProphecyConsequence),
        "size_classes": [size.value for size in SizeClass],
        "diets": [diet.value for diet in Diet],
        "socialities": [kind.value for kind in Sociality],
        "yield_products": [product.value for product in YieldProduct],
        "beast_tempers": [temper.value for temper in BeastTemper],
        "tenets": "; ".join(f"{tenet} ({effect})" for tenet, effect in TENET_EFFECTS.items()),
        "funeral_rites": [rite.value for rite in FuneralRite],
        "judgements": [doctrine.value for doctrine in JudgementDoctrine],
        "rebirth_paths": [path.value for path in RebirthPath],
        "place_kinds": [kind.value for kind in PlaceKind],
        "secret_kinds": [kind.value for kind in SecretKind],
    }


def render_text(source: str, variables: dict[str, object]) -> str:
    return normalize(string_template(source).render(**variables))


def tool_text(tool_id: ToolId, rules: Rules, context: ToolTextContext | None = None) -> RenderedToolText:
    text = text_of(tool_id)
    entity = creation_entity(tool_id)
    variables = template_variables(rules, context or ToolTextContext(), entity)
    fields = {name: render_text(source, variables) for name, source in text.fields.items()}
    if entity is not None:
        fields.update(stat_fields(entity, rules))
    return RenderedToolText(description=render_text(text.description, variables), fields=fields)


def tool_description(tool_id: ToolId, rules: Rules, context: ToolTextContext | None = None) -> str:
    return tool_text(tool_id, rules, context).description
