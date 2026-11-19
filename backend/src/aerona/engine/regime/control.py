from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.regime import (
    BASE_FIELDS,
    BREEDING_FIELDS,
    CREDENTIAL_FIELDS,
    DISCIPLE_FIELDS,
    EXAM_FIELDS,
    FREEDOM_FIELDS,
    MEMBER_FIELDS,
    REGIME_FIELDS,
    SCHOOL_FIELDS,
    SEGMENT_FIELDS,
    SITTING_FIELDS,
    TIE_FIELDS,
    VENAL_FIELDS,
    AcademicFreedomRow,
    BreedingPlanRow,
    CoalitionMemberRow,
    CredentialRow,
    ExaminationRow,
    ExamSittingRow,
    LineageSegmentRow,
    PatronageTieRow,
    PowerBaseRow,
    RegimeRow,
    SchoolLineageRow,
    SchoolMemberRow,
    VenalOfficeRow,
)
from aerona.domain.enums.cycles import LongPlanKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.genetics import Locus
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.regime import ClientRole, CredentialKind, SegmentLevel
from aerona.engine.collective.control import of_type, saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists, put_values
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.recording.record import RoleValue, record
from aerona.engine.recording.record import record as record_incident
from aerona.engine.regime.learning import LearningTally, grant, hold_sitting
from aerona.engine.regime.patronage import PatronageTally, make_sinecure, measure_bases, sell_seat
from aerona.engine.regime.rule import RegimeTally, purge_member, regime_row

POLITIES = frozenset({EntityType.POLITY})
MORTALS = frozenset({EntityType.MORTAL})
HOUSES = frozenset({EntityType.HOUSE})
PEOPLES = frozenset({EntityType.PEOPLE})
STRUCTURES = frozenset({EntityType.STRUCTURE})
DOCTRINES = frozenset({EntityType.THEORY, EntityType.IDEOLOGY})
KEPT_SEATS = ("ruler", "heir_designate", "regent")


async def realm_for(ctx: TickContext, polity_id: int) -> tuple[RealmBook, Realm]:
    await of_type(ctx, polity_id, POLITIES, "a realm")
    book = await RealmBook.load(ctx.session)
    realm = book.realms.get(polity_id)
    if realm is None:
        raise ValidationFailedError("That realm keeps no court.")
    return book, realm


async def set_regime(ctx: TickContext, polity_id: int, values: Values) -> RegimeRow:
    _, realm = await realm_for(ctx, polity_id)
    row = await regime_row(ctx, realm, RegimeTally())
    return await put_values(ctx, row, values, REGIME_FIELDS, "regime")


async def enrol(ctx: TickContext, polity_id: int, mortal_id: int, values: Values) -> CoalitionMemberRow:
    await of_type(ctx, polity_id, POLITIES, "a realm")
    await of_type(ctx, mortal_id, MORTALS, "a mortal")
    row = await ctx.session.get(CoalitionMemberRow, (polity_id, mortal_id))
    if row is None:
        row = await saved(ctx, CoalitionMemberRow(polity_entity_id=polity_id, mortal_entity_id=mortal_id, since_epoch=ctx.epoch, locked=[]))
    return await put_values(ctx, row, values, MEMBER_FIELDS, "coalition member")


async def purge(ctx: TickContext, polity_id: int, mortal_id: int) -> int:
    _, realm = await realm_for(ctx, polity_id)
    member = await found(ctx, CoalitionMemberRow, (polity_id, mortal_id), "coalition member")
    return await purge_member(ctx, realm, member, RegimeTally())


async def bind_client(ctx: TickContext, patron_id: int, client_id: int, role: ClientRole, strength: int) -> PatronageTieRow:
    await node_exists(ctx, patron_id, "patron")
    await of_type(ctx, client_id, MORTALS, "a mortal")
    if patron_id == client_id:
        raise ValidationFailedError("No one is their own client.")
    row = PatronageTieRow(
        patron_node_id=patron_id, client_entity_id=client_id, role=role, strength=max(0, min(PERCENT, strength)), since_epoch=ctx.epoch, locked=[]
    )
    return await saved(ctx, row)


async def seat_of(ctx: TickContext, office_id: int) -> tuple[OfficeRow, Realm]:
    office = await found(ctx, OfficeRow, office_id, "office")
    if office.kind.value in KEPT_SEATS:
        raise ValidationFailedError("The office of ruler, its heir and its regent are not for sale.")
    _, realm = await realm_for(ctx, office.polity_entity_id)
    return office, realm


async def sell(ctx: TickContext, office_id: int, buyer_id: int, price: int) -> VenalOfficeRow:
    office, realm = await seat_of(ctx, office_id)
    buyer = await of_type(ctx, buyer_id, MORTALS, "a mortal")
    venal = await sell_seat(ctx, realm, office, price=max(0, price), tally=PatronageTally(), buyer=buyer)
    if venal is None:
        raise ValidationFailedError(f"{buyer.name} cannot pay {price} for the seat.")
    return venal


async def sinecure(ctx: TickContext, office_id: int, holder_id: int) -> VenalOfficeRow:
    office, realm = await seat_of(ctx, office_id)
    holder = await of_type(ctx, holder_id, MORTALS, "a mortal")
    member = await ctx.session.get(CoalitionMemberRow, (office.polity_entity_id, holder_id))
    return await make_sinecure(ctx, realm, office, holder, member=member, tally=PatronageTally())


async def weigh_base(ctx: TickContext, polity_id: int) -> int:
    book, realm = await realm_for(ctx, polity_id)
    row = await regime_row(ctx, realm, RegimeTally())
    await measure_bases(ctx, book, realm, row, PatronageTally())
    await ctx.session.flush()
    return polity_id


async def set_base(ctx: TickContext, mortal_id: int, polity_id: int, values: Values) -> PowerBaseRow:
    await of_type(ctx, mortal_id, MORTALS, "a mortal")
    await of_type(ctx, polity_id, POLITIES, "a realm")
    row = await ctx.session.get(PowerBaseRow, mortal_id)
    if row is None:
        row = await saved(ctx, PowerBaseRow(mortal_entity_id=mortal_id, polity_entity_id=polity_id, updated_epoch=ctx.epoch, locked=[]))
    row.polity_entity_id = polity_id
    return await put_values(ctx, row, values, BASE_FIELDS, "power base")


async def set_segment(ctx: TickContext, house_id: int, level: SegmentLevel, tribe_id: int | None) -> LineageSegmentRow:
    await of_type(ctx, house_id, HOUSES, "a house")
    if tribe_id is not None:
        await of_type(ctx, tribe_id, PEOPLES, "a people")
    row = await ctx.session.get(LineageSegmentRow, house_id)
    if row is None:
        row = await saved(ctx, LineageSegmentRow(house_entity_id=house_id, since_epoch=ctx.epoch, locked=[]))
    return await put_values(ctx, row, {"level": level.value, "tribe_entity_id": tribe_id}, SEGMENT_FIELDS, "lineage")


async def new_breeding(
    ctx: TickContext,
    holder_id: int,
    house_id: int,
    name: str,
    *,
    locus: str | None,
    allele: str | None,
    claim_polity_id: int | None,
    target_share: int,
    steps: int,
) -> BreedingPlanRow:
    await node_exists(ctx, holder_id, "holder")
    await of_type(ctx, house_id, HOUSES, "a house")
    if claim_polity_id is not None:
        await of_type(ctx, claim_polity_id, POLITIES, "a realm")
    if (locus is None or allele is None) and claim_polity_id is None:
        raise ValidationFailedError("Name the gift to breed for, or the realm whose claim the matches should join.")
    plan = await saved(
        ctx,
        LongPlanRow(
            holder_node_id=holder_id,
            author_node_id=holder_id,
            target_node_id=house_id,
            kind=LongPlanKind.BLOODLINE,
            name=name,
            steps=max(1, steps),
            progress=0,
            step_cost=0,
            secrecy=60,
            started_epoch=ctx.epoch,
            locked=[],
        ),
    )
    row = await saved(
        ctx,
        BreedingPlanRow(
            plan_id=plan.id,
            house_entity_id=house_id,
            locus=locus,
            allele=allele,
            claim_polity_id=claim_polity_id,
            target_share=max(1, min(PERCENT, target_share)),
            locked=[],
        ),
    )
    roles: dict[IncidentRole, RoleValue] = {IncidentRole.SUBJECT: house_id, IncidentRole.AUTHORITY: holder_id}
    await record(
        ctx,
        "breeding.begun",
        roles=roles,
        facts={"plan_name": name, "locus": next((item for item in Locus if item.value == locus), None), "target_share": row.target_share},
    )
    return row


async def set_examinations(ctx: TickContext, polity_id: int, values: Values) -> ExaminationRow:
    await of_type(ctx, polity_id, POLITIES, "a realm")
    row = await ctx.session.get(ExaminationRow, polity_id)
    if row is None:
        row = await saved(ctx, ExaminationRow(polity_entity_id=polity_id, locked=[]))
    return await put_values(ctx, row, values, EXAM_FIELDS, "examination")


async def sit_now(ctx: TickContext, polity_id: int) -> ExamSittingRow:
    book, realm = await realm_for(ctx, polity_id)
    row = await set_examinations(ctx, polity_id, {})
    return await hold_sitting(ctx, book, realm, row, LearningTally())


async def confer(ctx: TickContext, mortal_id: int, kind: CredentialKind, granter_id: int | None, skill: SkillKind | None) -> CredentialRow:
    mortal = await of_type(ctx, mortal_id, MORTALS, "a mortal")
    if granter_id is not None:
        await node_exists(ctx, granter_id, "granter")
    return await grant(ctx, mortal, kind, granter_id=granter_id, skill=skill, tally=LearningTally())


async def set_freedom(ctx: TickContext, structure_id: int, values: Values) -> AcademicFreedomRow:
    await of_type(ctx, structure_id, STRUCTURES, "a house of learning")
    row = await ctx.session.get(AcademicFreedomRow, structure_id)
    if row is None:
        row = await saved(ctx, AcademicFreedomRow(structure_entity_id=structure_id, updated_epoch=ctx.epoch, locked=[]))
    row = await put_values(ctx, row, values, FREEDOM_FIELDS, "freedom of learning")
    return settle_freedom(ctx, row, values)


def settle_freedom(ctx: TickContext, row: AcademicFreedomRow, values: Values) -> AcademicFreedomRow:
    if "level" in values and "suppressed" not in values:
        row.suppressed = row.level < ctx.rules.academic_freedom.suppress_at
    return row


async def found_school(ctx: TickContext, founder_id: int, name: str, doctrine_id: int | None) -> SchoolLineageRow:
    founder: EntityRow = await of_type(ctx, founder_id, MORTALS, "a mortal")
    if doctrine_id is not None:
        await of_type(ctx, doctrine_id, DOCTRINES, "a theory or ideology")
    school = await saved(ctx, SchoolLineageRow(name=name, doctrine_entity_id=doctrine_id, founder_entity_id=founder.id, since_epoch=ctx.epoch, locked=[]))
    await saved(ctx, SchoolMemberRow(school_id=school.id, mortal_entity_id=founder.id, generation=0, since_epoch=ctx.epoch, locked=[]))
    await record_incident(ctx, "schools.founded", roles={IncidentRole.TEACHER: founder.id, IncidentRole.LEARNER: []}, facts={"school": name, "disciples": 0})
    return school


async def admit(ctx: TickContext, school_id: int, mortal_id: int, master_id: int | None) -> SchoolMemberRow:
    await found(ctx, SchoolLineageRow, school_id, "school")
    await of_type(ctx, mortal_id, MORTALS, "a mortal")
    master = await ctx.session.get(SchoolMemberRow, (school_id, master_id)) if master_id is not None else None
    if master_id is not None and master is None:
        raise ValidationFailedError("A master must belong to the school.")
    row = await ctx.session.get(SchoolMemberRow, (school_id, mortal_id))
    if row is None:
        row = SchoolMemberRow(school_id=school_id, mortal_entity_id=mortal_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.master_entity_id = master_id
    row.generation = master.generation + 1 if master is not None else 0
    await ctx.session.flush()
    return row


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "regime": (RegimeRow, REGIME_FIELDS, "regime"),
    "coalition_member": (CoalitionMemberRow, MEMBER_FIELDS, "coalition member"),
    "patronage": (PatronageTieRow, TIE_FIELDS, "patronage tie"),
    "venal_office": (VenalOfficeRow, VENAL_FIELDS, "bought office"),
    "power_base": (PowerBaseRow, BASE_FIELDS, "power base"),
    "lineage": (LineageSegmentRow, SEGMENT_FIELDS, "lineage"),
    "breeding": (BreedingPlanRow, BREEDING_FIELDS, "breeding plan"),
    "examination": (ExaminationRow, EXAM_FIELDS, "examination"),
    "exam_sitting": (ExamSittingRow, SITTING_FIELDS, "sitting"),
    "credential": (CredentialRow, CREDENTIAL_FIELDS, "credential"),
    "academic_freedom": (AcademicFreedomRow, FREEDOM_FIELDS, "freedom of learning"),
    "school": (SchoolLineageRow, SCHOOL_FIELDS, "school"),
    "disciple": (SchoolMemberRow, DISCIPLE_FIELDS, "disciple"),
}


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    if isinstance(row, AcademicFreedomRow):
        settle_freedom(ctx, row, values)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    await ctx.session.delete(await found(ctx, table, key, label))
    await ctx.session.flush()
