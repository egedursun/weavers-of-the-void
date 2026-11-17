from typing import Any

from sqlalchemy import select

from aerona.db.session import Database
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.military import ArmyUnitRow, SpyNetworkRow, UnitDesignRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow, WarRow
from aerona.domain.enums.military import SpyCover
from aerona.domain.enums.vehicles import VehicleFrame
from aerona.domain.enums.war import WarCause, WarStatus
from aerona.tools.toolkit import TurnToolkit
from tests.tools.factories import seed_realm, son_toolkit


async def ok(toolkit: TurnToolkit, name: str, arguments: dict[str, Any]) -> str:
    outcome = await toolkit.runtime.call(name, arguments)
    assert not outcome.is_error, outcome.text
    return outcome.text


async def test_a_son_wages_a_whole_war(database: Database) -> None:
    realm = await seed_realm(database)
    toolkit = await son_toolkit(database, realm.son_id, action_points=12)
    designed = await ok(
        toolkit,
        "design_unit",
        {"owner_id": realm.people_id, "name": "Tide Spears", "base_kind": "line_infantry", "melee": 70, "defence": 60, "armour": "hide", "shield": "large"},
    )
    assert "Tide Spears" in designed
    declared = await ok(
        toolkit,
        "wage_war",
        {
            "attacker_id": realm.people_id,
            "defender_id": realm.settlement_id,
            "cause": "claim",
            "aims": ["tribute", "seize_settlement"],
            "reason": "the salt is ours",
        },
    )
    assert "declared war" in declared
    async with database.read() as session:
        war = await session.scalar(select(WarRow).where(WarRow.status != WarStatus.ENDED))
        assert war is not None
        assert war.cause is WarCause.CLAIM
        war_id = war.id
    raised = await ok(toolkit, "raise_host", {"community_id": realm.people_id, "soldiers": 60, "war_id": war_id})
    assert "raised" in raised
    async with database.read() as session:
        army = await session.scalar(select(ArmyRow).where(ArmyRow.owner_entity_id == realm.people_id))
        assert army is not None
        army_id = army.entity_id
        designs = set(await session.scalars(select(ArmyUnitRow.design_id).where(ArmyUnitRow.army_entity_id == army_id)))
        design = await session.scalar(select(UnitDesignRow).where(UnitDesignRow.name == "Tide Spears"))
        assert design is not None
    assert design.id in designs
    await ok(toolkit, "lay_siege", {"war_id": war_id, "army_id": army_id, "settlement_id": realm.settlement_id})
    async with database.read() as session:
        assert await session.scalar(select(SiegeRow).where(SiegeRow.war_id == war_id)) is not None
    await ok(toolkit, "plant_spies", {"owner_id": realm.people_id, "target_id": realm.settlement_id, "cover": "priest"})
    await ok(toolkit, "commission_vessel", {"owner_id": realm.settlement_id, "name": "Saltwind", "frame": "longship"})
    peace = await ok(toolkit, "offer_peace", {"war_id": war_id, "victor_id": realm.people_id, "terms": ["tribute"]})
    assert "The war ended" in peace
    await ok(toolkit, "raise_host", {"community_id": realm.settlement_id, "soldiers": 20, "commander_id": realm.mortal_id})
    async with database.read() as session:
        watch = await session.scalar(select(ArmyRow).where(ArmyRow.owner_entity_id == realm.settlement_id, ArmyRow.war_id.is_(None)))
        assert watch is not None
        watch_id = watch.entity_id
    await ok(toolkit, "disband_host", {"army_id": watch_id, "reason": "the nets need mending more than the walls need guarding"})
    async with database.read() as session:
        network = await session.scalar(select(SpyNetworkRow).where(SpyNetworkRow.owner_entity_id == realm.people_id))
        assert network is not None
        assert network.cover is SpyCover.PRIEST
        vessel = await session.scalar(select(VesselProfileRow).where(VesselProfileRow.frame == VehicleFrame.LONGSHIP))
        assert vessel is not None
        ended = await session.get(WarRow, war_id)
        assert ended is not None
        assert ended.status is WarStatus.ENDED
        disbanded = await session.get(ArmyRow, watch_id)
        assert disbanded is not None
        assert disbanded.disbanded_epoch is not None
