from enum import StrEnum

import pytest

from aerona.catalog.entity_types import engine_kind_owner
from aerona.domain.enums.agent import CouncilVote, MessageIntent, PrayerRequest
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.chronicle import ChronicleKind, NotificationCategory, PartOfSpeech, ThreadStatus, WritingSystem
from aerona.domain.enums.creator import CreatorMoodAxis, CreatorPassion
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType, MortalRole, ProphecyReading
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.meta import AchievementKey, ScenarioKey, ScenarioStatus, ScoreComponent
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import Commodity, CreatureTrait, KnowledgeBranch, NaturalLaw, ResourceMechanic, SocialClass
from aerona.domain.enums.son import ExistenceMode, Passion, PowerEffect, ReputationLabel, SonStatus, Stat
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus, TravelMethod
from aerona.domain.enums.war import WarEnding
from aerona.domain.enums.world import Atmosphere, ClimateEra, Discovery, FateMode, Gravity, StarType, WorldType
from aerona.migration.legacy.stats import STAT_MODELS
from aerona.migration.legacy.vocabulary import Vocabulary
from aerona.rules.registry import Rules
from aerona.rules.snapshot import catalog

ENUMS: dict[str, type[StrEnum]] = {
    "entity_type": EntityType,
    "entity_status": EntityStatus,
    "entity_origin": EntityOrigin,
    "son_status": SonStatus,
    "rarity": Rarity,
    "domain": Domain,
    "son_stat": Stat,
    "passion": Passion,
    "existence_mode": ExistenceMode,
    "power_effect": PowerEffect,
    "foreign_god_power": ForeignGodPowerEffect,
    "foreign_god_status": ForeignGodStatus,
    "reputation_label": ReputationLabel,
    "creator_passion": CreatorPassion,
    "creator_mood_axis": CreatorMoodAxis,
    "fate_mode": FateMode,
    "bond_kind": BondKind,
    "chronicle_kind": ChronicleKind,
    "message_intent": MessageIntent,
    "prayer_request": PrayerRequest,
    "part_of_speech": PartOfSpeech,
    "actor_kind": ActorKind,
    "thread_status": ThreadStatus,
    "world_type": WorldType,
    "gravity": Gravity,
    "atmosphere": Atmosphere,
    "discovery": Discovery,
    "climate_era": ClimateEra,
    "star_type": StarType,
    "travel_method": TravelMethod,
    "journey_intent": JourneyIntent,
    "journey_status": JourneyStatus,
    "scenario_key": ScenarioKey,
    "scenario_status": ScenarioStatus,
    "achievement_key": AchievementKey,
    "score_component": ScoreComponent,
    "notification_category": NotificationCategory,
    "council_vote": CouncilVote,
    "social_class": SocialClass,
    "commodity": Commodity,
    "knowledge_branch": KnowledgeBranch,
    "creature_trait": CreatureTrait,
    "resource_mechanic": ResourceMechanic,
    "natural_law": NaturalLaw,
    "writing_system": WritingSystem,
    "prophecy_reading": ProphecyReading,
    "war_ending": WarEnding,
}
COMPLETE = (
    "entity_type",
    "entity_status",
    "entity_origin",
    "son_status",
    "rarity",
    "domain",
    "son_stat",
    "passion",
    "bond_kind",
    "chronicle_kind",
    "power_effect",
)


@pytest.mark.parametrize("name", sorted(ENUMS))
def test_every_mapped_value_is_a_member(vocabulary: Vocabulary, name: str) -> None:
    for english in vocabulary.enums[name].values():
        ENUMS[name](english)


@pytest.mark.parametrize("name", COMPLETE)
def test_core_enums_are_complete(vocabulary: Vocabulary, name: str) -> None:
    assert set(vocabulary.enums[name].values()) == {member.value for member in ENUMS[name]}


def test_flags_roles_and_engine_kinds_are_valid(vocabulary: Vocabulary) -> None:
    for english in vocabulary.tags.flags.values():
        EntityFlag(english)
    for english in [*vocabulary.mortal_roles.subtypes.values(), *vocabulary.mortal_roles.tags.values()]:
        MortalRole(english)
    for entity_type, table in vocabulary.engine_kinds.items():
        for english in table.values():
            assert engine_kind_owner(EngineKind(english)) is EntityType(entity_type)
    for table in vocabulary.bond_roles.values():
        for english in table.values():
            BondRole(english)
    assert set(vocabulary.bond_roles) <= {kind.value for kind in BondKind}


def test_entity_stats_name_real_fields(vocabulary: Vocabulary) -> None:
    assert set(vocabulary.entity_stats) == {entity_type.value for entity_type in EntityType}
    for entity_type, table in vocabulary.entity_stats.items():
        for english in table.values():
            assert english in STAT_MODELS[entity_type].model_fields


def test_rule_targets_exist_in_the_registry(vocabulary: Vocabulary) -> None:
    paths = {descriptor.path for descriptor in catalog(Rules())}
    targets = {target for target in vocabulary.rules.values() if target is not None}
    assert targets <= paths
    assert set(vocabulary.rules_unmapped) == {key for key, target in vocabulary.rules.items() if target is None}


def test_every_table_has_unique_physical_columns(vocabulary: Vocabulary) -> None:
    for table in vocabulary.tables.values():
        assert len(set(table.columns.values())) == len(table.columns)
        assert set(table.required) <= set(table.columns)
