from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.youth import MEMBER_AXES, PURPOSE_AXES, TOWN_EFFECTS, YOUTHS_WITHOUT_GROUP_LIFE_STAGES
from aerona.catalog.life_traits import FACTION_KIND_TRAITS, YOUTH_PURPOSE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.urban import TurfRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow, YouthStandingRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.life_traits import FactionKindTrait, YouthPurposeTrait
from aerona.domain.enums.mind import ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.youth import YouthPlace, YouthPurpose
from aerona.domain.models.calendar import epoch_end_year, epoch_start_year
from aerona.domain.models.moment import Moment
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import realm_of
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.births import birth_year
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term

GANGS = having(FACTION_KIND_TRAITS, FactionKindTrait.GANGS)
MOVEMENTS = having(FACTION_KIND_TRAITS, FactionKindTrait.MOVEMENTS)
UNRULY = having(YOUTH_PURPOSE_TRAITS, YouthPurposeTrait.UNRULY)
DELINQUENT = having(YOUTH_PURPOSE_TRAITS, YouthPurposeTrait.DELINQUENT)
USUAL = 50
STANDING_LOSS = 5


@dataclass
class YouthTally:
    formed: int = 0
    joined: int = 0
    came_of_age: int = 0
    delinquent: int = 0
    recruited: int = 0
    coopted: int = 0
    disbanded: int = 0


async def standing_for(session: AsyncSession, being: EntityRow) -> YouthStandingRow | None:
    folk = await people_of(session, being)
    return await session.get(YouthStandingRow, folk.id) if folk is not None else None


async def is_youth(session: AsyncSession, being: EntityRow) -> bool:
    if being.entity_type is not EntityType.MORTAL or being.status is not EntityStatus.CANON:
        return False
    standing = await standing_for(session, being)
    if standing is not None:
        return standing.youth_from <= stat_or(being, "age", 0) < standing.youth_to
    profile = await session.get(MortalProfileRow, being.id)
    return profile is not None and profile.life_stage is LifeStage.YOUTH


async def purpose_for(session: AsyncSession, folk_id: int | None) -> YouthPurpose:
    if folk_id is None:
        return YouthPurpose.SPORT
    values = await stored_values(session, ValueHolder.CULTURE, folk_id)
    axis = max(sorted(PURPOSE_AXES), key=lambda each: values.get(each, 0))
    return PURPOSE_AXES[axis]


async def members_of(session: AsyncSession, group_id: int) -> list[YouthGroupMemberRow]:
    return list(await session.scalars(select(YouthGroupMemberRow).where(YouthGroupMemberRow.group_id == group_id).order_by(YouthGroupMemberRow.member_node_id)))


async def coming_of_age(ctx: TickContext, being: EntityRow) -> Moment | None:
    born = await birth_year(ctx.session, being.id)
    standing = await standing_for(ctx.session, being)
    if born is None or standing is None:
        return None
    years = ctx.rules.time.years_per_epoch
    first, last = epoch_start_year(ctx.epoch, years), epoch_end_year(ctx.epoch, years) - 1
    return Moment(min(last, max(first, born + standing.youth_to)))


async def come_of_age(ctx: TickContext, group: YouthGroupRow, tally: YouthTally) -> None:
    for member in await members_of(ctx.session, group.id):
        being = await ctx.session.get(EntityRow, member.member_node_id)
        if being is None or held(member.member_node_id) or "member_node_id" in (member.locked or []) or await is_youth(ctx.session, being):
            continue
        await ctx.session.delete(member)
        if group.leader_node_id == member.member_node_id and "leader_node_id" not in (group.locked or []):
            group.leader_node_id = None
        if being.status is EntityStatus.CANON:
            await record(
                ctx,
                "youth.came_of_age",
                roles={IncidentRole.SUBJECT: being.id},
                facts={"group": group.name},
                place=group.settlement_entity_id,
                at_moment=await coming_of_age(ctx, being),
            )
            tally.came_of_age += 1
    await ctx.session.flush()


async def youths_without_group(ctx: TickContext) -> dict[int, list[EntityRow]]:
    grouped = select(YouthGroupMemberRow.member_node_id)
    rows = await ctx.session.scalars(
        select(EntityRow)
        .outerjoin(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id.is_not(None),
            EntityRow.id.not_in(grouped),
            or_(MortalProfileRow.entity_id.is_(None), MortalProfileRow.life_stage.in_(YOUTHS_WITHOUT_GROUP_LIFE_STAGES)),
        )
        .order_by(EntityRow.id)
    )
    found: dict[int, list[EntityRow]] = {}
    for being in rows:
        if being.location_id is not None and not held(being.id) and await is_youth(ctx.session, being):
            found.setdefault(being.location_id, []).append(being)
    return found


async def gather(ctx: TickContext, tally: YouthTally) -> None:
    table = ctx.rules.youth
    for town_id, youths in sorted((await youths_without_group(ctx)).items()):
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or town.entity_type is not EntityType.SETTLEMENT or held(town_id):
            continue
        group = await ctx.session.scalar(select(YouthGroupRow).where(YouthGroupRow.settlement_entity_id == town_id).order_by(YouthGroupRow.id).limit(1))
        standing = await standing_for(ctx.session, youths[0])
        place = standing.place if standing is not None else YouthPlace.HOUSEHOLD
        if group is None:
            size = max(1, table.form_size // 2) if place is YouthPlace.YOUTH_HOUSE else table.form_size
            if len(youths) < size:
                continue
            folk = await people_of(ctx.session, town)
            group = YouthGroupRow(
                settlement_entity_id=town_id,
                name=f"the youth of {town.name}",
                purpose=await purpose_for(ctx.session, folk.id if folk is not None else None),
                leader_node_id=youths[0].id,
                founded_epoch=ctx.epoch,
                locked=[],
            )
            ctx.session.add(group)
            await ctx.session.flush()
            await record(ctx, "youth.group_formed", roles={IncidentRole.PLACE: town_id}, facts={"group": group.name, "purpose": group.purpose})
            tally.formed += 1
        odds = table.join_pct // 2 if place is YouthPlace.WANDERING else table.join_pct
        for being in youths:
            if ctx.rng(f"youth_join.{being.id}.{ctx.epoch}").chance(odds) or group.founded_epoch == ctx.epoch:
                ctx.session.add(YouthGroupMemberRow(group_id=group.id, member_node_id=being.id, joined_epoch=ctx.epoch, locked=[]))
                tally.joined += 1
    await ctx.session.flush()


async def sway_town(ctx: TickContext, group: YouthGroupRow, profile: SettlementProfileRow | None) -> None:
    effect = TOWN_EFFECTS.get(group.purpose)
    if effect is None or profile is None or held(group.settlement_entity_id) or effect[0] in (profile.locked or []):
        return
    column, sign = effect
    amount = sign * ctx.rules.youth.group_effect
    with explaining():
        term("youth.group_effect", amount, source_node_id=group.settlement_entity_id)
        setattr(profile, column, clamp_int(getattr(profile, column) + amount, 0, PERCENT))


async def sway_members(ctx: TickContext, group: YouthGroupRow, members: list[YouthGroupMemberRow]) -> None:
    axis = MEMBER_AXES.get(group.purpose)
    if axis is None:
        return
    step = ctx.rules.youth.member_effect
    for member in members:
        if held(member.member_node_id):
            continue
        values = dict(await stored_values(ctx.session, ValueHolder.PERSONAL, member.member_node_id))
        values[axis] = values.get(axis, 0) + step
        with explaining():
            term("youth.member_effect", step, source_node_id=group.settlement_entity_id)
            await write_values(ctx.session, ValueHolder.PERSONAL, member.member_node_id, values)


def delinquency_odds(ctx: TickContext, group: YouthGroupRow, town: EntityRow, profile: SettlementProfileRow | None, standing: YouthStandingRow | None) -> float:
    odds = float(ctx.rules.youth.delinquency_base_pct)
    odds *= 1 + (PERCENT - stat_or(town, "prosperity", USUAL)) / PERCENT
    odds *= 1 + (PERCENT - (profile.public_order if profile is not None else USUAL)) / PERCENT
    if standing is not None:
        odds *= standing.freedom / USUAL * (1 - standing.duty / (2 * PERCENT))
    return min(float(PERCENT), odds * (2 if group.purpose in DELINQUENT else 1))


async def gangs_in(session: AsyncSession, town_id: int, kinds: frozenset[FactionKind]) -> list[int]:
    here = select(EntityRow.id).where(EntityRow.location_id == town_id)
    districts = select(DistrictRow.id).where(DistrictRow.settlement_entity_id == town_id)
    turf = select(TurfRow.faction_entity_id).where(TurfRow.district_id.in_(districts))
    members = select(FactionMembershipRow.faction_entity_id).where(FactionMembershipRow.mortal_entity_id.in_(here))
    rows = await session.scalars(
        select(FactionProfileRow.faction_entity_id)
        .where(FactionProfileRow.kind.in_(sorted(kinds)), FactionProfileRow.faction_entity_id.in_(members.union(turf)))
        .order_by(FactionProfileRow.faction_entity_id)
    )
    return [faction_id for faction_id in rows if not held(faction_id)]


async def misbehave(ctx: TickContext, group: YouthGroupRow, town: EntityRow, profile: SettlementProfileRow | None, tally: YouthTally) -> None:
    standing = await standing_for(ctx.session, town)
    if not ctx.rng(f"youth_delinquency.{group.id}.{ctx.epoch}").chance(delinquency_odds(ctx, group, town, profile, standing)):
        return
    table = ctx.rules.youth
    if profile is not None and not held(town.id) and "crime" not in (profile.locked or []):
        with explaining():
            term("youth.delinquency_crime", table.delinquency_crime, source_node_id=group.settlement_entity_id)
            profile.crime = clamp_int(profile.crime + table.delinquency_crime, 0, PERCENT)
    if "standing" not in (group.locked or []):
        group.standing = clamp_int(group.standing - STANDING_LOSS, 0, PERCENT)
    if group.purpose is YouthPurpose.MISCHIEF and "purpose" not in (group.locked or []) and await gangs_in(ctx.session, town.id, GANGS):
        group.purpose = YouthPurpose.CRIME
    await record(
        ctx,
        "youth.delinquency",
        roles={IncidentRole.PLACE: town.id, **({IncidentRole.ACTOR: group.leader_node_id} if group.leader_node_id is not None else {})},
        facts={"group": group.name, "purpose": group.purpose},
    )
    tally.delinquent += 1


async def recruit(ctx: TickContext, group: YouthGroupRow, members: list[YouthGroupMemberRow], tally: YouthTally) -> None:
    kinds = GANGS if group.purpose is YouthPurpose.CRIME else MOVEMENTS if group.purpose is YouthPurpose.POLITICS else None
    if kinds is None:
        return
    recruiters = await gangs_in(ctx.session, group.settlement_entity_id, kinds)
    if not recruiters:
        return
    for member in members:
        faction_id = recruiters[0]
        if held(member.member_node_id) or await ctx.session.get(FactionMembershipRow, (faction_id, member.member_node_id)) is not None:
            continue
        if not ctx.rng(f"youth_recruit.{group.id}.{member.member_node_id}.{ctx.epoch}").chance(ctx.rules.youth.recruitment_pct):
            continue
        ctx.session.add(FactionMembershipRow(faction_entity_id=faction_id, mortal_entity_id=member.member_node_id, joined_epoch=ctx.epoch, locked=[]))
        await record(
            ctx,
            "youth.recruited",
            roles={IncidentRole.ACTOR: faction_id, IncidentRole.TARGET: member.member_node_id},
            facts={"group": group.name, "purpose": group.purpose},
            place=group.settlement_entity_id,
        )
        tally.recruited += 1


async def coopt(ctx: TickContext, group: YouthGroupRow, tally: YouthTally) -> None:
    if group.purpose not in UNRULY or "purpose" in (group.locked or []):
        return
    realm = await realm_of(ctx.session, group.settlement_entity_id)
    if realm is None or held(realm):
        return
    town = await ctx.session.get(EntityRow, group.settlement_entity_id)
    standing = await standing_for(ctx.session, town) if town is not None else None
    odds = ctx.rules.youth.service_cooption_pct * (2 if standing is not None and standing.place is YouthPlace.SERVICE else 1)
    if not ctx.rng(f"youth_coopt.{group.id}.{ctx.epoch}").chance(min(PERCENT, odds)):
        return
    group.purpose = YouthPurpose.SERVICE
    await record(
        ctx,
        "youth.recruited",
        roles={IncidentRole.ACTOR: realm, **({IncidentRole.TARGET: group.leader_node_id} if group.leader_node_id is not None else {})},
        facts={"group": group.name, "purpose": group.purpose},
        place=group.settlement_entity_id,
    )
    tally.coopted += 1


async def disband(ctx: TickContext, group: YouthGroupRow, tally: YouthTally) -> None:
    await record(ctx, "youth.group_disbanded", roles={IncidentRole.PLACE: group.settlement_entity_id}, facts={"group": group.name})
    await ctx.session.delete(group)
    tally.disbanded += 1


async def keep_youth(ctx: TickContext) -> YouthTally:
    tally = YouthTally()
    groups = list(await ctx.session.scalars(select(YouthGroupRow).order_by(YouthGroupRow.id)))
    for group in groups:
        if not held(group.settlement_entity_id):
            await come_of_age(ctx, group, tally)
    await gather(ctx, tally)
    for group in list(await ctx.session.scalars(select(YouthGroupRow).order_by(YouthGroupRow.id))):
        if held(group.settlement_entity_id):
            continue
        members = await members_of(ctx.session, group.id)
        if not members:
            await disband(ctx, group, tally)
            continue
        town = await ctx.session.get(EntityRow, group.settlement_entity_id)
        if town is None:
            continue
        profile = await ctx.session.get(SettlementProfileRow, town.id)
        await sway_town(ctx, group, profile)
        await sway_members(ctx, group, members)
        await misbehave(ctx, group, town, profile, tally)
        await recruit(ctx, group, members, tally)
        await coopt(ctx, group, tally)
    await ctx.session.flush()
    return tally
