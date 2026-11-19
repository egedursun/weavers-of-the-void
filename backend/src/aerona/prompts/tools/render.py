from aerona.catalog.body_plans import PLANS
from aerona.catalog.bonds import BOND_KINDS
from aerona.catalog.communication import MORTAL_MEDIA
from aerona.catalog.cosmography import CLUSTER_KINDS, DIMENSION_KINDS, GALAXY_TYPES
from aerona.catalog.creatures import CREATURE_TRAITS
from aerona.catalog.cuisine import DISH_FOODS
from aerona.catalog.domain_powers import LAND_DOMAIN_WORDS, TAINTING_WORDS
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.catalog.effect_packages import PACKAGES
from aerona.catalog.entity_types import ENTITY_TYPES, EntityTypeSpec
from aerona.catalog.equipment import FAMILIES
from aerona.catalog.interventions import DISASTERS, MIRACLES
from aerona.catalog.mythic import GEAS_ACTS
from aerona.catalog.stars import STAR_TYPES
from aerona.catalog.structures import STRUCTURES
from aerona.catalog.tenets import TENET_EFFECTS
from aerona.catalog.theories import DISCIPLINES
from aerona.catalog.units import UNITS
from aerona.catalog.vehicles import FRAMES
from aerona.catalog.weather import SEASON_DOMAIN_WORDS
from aerona.catalog.worlds import WORLD_TYPES
from aerona.db.kind_concepts.society import BUILT_IN_ORGANISATIONS
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.agrarian import AidKind, KeystoneUse, PerennialKind, PreparednessKind
from aerona.domain.enums.arcana import SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.domain.enums.arts import ClubKind
from aerona.domain.enums.belonging import IdentityLayer
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.collective import CollectiveTrigger, DesignComponentKind, DesignKind, StoryletId
from aerona.domain.enums.constructs import OrderKind
from aerona.domain.enums.cosmography import DimensionElement
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.culture import ArtMode, IdeologyTenet, MagicSchool, MagicSource, ProphecyConsequence, ProphecyPredicate, RiteEffectKind
from aerona.domain.enums.cycles import (
    AdoptionKind,
    ChallengeKind,
    KinshipDescent,
    KinTermSystem,
    LongPlanKind,
    ManumissionPath,
    ReproductiveSystem,
    ResidenceRule,
)
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import FuneralCustom, MartialStyle, Sex
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.disease_agents import CureClass
from aerona.domain.enums.ecology import (
    AttackDelivery,
    AttackEffect,
    AttackRange,
    AwakeningTrigger,
    BeastTemper,
    Biochemistry,
    Diet,
    GrowthCycle,
    Habitat,
    PlantYield,
    SizeClass,
    Sociality,
    SpeciesClass,
    Temperament,
    TissueMaterial,
    YieldProduct,
)
from aerona.domain.enums.economy import CommodityKind, MaterialFamily
from aerona.domain.enums.entity import LIVING_CREATION_TYPES, EntityType, LegendCategory
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.facets import FacetKind
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.faith import JudgementDoctrine, RebirthPath
from aerona.domain.enums.forecasting import ObservationMethod, WeatherAim, WeatherWorkMethod
from aerona.domain.enums.law_depth import RegistryKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import ArmourType, Formation, ShieldType
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.mythic import CosmicOffice, GeasMode, ServitorRole
from aerona.domain.enums.nature import Dormancy, PlantDefence, Thermoregulation
from aerona.domain.enums.operations import EchelonOrder, QuirkKind
from aerona.domain.enums.place import PlaceKind, SecretKind
from aerona.domain.enums.polity import CLOSURES, HouseTrait, LawKind
from aerona.domain.enums.regime import SelectorateKind
from aerona.domain.enums.sacred import BureauRank, DivinationQuestion, OmenVerdict, PetitionKind, SacramentKind, SacramentProtection
from aerona.domain.enums.structure import BuildingForm
from aerona.domain.enums.tongues import LanguagePolicy, SoundChangeKind, SoundEnvironment
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.unions import (
    KinMatch,
    PartnerScope,
    PluralSide,
    UnionArrangement,
    UnionDescent,
    UnionDissolution,
    UnionExchange,
    UnionForm,
    UnionPurpose,
    UnionResidence,
)
from aerona.domain.enums.vehicles import MountKind
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
        "theory_domains": ", ".join(domain.value for domain in TheoryDomain),
        "art_disciplines": ", ".join(discipline.value for discipline in ArtMode),
        "art_structures": "; ".join(f"{discipline.value}: {', '.join(spec.structure)}" for discipline, spec in DISCIPLINES.items()),
        "body_plans": "; ".join(f"{plan} ({spec.label})" for plan, spec in PLANS.items() if plan is not BodyPlan.DIVINE_MANIFEST),
        "creature_traits": "; ".join(f"{trait} ({spec.effect})" for trait, spec in CREATURE_TRAITS.items()),
        "world_types": ", ".join(f"{kind} ({spec.label})" for kind, spec in WORLD_TYPES.items()),
        "curse_packages": "; ".join(
            f"{kind} ({spec.label}: {spec.description})" for kind, spec in PACKAGES.items() if Transmission.CURSE in spec.transmissions
        ),
        "star_types": ", ".join(f"{kind} ({spec.label})" for kind, spec in STAR_TYPES.items()),
        "galaxy_types": ", ".join(f"{kind} ({spec.label})" for kind, spec in GALAXY_TYPES.items()),
        "cluster_kinds": ", ".join(f"{kind} ({spec.label})" for kind, spec in CLUSTER_KINDS.items()),
        "dimension_kinds": ", ".join(f"{kind} ({spec.label})" for kind, spec in DIMENSION_KINDS.items()),
        "vessel_kinds": [kind.value for kind in VehicleKind],
        "legend_categories": [category.value for category in LegendCategory],
        "commodities": [commodity.value for commodity in CommodityKind],
        "materials": [material.value for material in MaterialKind],
        "material_families": [family.value for family in MaterialFamily],
        "structure_kinds": ", ".join(f"{kind} ({spec.label})" for kind, spec in STRUCTURES.items()),
        "art_media": ", ".join(medium.value for medium in ArtMode),
        "magic_schools": ", ".join(school.value for school in MagicSchool),
        "magic_sources": ", ".join(source.value for source in MagicSource),
        "rite_effects": ", ".join(effect.value for effect in RiteEffectKind),
        "spell_techniques": ", ".join(item.value for item in SpellTechnique),
        "spell_forms": ", ".join(item.value for item in SpellForm),
        "dimension_elements": ", ".join(item.value for item in DimensionElement),
        "closure_kinds": ", ".join(item.value for item in sorted(CLOSURES)),
        "spell_ranges": ", ".join(item.value for item in SpellRange),
        "spell_durations": ", ".join(item.value for item in SpellDuration),
        "spell_targets": ", ".join(item.value for item in SpellTarget),
        "foundable_factions": ", ".join(kind.value for kind, body in BUILT_IN_ORGANISATIONS.items() if body.foundable),
        "faction_kinds": ", ".join(item.value for item in FactionKind),
        "servitor_roles": ", ".join(item.value for item in ServitorRole),
        "geas_modes": ", ".join(item.value for item in GeasMode),
        "geas_acts": "; ".join(f"{mode.value}: {', '.join(act.value for act in acts)}" for mode, acts in GEAS_ACTS.items()),
        "cosmic_offices": ", ".join(item.value for item in CosmicOffice),
        "sound_change_kinds": ", ".join(item.value for item in SoundChangeKind),
        "sound_environments": ", ".join(item.value for item in SoundEnvironment),
        "language_policies": ", ".join(item.value for item in LanguagePolicy),
        "plague_responses": ", ".join(item.value for item in PlagueResponse),
        "collective_triggers": ", ".join(item.value for item in CollectiveTrigger),
        "storylet_ids": ", ".join(item.value for item in StoryletId),
        "long_plan_kinds": ", ".join(item.value for item in LongPlanKind),
        "kinship_descents": ", ".join(item.value for item in KinshipDescent),
        "kin_term_systems": ", ".join(item.value for item in KinTermSystem),
        "adoption_kinds": ", ".join(item.value for item in AdoptionKind),
        "first_sides": ", ".join(item.value for item in Sex),
        "union_forms": ", ".join(item.value for item in UnionForm),
        "union_purposes": ", ".join(item.value for item in UnionPurpose),
        "union_residences": ", ".join(item.value for item in UnionResidence),
        "union_descents": ", ".join(item.value for item in UnionDescent),
        "union_exchanges": ", ".join(item.value for item in UnionExchange),
        "union_arrangements": ", ".join(item.value for item in UnionArrangement),
        "union_dissolutions": ", ".join(item.value for item in UnionDissolution),
        "partner_scopes": ", ".join(item.value for item in PartnerScope),
        "kin_matches": ", ".join(item.value for item in KinMatch),
        "plural_sides": ", ".join(item.value for item in PluralSide),
        "residence_rules": ", ".join(item.value for item in ResidenceRule),
        "reproductive_systems": ", ".join(item.value for item in ReproductiveSystem),
        "challenge_kinds": ", ".join(item.value for item in ChallengeKind),
        "manumission_paths": ", ".join(item.value for item in ManumissionPath),
        "selectorates": ", ".join(item.value for item in SelectorateKind),
        "perennial_kinds": ", ".join(item.value for item in PerennialKind),
        "aid_kinds": ", ".join(item.value for item in AidKind),
        "preparedness_kinds": ", ".join(item.value for item in PreparednessKind),
        "keystone_uses": ", ".join(item.value for item in KeystoneUse),
        "quirk_kinds": ", ".join(item.value for item in QuirkKind),
        "echelon_orders": ", ".join(item.value for item in EchelonOrder),
        "bureau_ranks": ", ".join(item.value for item in BureauRank),
        "sacrament_kinds": ", ".join(item.value for item in SacramentKind),
        "sacrament_protections": ", ".join(item.value for item in SacramentProtection),
        "omen_verdicts": ", ".join(item.value for item in OmenVerdict),
        "divination_questions": ", ".join(item.value for item in DivinationQuestion),
        "petition_kinds": ", ".join(item.value for item in PetitionKind),
        "emotions": ", ".join(item.value for item in Emotion),
        "order_kinds": ", ".join(item.value for item in OrderKind),
        "club_kinds": ", ".join(item.value for item in ClubKind),
        "design_kinds": ", ".join(item.value for item in DesignKind),
        "design_components": ", ".join(item.value for item in DesignComponentKind),
        "vehicle_frames": ", ".join(f"{kind} ({spec.label})" for kind, spec in FRAMES.items()),
        "mount_kinds": ", ".join(item.value for item in MountKind),
        "unit_roles": ", ".join(f"{kind} ({spec.label})" for kind, spec in UNITS.items()),
        "equipment_families": ", ".join(f"{kind} ({spec.label})" for kind, spec in FAMILIES.items()),
        "foods": ", ".join(food.value for food in DISH_FOODS),
        "cooking_methods": ", ".join(item.value for item in CookingMethod),
        "dish_courses": ", ".join(item.value for item in DishCourse),
        "building_forms": ", ".join(item.value for item in BuildingForm),
        "martial_styles": ", ".join(item.value for item in MartialStyle),
        "house_traits": ", ".join(item.value for item in HouseTrait),
        "formations": ", ".join(item.value for item in Formation),
        "law_kinds": ", ".join(item.value for item in LawKind),
        "armour_types": ", ".join(item.value for item in ArmourType),
        "shield_types": ", ".join(item.value for item in ShieldType),
        "registry_kinds": ", ".join(item.value for item in RegistryKind if item is not RegistryKind.LAND_TITLE),
        "ideology_tenets": ", ".join(tenet.value for tenet in IdeologyTenet),
        "prophecy_predicates": ", ".join(item.value for item in ProphecyPredicate),
        "prophecy_consequences": ", ".join(item.value for item in ProphecyConsequence),
        "size_classes": [size.value for size in SizeClass],
        "diets": [diet.value for diet in Diet],
        "socialities": [kind.value for kind in Sociality],
        "yield_products": [product.value for product in YieldProduct],
        "identity_layers": [layer.value for layer in IdentityLayer],
        "beast_tempers": [temper.value for temper in BeastTemper],
        "species_classes": [kind.value for kind in SpeciesClass],
        "biochemistries": [kind.value for kind in Biochemistry],
        "growth_cycles": [kind.value for kind in GrowthCycle],
        "plant_yields": [kind.value for kind in PlantYield],
        "dormancies": [kind.value for kind in Dormancy],
        "thermoregulations": [kind.value for kind in Thermoregulation],
        "plant_defences": [kind.value for kind in PlantDefence],
        "attack_deliveries": [kind.value for kind in AttackDelivery],
        "attack_effects": [kind.value for kind in AttackEffect],
        "attack_ranges": [kind.value for kind in AttackRange],
        "temperaments": [kind.value for kind in Temperament],
        "habitats": [kind.value for kind in Habitat],
        "awakening_triggers": [kind.value for kind in AwakeningTrigger],
        "tissue_materials": [kind.value for kind in TissueMaterial],
        "tenets": "; ".join(f"{tenet} ({effect})" for tenet, effect in TENET_EFFECTS.items()),
        "funeral_rites": [rite.value for rite in FuneralCustom],
        "remains_treatments": [treatment.value for treatment in RemainsTreatment],
        "practices": [practice.value for practice in FacetKind],
        "mortal_media": sorted(medium.value for medium in MORTAL_MEDIA),
        "season_domains": SEASON_DOMAIN_WORDS,
        "cure_classes": [cure.value for cure in CureClass],
        "observation_methods": [method.value for method in ObservationMethod],
        "weather_aims": [aim.value for aim in WeatherAim],
        "weather_work_methods": [method.value for method in WeatherWorkMethod],
        "land_domains": LAND_DOMAIN_WORDS,
        "tainting_domains": TAINTING_WORDS,
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
