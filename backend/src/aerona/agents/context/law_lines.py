from sqlalchemy import select

from aerona.agents.context.scope import Scope
from aerona.catalog.law_depth import COURT_TEXT, MOTIVE_TEXT, REGISTRY_TEXT, SYSTEM_TEXT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import AppealRow, JurisdictionRow, LegalSystemRow, OutlawRow, PrisonerRow, PrisonRow, RegistryRow
from aerona.db.tables.military import SpyAgentRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.domain.enums.military import AgentStatus
from aerona.domain.enums.polity import OfficeKind


async def realm_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    realm = (
        await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == me.location_id).limit(1))
        if me.location_id
        else None
    )
    system = await session.get(LegalSystemRow, realm) if realm is not None else None
    if system is not None:
        found.append(f"your realm judges by {SYSTEM_TEXT[system.system]}")
    for claim in await session.scalars(select(JurisdictionRow).where(JurisdictionRow.holder_entity_id == realm).order_by(JurisdictionRow.claimant_entity_id)):
        claimant = await session.get(EntityRow, claim.claimant_entity_id)
        if claimant is not None:
            found.append(f"{claimant.name} claims {spoken(claim.claim)} courts in your realm ({claim.strength})")
    return found


async def own_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    jailed = await session.get(PrisonerRow, me.id)
    if jailed is not None:
        prison = await session.get(PrisonRow, jailed.prison_entity_id)
        state = f"; food {prison.food}, crowding {prison.crowding}" if prison is not None else ""
        found.append(f"imprisoned for {jailed.term} more epochs, rank {jailed.gang_rank} among its gangs{state}")
    outlaw = await session.get(OutlawRow, me.id)
    if outlaw is not None:
        found.append(
            f"outlawed, with a bounty of {outlaw.bounty + outlaw.private_bounty} on your head and renown {outlaw.renown} among the folk who shelter you"
        )
    for appeal in await session.scalars(
        select(AppealRow)
        .join(CrimeCaseRow, CrimeCaseRow.id == AppealRow.case_id)
        .where(CrimeCaseRow.accused_entity_id == me.id, AppealRow.decided_epoch.is_(None))
    ):
        found.append(f"your appeal waits before {COURT_TEXT[appeal.to_court]}")
    for deed in await session.scalars(
        select(RegistryRow).where((RegistryRow.owner_entity_id == me.id) | (RegistryRow.counterparty_entity_id == me.id)).order_by(RegistryRow.id)
    ):
        side = "owed to you" if deed.owner_entity_id == me.id else "owed by you"
        found.append(f"a registered {REGISTRY_TEXT[deed.kind]} of {deed.amount}, {side}")
    agent = await session.scalar(select(SpyAgentRow).where(SpyAgentRow.mortal_entity_id == me.id, SpyAgentRow.status == AgentStatus.ACTIVE).limit(1))
    if agent is not None:
        found.append(f"you spy {MOTIVE_TEXT[agent.motive]}, loyalty {agent.loyalty}")
    if await session.scalar(select(OfficeRow.id).where(OfficeRow.holder_entity_id == me.id, OfficeRow.kind == OfficeKind.SPYMASTER).limit(1)) is not None:
        found.append("as spymaster you may hunt for moles at court")
    return found


async def mortal_law_lines(scope: Scope, me: EntityRow) -> list[str]:
    return [*await realm_lines(scope, me), *await own_lines(scope, me)]
