from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.catalog.grade_duties import GRADE_DUTIES
from aerona.catalog.naming import NAME_FORMS, NAMING_PATTERNS
from aerona.catalog.revivals import REVIVAL_GOALS, REVIVAL_WAYS
from aerona.core.grammar import spoken
from aerona.db.tables.customs import (
    AgeSetMemberRow,
    AgeSetRow,
    BodyMarkRow,
    GradeDutyRow,
    IntoxicantCustomRow,
    MembershipRow,
    NameFormRow,
    NamingCustomRow,
    RevivalRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.engine.body.customs import people_of
from aerona.engine.customs.relief import tavern_of

LIST_LINES = 3


async def mortal_customs_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    for mark in await session.scalars(select(BodyMarkRow).where(BodyMarkRow.holder_node_id == me.id).order_by(BodyMarkRow.id).limit(LIST_LINES)):
        found.append(f"a mark on your body: {spoken(mark.kind)}, meaning {spoken(mark.meaning)}")
    for form in await session.scalars(select(NameFormRow).where(NameFormRow.holder_node_id == me.id).order_by(NameFormRow.form).limit(LIST_LINES)):
        found.append(f"your {NAME_FORMS[form.form].label.lower()}: {form.name}")
    member = await session.get(AgeSetMemberRow, me.id)
    age_set = await session.get(AgeSetRow, member.age_set_id) if member is not None else None
    if age_set is not None:
        found.append(f"you belong to the {age_set.name}, in the grade of {spoken(age_set.grade)}")
    membership = await session.get(MembershipRow, me.id)
    if membership is not None:
        found.append(f"your standing in {await named(scope, membership.polity_entity_id)}: {spoken(membership.category)}")
    folk = await people_of(session, me)
    if folk is not None:
        for custom in await session.scalars(
            select(IntoxicantCustomRow).where(IntoxicantCustomRow.people_entity_id == folk.id).order_by(IntoxicantCustomRow.intoxicant).limit(LIST_LINES)
        ):
            found.append(f"your people take {spoken(custom.intoxicant)} at {spoken(custom.use)}")
        naming = await session.get(NamingCustomRow, folk.id)
        if naming is not None:
            found.append(f"how your people name: {NAMING_PATTERNS[naming.pattern].label.lower()}")
        for duty in await session.scalars(select(GradeDutyRow).where(GradeDutyRow.people_entity_id == folk.id).order_by(GradeDutyRow.duty)):
            found.append(f"among your people the grade of {spoken(duty.grade)} carries the duty of {GRADE_DUTIES[duty.duty].label.lower()}")
        revival = await session.scalar(select(RevivalRow).where(RevivalRow.people_entity_id == folk.id, RevivalRow.ended_epoch.is_(None)).limit(1))
        if revival is not None:
            way, goal = REVIVAL_WAYS[revival.way].label.lower(), REVIVAL_GOALS[revival.goal]
            stage = spoken(revival.stage)
            found.append(f"a movement among your people seeks to {goal.label.lower()} by the way of {way}, now in {stage}; it is met when {goal.met}")
    if me.location_id is not None and await tavern_of(session, me.location_id) is not None:
        found.append("your town has a meeting place where news and recruits pass")
    return found


async def son_customs_lines(scope: Scope, son: SonRow) -> list[str]:
    if son.current_world_id is None:
        return []
    peoples = select(EntityRow.id).where(EntityRow.world_id == son.current_world_id)
    found: list[str] = []
    for revival in await scope.session.scalars(
        select(RevivalRow).where(RevivalRow.people_entity_id.in_(peoples), RevivalRow.ended_epoch.is_(None)).order_by(RevivalRow.id).limit(LIST_LINES)
    ):
        goal = REVIVAL_GOALS[revival.goal].label.lower()
        way, stage = REVIVAL_WAYS[revival.way].label.lower(), spoken(revival.stage)
        found.append(f"the {await named(scope, revival.people_entity_id)} move to {goal} by the way of {way} ({stage})")
    return found
