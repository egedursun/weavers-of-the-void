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
from aerona.catalog.impacts import IMPACT_BODIES
from aerona.catalog.interventions import DISASTERS, MIRACLES
from aerona.catalog.law_exceptions import LAW_EXCEPTIONS
from aerona.catalog.mythic import GEAS_ACTS
from aerona.catalog.outer_bargains import BARGAIN_GAINS, BARGAIN_PRICES
from aerona.catalog.reproduction import TWO_KINDS
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
from aerona.domain.enums.agrarian import AidKind, CommonsRule, KeystoneUse, NutrientKind, PerennialKind, PreparednessKind
from aerona.domain.enums.arcana import RiteCondition, SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.domain.enums.arts import ClubKind, ForgeryKind
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.climes import CirculationBand
from aerona.domain.enums.collective import CollectiveActKind, CollectiveTrigger, CrowdFeeling, DesignComponentKind, DesignKind, StoryletId
from aerona.domain.enums.constructs import CommandToken, OrderCondition, OrderKind, OrderTime
from aerona.domain.enums.cosmography import DimensionElement
from aerona.domain.enums.couplings import SealKind
from aerona.domain.enums.crafts import CatchGround, Gear, RightKind
from aerona.domain.enums.creature_groups import DriveMeans, GroupAim
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.culture import ArtMode, IdeologyTenet, MagicSchool, MagicSource, ProphecyConsequence, ProphecyPredicate, RiteEffectKind
from aerona.domain.enums.customs import CoopPurpose, EvidenceKind, MarkKind, MarkMeaning, MemberRight, Membership, RevivalGoal, RevivalWay
from aerona.domain.enums.cycles import (
    AdoptionKind,
    ChallengeKind,
    GiftOccasion,
    KinshipDescent,
    KinTermSystem,
    LongPlanKind,
    ManumissionPath,
    ReproductiveSystem,
    ResidenceRule,
)
from aerona.domain.enums.death_work import RemainsTreatment
from aerona.domain.enums.demography import FuneralCustom, MartialStyle
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.disease_agents import CureClass
from aerona.domain.enums.divine_conceptions import ConceptionAxis, CreatorPlace, DivineCount, DivineNearness, DivinePersonhood
from aerona.domain.enums.dominion import WorshipMode
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
from aerona.domain.enums.environment import CleansingMethod, MovementMode, ScarKind, SoilKind
from aerona.domain.enums.evolution import PlagueResponse, PlanetaryCycle, SuccessionStage
from aerona.domain.enums.facets import FacetKind
from aerona.domain.enums.faction import EstatePrivilege, FactionGoalKind, FactionKind
from aerona.domain.enums.faith import JudgementDoctrine, RebirthPath
from aerona.domain.enums.folkways import CharmPower, ImpuritySource, MishapKind
from aerona.domain.enums.forecasting import ObservationMethod, WeatherAim, WeatherWorkMethod
from aerona.domain.enums.fossil import FossilReading
from aerona.domain.enums.geology import RockKind, UndergroundStratum
from aerona.domain.enums.honours import HonourPrivilege, VeteranGrant
from aerona.domain.enums.intrigue import PlotKind
from aerona.domain.enums.law_depth import RecruitMotive, RegistryKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import (
    ArmourType,
    ArmyRole,
    CaptiveFate,
    DefenderAction,
    DuelContext,
    DuelEnd,
    Formation,
    SackChoice,
    ShieldType,
    SiegeWork,
    SpyOperation,
    Stance,
)
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.mythic import CosmicOffice, GeasMode, QuestTrial, ServitorOrigin, ServitorRole
from aerona.domain.enums.nature import Dormancy, PlantDefence, Thermoregulation
from aerona.domain.enums.operations import EchelonOrder, ExpeditionGround, ExpeditionRole, QuirkKind
from aerona.domain.enums.place import PlaceKind, SecretKind
from aerona.domain.enums.polity import CLOSURES, ClaimBasis, HouseTrait, LawKind, OathKind
from aerona.domain.enums.regime import ClientRole, SelectorateKind
from aerona.domain.enums.region import DangerHarm, DangerSource, RegionMemoryKind, TerrainHazard
from aerona.domain.enums.sacred import (
    BureauRank,
    DivinationKind,
    DivinationQuestion,
    GeniusLocusKind,
    OmenVerdict,
    PetitionKind,
    SacramentKind,
    SacramentProtection,
    VisionKind,
)
from aerona.domain.enums.statecraft import CouncilTask, CourtPosition, CrisisDemand, MandateKind
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
from aerona.domain.enums.world_view import SettleMode
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
        "impact_bodies": ", ".join(f"{body} ({spec.label})" for body, spec in IMPACT_BODIES.items()),
        "bargain_gains": ", ".join(f"{gain} ({spec.label})" for gain, spec in BARGAIN_GAINS.items()),
        "bargain_prices": ", ".join(f"{price} ({spec.label})" for price, spec in BARGAIN_PRICES.items()),
        "law_exceptions": ", ".join(f"{kind} ({spec.label})" for kind, spec in LAW_EXCEPTIONS.items()),
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
        "servitor_origins": ", ".join(item.value for item in ServitorOrigin),
        "geas_modes": ", ".join(item.value for item in GeasMode),
        "geas_acts": "; ".join(f"{mode.value}: {', '.join(act.value for act in acts)}" for mode, acts in GEAS_ACTS.items()),
        "cosmic_offices": ", ".join(item.value for item in CosmicOffice),
        "sound_change_kinds": ", ".join(item.value for item in SoundChangeKind),
        "sound_environments": ", ".join(item.value for item in SoundEnvironment),
        "language_policies": ", ".join(item.value for item in LanguagePolicy),
        "plague_responses": ", ".join(item.value for item in PlagueResponse),
        "collective_triggers": ", ".join(item.value for item in CollectiveTrigger),
        "collective_acts": ", ".join(item.value for item in CollectiveActKind),
        "crowd_feelings": ", ".join(item.value for item in CrowdFeeling),
        "revival_ways": ", ".join(item.value for item in RevivalWay),
        "mark_kinds": ", ".join(item.value for item in MarkKind),
        "mark_meanings": ", ".join(item.value for item in MarkMeaning),
        "salience_drivers": ", ".join(item.value for item in SalienceDriver),
        "revival_goals": ", ".join(item.value for item in RevivalGoal),
        "storylet_ids": ", ".join(item.value for item in StoryletId),
        "long_plan_kinds": ", ".join(item.value for item in LongPlanKind),
        "kinship_descents": ", ".join(item.value for item in KinshipDescent),
        "kin_term_systems": ", ".join(item.value for item in KinTermSystem),
        "adoption_kinds": ", ".join(item.value for item in AdoptionKind),
        "first_sides": ", ".join(item.value for item in TWO_KINDS),
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
        "expedition_roles": ", ".join(item.value for item in ExpeditionRole),
        "expedition_grounds": ", ".join(item.value for item in ExpeditionGround),
        "impurity_sources": ", ".join(item.value for item in ImpuritySource),
        "mishap_kinds": ", ".join(item.value for item in MishapKind),
        "plot_kinds": ", ".join(item.value for item in PlotKind),
        "echelon_orders": ", ".join(item.value for item in EchelonOrder),
        "movement_modes": ", ".join(item.value for item in MovementMode),
        "soil_kinds": ", ".join(item.value for item in SoilKind),
        "council_tasks": ", ".join(item.value for item in CouncilTask),
        "mandate_kinds": ", ".join(item.value for item in MandateKind),
        "crisis_demands": ", ".join(item.value for item in CrisisDemand),
        "oath_kinds": ", ".join(item.value for item in OathKind),
        "estate_privileges": ", ".join(item.value for item in EstatePrivilege),
        "court_positions": ", ".join(item.value for item in CourtPosition),
        "client_roles": ", ".join(item.value for item in ClientRole),
        "member_rights": ", ".join(item.value for item in MemberRight),
        "memberships": ", ".join(item.value for item in Membership),
        "claim_bases": ", ".join(item.value for item in ClaimBasis),
        "coop_purposes": ", ".join(item.value for item in CoopPurpose),
        "evidence_kinds": ", ".join(item.value for item in EvidenceKind),
        "faction_goals": ", ".join(item.value for item in FactionGoalKind),
        "nutrient_kinds": ", ".join(item.value for item in NutrientKind),
        "duel_contexts": ", ".join(item.value for item in DuelContext),
        "duel_ends": ", ".join(item.value for item in DuelEnd),
        "army_stances": ", ".join(item.value for item in Stance),
        "settle_modes": ", ".join(item.value for item in SettleMode),
        "army_roles": ", ".join(item.value for item in ArmyRole),
        "captive_fates": ", ".join(item.value for item in CaptiveFate),
        "siege_works": ", ".join(item.value for item in SiegeWork),
        "defender_actions": ", ".join(item.value for item in DefenderAction),
        "fall_choices": ", ".join(item.value for item in SackChoice),
        "spy_operations": ", ".join(item.value for item in SpyOperation),
        "recruit_motives": ", ".join(item.value for item in RecruitMotive),
        "veteran_grants": ", ".join(item.value for item in VeteranGrant),
        "bureau_ranks": ", ".join(item.value for item in BureauRank),
        "sacrament_kinds": ", ".join(item.value for item in SacramentKind),
        "sacrament_protections": ", ".join(item.value for item in SacramentProtection),
        "omen_verdicts": ", ".join(item.value for item in OmenVerdict),
        "divination_questions": ", ".join(item.value for item in DivinationQuestion),
        "petition_kinds": ", ".join(item.value for item in PetitionKind),
        "spirit_kinds": ", ".join(item.value for item in GeniusLocusKind),
        "vision_kinds": ", ".join(item.value for item in VisionKind),
        "divination_kinds": ", ".join(item.value for item in DivinationKind),
        "charm_powers": ", ".join(item.value for item in CharmPower),
        "emotions": ", ".join(item.value for item in Emotion),
        "order_kinds": ", ".join(item.value for item in OrderKind),
        "order_conditions": ", ".join(item.value for item in OrderCondition),
        "order_times": ", ".join(item.value for item in OrderTime),
        "worship_modes": ", ".join(item.value for item in WorshipMode),
        "command_tokens": ", ".join(item.value for item in CommandToken),
        "quest_trials": ", ".join(item.value for item in QuestTrial),
        "rite_conditions": ", ".join(item.value for item in RiteCondition),
        "club_kinds": ", ".join(item.value for item in ClubKind),
        "forgery_kinds": ", ".join(item.value for item in ForgeryKind),
        "right_kinds": ", ".join(item.value for item in RightKind),
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
        "gift_occasions": [occasion.value for occasion in GiftOccasion],
        "honour_privileges": [privilege.value for privilege in HonourPrivilege],
        "observation_methods": [method.value for method in ObservationMethod],
        "scar_kinds": [kind.value for kind in ScarKind],
        "rock_kinds": [kind.value for kind in RockKind],
        "seal_kinds": [kind.value for kind in SealKind],
        "wind_bands": [kind.value for kind in CirculationBand],
        "commons_rules": [kind.value for kind in CommonsRule],
        "catch_grounds": [kind.value for kind in CatchGround],
        "catch_gear": [kind.value for kind in Gear],
        "planetary_cycles": [kind.value for kind in PlanetaryCycle],
        "fossil_readings": [kind.value for kind in FossilReading if kind is not FossilReading.UNREAD],
        "underground_strata": [kind.value for kind in UndergroundStratum],
        "region_memory_kinds": [kind.value for kind in RegionMemoryKind],
        "danger_sources": [kind.value for kind in DangerSource],
        "danger_targets": [kind.value for kind in DangerHarm],
        "terrain_hazards": [kind.value for kind in TerrainHazard],
        "succession_stages": [kind.value for kind in SuccessionStage],
        "cleansing_methods": [method.value for method in CleansingMethod],
        "group_aims": [aim.value for aim in GroupAim],
        "drive_means": [means.value for means in DriveMeans],
        "conception_axes": [axis.value for axis in ConceptionAxis],
        "divine_counts": [count.value for count in DivineCount],
        "divine_nearness": [nearness.value for nearness in DivineNearness],
        "divine_personhood": [personhood.value for personhood in DivinePersonhood],
        "creator_places": [place.value for place in CreatorPlace],
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
