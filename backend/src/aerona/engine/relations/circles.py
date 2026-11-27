from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.relations import CIRCLES
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.mind import PreferenceRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.relations import SocialCircleRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held, write_blocked
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.mind import ActKind, MemoryKind, PreferenceKind, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.relations import CircleKind, ContestKind, ContestStake
from aerona.engine.collective.norms import breach
from aerona.engine.context import TickContext
from aerona.engine.mind.book import is_locked, mind_of, stored_values, write_values
from aerona.engine.mind.ethics import conscience
from aerona.engine.mind.memories import remember
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.numbers import clamp_int, scaled_cap
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.renames import rename_everywhere
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.relations.book import ensure_relation, shift
from aerona.engine.relations.contests import Bout, ContestTally, hold_contest, pass_wealth

VALUE_SPAN = 100
Interest = tuple[PreferenceKind | None, str | None, ValueAxis | None]


@dataclass
class CircleTally:
    founded: int = 0
    joined: int = 0
    bonded: int = 0
    spread: int = 0
    disbanded: int = 0
    matches: int = 0
    debts: int = 0


def kind_for_taste(kind: PreferenceKind) -> CircleKind | None:
    return next((circle for circle, spec in CIRCLES.items() if kind in spec.tastes), None)


def kind_for_axis(axis: ValueAxis) -> CircleKind | None:
    return next((circle for circle, spec in CIRCLES.items() if axis in spec.axes), None)


async def circles_at(session: AsyncSession, place_id: int) -> list[SocialCircleRow]:
    query = (
        select(SocialCircleRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == SocialCircleRow.faction_entity_id)
        .join(EntityRow, EntityRow.id == SocialCircleRow.faction_entity_id)
        .where(SocialCircleRow.meeting_place_id == place_id, EntityRow.status == EntityStatus.CANON)
        .order_by(SocialCircleRow.faction_entity_id)
    )
    return list(await session.scalars(query))


async def members_of(session: AsyncSession, circle_id: int) -> list[int]:
    query = select(FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id == circle_id)
    return list(await session.scalars(query.order_by(FactionMembershipRow.mortal_entity_id)))


async def interests(ctx: TickContext, mortals: list[EntityRow]) -> dict[Interest, list[int]]:
    table = ctx.rules.circles
    found: dict[Interest, list[int]] = defaultdict(list)
    ids = [mortal.id for mortal in mortals]
    tastes = await ctx.session.scalars(
        select(PreferenceRow).where(PreferenceRow.holder_node_id.in_(ids), PreferenceRow.strength >= table.taste_at).order_by(PreferenceRow.id)
    )
    for row in tastes:
        if kind_for_taste(row.kind) is not None:
            found[(row.kind, row.target, None)].append(row.holder_node_id)
    for mortal in mortals:
        values = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
        for axis, value in values.items():
            if value >= table.belief_at and kind_for_axis(axis) is not None:
                found[(None, None, axis)].append(mortal.id)
    return found


def matches(circle: SocialCircleRow, interest: Interest) -> bool:
    taste_kind, key, axis = interest
    if axis is not None:
        return circle.axis is axis
    return circle.taste_key == f"{taste_kind.value if taste_kind else ''}:{key}"


async def found_circle(ctx: TickContext, place: EntityRow, interest: Interest, members: list[int]) -> SocialCircleRow | None:
    taste_kind, key, axis = interest
    kind = kind_for_axis(axis) if axis is not None else kind_for_taste(taste_kind) if taste_kind is not None else None
    if kind is None:
        return None
    faction = await found_faction(ctx, place, FactionKind.SOCIAL_CIRCLE)
    label = CIRCLES[kind].label
    await rename_everywhere(ctx.session, faction.id, f"The {label} of {place.name}", ctx.epoch, free=True)
    profile = await ctx.session.get(FactionProfileRow, faction.id)
    if profile is not None:
        profile.leader_entity_id = members[0]
        profile.secrecy = ctx.rules.intrigue.secret_base if CIRCLES[kind].secret else 0
    row = SocialCircleRow(
        faction_entity_id=faction.id,
        kind=kind,
        taste_key=f"{taste_kind.value}:{key}" if taste_kind is not None else None,
        axis=axis,
        meeting_place_id=place.id,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    for mortal_id in members:
        ctx.session.add(
            FactionMembershipRow(faction_entity_id=faction.id, mortal_entity_id=mortal_id, rank=FactionRank.MEMBER, joined_epoch=ctx.epoch, locked=[])
        )
    await ctx.session.flush()
    await record(
        ctx,
        "circle.founded",
        roles={IncidentRole.PRODUCT: faction.id, IncidentRole.PLACE: place.id, IncidentRole.MEMBER: members},
        facts={"circle": kind},
        steps=(StepDraft(StepAction.FOUND, actor=members[0], target=faction.id),),
        place=place.id,
    )
    return row


async def gather(ctx: TickContext, place: EntityRow, mortals: list[EntityRow], tally: CircleTally) -> None:
    table = ctx.rules.circles
    circles = await circles_at(ctx.session, place.id)
    found = await interests(ctx, [mortal for mortal in mortals if not held(mortal.id)])
    for interest, people in sorted(found.items(), key=lambda item: (-len(item[1]), str(item[0]))):
        circle = next((row for row in circles if matches(row, interest)), None)
        if circle is None:
            if len(people) < table.min_members or len(circles) >= scaled_cap(table.per_place, table.place_mortals, len(mortals)) or held(place.id):
                continue
            made = await found_circle(ctx, place, interest, people)
            if made is not None:
                circles.append(made)
                tally.founded += 1
            continue
        if held(circle.faction_entity_id) or "members" in circle.locked:
            continue
        have = set(await members_of(ctx.session, circle.faction_entity_id))
        for mortal_id in people:
            if mortal_id not in have:
                ctx.session.add(
                    FactionMembershipRow(
                        faction_entity_id=circle.faction_entity_id, mortal_entity_id=mortal_id, rank=FactionRank.NOVICE, joined_epoch=ctx.epoch, locked=[]
                    )
                )
                tally.joined += 1
    await ctx.session.flush()


async def creed_for(session: AsyncSession, circle: SocialCircleRow) -> int | None:
    if circle.axis is None or circle.meeting_place_id is None:
        return None
    rows = await session.execute(
        select(IdeologyAdherentRow.ideology_entity_id, IdeologyProfileRow.value_delta)
        .join(IdeologyProfileRow, IdeologyProfileRow.ideology_entity_id == IdeologyAdherentRow.ideology_entity_id)
        .where(IdeologyAdherentRow.adherent_entity_id == circle.meeting_place_id)
        .order_by(IdeologyAdherentRow.ideology_entity_id)
    )
    return next((ideology for ideology, delta in rows.all() if (delta or {}).get(circle.axis.value, 0) > 0), None)


async def bind(ctx: TickContext, circle: SocialCircleRow, members: list[int], tally: CircleTally) -> None:
    table = ctx.rules.circles
    for holder in members:
        if held(holder):
            continue
        for other in members:
            if other == holder:
                continue
            row = await ensure_relation(ctx.session, holder, other, ctx.epoch)
            if row is not None:
                shift(ctx.rules, row, ctx.epoch, friendship=table.friendship, familiarity=table.friendship)
                tally.bonded += 1


async def pull(ctx: TickContext, circle: SocialCircleRow, members: list[int], tally: CircleTally) -> None:
    table = ctx.rules.circles
    if circle.axis is not None:
        for member in members:
            if held(member) or write_blocked(member, "values") or is_locked(await mind_of(ctx.session, member), "values"):
                continue
            values = await stored_values(ctx.session, ValueHolder.PERSONAL, member)
            values[circle.axis] = clamp_int(values.get(circle.axis, 0) + table.belief_pull, -VALUE_SPAN, VALUE_SPAN)
            await write_values(ctx.session, ValueHolder.PERSONAL, member, values)
    if "ideology" not in circle.locked:
        circle.ideology_entity_id = await creed_for(ctx.session, circle)
    if circle.ideology_entity_id is None or circle.meeting_place_id is None or held(circle.meeting_place_id):
        return
    adherence = await ctx.session.get(IdeologyAdherentRow, (circle.ideology_entity_id, circle.meeting_place_id))
    if adherence is not None:
        adherence.strength = min(PERCENT, adherence.strength + table.spread)
        tally.spread += 1


async def disband(ctx: TickContext, circle: SocialCircleRow, tally: CircleTally) -> None:
    faction = await living_entity(ctx.session, circle.faction_entity_id)
    if faction is not None:
        await retire_in(ctx, faction, "its members drifted apart", close_bonds=True)
    tally.disbanded += 1


async def tend_circles(ctx: TickContext, place: EntityRow, mortals: list[EntityRow], tally: CircleTally) -> None:
    await gather(ctx, place, mortals, tally)
    for circle in await circles_at(ctx.session, place.id):
        if held(circle.faction_entity_id):
            continue
        members = [member for member in await members_of(ctx.session, circle.faction_entity_id) if await living_entity(ctx.session, member) is not None]
        if len(members) < 2 and "members" not in circle.locked:
            await disband(ctx, circle, tally)
            continue
        await bind(ctx, circle, members, tally)
        await pull(ctx, circle, members, tally)
        if CIRCLES[circle.kind].wagers:
            await wager(ctx, circle, members, tally)


async def champion(ctx: TickContext, members: list[int]) -> EntityRow | None:
    profiles = list(await ctx.session.scalars(select(MortalProfileRow).where(MortalProfileRow.entity_id.in_(members)).order_by(MortalProfileRow.entity_id)))
    best = max(profiles, key=lambda row: (row.renown, -row.entity_id), default=None)
    return await living_entity(ctx.session, best.entity_id) if best is not None else None


async def match_clubs(ctx: TickContext, tally: CircleTally) -> None:
    clubs = [
        row
        for row in await ctx.session.scalars(
            select(SocialCircleRow)
            .join(EntityRow, EntityRow.id == SocialCircleRow.faction_entity_id)
            .where(EntityRow.status == EntityStatus.CANON)
            .order_by(SocialCircleRow.faction_entity_id)
        )
        if CIRCLES[row.kind].fields and not held(row.faction_entity_id)
    ]
    for club in clubs:
        rivals = [row for row in clubs if row.meeting_place_id != club.meeting_place_id and row.faction_entity_id > club.faction_entity_id]
        if not rivals or not ctx.rng(f"circle.match.{club.faction_entity_id}.{ctx.epoch}").chance(ctx.rules.circles.sport_rivalry_pct):
            continue
        rival = rivals[0]
        ours = await champion(ctx, await members_of(ctx.session, club.faction_entity_id))
        theirs = await champion(ctx, await members_of(ctx.session, rival.faction_entity_id))
        if ours is None or theirs is None or ours.id == theirs.id:
            continue
        row = await hold_contest(ctx, Bout(ContestKind.RACE, ContestStake.HONOUR, ours, theirs, place_id=club.meeting_place_id), ContestTally())
        if row is None:
            continue
        tally.matches += 1
        await record(
            ctx,
            "circle.match",
            roles={IncidentRole.ACTOR: club.faction_entity_id, IncidentRole.OPPONENT: rival.faction_entity_id},
            facts={"outcome": row.outcome},
            place=club.meeting_place_id,
        )


async def wager(ctx: TickContext, circle: SocialCircleRow, members: list[int], tally: CircleTally) -> None:
    if len(members) < 2 or not ctx.rng(f"circle.debt.{circle.faction_entity_id}.{ctx.epoch}").chance(ctx.rules.circles.gaming_debt_pct):
        return
    loser, winner = ctx.rng(f"circle.debtors.{circle.faction_entity_id}.{ctx.epoch}").sample(members, 2)
    if held(loser, winner):
        return
    await pass_wealth(ctx.session, loser, winner, ctx.rules.contests.wager_wealth)
    await remember(
        ctx.session, ctx.rules, holder_id=loser, subject_id=winner, kind=MemoryKind.ILL_WILL, magnitude=-ctx.rules.contests.wager_wealth, epoch=ctx.epoch
    )
    stance = await conscience(ctx, winner, ActKind.USURY, loser)
    place = await ctx.session.get(SettlementProfileRow, circle.meeting_place_id) if circle.meeting_place_id is not None else None
    if stance is not None and breach(stance) and place is not None and "crime" not in place.locked:
        place.crime = clamp_int(place.crime + ctx.rules.contests.wager_wealth, 0, PERCENT)
    tally.debts += 1
    await record(
        ctx,
        "circle.debt",
        roles={IncidentRole.ACTOR: loser, IncidentRole.TARGET: winner, IncidentRole.SUBJECT: circle.faction_entity_id},
        facts={"debt": ctx.rules.contests.wager_wealth},
        place=circle.meeting_place_id,
    )
