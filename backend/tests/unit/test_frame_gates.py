from dataclasses import dataclass
from typing import cast

from aerona.catalog.vehicles import FRAMES
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import CivilizationTier
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.vehicles import VehicleFrame, VehicleSize
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.vehicles.fleet import least_tier, opened
from aerona.rules.registry import Rules


@dataclass
class Levels:
    levels: dict[KnowledgeBranch, int]

    def level(self, entity_id: int, branch: KnowledgeBranch) -> int:
        return self.levels.get(branch, 0)


def known(levels: dict[KnowledgeBranch, int]) -> KnowledgeMap:
    return cast(KnowledgeMap, Levels(levels))


def owner(tier: CivilizationTier) -> EntityRow:
    return EntityRow(id=1, civ_tier=int(tier))


def test_knowledge_opens_a_frame_and_the_size_of_a_power_only_caps_its_hull() -> None:
    rules = Rules()
    skilled = known({branch: 9 for branch in KnowledgeBranch})
    assert opened(FRAMES[VehicleFrame.AEROPLANE], skilled, owner(CivilizationTier.KINGDOM), rules)
    assert opened(FRAMES[VehicleFrame.TANK], skilled, owner(CivilizationTier.CITY_STATE), rules)
    assert opened(FRAMES[VehicleFrame.SPACE_FIGHTER], skilled, owner(CivilizationTier.KINGDOM), rules)
    assert not opened(FRAMES[VehicleFrame.DREADNOUGHT], skilled, owner(CivilizationTier.TRIBE), rules)
    assert not opened(FRAMES[VehicleFrame.AEROPLANE], known({}), owner(CivilizationTier.COSMIC_POWER), rules)
    assert least_tier(rules, VehicleSize.SMALL) == CivilizationTier.TRIBE
    assert least_tier(rules, VehicleSize.COLOSSAL) == CivilizationTier.KINGDOM


def test_no_frame_waits_on_a_single_world_empire() -> None:
    rules = Rules()
    skilled = known({branch: 9 for branch in KnowledgeBranch})
    kingdom = owner(CivilizationTier.KINGDOM)
    assert all(opened(spec, skilled, kingdom, rules) for spec in FRAMES.values())
