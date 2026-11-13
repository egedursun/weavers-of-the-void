import re
from pathlib import Path

from aerona.db import tables
from aerona.db.base import Base
from aerona.db.tables.arcana import (
    GRAMMAR_FIELDS,
    LAB_TEXT_FIELDS,
    LONGEVITY_FIELDS,
    UPKEEP_FIELDS,
    WARPING_FIELDS,
    LabTextRow,
    LawUpkeepRow,
    LongevityRow,
    RiteGrammarRow,
    WarpingRow,
)
from aerona.db.tables.collective import (
    ACCOUNT_FIELDS,
    ARMS_FIELDS,
    BIAS_FIELDS,
    COMMEMORATION_FIELDS,
    COMPONENT_FIELDS,
    DATING_FIELDS,
    DESIGN_FIELDS,
    DIASPORA_FIELDS,
    GENERATION_FIELDS,
    LOST_LAND_FIELDS,
    MOB_FIELDS,
    MOOD_FIELDS,
    MOVEMENT_FIELDS,
    MYTH_FIELDS,
    NORM_FIELDS,
    ROLE_FIELDS,
    SEX_RATIO_FIELDS,
    STORYLET_FIELDS,
    STRIKE_FIELDS,
    TRANSITION_FIELDS,
    WEAR_FIELDS,
    AccountRow,
    ArmsRow,
    CommemorationRow,
    ComponentWearRow,
    CrowdMoodRow,
    DatingSystemRow,
    DemographicTransitionRow,
    DesignComponentRow,
    DesignRow,
    DiasporaRow,
    FoundingMythRow,
    GenerationRow,
    LearningBiasRow,
    LostLandRow,
    MemoryStrikeRow,
    MobRow,
    MovementRow,
    RoleNormRow,
    SexRatioRow,
    SocialNormRow,
    StoryletRunRow,
)
from aerona.db.tables.cuisine import DISH_FIELDS, CommunityDishRow, DishRow
from aerona.db.tables.equipment import MODEL_FIELDS, EquipmentModelRow
from aerona.db.tables.integrity import (
    DESIGN_SECTION_FIELDS,
    MEGASTRUCTURE_FIELDS,
    STRUCTURE_SECTION_FIELDS,
    MegastructureRow,
    StructureDesignSectionRow,
    StructureSectionRow,
)
from aerona.db.tables.military import UnitDesignRow
from aerona.db.tables.mythic import (
    GEAS_FIELDS,
    HEROQUEST_FIELDS,
    MANTLING_FIELDS,
    OFFICE_FIELDS,
    SERVITOR_FIELDS,
    CosmicOfficeRow,
    GeasRow,
    HeroquestRow,
    MantlingRow,
    ServitorRow,
)
from aerona.db.tables.structures import StructureDesignRow
from aerona.db.tables.tongues import (
    DECIPHER_FIELDS,
    DIVINE_TONGUE_FIELDS,
    POLICY_FIELDS,
    SCRIPT_FIELDS,
    SOUND_CHANGE_FIELDS,
    DecipherWorkRow,
    DivineTongueRow,
    LanguageGrammarRow,
    LanguagePolicyRow,
    ScriptRow,
    SoundChangeRow,
)
from aerona.db.tables.tongues import GRAMMAR_FIELDS as TONGUE_GRAMMAR_FIELDS
from aerona.db.tables.vehicles import (
    GROUP_FIELDS,
    GROUP_SECTION_FIELDS,
    MOUNT_FIELDS,
    SECTION_FIELDS,
    VESSEL_SECTION_FIELDS,
    DesignMountRow,
    DesignSectionRow,
    VehicleGroupRow,
    VehicleGroupSectionRow,
    VesselSectionRow,
)
from aerona.engine.cuisine.control import EDITABLE as CUISINE_EDITABLE
from aerona.engine.equipment.control import UNIT_TYPE_FIELDS
from aerona.engine.primitives.edits import FIXED
from aerona.engine.structures.control import DESIGN_CHOICES, DESIGN_NUMBERS

EDITORS: tuple[tuple[type[Base], tuple[str, ...], frozenset[str]], ...] = (
    (RiteGrammarRow, GRAMMAR_FIELDS, frozenset({"difficulty"})),
    (LabTextRow, LAB_TEXT_FIELDS, frozenset()),
    (WarpingRow, WARPING_FIELDS, frozenset()),
    (LongevityRow, LONGEVITY_FIELDS, frozenset()),
    (LawUpkeepRow, UPKEEP_FIELDS, frozenset()),
    (HeroquestRow, HEROQUEST_FIELDS, frozenset({"quester_entity_id", "collection_id"})),
    (MantlingRow, MANTLING_FIELDS, frozenset()),
    (ServitorRow, SERVITOR_FIELDS, frozenset()),
    (GeasRow, GEAS_FIELDS, frozenset({"bearer_entity_id"})),
    (CosmicOfficeRow, OFFICE_FIELDS, frozenset()),
    (SoundChangeRow, SOUND_CHANGE_FIELDS, frozenset({"language_entity_id"})),
    (LanguageGrammarRow, TONGUE_GRAMMAR_FIELDS, frozenset()),
    (ScriptRow, SCRIPT_FIELDS, frozenset()),
    (DecipherWorkRow, DECIPHER_FIELDS, frozenset()),
    (LanguagePolicyRow, POLICY_FIELDS, frozenset()),
    (DivineTongueRow, DIVINE_TONGUE_FIELDS, frozenset()),
)

STRUCTURE_DESIGN_FIELDS = (*DESIGN_NUMBERS, *DESIGN_CHOICES, "ley", "name", "description", "origin_node_id")
FRONT_EDITORS: tuple[tuple[type[Base], tuple[str, ...], frozenset[str], str], ...] = (
    (CrowdMoodRow, MOOD_FIELDS, frozenset(), "crowd_mood:edit"),
    (MobRow, MOB_FIELDS, frozenset({"settlement_entity_id", "district_id", "cascade_id", "ended_by"}), "mob:edit"),
    (MovementRow, MOVEMENT_FIELDS, frozenset({"settlement_entity_id"}), "popular_movement:edit"),
    (
        AccountRow,
        ACCOUNT_FIELDS,
        frozenset({"holder_entity_id", "epoch", "collection_id", "revised_from_id", "artwork_entity_id", "structure_entity_id"}),
        "account:edit",
    ),
    (MemoryStrikeRow, STRIKE_FIELDS, frozenset(), "memory_strike:edit"),
    (FoundingMythRow, MYTH_FIELDS, frozenset({"debunked_epoch"}), "founding_myth:edit"),
    (CommemorationRow, COMMEMORATION_FIELDS, frozenset({"last_observed_epoch"}), "commemoration:edit"),
    (LostLandRow, LOST_LAND_FIELDS, frozenset({"lost_epoch"}), "lost_land:edit"),
    (
        StoryletRunRow,
        STORYLET_FIELDS,
        frozenset({"storylet", "world_id", "cast", "step", "follows_run_id", "collection_id", "opened_epoch"}),
        "storylet:edit",
    ),
    (SocialNormRow, NORM_FIELDS, frozenset(), "social_norm:edit"),
    (LearningBiasRow, BIAS_FIELDS, frozenset(), "learning_bias:edit"),
    (GenerationRow, GENERATION_FIELDS, frozenset({"formative", "value_shifts"}), "generation:edit"),
    (DiasporaRow, DIASPORA_FIELDS, frozenset(), "diaspora:edit"),
    (DemographicTransitionRow, TRANSITION_FIELDS, frozenset(), "transition:edit"),
    (SexRatioRow, SEX_RATIO_FIELDS, frozenset(), "sex_ratio:edit"),
    (RoleNormRow, ROLE_FIELDS, frozenset(), "role_norm:edit"),
    (DatingSystemRow, DATING_FIELDS, frozenset({"reformed_epoch"}), "dating_system:edit"),
    (ArmsRow, ARMS_FIELDS, frozenset({"holder_kind", "parent_entity_id", "quartered_entity_id"}), "arms:edit"),
    (DesignRow, DESIGN_FIELDS, frozenset({"owner_entity_id", "kind", "parent_design_id", "mass", "epoch", "entity_id"}), "design:edit"),
    (DesignComponentRow, COMPONENT_FIELDS, frozenset(), "design_component:set"),
    (ComponentWearRow, WEAR_FIELDS, frozenset(), "component_wear:edit"),
    (StructureDesignRow, STRUCTURE_DESIGN_FIELDS, frozenset({"world_id", "creator_son_id", "created_epoch", "retired", "entity_id"}), "structure_design:edit"),
    (DesignSectionRow, SECTION_FIELDS, frozenset(), "design_section:set"),
    (DesignMountRow, MOUNT_FIELDS, frozenset({"design_id"}), "design_mount:edit"),
    (VehicleGroupRow, GROUP_FIELDS, frozenset({"built_epoch"}), "vehicle_group:edit"),
    (VehicleGroupSectionRow, GROUP_SECTION_FIELDS, frozenset(), "vehicle_group_section:set"),
    (VesselSectionRow, VESSEL_SECTION_FIELDS, frozenset(), "vessel_section:set"),
    (EquipmentModelRow, MODEL_FIELDS, frozenset({"parent_model_id", "created_epoch", "entity_id"}), "equipment_model:edit"),
    (UnitDesignRow, UNIT_TYPE_FIELDS, frozenset({"created_epoch", "parent_design_id", "entity_id"}), "unit_type:edit"),
    (StructureSectionRow, STRUCTURE_SECTION_FIELDS, frozenset(), "structure_section:edit"),
    (StructureDesignSectionRow, DESIGN_SECTION_FIELDS, frozenset(), "structure_design_section:set"),
    (MegastructureRow, MEGASTRUCTURE_FIELDS, frozenset({"updated_epoch"}), "megastructure:edit"),
    (DishRow, DISH_FIELDS, frozenset({"created_epoch", "entity_id"}), "dish:edit"),
    (CommunityDishRow, CUISINE_EDITABLE["community_dish"][1], frozenset({"since_epoch"}), "community_dish:edit"),
)
FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "src"


def test_every_column_of_a_record_the_god_edits_is_in_its_editor() -> None:
    missing = {
        kind.__tablename__: sorted(
            column.name
            for column in kind.__table__.columns
            if not column.primary_key and column.name not in FIXED and column.name not in fields and column.name not in derived
        )
        for kind, fields, derived in (*EDITORS, *((kind, fields, derived) for kind, fields, derived, _ in FRONT_EDITORS))
    }
    assert {table: columns for table, columns in missing.items() if columns} == {}


def test_no_editor_offers_a_value_the_store_keeps_for_itself() -> None:
    offered = {
        f"{module.__name__}.{name}": sorted(set(value) & FIXED)
        for module in (getattr(tables, item) for item in dir(tables) if not item.startswith("_"))
        if hasattr(module, "__name__") and module.__name__.startswith("aerona.db.tables.")
        for name, value in vars(module).items()
        if name.endswith("_FIELDS") and isinstance(value, tuple)
    }
    assert {name: keys for name, keys in offered.items() if keys} == {}


def test_no_drawer_editor_offers_a_value_the_store_keeps_for_itself() -> None:
    root = Path(__file__).resolve().parents[3] / "frontend" / "src"
    offered = sorted(
        f"{path.relative_to(root)}: {key}"
        for path in root.rglob("*.tsx")
        if path.is_file()
        for key in FIXED
        if f"key: '{key}'" in path.read_text(encoding="utf-8")
    )
    assert offered == []


def offers(text: str, field: str) -> bool:
    return (
        f"key: '{field}'" in text or re.search(rf"values: \{{[^}}]*\b{field}\b", text) is not None or re.search(rf"(?m)^\s+{field}: (?!'|\d)", text) is not None
    )


def test_every_editable_value_is_offered_by_the_screen_that_edits_it() -> None:
    sources = {path: path.read_text(encoding="utf-8") for path in FRONTEND.rglob("*.tsx") if ".test." not in path.name}
    gaps: dict[str, list[str]] = {}
    for _, fields, _, lever in FRONT_EDITORS:
        screens = [text for text in sources.values() if f"'{lever}'" in text]
        assert screens, lever
        missing = [field for field in fields if not any(offers(text, field) for text in screens)]
        if missing:
            gaps[lever] = missing
    assert gaps == {}
