from sqlalchemy import select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.db.tables.customs import (
    AgeSetMemberRow,
    AgeSetRow,
    BodyMarkRow,
    IntoxicantCustomRow,
    MembershipRow,
    NameFormRow,
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
        found.append(f"a mark on your body: {words(mark.kind.value)}, meaning {words(mark.meaning.value)}")
    for form in await session.scalars(select(NameFormRow).where(NameFormRow.holder_node_id == me.id).order_by(NameFormRow.form).limit(LIST_LINES)):
        found.append(f"your {words(form.form.value)} name: {form.name}")
    member = await session.get(AgeSetMemberRow, me.id)
    age_set = await session.get(AgeSetRow, member.age_set_id) if member is not None else None
    if age_set is not None:
        found.append(f"you belong to the {age_set.name}, in the grade of {words(age_set.grade.value)}")
    membership = await session.get(MembershipRow, me.id)
    if membership is not None:
        found.append(f"your standing in {await named(scope, membership.polity_entity_id)}: {words(membership.category.value)}")
    folk = await people_of(session, me)
    if folk is not None:
        for custom in await session.scalars(
            select(IntoxicantCustomRow).where(IntoxicantCustomRow.people_entity_id == folk.id).order_by(IntoxicantCustomRow.intoxicant).limit(LIST_LINES)
        ):
            found.append(f"your people take {words(custom.intoxicant.value)} at {words(custom.use.value)}")
        revival = await session.scalar(select(RevivalRow).where(RevivalRow.people_entity_id == folk.id, RevivalRow.ended_epoch.is_(None)).limit(1))
        if revival is not None:
            found.append(f"a movement among your people seeks to {words(revival.goal.value)}, now in {words(revival.stage.value)}")
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
        found.append(f"the {await named(scope, revival.people_entity_id)} move to {words(revival.goal.value)} ({words(revival.stage.value)})")
    return found
