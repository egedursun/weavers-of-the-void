from dataclasses import replace

from aerona.catalog.bonds import BOND_KINDS, EVENT_BOND_KINDS, WEAVABLE_BOND_KINDS, endpoints_valid, should_swap
from aerona.catalog.chronicle import CHRONICLE_KINDS, NOTIFICATION_CATEGORIES, chronicle_notification
from aerona.catalog.climate import CLIMATES, climate_weight, climate_weights
from aerona.catalog.creatures import CREATURE_TRAITS, trait_war_bonus
from aerona.catalog.entity_types import CREATION_BASE_COST_RULES, ENTITY_TYPES, build_creation_cost_table, engine_kind_owner
from aerona.catalog.gates import GATE_RULES, Gate, creation_gate_rarity, gate_rarity, may_create, passes_gate
from aerona.catalog.interventions import DISASTERS, MIRACLES
from aerona.catalog.knowledge import KNOWLEDGE_BRANCHES, NATURAL_LAWS, RESOURCE_MECHANICS
from aerona.catalog.powers import POWERS, power_description, unlocked_power_slots
from aerona.catalog.rarities import build_rarity_table, entity_rarity, name_similarity_policy
from aerona.catalog.society import community_relation_label, son_relation_label
from aerona.catalog.stats import STATS, existence_band, max_essence, max_hp
from aerona.catalog.travel import TRAVEL_METHODS, travel_method_table
from aerona.catalog.worlds import WORLD_TYPES
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory, NotificationCategory
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.intervention import Disaster, Miracle
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import CommunityRelationLabel, CreatureTrait, KnowledgeBranch, NaturalLaw, ResourceMechanic
from aerona.domain.enums.son import ExistenceBand, PowerEffect, SonRelationLabel, Stat
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import ClimateEra, WorldType
from aerona.rules.registry import Rules
from aerona.rules.snapshot import apply_overrides

RULES = Rules()


def test_every_enum_member_has_catalog_content() -> None:
    assert set(ENTITY_TYPES) == set(EntityType)
    assert set(CREATION_BASE_COST_RULES) == set(EntityType)
    assert set(BOND_KINDS) == set(BondKind)
    assert set(CHRONICLE_KINDS) == set(ChronicleKind)
    assert set(NOTIFICATION_CATEGORIES) == set(NotificationCategory)
    assert set(POWERS) == set(PowerEffect)
    assert set(STATS) == set(Stat)
    assert set(KNOWLEDGE_BRANCHES) == set(KnowledgeBranch)
    assert set(NATURAL_LAWS) == set(NaturalLaw)
    assert set(RESOURCE_MECHANICS) == set(ResourceMechanic)
    assert set(CREATURE_TRAITS) == set(CreatureTrait)
    assert set(TRAVEL_METHODS) == set(TravelMethod)
    assert set(CLIMATES) == set(ClimateEra)
    assert set(DISASTERS) == set(Disaster)
    assert set(MIRACLES) == set(Miracle)
    assert set(WORLD_TYPES) == set(WorldType)
    assert set(GATE_RULES) == set(Gate)


def test_designed_world_types_are_all_present() -> None:
    designed = {
        "ringed",
        "asteroid_belt",
        "tidally_locked",
        "void_pocket",
        "gods_palace",
        "generation_ship",
        "corpse_world",
        "super_earth",
        "ice_giant",
        "hot_giant",
        "iron",
        "carbon",
        "greenhouse",
        "dwarf_planet",
        "chthonian",
        "hycean",
        "jungle",
        "forge",
        "fungal",
        "shattered",
        "hollow",
        "ice_shell",
        "methane",
    }
    assert designed <= {world_type.value for world_type in WorldType}
    assert len(WorldType) == 37


def test_every_engine_kind_belongs_to_exactly_one_type() -> None:
    for kind in EngineKind:
        owners = [spec.type for spec in ENTITY_TYPES.values() if kind in spec.engine_kinds]
        assert len(owners) == 1, kind
        assert engine_kind_owner(kind) is owners[0]


def test_rarity_table_reads_the_rules() -> None:
    table = build_rarity_table(RULES)
    assert table[Rarity.COMMON].action_points == RULES.rarities.common_action_points
    assert not table[Rarity.MYTHIC].summonable
    assert table[Rarity.COMMON].summonable
    tuned = apply_overrides(RULES, {("rarities", "epic_power_cap"): 9})
    assert build_rarity_table(tuned)[Rarity.EPIC].power_cap == 9


def test_rarity_helpers() -> None:
    assert Rarity.EPIC.at_least(Rarity.RARE)
    assert not Rarity.COMMON.at_least(Rarity.UNCOMMON)
    assert Rarity.LEGENDARY.next() is Rarity.MYTHIC
    assert Rarity.MYTHIC.next() is None
    assert Rarity.from_rank(99) is Rarity.MYTHIC
    assert entity_rarity(RULES, 1) is Rarity.COMMON
    assert entity_rarity(RULES, RULES.core_rules.tier_mythic) is Rarity.MYTHIC


def test_gates_follow_rules() -> None:
    assert creation_gate_rarity(RULES, EntityType.NATURAL_LAW) is Rarity.LEGENDARY
    assert may_create(RULES, Rarity.COMMON, EntityType.PLACE)
    assert not may_create(RULES, Rarity.COMMON, EntityType.REGION)
    assert gate_rarity(RULES, Gate.HANG_EXTINGUISH_STAR) is Rarity.MYTHIC
    lowered = apply_overrides(RULES, {("rarity_gates", "seal_gate"): 0})
    assert passes_gate(lowered, Rarity.COMMON, Gate.SEAL_GATE)


def test_creation_costs_come_from_rules() -> None:
    table = build_creation_cost_table(RULES)
    base = RULES.creation_base_cost.people + RULES.core_rules.cost_per_power_level * 2
    expected = round(base * RULES.core_rules.cost_in_domain_pct / 100)
    assert table.cost(EntityType.PEOPLE, 2, in_domain=True, creativity=0) == expected
    assert table.cost(EntityType.PEOPLE, 2, in_domain=False, creativity=0) > expected
    assert table.cost(EntityType.PEOPLE, 2, in_domain=True, creativity=100) < expected
    assert table.cost(EntityType.PEOPLE, 2, in_domain=True, creativity=0, cheap_power=True) < expected
    assert table.entries[EntityType.REGION].minimum_rarity is Rarity.EPIC


def test_power_descriptions_render_live_numbers() -> None:
    for effect in PowerEffect:
        assert power_description(RULES, effect)
    tuned = replace(RULES, son_tools=replace(RULES.son_tools, challenge_power_bonus=33))
    assert "+33" in power_description(tuned, PowerEffect.DUEL_MASTER)
    assert unlocked_power_slots(RULES, 1) == (0,)
    assert unlocked_power_slots(RULES, 99) == (0, 1, 2)


def test_bond_endpoint_and_direction_rules() -> None:
    assert should_swap(BondKind.SPEAKS, EntityType.LANGUAGE, EntityType.PEOPLE)
    assert not should_swap(BondKind.SPEAKS, EntityType.PEOPLE, EntityType.LANGUAGE)
    assert endpoints_valid(BondKind.KNOWS, EntityType.PEOPLE, EntityType.KNOWLEDGE)
    assert not endpoints_valid(BondKind.KNOWS, EntityType.PEOPLE, EntityType.LANGUAGE)
    assert BondKind.CAUSED in EVENT_BOND_KINDS
    assert BondKind.RELATED in WEAVABLE_BOND_KINDS
    assert BondKind.PARTY_TO not in WEAVABLE_BOND_KINDS


def test_chronicle_notification_mapping() -> None:
    assert chronicle_notification(ChronicleKind.REBELLION, None) is NotificationCategory.REBELLION
    assert chronicle_notification(ChronicleKind.WORLD, FeedCategory.LEAK) is NotificationCategory.HORROR
    assert chronicle_notification(ChronicleKind.WORLD, FeedCategory.LIFE) is None
    assert not CHRONICLE_KINDS[ChronicleKind.ENGINE_RAW].visible


def test_stat_formulas_and_bands() -> None:
    assert max_hp(RULES, 100) == round(RULES.core_rules.max_hp_base + RULES.core_rules.max_hp_per_endurance)
    assert max_essence(RULES, None) == max_essence(RULES, RULES.core_rules.default_might)
    assert existence_band(RULES, 100) is ExistenceBand.RADIANT
    assert existence_band(RULES, 0) is ExistenceBand.BEING_FORGOTTEN
    assert "Max HP" in STATS[Stat.ENDURANCE].describe(RULES)


def test_relation_labels() -> None:
    assert community_relation_label(RULES, -100) is CommunityRelationLabel.BLOOD_ENEMY
    assert community_relation_label(RULES, 0) is CommunityRelationLabel.NEUTRAL
    assert community_relation_label(RULES, 100) is CommunityRelationLabel.SIBLING
    assert son_relation_label(RULES, 100) is SonRelationLabel.DEVOTION
    assert son_relation_label(RULES, -100) is SonRelationLabel.HATRED
    assert son_relation_label(RULES, 0) is SonRelationLabel.DISTANCE


def test_travel_climate_and_traits_read_rules() -> None:
    table = travel_method_table(RULES)
    assert table[TravelMethod.LIGHT_SAIL].duration_epochs == RULES.travel_methods.light_sail_duration
    assert climate_weight(RULES, WorldType.OCEAN, ClimateEra.RAIN) == RULES.climate_world_type.ocean_rain / 100 * RULES.climate_effects.rain_age_weight
    assert climate_weights(RULES, WorldType.CRYSTAL)[ClimateEra.TEMPERATE] == RULES.climate_effects.temperate_weight
    assert trait_war_bonus(RULES, CreatureTrait.STONESKIN) == RULES.creature_traits.stoneskin_war_bonus


def test_name_policy_reads_rules() -> None:
    policy = name_similarity_policy(RULES)
    assert policy.root_letters == RULES.language.root_letters
