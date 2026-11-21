from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.total import total
from aerona.db.tables.leagues import LeagueMemberRow
from aerona.db.tables.mass_weapons import DeterrencePostureRow, MassWeaponRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.leagues import LeagueStanding
from aerona.domain.enums.mass_weapons import ARMED_STAGES, MassHarm, MassReach, RemnantKind
from aerona.engine.lore.research import lacks, techniques_of
from aerona.engine.primitives.queries import active_bonds

H = MassHarm
NEAR_TECH = total(
    MassHarm,
    {
        H.BLAST: Technique.GUNPOWDER,
        H.FIRE: Technique.ALCHEMY,
        H.POISON: Technique.HERBALISM,
        H.DISEASE: Technique.INOCULATION,
        H.RADIATION: Technique.NUCLEAR_POWER,
        H.SWARM: Technique.MACHINE_TOOLS,
        H.FIELD: None,
        H.RITE: None,
        H.DIVINE_RELIC: None,
    },
)
WIDE_TECH = total(
    MassHarm,
    {
        H.BLAST: Technique.NUCLEAR_WEAPONS,
        H.FIRE: Technique.INDUSTRIAL_CHEMISTRY,
        H.POISON: Technique.INDUSTRIAL_CHEMISTRY,
        H.DISEASE: Technique.GENETIC_ENGINEERING,
        H.RADIATION: Technique.NUCLEAR_WEAPONS,
        H.SWARM: Technique.ARTIFICIAL_MINDS,
        H.FIELD: None,
        H.RITE: None,
        H.DIVINE_RELIC: None,
    },
)
REACH_RANK = total(MassReach, {MassReach.SETTLEMENT: 1, MassReach.REGION: 3, MassReach.WORLD: 10})
KILL_WEIGHT = total(
    MassHarm,
    {H.BLAST: 100, H.FIRE: 80, H.POISON: 50, H.DISEASE: 40, H.RADIATION: 80, H.SWARM: 60, H.FIELD: 50, H.RITE: 40, H.DIVINE_RELIC: 100},
)
REMNANT_OF = total(
    MassHarm,
    {
        H.BLAST: RemnantKind.BURIED_CHARGES,
        H.FIRE: None,
        H.POISON: RemnantKind.POISONED_GROUND,
        H.DISEASE: None,
        H.RADIATION: RemnantKind.FALLOUT,
        H.SWARM: RemnantKind.ABANDONED_MACHINES,
        H.FIELD: RemnantKind.CURSED_GROUND,
        H.RITE: RemnantKind.CURSED_GROUND,
        H.DIVINE_RELIC: RemnantKind.CURSED_GROUND,
    },
)
BURNING = frozenset({MassHarm.BLAST, MassHarm.FIRE, MassHarm.SWARM})


@dataclass
class ArsenalTally:
    begun: int = 0
    staged: int = 0
    built: int = 0
    tested: int = 0
    used: int = 0
    killed: int = 0
    bluffs: int = 0
    remnants: int = 0
    remnant_dead: int = 0
    cleared: int = 0
    treaties: int = 0


def technique_for(harm: MassHarm, reach: MassReach) -> Technique | None:
    return NEAR_TECH[harm] if reach is MassReach.SETTLEMENT else WIDE_TECH[harm]


async def can_build(session: AsyncSession, holder_id: int, harm: MassHarm, reach: MassReach) -> bool:
    needed = technique_for(harm, reach)
    return needed is None or not await lacks(session, holder_id, needed)


async def knows_how(session: AsyncSession, holder_id: int, harm: MassHarm, reach: MassReach) -> bool:
    needed = technique_for(harm, reach)
    return needed is not None and needed in await techniques_of(session, holder_id)


async def weapons_of(session: AsyncSession, holder_id: int) -> list[MassWeaponRow]:
    return list(await session.scalars(select(MassWeaponRow).where(MassWeaponRow.holder_entity_id == holder_id).order_by(MassWeaponRow.id)))


async def armed(session: AsyncSession, holder_id: int) -> bool:
    return any(weapon.count > 0 and weapon.stage in ARMED_STAGES for weapon in await weapons_of(session, holder_id))


async def postures_of(session: AsyncSession, holder_id: int) -> list[DeterrencePostureRow]:
    query = select(DeterrencePostureRow).where(DeterrencePostureRow.holder_entity_id == holder_id)
    return list(await session.scalars(query.order_by(DeterrencePostureRow.id)))


async def realms_of(session: AsyncSession, node_id: int) -> set[int]:
    members = await session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == node_id))
    return {node_id, *members}


async def league_partners(session: AsyncSession, polity_id: int) -> set[int]:
    member = (LeagueMemberRow.polity_entity_id == polity_id, LeagueMemberRow.standing == LeagueStanding.MEMBER)
    leagues = select(LeagueMemberRow.league_entity_id).where(*member)
    query = select(LeagueMemberRow.polity_entity_id).where(LeagueMemberRow.league_entity_id.in_(leagues), LeagueMemberRow.standing == LeagueStanding.MEMBER)
    return {partner for partner in await session.scalars(query) if partner != polity_id}


async def rivals_of(session: AsyncSession, holder_id: int) -> set[int]:
    found: set[int] = set()
    for bond in await active_bonds(session, [BondKind.ENEMY], sources=[holder_id]):
        found.add(bond.target_node_id)
    for bond in await active_bonds(session, [BondKind.ENEMY], targets=[holder_id]):
        found.add(bond.source_node_id)
    found.discard(holder_id)
    return found
