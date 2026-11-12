from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import HouseProfileRow, OfficeRow
from aerona.db.tables.regime import CoalitionMemberRow, ExaminationRow, PatronageTieRow, RegimeRow, SchoolLineageRow, SchoolMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.regime import ClientRole, CredentialKind
from aerona.engine.primitives.queries import living_entity
from aerona.engine.regime import control
from aerona.engine.regime.book import realm_seat
from aerona.engine.regime.learning import EXAMINED, best_skill, holds
from aerona.engine.regime.patronage import SEATS_KEPT
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.cycles import ruled_realm

NAME = 200
CLIENT_STRENGTH = 30
PLAN_STEPS = 100


class SeekPatronInput(ToolInput):
    patron_id: int


class BuyOfficeInput(ToolInput):
    office_id: int


class SitExaminationInput(ToolInput):
    pass


class JoinSchoolInput(ToolInput):
    school_id: int


class PurgeCircleInput(ToolInput):
    mortal_id: int


class GuardThroneInput(ToolInput):
    rotation: bool = False
    parallel_guard: bool = False
    loyalty_promotion: bool = False
    hostages: bool = False


class SteerMarriagesInput(ToolInput):
    name: str = Field(min_length=1, max_length=NAME)
    locus: str | None = Field(default=None, max_length=NAME)
    allele: str | None = Field(default=None, max_length=NAME)
    claim_polity_id: int | None = None
    target_share: int = Field(default=60, ge=1, le=PERCENT)
    steps: int = Field(default=10, ge=1, le=PLAN_STEPS)


async def seek_patron(call: MortalCall, args: SeekPatronInput) -> str:
    patron = await living_entity(call.session, args.patron_id)
    if patron is None or patron.id == call.me.id:
        fail(MortalResult.PATRON_REFUSED, why="there is no such patron")
    if held(patron.id):
        fail(MortalResult.PATRON_REFUSED, why="a stronger hand holds them")
    known = await call.session.scalar(
        select(PatronageTieRow.id).where(PatronageTieRow.patron_node_id == patron.id, PatronageTieRow.client_entity_id == call.me.id).limit(1)
    )
    if known is not None:
        fail(MortalResult.PATRON_REFUSED, why="you already serve them")
    await control.bind_client(call.tick, patron.id, call.me.id, ClientRole.RETAINER, CLIENT_STRENGTH)
    call.target(patron.id)
    await call.chronicle(ChronicleKind.WORLD, lines.SEEK_PATRON, entity_ids=[call.me.id, patron.id], me=call.me.name, patron=patron.name)
    return result(MortalResult.PATRON_FOUND, name=patron.name)


async def buy_office(call: MortalCall, args: BuyOfficeInput) -> str:
    office = await call.session.get(OfficeRow, args.office_id)
    if office is None or office.kind in SEATS_KEPT:
        fail(MortalResult.OFFICE_REFUSED, why="that seat is not for sale")
    if office.holder_entity_id is not None:
        fail(MortalResult.OFFICE_REFUSED, why="someone already holds that seat")
    if await realm_seat(call.session, call.me.location_id) != office.polity_entity_id:
        fail(MortalResult.OFFICE_REFUSED, why="that seat belongs to another realm")
    price = call.tick.rules.venality.base_price
    try:
        await control.sell(call.tick, office.id, call.me.id, price)
    except ValidationFailedError as error:
        fail(MortalResult.OFFICE_REFUSED, why=str(error).rstrip("."))
    call.target(office.polity_entity_id)
    seat = office.kind.value.replace("_", " ")
    await call.chronicle(ChronicleKind.WORLD, lines.BUY_OFFICE, entity_ids=[call.me.id, office.polity_entity_id], me=call.me.name, seat=seat)
    return result(MortalResult.OFFICE_BOUGHT, seat=seat, price=price)


async def sit_examination(call: MortalCall, args: SitExaminationInput) -> str:
    realm_id = await realm_seat(call.session, call.me.location_id)
    if realm_id is None or await call.session.get(ExaminationRow, realm_id) is None:
        fail(MortalResult.EXAM_REFUSED, why="your realm holds no examinations")
    if await holds(call.tick, call.me.id, CredentialKind.EXAMINATION):
        fail(MortalResult.EXAM_REFUSED, why="you have already passed")
    best = await best_skill(call.tick, call.me.id, EXAMINED)
    if best is None or best[1] < call.tick.rules.examinations.skill_mark:
        fail(MortalResult.EXAM_REFUSED, why="your learning in law, letters and lore falls short of the mark")
    await control.confer(call.tick, call.me.id, CredentialKind.EXAMINATION, realm_id, best[0])
    call.target(realm_id)
    await call.chronicle(ChronicleKind.WORLD, lines.SIT_EXAMINATION, entity_ids=[call.me.id, realm_id], me=call.me.name)
    return result(MortalResult.EXAM_PASSED, skill=best[0].value)


async def join_school(call: MortalCall, args: JoinSchoolInput) -> str:
    school = await call.session.get(SchoolLineageRow, args.school_id)
    if school is None:
        fail(MortalResult.SCHOOL_JOIN_REFUSED, why="there is no such school")
    if await call.session.get(SchoolMemberRow, (school.id, call.me.id)) is not None:
        fail(MortalResult.SCHOOL_JOIN_REFUSED, why="you already belong to it")
    master = school.founder_entity_id if school.founder_entity_id is not None and await living_entity(call.session, school.founder_entity_id) else None
    if master is not None and await call.session.get(SchoolMemberRow, (school.id, master)) is None:
        master = None
    await control.admit(call.tick, school.id, call.me.id, master)
    await call.chronicle(ChronicleKind.WORLD, lines.JOIN_SCHOOL, entity_ids=[call.me.id], me=call.me.name, school=school.name)
    return result(MortalResult.SCHOOL_JOINED, name=school.name)


async def purge_circle(call: MortalCall, args: PurgeCircleInput) -> str:
    realm = await ruled_realm(call)
    if realm is None:
        fail(MortalResult.PURGE_REFUSED, why="you rule no realm")
    member = await call.session.get(CoalitionMemberRow, (realm.id, args.mortal_id))
    victim = await call.session.get(EntityRow, args.mortal_id)
    if member is None or victim is None:
        fail(MortalResult.PURGE_REFUSED, why="they are not of your ruling circle")
    if held(victim.id):
        fail(MortalResult.PURGE_REFUSED, why="a stronger hand holds them")
    await control.purge(call.tick, realm.id, victim.id)
    call.target(realm.id)
    await call.chronicle(ChronicleKind.WORLD, lines.PURGE_CIRCLE, entity_ids=[call.me.id, victim.id], me=call.me.name, victim=victim.name)
    return result(MortalResult.CIRCLE_PURGED, name=victim.name)


async def guard_throne(call: MortalCall, args: GuardThroneInput) -> str:
    realm = await ruled_realm(call)
    if realm is None or held(realm.id):
        fail(MortalResult.GUARD_REFUSED, why="you rule no realm")
    values = {"rotation": args.rotation, "parallel_guard": args.parallel_guard, "loyalty_promotion": args.loyalty_promotion, "hostages": args.hostages}
    row: RegimeRow = await control.set_regime(call.tick, realm.id, values)
    taken = [name.replace("_", " ") for name, value in values.items() if value]
    call.target(realm.id)
    await call.chronicle(ChronicleKind.WORLD, lines.GUARD_THRONE, entity_ids=[call.me.id, realm.id], me=call.me.name, realm=realm.name)
    return result(MortalResult.THRONE_GUARDED, measures=", ".join(taken) if taken else "none", loyalty=row.coalition_loyalty)


async def steer_marriages(call: MortalCall, args: SteerMarriagesInput) -> str:
    house_id = await call.session.scalar(select(HouseProfileRow.house_entity_id).where(HouseProfileRow.head_entity_id == call.me.id).limit(1))
    if house_id is None or held(house_id):
        fail(MortalResult.MARRIAGES_REFUSED, why="you head no house")
    try:
        plan = await control.new_breeding(
            call.tick,
            call.me.id,
            house_id,
            args.name,
            locus=args.locus,
            allele=args.allele,
            claim_polity_id=args.claim_polity_id,
            target_share=args.target_share,
            steps=args.steps,
        )
    except ValidationFailedError as error:
        fail(MortalResult.MARRIAGES_REFUSED, why=str(error).rstrip("."))
    call.target(house_id)
    await call.chronicle(ChronicleKind.WORLD, lines.STEER_MARRIAGES, entity_ids=[call.me.id, house_id], me=call.me.name, plan=args.name)
    return result(MortalResult.MARRIAGES_STEERED, name=args.name, id=plan.plan_id)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.SEEK_PATRON, mortal, SeekPatronInput, meta, seek_patron),
        ToolSpec(MortalToolId.BUY_OFFICE, mortal, BuyOfficeInput, meta, buy_office),
        ToolSpec(MortalToolId.SIT_EXAMINATION, mortal, SitExaminationInput, meta, sit_examination),
        ToolSpec(MortalToolId.JOIN_SCHOOL, mortal, JoinSchoolInput, meta, join_school),
        ToolSpec(MortalToolId.PURGE_CIRCLE, mortal, PurgeCircleInput, meta, purge_circle),
        ToolSpec(MortalToolId.GUARD_THRONE, mortal, GuardThroneInput, meta, guard_throne),
        ToolSpec(MortalToolId.STEER_MARRIAGES, mortal, SteerMarriagesInput, meta, steer_marriages),
    ]
