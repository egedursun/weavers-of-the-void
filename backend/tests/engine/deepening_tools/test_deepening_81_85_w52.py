from aerona.catalog.discovery import AGES, BLUEPRINT_KINDS, BLUEPRINT_SOURCES, DEEDS, INCIDENTS
from aerona.catalog.eras import ERA_FLOORS
from aerona.catalog.techniques import BRANCH_GRAPH, TECHNIQUES
from aerona.catalog.technology import ERA_LEVEL, FAMILY_BRANCHES, FAMILY_TECHNIQUES
from aerona.catalog.theories import ANOMALIES, ANOMALY_DOMAINS, DOMAINS
from aerona.db.tables.discovery import PolityEraRow
from aerona.domain.enums.ages import ArcRole, SetupKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.discovery import AgeKind, AnomalyKind, BlueprintKind, BlueprintSource, EraDeed, ResearchIncident, TheoryDomain
from aerona.domain.enums.eras import EraChannel, ProgrammeStage, TechFamily
from aerona.domain.enums.site import RoomContentKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.eras.effects import channel_value
from aerona.engine.lore.eras import next_age
from aerona.rules.registry import Rules

RULES = Rules()


def test_the_widths_of_batches_81_to_85() -> None:
    assert (len(KnowledgeBranch), len(Technique), len(TechFamily)) == (23, 107, 14)
    assert (len(AgeKind), len(EraDeed), len(ResearchIncident), len(BlueprintKind), len(BlueprintSource)) == (10, 15, 10, 11, 6)
    assert (len(TheoryDomain), len(AnomalyKind), len(TechnologyEra), len(EraChannel), len(ProgrammeStage)) == (10, 6, 13, 19, 6)
    assert (len(StorytellerProfile), len(ArcRole), len(SetupKind), len(RoomContentKind)) == (8, 9, 7, 8)


def test_every_new_value_has_its_catalogue_row() -> None:
    assert set(TECHNIQUES) == set(Technique) and set(BRANCH_GRAPH) == set(KnowledgeBranch)
    assert set(FAMILY_BRANCHES) == set(TechFamily) and set(FAMILY_TECHNIQUES) == set(TechFamily) and set(ERA_LEVEL) == set(TechnologyEra)
    assert set(AGES) == set(AgeKind) and set(DEEDS) == set(EraDeed) and set(INCIDENTS) == set(ResearchIncident)
    assert set(BLUEPRINT_KINDS) == set(BlueprintKind) and set(BLUEPRINT_SOURCES) == set(BlueprintSource)
    assert set(DOMAINS) == set(TheoryDomain) and set(ANOMALIES) == set(AnomalyKind) == set(ANOMALY_DOMAINS)
    assert TechnologyEra.COPPER in ERA_FLOORS
    assert list(TechnologyEra).index(TechnologyEra.STONE) < list(TechnologyEra).index(TechnologyEra.COPPER) < list(TechnologyEra).index(TechnologyEra.BRONZE)


def test_learning_and_health_channels_carry_era_techniques() -> None:
    assert channel_value(RULES, {Technique.SANITATION}, EraChannel.HEALTH) == RULES.eras.sanitation_health_pct
    assert channel_value(RULES, {Technique.POSITIONAL_RECKONING}, EraChannel.LEARNING) == RULES.eras.reckoning_learning_pct


def test_a_dark_age_ends_reborn_after_recovery_and_migrations_bring_wandering() -> None:
    table = RULES.discovery
    dark = PolityEraRow(polity_entity_id=1, score=table.dark_at + table.heroic_rise + 1, age=AgeKind.DARK, since_epoch=1, lowest=table.dark_at, locked=[])
    assert next_age(dark, RULES, frozenset({EraDeed.FIRST_TECHNIQUE})) is AgeKind.REBORN
    assert next_age(dark, RULES) is AgeKind.HEROIC
    calm = PolityEraRow(polity_entity_id=1, score=table.dark_at + 1, age=AgeKind.NORMAL, since_epoch=1, lowest=0, locked=[])
    assert next_age(calm, RULES, frozenset({EraDeed.GREAT_MIGRATION})) is AgeKind.WANDERING
