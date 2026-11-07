from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.intrigue import name_of
from aerona.db.tables.affairs import CouncilSeatRow, CourtPositionRow, CourtRow, MandateRow, NobleDemandRow, ResolutionRow, TaxPolicyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow, VassalageRow
from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow, DiplomacyProfileRow, PolityRegardRow, SphereRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.statecraft import CrisisState, MandateState, ResolutionState
from aerona.engine.polity.crises import DEMAND_TEXT

SHOWN = 3


async def seat_of(session: AsyncSession, me: EntityRow) -> int | None:
    found: int | None = await session.scalar(select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == me.id).order_by(OfficeRow.id).limit(1))
    return found


async def crisis_lines(session: AsyncSession, realm: int) -> list[str]:
    found: list[str] = []
    backed = select(CrisisBackerRow.crisis_id).where(CrisisBackerRow.backer_entity_id == realm)
    rows = await session.scalars(
        select(CrisisRow)
        .where(
            CrisisRow.state == CrisisState.ESCALATING,
            or_(CrisisRow.demander_entity_id == realm, CrisisRow.target_entity_id == realm, CrisisRow.id.in_(backed)),
        )
        .order_by(CrisisRow.id)
    )
    for row in rows:
        demander, target = await name_of(session, row.demander_entity_id), await name_of(session, row.target_entity_id)
        found.append(f"crisis #{row.id}: {demander} demands that {target} {DEMAND_TEXT[row.demand]}, at step {row.escalation}")
    return found


async def statecraft_lines(session: AsyncSession, me: EntityRow) -> list[str]:
    realm = await seat_of(session, me)
    if realm is None:
        return []
    found = await crisis_lines(session, realm)
    feared = await session.scalars(
        select(PolityRegardRow).where(PolityRegardRow.subject_entity_id == realm, PolityRegardRow.threat > 0).order_by(PolityRegardRow.threat.desc())
    )
    for row in list(feared)[:SHOWN]:
        found.append(f"{await name_of(session, row.holder_entity_id)} feels threat {row.threat} and trust {row.trust} toward your realm")
    felt = await session.scalars(
        select(PolityRegardRow).where(PolityRegardRow.holder_entity_id == realm, PolityRegardRow.threat > 0).order_by(PolityRegardRow.threat.desc())
    )
    for row in list(felt)[:SHOWN]:
        found.append(f"your realm feels threat {row.threat} from {await name_of(session, row.subject_entity_id)}")
    for subject in await session.scalars(select(VassalageRow).where(or_(VassalageRow.vassal_entity_id == realm, VassalageRow.overlord_entity_id == realm))):
        kind = subject.kind.value.replace("_", " ")
        if subject.vassal_entity_id == realm:
            found.append(f"your realm is a {kind} of {await name_of(session, subject.overlord_entity_id)}, wishing for liberty {subject.liberty}")
        else:
            found.append(f"{await name_of(session, subject.vassal_entity_id)} is your {kind}, wishing for liberty {subject.liberty}")
    for sphere in await session.scalars(select(SphereRow).where(or_(SphereRow.power_entity_id == realm, SphereRow.client_entity_id == realm))):
        if sphere.power_entity_id == realm:
            found.append(f"{await name_of(session, sphere.client_entity_id)} lies in your sphere at strength {sphere.strength}")
        else:
            found.append(f"your realm lies in the sphere of {await name_of(session, sphere.power_entity_id)}")
    diplomacy = await session.get(DiplomacyProfileRow, realm)
    if diplomacy is not None:
        found.append(f"your realm keeps {diplomacy.relations} relations of a capacity of {diplomacy.capacity}")
    return found


async def affairs_lines(session: AsyncSession, me: EntityRow) -> list[str]:
    found: list[str] = []
    for demand in await session.scalars(select(NobleDemandRow).where(NobleDemandRow.mortal_entity_id == me.id)):
        state = "met" if demand.met else f"unmet since epoch {demand.since_epoch}"
        found.append(f"you demand {demand.want.value.replace('_', ' ')} of your ruler, {state}")
    realm = await seat_of(session, me)
    if realm is None:
        return found
    profile = await session.get(PolityProfileRow, realm)
    if profile is not None:
        found.append(f"corruption in your realm stands at {profile.corruption}")
    for office in await session.scalars(select(OfficeRow).where(OfficeRow.polity_entity_id == realm, OfficeRow.task.is_not(None)).order_by(OfficeRow.id)):
        task = office.task.value.replace("_", " ") if office.task else "nothing"
        found.append(f"office #{office.id} ({office.kind.value.replace('_', ' ')}) works at {task}, diligence {office.diligence}")
    for tax in await session.scalars(select(TaxPolicyRow).where(TaxPolicyRow.polity_entity_id == realm, TaxPolicyRow.rate > 0).order_by(TaxPolicyRow.kind)):
        farmed = ", farmed out" if tax.farmed else ""
        found.append(f"the {tax.kind.value} tax stands at {tax.rate}{farmed}, bringing {tax.take}")
    for mandate in await session.scalars(
        select(MandateRow).where(MandateRow.polity_entity_id == realm, MandateRow.state == MandateState.ACTIVE).order_by(MandateRow.id)
    ):
        found.append(f"a {mandate.kind.value.replace('_', ' ')} mandate stands until epoch {mandate.until_epoch}")
    for seat in await session.scalars(select(CouncilSeatRow).where(CouncilSeatRow.polity_entity_id == realm).order_by(CouncilSeatRow.seats.desc())):
        found.append(f"{await name_of(session, seat.holder_node_id)} holds {seat.seats} council seats")
    court = await session.get(CourtRow, realm)
    if court is not None:
        found.append(f"your court shines at grandeur {court.grandeur} with {court.courtiers} courtiers")
    for position in await session.scalars(
        select(CourtPositionRow).where(CourtPositionRow.polity_entity_id == realm, CourtPositionRow.holder_entity_id.is_not(None))
    ):
        found.append(f"{await name_of(session, position.holder_entity_id)} serves as {position.position.value.replace('_', ' ')}")
    core = profile.core_entity_id if profile is not None else None
    joined = select(BondRow.target_node_id).where(BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE, BondRow.source_node_id == core)
    for resolution in await session.scalars(
        select(ResolutionRow).where(ResolutionRow.assembly_entity_id.in_(joined), ResolutionRow.state == ResolutionState.PASSED).order_by(ResolutionRow.id)
    ):
        target = f" against {await name_of(session, resolution.target_node_id)}" if resolution.target_node_id is not None else ""
        found.append(f"your assembly binds you to a {resolution.kind.value.replace('_', ' ')}{target} until epoch {resolution.until_epoch}")
    return found
