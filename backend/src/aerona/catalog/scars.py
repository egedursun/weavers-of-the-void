from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.evolution import SuccessionStage
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class ScarSpec:
    label: str
    fertility: Callable[[Rules], int]
    passage: Callable[[Rules], int]
    decay: Callable[[Rules], int]
    resets_to: SuccessionStage | None


SCARS: Mapping[ScarKind, ScarSpec] = total(
    ScarKind,
    {
        ScarKind.BATTLEFIELD: ScarSpec(
            "Battlefield",
            lambda rules: rules.scars.battlefield_fertility_pct,
            lambda rules: rules.scars.battlefield_passage_loss,
            lambda rules: rules.scars.battlefield_decay,
            SuccessionStage.GRASSLAND,
        ),
        ScarKind.PLAGUE_GROUND: ScarSpec(
            "Plague ground",
            lambda rules: rules.scars.plague_ground_fertility_pct,
            lambda rules: rules.scars.plague_ground_passage_loss,
            lambda rules: rules.scars.plague_ground_decay,
            None,
        ),
        ScarKind.MADE_BARREN: ScarSpec(
            "Made barren",
            lambda rules: rules.scars.salted_earth_fertility_pct,
            lambda rules: rules.scars.made_barren_passage_loss,
            lambda rules: rules.scars.salted_earth_decay,
            SuccessionStage.BARE,
        ),
        ScarKind.BURNED: ScarSpec(
            "Burned",
            lambda rules: rules.scars.burned_fertility_pct,
            lambda rules: rules.scars.burned_passage_loss,
            lambda rules: rules.scars.burned_decay,
            SuccessionStage.GRASSLAND,
        ),
        ScarKind.CRATER: ScarSpec(
            "Crater",
            lambda rules: rules.scars.crater_fertility_pct,
            lambda rules: rules.scars.crater_passage_loss,
            lambda rules: rules.scars.crater_decay,
            SuccessionStage.BARE,
        ),
        ScarKind.HAUNTED: ScarSpec(
            "Haunted",
            lambda rules: rules.scars.haunted_fertility_pct,
            lambda rules: rules.scars.haunted_passage_loss,
            lambda rules: rules.scars.haunted_decay,
            None,
        ),
        ScarKind.BLIGHTED: ScarSpec(
            "Blighted",
            lambda rules: rules.scars.blighted_fertility_pct,
            lambda rules: rules.scars.blighted_passage_loss,
            lambda rules: rules.scars.blighted_decay,
            SuccessionStage.GRASSLAND,
        ),
        ScarKind.LEAK_WOUND: ScarSpec(
            "Leak wound",
            lambda rules: rules.scars.leak_wound_fertility_pct,
            lambda rules: rules.scars.leak_wound_passage_loss,
            lambda rules: rules.scars.leak_wound_decay,
            SuccessionStage.BARE,
        ),
        ScarKind.PLUNDERED: ScarSpec(
            "Plundered",
            lambda rules: rules.campaign_depth.plunder_harvest_pct,
            lambda rules: rules.scars.plundered_passage_loss,
            lambda rules: rules.campaign_depth.plunder_heal,
            None,
        ),
        ScarKind.EARTHWORKS: ScarSpec(
            "Earthworks",
            lambda rules: rules.army_depth.earthworks_fertility_pct,
            lambda rules: rules.scars.earthworks_passage_loss,
            lambda rules: rules.army_depth.earthworks_decay,
            SuccessionStage.GRASSLAND,
        ),
        ScarKind.MILITARY_ROAD: ScarSpec(
            "Military road",
            lambda rules: rules.army_depth.road_fertility_pct,
            lambda rules: rules.scars.military_road_passage_loss,
            lambda rules: rules.army_depth.road_decay,
            None,
        ),
        ScarKind.BRIDGE_DOWN: ScarSpec(
            "Bridge down",
            lambda rules: rules.army_depth.bridge_down_fertility_pct,
            lambda rules: rules.scars.bridge_down_passage_loss,
            lambda rules: rules.army_depth.bridge_down_decay,
            None,
        ),
        ScarKind.FLOODED: ScarSpec(
            "Flooded",
            lambda rules: rules.scars.flooded_fertility_loss,
            lambda rules: rules.scars.flooded_passage_loss,
            lambda rules: rules.scars.flooded_decay,
            SuccessionStage.YOUNG_FOREST,
        ),
        ScarKind.POISONED: ScarSpec(
            "Poisoned",
            lambda rules: rules.scars.poisoned_fertility_loss,
            lambda rules: rules.scars.poisoned_passage_loss,
            lambda rules: rules.scars.poisoned_decay,
            SuccessionStage.BARE,
        ),
        ScarKind.MINED_OUT: ScarSpec(
            "Mined out",
            lambda rules: rules.scars.mined_out_fertility_loss,
            lambda rules: rules.scars.mined_out_passage_loss,
            lambda rules: rules.scars.mined_out_decay,
            SuccessionStage.BARE,
        ),
        ScarKind.ERODED: ScarSpec(
            "Eroded",
            lambda rules: rules.scars.eroded_fertility_loss,
            lambda rules: rules.scars.eroded_passage_loss,
            lambda rules: rules.scars.eroded_decay,
            SuccessionStage.PIONEER,
        ),
        ScarKind.DEFORESTED: ScarSpec(
            "Deforested",
            lambda rules: rules.scars.deforested_fertility_loss,
            lambda rules: rules.scars.deforested_passage_loss,
            lambda rules: rules.scars.deforested_decay,
            SuccessionStage.SHRUBLAND,
        ),
        ScarKind.DRAINED: ScarSpec(
            "Drained",
            lambda rules: rules.scars.drained_fertility_loss,
            lambda rules: rules.scars.drained_passage_loss,
            lambda rules: rules.scars.drained_decay,
            SuccessionStage.GRASSLAND,
        ),
        ScarKind.OVERGRAZED: ScarSpec(
            "Overgrazed",
            lambda rules: rules.scars.overgrazed_fertility_loss,
            lambda rules: rules.scars.overgrazed_passage_loss,
            lambda rules: rules.scars.overgrazed_decay,
            SuccessionStage.PIONEER,
        ),
    },
)
