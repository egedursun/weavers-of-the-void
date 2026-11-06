from pydantic import Field
from sqlalchemy import select

from aerona.catalog.relations import CIRCLES, CONTESTS, PASSION_LABELS, STAKE_LABELS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.relations import ContestRow, GroupRankRow, PassionRow, PersuasionRow, RelationshipRow, SocialCircleRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.relations import (
    AppealKind,
    CircleKind,
    ContestEnd,
    ContestKind,
    ContestStake,
    GroupKind,
    PassionKind,
    PassionSource,
    PersuasionAim,
    RelationType,
)
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.records import retire_in
from aerona.engine.relations.book import ensure_relation, ranked
from aerona.engine.relations.contests import Bout, ContestTally, hold_contest
from aerona.engine.relations.passions import invoke, kindle
from aerona.engine.relations.persuasion import persuade
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
FIELDS = ("friendship", "romance", "familiarity", "rivalry")


class SetTie(Command):
    holder_id: int
    subject_id: int
    friendship: int | None = Field(default=None, ge=-SPAN, le=SPAN)
    romance: int | None = Field(default=None, ge=0, le=SPAN)
    familiarity: int | None = Field(default=None, ge=0, le=SPAN)
    rivalry: int | None = Field(default=None, ge=0, le=SPAN)
    kinds: list[RelationType] | None = None
    affair: bool | None = None
    affair_known: bool | None = None
    mutual: bool = False
    hold: bool = True


class TieTarget(Command):
    relation_id: int


class FoundCircle(Command):
    place_id: int
    kind: CircleKind
    axis: ValueAxis | None = None
    taste_key: str | None = Field(default=None, max_length=120)
    member_ids: list[int] = Field(default_factory=list, max_length=50)


class EditCircle(Command):
    circle_id: int
    kind: CircleKind | None = None
    axis: ValueAxis | None = None
    taste_key: str | None = Field(default=None, max_length=120)
    meeting_place_id: int | None = None
    ideology_id: int | None = None
    hold: bool = True


class CircleMember(Command):
    circle_id: int
    mortal_id: int
    remove: bool = False


class CircleTarget(Command):
    circle_id: int


class SetPassion(Command):
    holder_id: int
    kind: PassionKind
    object_id: int
    strength: int = Field(ge=0, le=SPAN)
    source: PassionSource = PassionSource.DIVINE
    hold: bool = True


class PassionTarget(Command):
    passion_id: int


class SetRank(Command):
    group_id: int
    member_id: int
    group_kind: GroupKind
    rank: int = Field(ge=1, le=1000)
    dominance: int | None = Field(default=None, ge=0, le=SPAN)
    hold: bool = True


class RankTarget(Command):
    group_id: int
    member_id: int


class HoldContest(Command):
    challenger_id: int
    defender_id: int
    kind: ContestKind
    stake: ContestStake = ContestStake.HONOUR
    judge_id: int | None = None
    stake_node_id: int | None = None
    wager: int = Field(default=0, ge=0, le=SPAN)


class EditContest(Command):
    contest_id: int
    outcome: ContestEnd | None = None
    famous: bool | None = None
    note: str | None = Field(default=None, max_length=120)


class ContestTarget(Command):
    contest_id: int


class Persuade(Command):
    speaker_id: int
    target_id: int
    appeal: AppealKind
    aim: PersuasionAim = PersuasionAim.BELIEF
    axis: ValueAxis | None = None
    toward: int = Field(default=SPAN, ge=-SPAN, le=SPAN)


class PersuasionTarget(Command):
    persuasion_id: int


async def mortal(scope: PlayerScope, node_id: int) -> EntityRow:
    found = await scope.session.get(EntityRow, node_id)
    if found is None or found.entity_type is not EntityType.MORTAL or found.status is not EntityStatus.CANON:
        raise ValidationFailedError("Only living mortals hold bonds, passions and places in a pecking order.")
    return found


async def node(scope: PlayerScope, node_id: int) -> None:
    if await scope.session.get(NodeRow, node_id) is None:
        raise ValidationFailedError("That record does not exist.")


def held(locked: list[str] | None, fields: list[str], hold: bool) -> list[str]:
    found = set(locked or [])
    return sorted(found | set(fields)) if hold else sorted(found - set(fields))


async def write_relation(scope: PlayerScope, holder: int, subject: int, command: SetTie) -> RelationshipRow:
    row = await ensure_relation(scope.session, holder, subject, await scope.epoch())
    if row is None:
        raise ValidationFailedError("That bond cannot be written.")
    touched = [name for name in FIELDS if getattr(command, name) is not None]
    for name in touched:
        setattr(row, name, getattr(command, name))
    if command.kinds is not None:
        row.kinds = ranked(kind.value for kind in command.kinds)
        touched.append("kinds")
    for name in ("affair", "affair_known"):
        value = getattr(command, name)
        if value is not None:
            setattr(row, name, value)
            touched.append("affair")
    row.locked = held(row.locked, touched, command.hold)
    row.last_epoch = await scope.epoch()
    return row


@player_action("tie:set", ActionKind.OTHER)
async def set_relation(scope: PlayerScope, command: SetTie) -> Effect:
    first, second = await mortal(scope, command.holder_id), await mortal(scope, command.subject_id)
    if first.id == second.id:
        raise ValidationFailedError("A mortal has no bond with themselves.")
    row = await write_relation(scope, first.id, second.id, command)
    if command.mutual:
        await write_relation(scope, second.id, first.id, command)
    await scope.session.flush()
    return Effect(f"How {first.name} feels toward {second.name} was reshaped.", target_node_id=first.id, values={"relation_id": row.id})


@player_action("tie:remove", ActionKind.OTHER)
async def remove_relation(scope: PlayerScope, command: TieTarget) -> Effect:
    row = await scope.session.get(RelationshipRow, command.relation_id)
    if row is None:
        raise NotFoundError("No such bond.")
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The bond was forgotten.", target_node_id=holder)


async def circle_row(scope: PlayerScope, circle_id: int) -> SocialCircleRow:
    row = await scope.session.get(SocialCircleRow, circle_id)
    if row is None:
        raise NotFoundError("No such circle.")
    return row


@player_action("circle:found", ActionKind.OTHER)
async def found_circle(scope: PlayerScope, command: FoundCircle) -> Effect:
    place = await scope.session.get(EntityRow, command.place_id)
    if place is None or place.status is not EntityStatus.CANON:
        raise ValidationFailedError("A circle needs a living place to meet.")
    ctx = await scope.context("circle:found")
    faction = await found_faction(ctx, place, FactionKind.SOCIAL_CIRCLE)
    faction.name = f"The {CIRCLES[command.kind].label} of {place.name}"
    row = SocialCircleRow(
        faction_entity_id=faction.id,
        kind=command.kind,
        axis=command.axis,
        taste_key=command.taste_key,
        meeting_place_id=place.id,
        founded_epoch=ctx.epoch,
        locked=["members"],
    )
    scope.session.add(row)
    for member in command.member_ids:
        await mortal(scope, member)
        scope.session.add(
            FactionMembershipRow(faction_entity_id=faction.id, mortal_entity_id=member, rank=FactionRank.MEMBER, joined_epoch=ctx.epoch, locked=[])
        )
    await scope.session.flush()
    return Effect(f"{faction.name} first gathered.", target_node_id=faction.id, values={"circle_id": faction.id})


@player_action("circle:edit", ActionKind.OTHER)
async def edit_circle(scope: PlayerScope, command: EditCircle) -> Effect:
    row = await circle_row(scope, command.circle_id)
    touched: list[str] = []
    for name, value in (("kind", command.kind), ("axis", command.axis), ("taste_key", command.taste_key)):
        if value is not None:
            setattr(row, name, value)
            touched.append(name)
    if command.meeting_place_id is not None:
        await node(scope, command.meeting_place_id)
        row.meeting_place_id = command.meeting_place_id
        touched.append("meeting_place_id")
    if command.ideology_id is not None:
        await node(scope, command.ideology_id)
        row.ideology_entity_id = command.ideology_id
        touched.append("ideology")
    row.locked = held(row.locked, touched or ["members"], command.hold)
    await scope.session.flush()
    return Effect("The circle was reshaped.", target_node_id=row.faction_entity_id)


@player_action("circle:member", ActionKind.OTHER)
async def circle_member(scope: PlayerScope, command: CircleMember) -> Effect:
    row = await circle_row(scope, command.circle_id)
    member = await mortal(scope, command.mortal_id)
    found = await scope.session.get(FactionMembershipRow, (row.faction_entity_id, member.id))
    if command.remove:
        if found is not None:
            await scope.session.delete(found)
        verb = "left"
    else:
        if found is None:
            joined = FactionMembershipRow(
                faction_entity_id=row.faction_entity_id, mortal_entity_id=member.id, rank=FactionRank.MEMBER, joined_epoch=await scope.epoch(), locked=[]
            )
            scope.session.add(joined)
        verb = "joined"
    await scope.session.flush()
    return Effect(f"{member.name} {verb} the circle.", target_node_id=row.faction_entity_id)


@player_action("circle:disband", ActionKind.OTHER)
async def disband_circle(scope: PlayerScope, command: CircleTarget) -> Effect:
    row = await circle_row(scope, command.circle_id)
    faction = await scope.session.get(EntityRow, row.faction_entity_id)
    await scope.session.delete(row)
    if faction is not None and faction.status is EntityStatus.CANON:
        await retire_in(await scope.context("circle:disband"), faction, "the circle was broken up", close_bonds=True)
    await scope.session.flush()
    return Effect("The circle was broken up.", target_node_id=command.circle_id)


@player_action("passion:set", ActionKind.OTHER)
async def set_passion(scope: PlayerScope, command: SetPassion) -> Effect:
    holder = await mortal(scope, command.holder_id)
    await node(scope, command.object_id)
    row = await kindle(scope.session, holder.id, command.kind, command.object_id, strength=0, source=command.source, epoch=await scope.epoch())
    if row is None:
        raise ValidationFailedError("That passion cannot be kindled.")
    row.strength, row.source = command.strength, command.source
    row.locked = held(row.locked, ["strength", "kind"], command.hold)
    await scope.session.flush()
    label = PASSION_LABELS[command.kind].lower()
    return Effect(f"{holder.name} now holds a {label} of strength {command.strength}.", target_node_id=holder.id, values={"passion_id": row.id})


async def passion_row(scope: PlayerScope, passion_id: int) -> PassionRow:
    row = await scope.session.get(PassionRow, passion_id)
    if row is None:
        raise NotFoundError("No such passion.")
    return row


@player_action("passion:invoke", ActionKind.OTHER)
async def invoke_passion(scope: PlayerScope, command: PassionTarget) -> Effect:
    row = await passion_row(scope, command.passion_id)
    holder = await mortal(scope, row.holder_node_id)
    ctx = await scope.context("passion:invoke")
    lifted = await invoke(ctx, holder, [row.object_node_id])
    told = "was carried by" if lifted > 1 else "was not carried by"
    return Effect(f"{holder.name} {told} a {PASSION_LABELS[row.kind].lower()}.", target_node_id=holder.id, values={"lift": round(lifted * PERCENT)})


@player_action("passion:remove", ActionKind.OTHER)
async def remove_passion(scope: PlayerScope, command: PassionTarget) -> Effect:
    row = await passion_row(scope, command.passion_id)
    holder = row.holder_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The passion was quenched.", target_node_id=holder)


@player_action("rank:set", ActionKind.OTHER)
async def set_rank(scope: PlayerScope, command: SetRank) -> Effect:
    await node(scope, command.group_id)
    member = await mortal(scope, command.member_id)
    row = await scope.session.get(GroupRankRow, (command.group_id, member.id))
    epoch = await scope.epoch()
    if row is None:
        row = GroupRankRow(
            group_node_id=command.group_id,
            member_node_id=member.id,
            group_kind=command.group_kind,
            rank=command.rank,
            dominance=0,
            since_epoch=epoch,
            locked=[],
        )
        scope.session.add(row)
    others = await scope.session.scalars(
        select(GroupRankRow).where(GroupRankRow.group_node_id == command.group_id, GroupRankRow.member_node_id != member.id, GroupRankRow.rank >= command.rank)
    )
    for other in others:
        other.rank += 1
    row.group_kind, row.rank, row.since_epoch = command.group_kind, command.rank, epoch
    touched = ["rank"]
    if command.dominance is not None:
        row.dominance = command.dominance
        touched.append("dominance")
    row.locked = held(row.locked, touched, command.hold)
    await scope.session.flush()
    return Effect(f"{member.name} now stands at rank {command.rank}.", target_node_id=member.id)


@player_action("rank:remove", ActionKind.OTHER)
async def remove_rank(scope: PlayerScope, command: RankTarget) -> Effect:
    row = await scope.session.get(GroupRankRow, (command.group_id, command.member_id))
    if row is None:
        raise NotFoundError("That mortal holds no place in that group.")
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The place in the pecking order was taken away.", target_node_id=command.member_id)


@player_action("contest:hold", ActionKind.OTHER)
async def stage_contest(scope: PlayerScope, command: HoldContest) -> Effect:
    challenger, defender = await mortal(scope, command.challenger_id), await mortal(scope, command.defender_id)
    if challenger.id == defender.id:
        raise ValidationFailedError("A contest needs two contestants.")
    for other in (command.judge_id, command.stake_node_id):
        if other is not None:
            await node(scope, other)
    ctx = await scope.context("contest:hold")
    bout = Bout(
        command.kind,
        command.stake,
        challenger,
        defender,
        judge_id=command.judge_id,
        stake_node_id=command.stake_node_id,
        place_id=challenger.location_id,
        wager=command.wager,
    )
    row = await hold_contest(ctx, bout, ContestTally())
    if row is None:
        raise ValidationFailedError("A held mortal cannot be drawn into a contest.")
    label = CONTESTS[command.kind].label.lower()
    return Effect(
        f"{challenger.name} and {defender.name} met in a {label} for {STAKE_LABELS[command.stake].lower()}.",
        target_node_id=challenger.id,
        values={"contest_id": row.id},
    )


async def contest_row(scope: PlayerScope, contest_id: int) -> ContestRow:
    row = await scope.session.get(ContestRow, contest_id)
    if row is None:
        raise NotFoundError("No such contest.")
    return row


@player_action("contest:edit", ActionKind.OTHER)
async def edit_contest(scope: PlayerScope, command: EditContest) -> Effect:
    row = await contest_row(scope, command.contest_id)
    if command.outcome is not None:
        row.outcome = command.outcome
    if command.famous is not None:
        row.famous = command.famous
    if command.note is not None:
        row.note = command.note
    await scope.session.flush()
    return Effect("The tale of the contest was retold.", target_node_id=row.challenger_node_id)


@player_action("contest:remove", ActionKind.OTHER)
async def remove_contest(scope: PlayerScope, command: ContestTarget) -> Effect:
    row = await contest_row(scope, command.contest_id)
    holder = row.challenger_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The contest was struck from memory.", target_node_id=holder)


@player_action("persuasion:attempt", ActionKind.OTHER)
async def attempt_persuasion(scope: PlayerScope, command: Persuade) -> Effect:
    speaker, target = await mortal(scope, command.speaker_id), await mortal(scope, command.target_id)
    if command.aim is PersuasionAim.BELIEF and command.axis is None:
        raise ValidationFailedError("Name the belief the argument is about.")
    ctx = await scope.context("persuasion:attempt")
    argument = await persuade(ctx, speaker.id, target.id, command.appeal, command.aim, axis=command.axis, toward=command.toward)
    told = "won over" if argument.success else "failed to sway"
    return Effect(f"{speaker.name} {told} {target.name} ({argument.score}).", target_node_id=target.id, values={"persuasion_id": argument.record_id or 0})


@player_action("persuasion:remove", ActionKind.OTHER)
async def remove_persuasion(scope: PlayerScope, command: PersuasionTarget) -> Effect:
    row = await scope.session.get(PersuasionRow, command.persuasion_id)
    if row is None:
        raise NotFoundError("No such argument.")
    target = row.target_node_id
    await scope.session.delete(row)
    await scope.session.flush()
    return Effect("The argument was forgotten.", target_node_id=target)
