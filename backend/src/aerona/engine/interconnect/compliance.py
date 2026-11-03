from dataclasses import dataclass

from aerona.db.tables.body import ConditionRow, InjuryRow
from aerona.db.tables.environment import ForcedWeatherRow, LeyLineRow, NotableYearRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.db.tables.mind import CultureValueRow, MemoryRow, NeedRow, PersonalityValueRow, PressureRow, SkillRow


@dataclass(frozen=True)
class ComplianceRow:
    section: str
    tables: tuple[str, ...]
    phases: tuple[str, ...]
    levers: tuple[str, ...]
    surfaces: tuple[str, ...]
    contexts: tuple[str, ...]
    tools: tuple[str, ...]
    templates: tuple[str, ...]
    backfill: tuple[str, ...]


CATALOGUE: tuple[ComplianceRow, ...] = (
    ComplianceRow(
        "F1",
        (NotableYearRow.__tablename__,),
        ("harvest", "environment_survey"),
        ("year:force_notable",),
        ("YearStrip", "NotableYears"),
        ("world_header",),
        (),
        ("year.",),
        ("environment.notable_years_backfill",),
    ),
    ComplianceRow(
        "F2",
        (RegionEnvironmentRow.__tablename__, WorldSeasonRow.__tablename__, LeyLineRow.__tablename__, ForcedWeatherRow.__tablename__),
        ("environment_survey", "environment_derive", "ley_lines", "land_use"),
        ("environment:set", "seasons:edit", "weather:force", "weather:release", "ley:sever", "ley:forge", "ley:unforge"),
        ("map-layer-terrain", "map-layer-soil", "map-layer-climate", "map-layer-land-use", "map-layer-ley", "WorldSeasonsSection"),
        ("geography_lines", "mortal_context"),
        ("shape_weather", "reorder_seasons", "sever_ley"),
        ("land.", "season.", "tools.son.shape_weather"),
        ("environment_survey",),
    ),
    ComplianceRow(
        "F4",
        (InjuryRow.__tablename__, ConditionRow.__tablename__),
        ("body_healing", "body_conditions", "war_casualties"),
        ("body:heal", "body:maim", "body:prosthesis", "body:frame"),
        ("AnatomyFigure", "BodySection"),
        ("entity_detail",),
        (),
        ("injury.", "healing."),
        ("body.species_plans", "body_survey"),
    ),
    ComplianceRow(
        "F5",
        (CultureValueRow.__tablename__, PersonalityValueRow.__tablename__),
        ("mind_values",),
        ("mind:values", "mind:lock"),
        ("ValueRadar",),
        ("entity_detail",),
        (),
        ("culture.",),
        ("mind.depth_personality", "mind_survey"),
    ),
    ComplianceRow(
        "F6",
        (SkillRow.__tablename__,),
        ("mind_skills",),
        ("mind:skill", "mind:skill_remove"),
        ("SkillsSection",),
        ("entity_detail",),
        (),
        ("skill.",),
        ("mind_survey",),
    ),
    ComplianceRow(
        "F7",
        (MemoryRow.__tablename__,),
        ("mind_memories", "mind_opinion"),
        ("mind:memory", "mind:memory_edit", "mind:memory_remove"),
        ("MemoriesSection", "OpinionBreakdown"),
        ("entity_detail",),
        (),
        ("memory.",),
        ("mind.relation_history",),
    ),
    ComplianceRow(
        "F8",
        (NeedRow.__tablename__, PressureRow.__tablename__),
        ("mind_needs", "famine_aid"),
        ("mind:need", "mind:pressure", "mind:lock"),
        ("MindSection",),
        ("entity_detail",),
        (),
        ("need.",),
        ("mind_needs",),
    ),
    ComplianceRow(
        "F9",
        (ModifierRow.__tablename__,),
        ("modifier_upkeep",),
        ("modifier:add", "modifier:remove", "lever:pin"),
        ("EntityMechanics", "WhyBreakdown"),
        ("entity_detail",),
        (),
        (),
        ("derive_modifiers",),
    ),
    ComplianceRow(
        "F10",
        (IncidentRow.__tablename__, IncidentParticipantRow.__tablename__),
        ("modifier_upkeep",),
        ("incident:annotate",),
        ("BiographySection", "CausalChain"),
        ("entity_detail",),
        (),
        (),
        ("26caa21842b3",),
    ),
)
