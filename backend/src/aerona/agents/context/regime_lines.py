from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.core.grammar import an
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.regime import (
    AcademicFreedomRow,
    CoalitionMemberRow,
    CredentialRow,
    ExaminationRow,
    PatronageTieRow,
    PowerBaseRow,
    RegimeRow,
    SchoolLineageRow,
    SchoolMemberRow,
)
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.regime import PowerStance, Routinisation
from aerona.engine.primitives.records import definite
from aerona.engine.regime.book import dominant, realm_seat
from aerona.engine.regime.patronage import SEATS_KEPT

TIE_LINES = 4
SEAT_LINES = 3
REALM_LINES = 3


async def tie_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    for tie in await scope.session.scalars(
        select(PatronageTieRow)
        .where(or_(PatronageTieRow.patron_node_id == me.id, PatronageTieRow.client_entity_id == me.id))
        .order_by(PatronageTieRow.strength.desc(), PatronageTieRow.id)
        .limit(TIE_LINES)
    ):
        if tie.client_entity_id == me.id:
            found.append(f"your patron is {await named(scope, tie.patron_node_id)}, whom you serve as {an(words(tie.role.value))} client, tie {tie.strength}")
        else:
            found.append(
                f"{await named(scope, tie.client_entity_id)} (mortal {tie.client_entity_id}) is your {words(tie.role.value)} client, tie {tie.strength}"
            )
    return found


async def standing_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for credential in await session.scalars(select(CredentialRow).where(CredentialRow.mortal_entity_id == me.id).order_by(CredentialRow.id)):
        found.append(f"you hold the credential of {words(credential.kind.value)}")
    base = await session.get(PowerBaseRow, me.id)
    if base is not None:
        found.append(f"your power base weighs {base.total}, a threat of {base.threat} to the ruler; you stand {words(base.stance.value)}")
    for member in await session.scalars(select(CoalitionMemberRow).where(CoalitionMemberRow.mortal_entity_id == me.id)):
        found.append(f"you sit in the ruling circle of {await named(scope, member.polity_entity_id)}, reward {member.reward}, loyalty {member.loyalty}")
    for membership in await session.scalars(select(SchoolMemberRow).where(SchoolMemberRow.mortal_entity_id == me.id)):
        school = await session.get(SchoolLineageRow, membership.school_id)
        if school is not None:
            master = f", taught by {await named(scope, membership.master_entity_id)}" if membership.master_entity_id is not None else ""
            found.append(f"you belong to {definite(school.name)} (school {school.id}){master}")
    return found


async def realm_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    realm_id = await realm_seat(session, me.location_id)
    regime = await session.get(RegimeRow, realm_id) if realm_id is not None else None
    if realm_id is None or regime is None:
        return []
    found = [
        f"your realm is chosen by its {words(regime.selectorate.value)} ({regime.coalition_size} of {regime.selectorate_size} in the winning circle), "
        f"spends {regime.public_share}% on public goods, rests on {words(dominant(regime).value)} legitimacy, its ruler's time horizon {regime.horizon}"
    ]
    if await session.get(ExaminationRow, realm_id) is not None:
        found.append("your realm chooses its officials by examination")
    seats = await session.scalars(
        select(OfficeRow).where(OfficeRow.polity_entity_id == realm_id, OfficeRow.holder_entity_id.is_(None)).order_by(OfficeRow.id).limit(SEAT_LINES)
    )
    for seat in seats:
        if seat.kind not in SEATS_KEPT:
            found.append(f"the seat of {words(seat.kind.value)} (office {seat.id}) stands empty")
    return found


async def throne_lines(scope: Scope, me: EntityRow) -> list[str]:
    realm_id = await scope.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == me.id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    if realm_id is None:
        return []
    found: list[str] = []
    for base in await scope.session.scalars(
        select(PowerBaseRow)
        .where(PowerBaseRow.polity_entity_id == realm_id, PowerBaseRow.stance != PowerStance.LOYAL)
        .order_by(PowerBaseRow.threat.desc(), PowerBaseRow.mortal_entity_id)
        .limit(TIE_LINES)
    ):
        found.append(
            f"{await named(scope, base.mortal_entity_id)} (mortal {base.mortal_entity_id}) stands {words(base.stance.value)} "
            f"toward your rule, threat {base.threat}"
        )
    return found


async def mortal_regime_lines(scope: Scope, me: EntityRow) -> list[str]:
    return [*await tie_lines(scope, me), *await standing_lines(scope, me), *await realm_lines(scope, me), *await throne_lines(scope, me)]


async def son_regime_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    session = scope.session
    found: list[str] = []
    for regime, realm in await session.execute(
        select(RegimeRow, EntityRow)
        .join(EntityRow, EntityRow.id == RegimeRow.polity_entity_id)
        .where(EntityRow.world_id == son.current_world_id, RegimeRow.routinisation.in_([Routinisation.PENDING, Routinisation.SCHISM]))
        .order_by(RegimeRow.polity_entity_id)
        .limit(REALM_LINES)
    ):
        found.append(f"realm {realm.name} (polity {realm.id}) is torn over its founder's legacy: {words(regime.routinisation.value)}")
    for freedom, house in await session.execute(
        select(AcademicFreedomRow, EntityRow)
        .join(EntityRow, EntityRow.id == AcademicFreedomRow.structure_entity_id)
        .where(EntityRow.world_id == son.current_world_id, AcademicFreedomRow.suppressed.is_(True))
        .order_by(AcademicFreedomRow.level, AcademicFreedomRow.structure_entity_id)
        .limit(REALM_LINES)
    ):
        found.append(f"learning is suppressed at {house.name} (structure {house.id}), freedom {freedom.level}")
    for base, subject in await session.execute(
        select(PowerBaseRow, EntityRow)
        .join(EntityRow, EntityRow.id == PowerBaseRow.mortal_entity_id)
        .where(EntityRow.world_id == son.current_world_id, PowerBaseRow.stance == PowerStance.PLOTTING)
        .order_by(PowerBaseRow.threat.desc(), PowerBaseRow.mortal_entity_id)
        .limit(REALM_LINES)
    ):
        found.append(f"{subject.name} (mortal {subject.id}) plots to take power in {await named(scope, base.polity_entity_id)}, threat {base.threat}")
    return found
