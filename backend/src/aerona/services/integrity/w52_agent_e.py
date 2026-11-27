from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.war_w52 import DEFENCES
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.honours import NamedUnitRow, UnitHonourRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.settlement import SettlementInfrastructureRow, SettlementProfileRow
from aerona.db.tables.warfare import BattleRow, SiegeRow, WarRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.settlement import WaterSupply
from aerona.domain.enums.world_view import WarTerrain
from aerona.engine.cosmos.world_views import view_of
from aerona.engine.environment.battleground import war_ground
from aerona.engine.military.engineering import RIVERS
from aerona.engine.settlement.modes import MODE_KEY, choose_mode, fits, scene_of
from aerona.rules.registry import Rules

UNKNOWN_PLACE = "an unrecorded field"


async def misplaced_moles(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(SpyNetworkRow).where(SpyNetworkRow.institution_entity_id.is_not(None)).order_by(SpyNetworkRow.id)):
        place = await session.get(EntityRow, row.institution_entity_id)
        if place is None or place.status is not EntityStatus.CANON or row.target_entity_id not in {place.id, place.location_id}:
            found.append(row.id)
    return found


async def unplace_mole(session: AsyncSession, key: int) -> None:
    row = await session.get(SpyNetworkRow, key)
    if row is not None:
        row.institution_entity_id = None


async def dry_floods(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for siege in await session.scalars(select(SiegeRow).where(SiegeRow.last_defence.is_not(None)).order_by(SiegeRow.id)):
        if siege.last_defence is None or not DEFENCES[siege.last_defence].needs_water:
            continue
        town = await session.get(EntityRow, siege.besieged_entity_id)
        ground = await session.get(RegionEnvironmentRow, town.location_id) if town is not None and town.location_id is not None else None
        walls = await session.get(SettlementInfrastructureRow, siege.besieged_entity_id)
        if (ground is None or ground.river_class not in RIVERS) and (walls is None or walls.water is not WaterSupply.AQUEDUCT):
            found.append(siege.id)
    return found


async def drop_flood(session: AsyncSession, key: int) -> None:
    siege = await session.get(SiegeRow, key)
    if siege is not None:
        siege.last_defence = None


async def unplaced_honours(session: AsyncSession) -> list[int]:
    return list(await session.scalars(select(UnitHonourRow.id).where(UnitHonourRow.note == "").order_by(UnitHonourRow.id)))


async def place_honour(session: AsyncSession, key: int) -> None:
    row = await session.get(UnitHonourRow, key)
    if row is None:
        return
    unit = await session.get(NamedUnitRow, row.named_unit_id)
    row.note = unit.name if unit is not None else UNKNOWN_PLACE


async def world_rules(session: AsyncSession) -> Rules:
    cosmos = CosmosRepository(session)
    return await cosmos.rules() if await cosmos.get() is not None else Rules()


async def unfit_settle_modes(session: AsyncSession) -> list[int]:
    rules = await world_rules(session)
    found: list[int] = []
    for profile in await session.scalars(select(SettlementProfileRow).order_by(SettlementProfileRow.settlement_entity_id)):
        town = await session.get(EntityRow, profile.settlement_entity_id)
        if town is None or MODE_KEY in profile.locked:
            continue
        if not fits(rules, profile.settle_mode, await scene_of(session, rules, town)):
            found.append(profile.settlement_entity_id)
    return found


async def refit_settle_mode(session: AsyncSession, key: int) -> None:
    profile = await session.get(SettlementProfileRow, key)
    town = await session.get(EntityRow, key)
    if profile is not None and town is not None:
        profile.settle_mode = await choose_mode(session, await world_rules(session), town)


async def ground_allowed(session: AsyncSession, rules: Rules, battle: BattleRow) -> WarTerrain:
    war = await session.get(WarRow, battle.war_id)
    view = await view_of(session, rules, war.world_id if war is not None else None)
    place = await session.get(RegionEnvironmentRow, battle.place_entity_id) if battle.place_entity_id is not None else None
    return war_ground(view.war, battle.terrain if battle.terrain is not None else place.dominant_terrain if place is not None else None)


async def misplaced_grounds(session: AsyncSession) -> list[int]:
    rules = await world_rules(session)
    found: list[int] = []
    for battle in await session.scalars(select(BattleRow).order_by(BattleRow.id)):
        allowed = await ground_allowed(session, rules, battle)
        if battle.ground is not allowed and battle.ground is not WarTerrain.UNDERGROUND:
            found.append(battle.id)
    return found


async def reground_battle(session: AsyncSession, key: int) -> None:
    battle = await session.get(BattleRow, key)
    if battle is not None:
        battle.ground = await ground_allowed(session, await world_rules(session), battle)
