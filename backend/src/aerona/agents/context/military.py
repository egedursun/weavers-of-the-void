from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow, FeudRow, MercenaryContractRow, SpyNetworkRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, SiegeRow, WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.military import ContractStatus, FeudStatus, MoraleState, VesselStatus
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.military.records import battle_field
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat

TOP_STACKS = 3


def words(value: str) -> str:
    return value.replace("_", " ")


async def army_sheet(session: AsyncSession, army_id: int) -> str:
    army = await session.get(EntityRow, army_id)
    profile = await session.get(ArmyProfileRow, army_id)
    if army is None or profile is None:
        return ""
    stacks = list(
        await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id, ArmyUnitRow.count > 0).order_by(ArmyUnitRow.count.desc()))
    )
    makeup = ", ".join(f"{row.count} {words(row.kind.value)}" for row in stacks[:TOP_STACKS])
    hired = await session.scalar(
        select(MercenaryContractRow.id).where(MercenaryContractRow.army_entity_id == army_id, MercenaryContractRow.status == ContractStatus.ACTIVE).limit(1)
    )
    tail = "; sworn for pay" if hired is not None else ""
    return (
        f"{army.name}: {stat(army, 'size') or 0} soldiers ({makeup}), morale {stat(army, 'morale') or 0}, cohesion {profile.cohesion}, "
        f"{profile.supply_days} days of food, stance {words(profile.stance.value)}{order_line(stacks)}{tail}"
    )


def order_line(stacks: list[ArmyUnitRow]) -> str:
    soldiers = sum(row.count for row in stacks)
    if soldiers <= 0:
        return ""
    organisation = round(sum(row.organisation * row.count for row in stacks) / soldiers)
    shaken = sorted({words(row.morale_state.value) for row in stacks if row.morale_state is not MoraleState.STEADY})
    volleys = sum(row.ammunition for row in stacks if row.ammunition > 0)
    missing = sum(row.missing for row in stacks)
    parts = [f"organisation {organisation}"]
    if shaken:
        parts.append(f"some stacks {', '.join(shaken)}")
    if volleys:
        parts.append(f"{volleys} volleys in hand")
    if missing:
        parts.append(f"{missing} stragglers")
    return ", " + ", ".join(parts)


async def war_sheet(session: AsyncSession, war: WarRow, side_id: int) -> list[str]:
    lines: list[str] = []
    for row in await session.scalars(select(ArmyRow).where(ArmyRow.war_id == war.id, ArmyRow.owner_entity_id == side_id, ArmyRow.disbanded_epoch.is_(None))):
        sheet = await army_sheet(session, row.entity_id)
        if sheet:
            lines.append(sheet)
    for siege in await session.scalars(select(SiegeRow).where(SiegeRow.war_id == war.id, SiegeRow.status == SiegeStatus.ONGOING)):
        besieged = await session.get(EntityRow, siege.besieged_entity_id)
        works = ", ".join(words(key) for key, value in siege.works.items() if key != "famine" and int(value) >= 100)
        relief = " relief is coming" if siege.relief_army_id is not None else ""
        lines.append(
            f"siege of {besieged.name if besieged else 'a city'}: {siege.supplies} days of food, {words(siege.starvation.value)}, "
            f"{siege.breaches} breaches{', works: ' + works if works else ''}{relief}"
        )
    last = await session.scalar(select(BattleRow).where(BattleRow.war_id == war.id).order_by(BattleRow.id.desc()).limit(1))
    if last is not None:
        winner = await session.get(EntityRow, last.winner_entity_id)
        tactics = (
            f"{words(last.tactics_attacker.value)} against {words(last.tactics_defender.value)}" if last.tactics_attacker and last.tactics_defender else ""
        )
        outcome = words(last.outcome_class.value) if last.outcome_class else words(last.outcome.value)
        plan = f"; {tactics}" if tactics else ""
        name = winner.name if winner else "one side"
        field = battle_field(last, {row.id: row.name for row in await field_names(session, last)})
        lines.append(f"last battle: {name} won ({outcome}{plan}), losses {last.winner_losses}/{last.loser_losses}{'; ' + field if field else ''}")
    return lines


async def field_names(session: AsyncSession, battle: BattleRow) -> list[EntityRow]:
    ids = [item for item in (battle.planned_entity_id, battle.trap_entity_id, battle.command_collapsed_entity_id) if item is not None]
    return list(await session.scalars(select(EntityRow).where(EntityRow.id.in_(ids)))) if ids else []


async def intrigue_sheet(session: AsyncSession, community_id: int) -> list[str]:
    lines: list[str] = []
    owned = select(SpyNetworkRow).where(or_(SpyNetworkRow.owner_entity_id == community_id, SpyNetworkRow.side_entity_id == community_id))
    for network in await session.scalars(owned):
        target = await session.get(EntityRow, network.target_entity_id)
        revealed = f", {len(network.revealed_aims)} enemy aims known" if network.revealed_aims else ""
        lines.append(f"spies in {target.name if target else 'a rival'} (depth {network.depth}, intel {network.intel}{revealed})")
    for feud in await session.scalars(
        select(FeudRow).where(or_(FeudRow.first_entity_id == community_id, FeudRow.second_entity_id == community_id), FeudRow.status == FeudStatus.ACTIVE)
    ):
        other = await session.get(EntityRow, feud.second_entity_id if feud.first_entity_id == community_id else feud.first_entity_id)
        lines.append(f"blood feud with {other.name if other else 'a rival'} (intensity {feud.intensity}, {feud.generations} generations)")
    return lines


async def fleet_sheet(session: AsyncSession, community_id: int) -> list[str]:
    lines: list[str] = []
    for bond in await active_bonds(session, [BondKind.OWNS], sources=[community_id]):
        row = await session.get(VesselProfileRow, bond.target_node_id)
        vessel = await session.get(EntityRow, bond.target_node_id)
        if row is None or vessel is None or row.status in {VesselStatus.WRECKED}:
            continue
        lines.append(
            f"ship {vessel.name}: {words(row.hull_class.value)}, hull {row.condition}, crew {row.crew}, renown {row.renown}"
            + (f", strange ({stat(vessel, 'strangeness')})" if (stat(vessel, "strangeness") or 0) > 0 else "")
        )
    return lines
