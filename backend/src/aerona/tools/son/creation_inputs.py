from typing import Annotated, Any

from pydantic import Field, create_model

from aerona.catalog.entity_types import ENTITY_TYPES, EntityTypeSpec
from aerona.constants.tool_inputs import (
    CREATION_DESCRIPTION_MAX,
    CREATION_DESCRIPTION_MIN,
    IMAGE_PROMPT_MAX,
    NAME_MAX,
    NAME_MIN,
    POWER_LEVEL_MAX,
    POWER_LEVEL_MIN,
    SUBTYPE_MAX,
    TAG_MAX,
    TAGS_MAX,
    TITLE_MAX,
)
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ArtMedium, CalendarSlot, ItemClass, LegendArchetype, ProphecyConsequence, ProphecyPredicate, TraditionKind
from aerona.domain.enums.ecology import (
    AwakeningTrigger,
    BeastTemper,
    Biochemistry,
    BreathKind,
    Diet,
    GazeKind,
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
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EngineKind, EntityType, LegendCategory
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.faith import FuneralRite, JudgementDoctrine, RebirthPath, TenetKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import VesselArmament
from aerona.domain.enums.mind import ActKind, TraitKind
from aerona.domain.enums.mortal import MortalSex
from aerona.domain.enums.place import PlaceKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, NaturalLaw, ResourceMechanic
from aerona.domain.enums.structure import STRUCTURE_LEVEL_MAX, StructureKind
from aerona.domain.enums.travel import VehicleKind
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.domain.enums.world import SkyEventKind
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.shared_inputs import LinkInput, WordInput
from aerona.tools.son.targets import CREATION_FORBIDDEN_BONDS

Tag = Annotated[str, Field(min_length=1, max_length=TAG_MAX)]
TENETS_MAX = 12
WORSHIPPING_TYPES = frozenset({EntityType.CULT, EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION})


class EventEffectInput(ToolInput):
    entity_id: int
    stat: str
    percent: float


CREATION_BOND_CHOICES = [kind.value for kind in BondKind if kind not in CREATION_FORBIDDEN_BONDS]


class CreationLinkInput(LinkInput):
    kind: Annotated[BondKind, Field(json_schema_extra={"enum": CREATION_BOND_CHOICES})]


class CreationInput(ToolInput):
    name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
    subtype: Annotated[str, Field(max_length=SUBTYPE_MAX)] | None = None
    description: Annotated[str, Field(min_length=CREATION_DESCRIPTION_MIN, max_length=CREATION_DESCRIPTION_MAX)]
    domain: str | None = None
    power_level: Annotated[int, Field(ge=POWER_LEVEL_MIN, le=POWER_LEVEL_MAX)]
    links: Annotated[list[CreationLinkInput], Field(min_length=1)]
    image_prompt: Annotated[str, Field(max_length=IMAGE_PROMPT_MAX)] | None = None
    tags: Annotated[list[Tag], Field(max_length=TAGS_MAX)] | None = None
    story_id: int | None = None
    co_creator_id: int | None = None

    def stat_values(self) -> dict[str, Any]:
        stats = getattr(self, "stats", None)
        return stats.model_dump(exclude_none=True) if isinstance(stats, ToolInput) else {}

    def option(self, name: str) -> Any:
        return getattr(self, name, None)


MORTAL_TRAITS_MAX = 5


def _stats_input(spec: EntityTypeSpec) -> type[ToolInput]:
    fields: dict[str, Any] = {field.key: (int | None, None) for field in spec.stats}
    model: type[ToolInput] = create_model(f"{spec.type.value.title().replace('_', '')}StatsInput", __base__=ToolInput, **fields)
    return model


def _extra_fields(entity_type: EntityType) -> dict[str, Any]:
    extras: dict[str, dict[str, Any]] = {
        EntityType.NATURAL_LAW: {"mechanic": (NaturalLaw | None, None)},
        EntityType.KNOWLEDGE: {"branch": (KnowledgeBranch, ...), "learner_ids": (list[int] | None, None)},
        EntityType.REGION: {"water": (bool | None, None)},
        EntityType.PLACE: {"place_kind": (PlaceKind, ...)},
        EntityType.SPECIES: {
            "traits": (list[CreatureTrait] | None, None),
            "body_plan": (BodyPlan, ...),
            "size_class": (SizeClass, ...),
            "diet": (Diet, ...),
            "sociality": (Sociality | None, None),
            "nocturnal": (bool | None, None),
            "migratory": (bool | None, None),
            "products": (list[YieldProduct] | None, None),
            "species_class": (SpeciesClass | None, None),
            "biochemistry": (Biochemistry | None, None),
            "growth_cycle": (GrowthCycle | None, None),
            "plant_yields": (list[PlantYield] | None, None),
        },
        EntityType.BEAST: {
            "species_id": (int | None, None),
            "size_class": (SizeClass | None, None),
            "temper": (BeastTemper | None, None),
            "endurance": (Annotated[int, Field(ge=0, le=100)] | None, None),
            "perception": (Annotated[int, Field(ge=0, le=100)] | None, None),
            "willpower": (Annotated[int, Field(ge=0, le=100)] | None, None),
            "intelligence": (Annotated[int, Field(ge=0, le=100)] | None, None),
            "breath": (BreathKind | None, None),
            "gaze": (GazeKind | None, None),
            "temperament": (Temperament | None, None),
            "habitat": (Habitat | None, None),
            "awakening": (AwakeningTrigger | None, None),
            "skin": (TissueMaterial | None, None),
        },
        EntityType.VESSEL: {
            "target_world_id": (int | None, None),
            "vessel_kind": (VehicleKind | None, None),
            "frame": (VehicleFrame | None, None),
            "armament": (list[VesselArmament] | None, None),
            "hull_material": (MaterialKind | None, None),
            "fabric_material": (MaterialKind | None, None),
            "home_port_id": (int | None, None),
            "captain_id": (int | None, None),
        },
        EntityType.LANGUAGE: {"words": (Annotated[list[WordInput], Field(min_length=1)], ...)},
        EntityType.MORTAL: {
            "title": (Annotated[str, Field(max_length=TITLE_MAX)] | None, None),
            "sex": (MortalSex | None, None),
            "traits": (Annotated[list[TraitKind], Field(max_length=MORTAL_TRAITS_MAX)] | None, None),
        },
        EntityType.EVENT: {"effects": (list[EventEffectInput] | None, None)},
        EntityType.LEGEND: {"legend_category": (LegendCategory | None, None), "archetype": (LegendArchetype, ...)},
        EntityType.TRADITION: {
            "tradition_kind": (TraditionKind, ...),
            "calendar_slot": (CalendarSlot | None, None),
            "taboo_target": (CommodityKind | None, None),
            "taboo_act": (ActKind | None, None),
            "funeral_rite": (FuneralRite | None, None),
        },
        EntityType.ITEM: {
            "item_class": (ItemClass, ...),
            "material": (MaterialKind | None, None),
            "world_material_id": (int | None, None),
            "secondary_materials": (list[MaterialKind] | None, None),
        },
        EntityType.ARTWORK: {"medium": (ArtMedium, ...), "subject_id": (int | None, None)},
        EntityType.PROPHECY: {
            "predicate": (ProphecyPredicate, ...),
            "subject_id": (int | None, None),
            "second_id": (int | None, None),
            "archetype": (LegendArchetype | None, None),
            "sky_kind": (SkyEventKind | None, None),
            "event_kind": (EngineKind | None, None),
            "within_epochs": (int | None, None),
            "consequence": (ProphecyConsequence | None, None),
            "consequence_id": (int | None, None),
        },
        EntityType.STRUCTURE: {
            "structure_kind": (StructureKind, ...),
            "material": (MaterialKind | None, None),
            "world_material_id": (int | None, None),
            "level": (Annotated[int, Field(ge=1, le=STRUCTURE_LEVEL_MAX)] | None, None),
            "design_id": (int | None, None),
        },
        EntityType.FACTION: {"faction_kind": (FactionKind, ...)},
        EntityType.LAW: {"law_kind": (LawKind, ...), "law_params": (dict[str, int | str | bool] | None, None)},
        EntityType.CULT: {
            "tenets": (Annotated[list[TenetKind], Field(max_length=TENETS_MAX)] | None, None),
            "judgement": (JudgementDoctrine | None, None),
            "rebirth_path": (RebirthPath | None, None),
        },
        EntityType.RESOURCE: {
            "commodity": (CommodityKind, ...),
            "material": (MaterialKind | None, None),
            "mechanics": (list[ResourceMechanic] | None, None),
        },
    }
    fields = dict(extras.get(entity_type, {}))
    if entity_type in WORSHIPPING_TYPES:
        fields["worshipped_son_id"] = (int | None, None)
    return fields


def creation_input(entity_type: EntityType) -> type[CreationInput]:
    spec = ENTITY_TYPES[entity_type]
    fields: dict[str, Any] = {"stats": (_stats_input(spec) | None, None), **_extra_fields(entity_type)}
    if spec.placeable:
        fields["location_id"] = (int | None, None)
    model: type[CreationInput] = create_model(f"Create{entity_type.value.title().replace('_', '')}Input", __base__=CreationInput, **fields)
    return model


CREATION_INPUTS: dict[EntityType, type[CreationInput]] = {
    entity_type: creation_input(entity_type) for entity_type, spec in ENTITY_TYPES.items() if spec.creation_tool is not None
}
