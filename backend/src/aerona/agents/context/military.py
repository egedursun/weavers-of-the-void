from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.made_lines import kit_line
from aerona.catalog.command import AREAS
from aerona.catalog.war_terms import CASUS_BELLI_LABELS
from aerona.catalog.war_w52 import ARMY_ROLES, DEFENCES, FALL_CHOICES, OPERATIONS, SIEGE_ACTION_SPECS, SIEGE_WORKS, STAFF_ROLES, STANCES
from aerona.core.grammar import several, spoken
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyOfficerRow, ArmyProfileRow, ArmyUnitRow, FeudRow, MercenaryContractRow, SpyNetworkRow
from aerona.db.tables.warfare import ArmyRow, BattleRow, CasusBelliRow, SiegeRow, WarProductionRow, WarRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.military import ContractStatus, FeudStatus, MoraleState, SpyOperation, VesselStatus
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.military.campaign import on_road
from aerona.engine.military.command import best_area, command_areas
from aerona.engine.military.engineering import earthworks_of, engineers, sappers, supply_limit
from aerona.engine.military.records import battle_field
from aerona.engine.military.templates import realm_template_of
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

TOP_STACKS = 3

OPERATION_KEYS = frozenset(operation.value for operation in SpyOperation)


async def army_sheet(session: AsyncSession, rules: Rules, army_id: int) -> str:
    army = await session.get(EntityRow, army_id)
    profile = await session.get(ArmyProfileRow, army_id)
    if army is None or profile is None:
        return ""
    stacks = list(
        await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id, ArmyUnitRow.count > 0).order_by(ArmyUnitRow.count.desc()))
    )
    makeup = ", ".join(f"{spoken(row.kind)} {row.count} strong" for row in stacks[:TOP_STACKS])
    hired = await session.scalar(
        select(MercenaryContractRow.id).where(MercenaryContractRow.army_entity_id == army_id, MercenaryContractRow.status == ContractStatus.ACTIVE).limit(1)
    )
    tail = "; sworn for pay" if hired is not None else ""
    return (
        f"{army.name}: {several(stat(army, 'size') or 0, 'soldier', 'soldiers')} ({makeup}), morale {stat(army, 'morale') or 0}, cohesion {profile.cohesion}, "
        f"{several(profile.supply_days, 'day', 'days')} of food, stance {STANCES[profile.stance].label.lower()}{order_line(stacks)}{tail}"
        f"{await works_line(session, rules, army_id, profile, stacks)}{await kit_line(session, army_id)}{await staff_line(session, army_id)}"
    )


async def staff_line(session: AsyncSession, army_id: int) -> str:
    officers = await session.scalars(
        select(ArmyOfficerRow).where(ArmyOfficerRow.army_entity_id == army_id, ArmyOfficerRow.until_epoch.is_(None)).order_by(ArmyOfficerRow.id)
    )
    shown = []
    for officer in officers:
        mortal = await session.get(EntityRow, officer.mortal_entity_id)
        if mortal is not None and officer.role in STAFF_ROLES:
            shown.append(f"{ARMY_ROLES[officer.role].label.lower()} {mortal.name}")
    return f"; staff: {', '.join(shown)}" if shown else ""


async def works_line(session: AsyncSession, rules: Rules, army_id: int, profile: ArmyProfileRow, stacks: list[ArmyUnitRow]) -> str:
    army = await session.get(EntityRow, army_id)
    row = await session.get(ArmyRow, army_id)
    region = await session.get(RegionEnvironmentRow, profile.region_entity_id) if profile.region_entity_id is not None else None
    parts: list[str] = []
    limit = supply_limit(rules, region, None)
    size = (stat(army, "size") or 0) if army is not None else 0
    parts.append(f"the land feeds about {limit}" + (", too few for it" if size > limit else ""))
    earthworks = earthworks_of(region)
    if earthworks:
        parts.append(f"earthworks {earthworks} here")
    if region is not None and on_road(region, rules):
        parts.append("on a road")
    if region is not None and region.scars.get(ScarKind.BRIDGE_DOWN.value, 0) > 0:
        parts.append("the bridge here is down")
    if engineers(rules, stacks):
        parts.append(f"{several(sappers(stacks), 'sapper', 'sappers')}")
    best = best_area(await command_areas(session, row.commander_entity_id if row is not None else None))
    if best is not None:
        parts.append(f"commander leads best at {AREAS[best].label.lower()}")
    template = await realm_template_of(session, row.owner_entity_id) if row is not None else None
    if template is not None:
        parts.append(f"realm template {template.name}" + (" (outdated)" if template.obsolete else ""))
    return "; " + ", ".join(parts)


def order_line(stacks: list[ArmyUnitRow]) -> str:
    soldiers = sum(row.count for row in stacks)
    if soldiers <= 0:
        return ""
    organisation = round(sum(row.organisation * row.count for row in stacks) / soldiers)
    shaken = sorted({spoken(row.morale_state) for row in stacks if row.morale_state is not MoraleState.STEADY})
    volleys = sum(row.ammunition for row in stacks if row.ammunition > 0)
    missing = sum(row.missing for row in stacks)
    parts = [f"organisation {organisation}"]
    if shaken:
        parts.append(f"some stacks {', '.join(shaken)}")
    if volleys:
        parts.append(f"{several(volleys, 'volley', 'volleys')} in hand")
    if missing:
        parts.append(f"{several(missing, 'straggler', 'stragglers')}")
    return ", " + ", ".join(parts)


async def war_sheet(session: AsyncSession, rules: Rules, war: WarRow, side_id: int) -> list[str]:
    lines: list[str] = []
    for row in await session.scalars(select(ArmyRow).where(ArmyRow.war_id == war.id, ArmyRow.owner_entity_id == side_id, ArmyRow.disbanded_epoch.is_(None))):
        sheet = await army_sheet(session, rules, row.entity_id)
        if sheet:
            lines.append(sheet)
    for siege in await session.scalars(select(SiegeRow).where(SiegeRow.war_id == war.id, SiegeRow.status == SiegeStatus.ONGOING)):
        besieged = await session.get(EntityRow, siege.besieged_entity_id)
        works = ", ".join(
            f"{SIEGE_WORKS[work].label.lower()} {int(siege.works.get(work.value, 0))}" for work in SIEGE_WORKS if int(siege.works.get(work.value, 0)) > 0
        )
        relief = " relief is coming" if siege.relief_army_id is not None else ""
        moves = siege_moves(siege)
        lines.append(
            f"siege of {besieged.name if besieged else 'a city'}: {several(siege.supplies, 'day', 'days')} of food, {spoken(siege.starvation)}, "
            f"{several(siege.breaches, 'breach', 'breaches')}{', works: ' + works if works else ''}{moves}{relief}"
        )
    last = await session.scalar(select(BattleRow).where(BattleRow.war_id == war.id).order_by(BattleRow.id.desc()).limit(1))
    if last is not None:
        winner = await session.get(EntityRow, last.winner_entity_id)
        tactics = f"{spoken(last.tactics_attacker)} against {spoken(last.tactics_defender)}" if last.tactics_attacker and last.tactics_defender else ""
        outcome = spoken(last.outcome_class) if last.outcome_class else spoken(last.outcome)
        plan = f"; {tactics}" if tactics else ""
        name = winner.name if winner else "one side"
        field = battle_field(last, {row.id: row.name for row in await field_names(session, last)})
        lines.append(f"last battle: {name} won ({outcome}{plan}), losses {last.winner_losses}/{last.loser_losses}{'; ' + field if field else ''}")
    return lines


async def field_names(session: AsyncSession, battle: BattleRow) -> list[EntityRow]:
    ids = [
        item for item in (battle.planned_entity_id, battle.trap_entity_id, battle.command_collapsed_entity_id, battle.standard_entity_id) if item is not None
    ]
    return list(await session.scalars(select(EntityRow).where(EntityRow.id.in_(ids)))) if ids else []


async def grievance_sheet(session: AsyncSession, community_id: int) -> list[str]:
    lines: list[str] = []
    held = select(CasusBelliRow).where(CasusBelliRow.holder_entity_id == community_id, CasusBelliRow.used_war_id.is_(None))
    for row in await session.scalars(held.order_by(CasusBelliRow.justification.desc(), CasusBelliRow.id)):
        target = await session.get(EntityRow, row.target_entity_id)
        lines.append(f"casus belli against {target.name if target else 'a rival'}: {CASUS_BELLI_LABELS[row.kind].lower()}, justification {row.justification}")
    line = await session.get(WarProductionRow, community_id)
    if line is not None and line.converted:
        lines.append(f"workshops turned to {spoken(line.commodity)} for the war, efficiency +{line.efficiency}%")
    return lines


async def intrigue_sheet(session: AsyncSession, community_id: int) -> list[str]:
    lines: list[str] = []
    owned = select(SpyNetworkRow).where(or_(SpyNetworkRow.owner_entity_id == community_id, SpyNetworkRow.side_entity_id == community_id))
    for network in await session.scalars(owned):
        target = await session.get(EntityRow, network.target_entity_id)
        revealed = f", {several(len(network.revealed_aims), 'enemy aim', 'enemy aims')} known" if network.revealed_aims else ""
        inside = await session.get(EntityRow, network.institution_entity_id) if network.institution_entity_id is not None else None
        placed = f", an agent placed inside {inside.name}" if inside is not None else ""
        last = f", last operation: {OPERATIONS[SpyOperation(network.last_operation)].label.lower()}" if network.last_operation in OPERATION_KEYS else ""
        lines.append(f"spies in {target.name if target else 'a rival'} (depth {network.depth}, intel {network.intel}{revealed}{placed}{last})")
    for feud in await session.scalars(
        select(FeudRow).where(or_(FeudRow.first_entity_id == community_id, FeudRow.second_entity_id == community_id), FeudRow.status == FeudStatus.ACTIVE)
    ):
        other = await session.get(EntityRow, feud.second_entity_id if feud.first_entity_id == community_id else feud.first_entity_id)
        lines.append(
            f"blood feud with {other.name if other else 'a rival'} (intensity {feud.intensity}, {several(feud.generations, 'generation', 'generations')})"
        )
    return lines


async def fleet_sheet(session: AsyncSession, community_id: int) -> list[str]:
    lines: list[str] = []
    for bond in await active_bonds(session, [BondKind.OWNS], sources=[community_id]):
        row = await session.get(VesselProfileRow, bond.target_node_id)
        vessel = await session.get(EntityRow, bond.target_node_id)
        if row is None or vessel is None or row.status in {VesselStatus.WRECKED}:
            continue
        lines.append(
            f"ship {vessel.name}: {spoken(row.frame)}, hull {row.condition}, crew {row.crew}, renown {row.renown}"
            + (f", strange ({stat(vessel, 'strangeness')})" if (stat(vessel, "strangeness") or 0) > 0 else "")
        )
    return lines


def siege_moves(siege: SiegeRow) -> str:
    parts = []
    if siege.last_action is not None:
        parts.append(f"besiegers last chose to {SIEGE_ACTION_SPECS[siege.last_action].label.lower()}")
    if siege.last_defence is not None:
        parts.append(f"defenders last chose to {DEFENCES[siege.last_defence].label.lower()}")
    if siege.choice is not None:
        parts.append(f"if it falls: {FALL_CHOICES[siege.choice].label.lower()}")
    return f"; {'; '.join(parts)}" if parts else ""
