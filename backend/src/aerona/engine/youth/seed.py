from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.childhood import ChildStandingRow
from aerona.db.tables.customs import AgeSetMemberRow, AgeSetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow, YouthStandingRow
from aerona.db.write_guard import held
from aerona.domain.enums.customs import AgeGrade
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.youth import YouthPlace
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record
from aerona.engine.youth.groups import purpose_for

LEANING = 60
YOUTH_SPAN = 8


@dataclass
class YouthSeedTally:
    standing: int = 0
    groups: int = 0


def half(value: int) -> int:
    return clamp_int(PERCENT // 2 + value // 2, 0, PERCENT)


async def seed_standing(ctx: TickContext, tally: YouthSeedTally) -> None:
    owned = set(await ctx.session.scalars(select(YouthStandingRow.people_entity_id)))
    for folk in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    ):
        if folk.id in owned or held(folk.id):
            continue
        values = await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)
        children = await ctx.session.get(ChildStandingRow, folk.id)
        start = children.responsibility_age if children is not None else 12
        sets = await ctx.session.scalar(select(AgeSetRow.id).where(AgeSetRow.people_entity_id == folk.id).limit(1)) is not None
        if sets:
            place = YouthPlace.YOUTH_HOUSE
        elif values.get(ValueAxis.KNOWLEDGE, 0) >= LEANING:
            place = YouthPlace.SCHOOL
        elif values.get(ValueAxis.CRAFTSMANSHIP, 0) >= LEANING:
            place = YouthPlace.APPRENTICESHIP
        else:
            place = YouthPlace.HOUSEHOLD
        ctx.session.add(
            YouthStandingRow(
                people_entity_id=folk.id,
                youth_from=start,
                youth_to=start + YOUTH_SPAN,
                place=place,
                freedom=half(-values.get(ValueAxis.TRADITION, 0)),
                duty=half((values.get(ValueAxis.LAW, 0) + values.get(ValueAxis.LOYALTY, 0)) // 2),
                locked=[],
            )
        )
        tally.standing += 1


async def seed_from_age_sets(ctx: TickContext, tally: YouthSeedTally) -> None:
    linked = set(await ctx.session.scalars(select(YouthGroupRow.age_set_id).where(YouthGroupRow.age_set_id.is_not(None))))
    grouped = set(await ctx.session.scalars(select(YouthGroupMemberRow.member_node_id)))
    for age_set in list(await ctx.session.scalars(select(AgeSetRow).where(AgeSetRow.grade == AgeGrade.YOUTHS).order_by(AgeSetRow.id))):
        if age_set.id in linked or held(age_set.people_entity_id):
            continue
        members = [
            being
            for being in await ctx.session.scalars(
                select(EntityRow)
                .join(AgeSetMemberRow, AgeSetMemberRow.mortal_entity_id == EntityRow.id)
                .where(AgeSetMemberRow.age_set_id == age_set.id, EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.id)
            )
            if being.id not in grouped and being.location_id is not None and not held(being.id)
        ]
        if not members:
            continue
        town_id = Counter(being.location_id for being in members).most_common(1)[0][0]
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or town.entity_type is not EntityType.SETTLEMENT or held(town.id):
            continue
        group = YouthGroupRow(
            settlement_entity_id=town.id,
            name=age_set.name,
            purpose=await purpose_for(ctx.session, age_set.people_entity_id),
            leader_node_id=members[0].id,
            age_set_id=age_set.id,
            founded_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(group)
        await ctx.session.flush()
        ctx.session.add_all(YouthGroupMemberRow(group_id=group.id, member_node_id=being.id, joined_epoch=ctx.epoch, locked=[]) for being in members)
        grouped |= {being.id for being in members}
        await record(ctx, "youth.group_formed", roles={IncidentRole.PLACE: town.id}, facts={"group": group.name, "purpose": group.purpose})
        tally.groups += 1


async def seed_youth(ctx: TickContext) -> YouthSeedTally:
    tally = YouthSeedTally()
    await seed_standing(ctx, tally)
    await seed_from_age_sets(ctx, tally)
    await ctx.session.flush()
    return tally
