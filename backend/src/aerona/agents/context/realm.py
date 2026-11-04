from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.laws import law_effect
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionGoalRow, FactionMembershipRow, FactionProfileRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.polity import (
    ClaimRow,
    LawJurisdictionRow,
    LawProfileRow,
    OfficeRow,
    PolityProfileRow,
    TreatyClauseRow,
    TreatyPartyRow,
    TreatyProfileRow,
)
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.polity import OfficeKind, TreatyStatus


def words(value: str) -> str:
    return value.replace("_", " ")


@dataclass
class StatecraftLines:
    treaties: list[str] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)
    succession: str = ""
    laws: list[str] = field(default_factory=list)
    factions: list[str] = field(default_factory=list)


async def name_of(session: AsyncSession, node_id: int | None) -> str:
    entity = await session.get(EntityRow, node_id) if node_id is not None else None
    return entity.name if entity is not None else "someone"


async def treaty_lines(session: AsyncSession, parties: list[int]) -> list[str]:
    found: list[str] = []
    rows = await session.scalars(
        select(TreatyProfileRow)
        .join(TreatyPartyRow, TreatyPartyRow.treaty_entity_id == TreatyProfileRow.treaty_entity_id)
        .where(TreatyPartyRow.party_node_id.in_(parties), TreatyProfileRow.status == TreatyStatus.IN_FORCE)
        .order_by(TreatyProfileRow.treaty_entity_id)
    )
    for profile in dict.fromkeys(rows):
        treaty = await session.get(EntityRow, profile.treaty_entity_id)
        clauses = []
        for clause in await session.scalars(
            select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == profile.treaty_entity_id).order_by(TreatyClauseRow.id)
        ):
            terms = ", ".join(f"{words(key)} {value}" for key, value in clause.params.items() if key != "misread")
            who = f"{await name_of(session, clause.obligor_node_id)} owes {await name_of(session, clause.beneficiary_node_id)}"
            clauses.append(f"{words(clause.kind.value)} ({who}{'; ' + terms if terms else ''})")
        until = f", until age {profile.until_epoch}" if profile.until_epoch is not None else ""
        found.append(f"{treaty.name if treaty is not None else 'a treaty'} [{words(profile.kind.value)}{until}]: {'; '.join(clauses) or 'no clauses'}")
    return found


async def statecraft(session: AsyncSession, me: EntityRow, home: EntityRow, realm_id: int | None) -> StatecraftLines:
    lines = StatecraftLines()
    parties = [home.id, *([realm_id] if realm_id is not None else [])]
    lines.treaties = await treaty_lines(session, parties)
    lines.factions = await faction_lines(session, me.id)
    claims = await session.scalars(
        select(ClaimRow).where(ClaimRow.ended_epoch.is_(None), (ClaimRow.claimant_entity_id == me.id) | (ClaimRow.polity_entity_id == (realm_id or -1)))
    )
    for claim in claims:
        claimant = await name_of(session, claim.claimant_entity_id)
        realm = await name_of(session, claim.polity_entity_id)
        pressed = ", pressed by war" if claim.pressed else ""
        lines.claims.append(f"{claimant} claims the {words(claim.office.value)} of {realm} by {words(claim.basis.value)} (strength {claim.strength}{pressed})")
    if realm_id is None:
        return lines
    ruler = await session.scalar(select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm_id, OfficeRow.kind == OfficeKind.RULER).limit(1))
    heir = await session.get(DesignatedHeirRow, ruler) if ruler is not None else None
    if ruler is not None:
        lines.succession = (
            f"{await name_of(session, ruler)} rules; the heir is {await name_of(session, heir.heir_entity_id) if heir is not None else 'not named'}"
        )
    laws = await session.scalars(
        select(LawProfileRow)
        .join(LawJurisdictionRow, LawJurisdictionRow.law_entity_id == LawProfileRow.law_entity_id)
        .join(EntityRow, EntityRow.id == LawProfileRow.law_entity_id)
        .where(LawJurisdictionRow.node_entity_id.in_(parties), EntityRow.status == EntityStatus.CANON)
        .order_by(LawProfileRow.law_entity_id)
    )
    for profile in laws:
        lines.laws.append(f"{words(profile.kind.value)}: {law_effect(profile.kind, dict(profile.params))} (enforced {profile.enforcement})")
    return lines


async def realm_overview(session: AsyncSession, world_id: int | None) -> list[str]:
    statement = (
        select(PolityProfileRow, EntityRow).join(EntityRow, EntityRow.id == PolityProfileRow.polity_entity_id).where(EntityRow.status == EntityStatus.CANON)
    )
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    found: list[str] = []
    for profile, realm in await session.execute(statement.order_by(EntityRow.id)):
        lines = await statecraft(session, realm, realm, realm.id)
        ruler = f"; {lines.succession}" if lines.succession else ""
        laws = f"; laws: {'; '.join(lines.laws)}" if lines.laws else ""
        treaties = f"; treaties: {'; '.join(lines.treaties)}" if lines.treaties else ""
        claims = f"; claims: {'; '.join(lines.claims)}" if lines.claims else ""
        found.append(
            f"realm#{realm.id} {realm.name} ({words(profile.government.value)}, tier {profile.tier}, legitimacy {profile.legitimacy}, "
            f"{words(profile.standing.value)}){ruler}{laws}{treaties}{claims}"
        )
    return found


async def faction_lines(session: AsyncSession, mortal_id: int) -> list[str]:
    found: list[str] = []
    for membership in await session.scalars(select(FactionMembershipRow).where(FactionMembershipRow.mortal_entity_id == mortal_id)):
        faction = await session.get(EntityRow, membership.faction_entity_id)
        profile = await session.get(FactionProfileRow, membership.faction_entity_id)
        if faction is None or profile is None or faction.status is not EntityStatus.CANON:
            continue
        goals = await session.scalars(
            select(FactionGoalRow)
            .where(FactionGoalRow.faction_entity_id == faction.id, FactionGoalRow.achieved_epoch.is_(None))
            .order_by(FactionGoalRow.priority.desc())
        )
        aims = [f"{words(goal.kind.value)} ({goal.progress}%)" for goal in goals]
        outlaw = ", outlawed" if profile.outlawed else ""
        found.append(
            f"you are a {membership.rank.value} of {faction.name} ({words(profile.kind.value)}{outlaw}; "
            f"treasury {profile.treasury}, cohesion {profile.cohesion})" + (f", striving to {', '.join(aims)}" if aims else "")
        )
    return found
