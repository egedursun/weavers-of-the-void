from collections.abc import Mapping
from enum import StrEnum

from fastapi import APIRouter, Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.api.dependencies import ServicesDep, reader
from aerona.api.schemas.bonds import BondsView, CircleView, ContestView, PassionView, PersuasionView, RankView, TieView
from aerona.api.schemas.mind import LabelView
from aerona.api.schemas.records import NodeRef
from aerona.api.views.common import node_ref, node_refs
from aerona.catalog.relations import (
    AIM_LABELS,
    APPEALS,
    CIRCLES,
    CONTESTS,
    GROUP_LABELS,
    PASSION_LABELS,
    PASSION_SOURCE_LABELS,
    STAKE_LABELS,
)
from aerona.core.errors import NotFoundError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.relations import ContestRow, GroupRankRow, PassionRow, PersuasionRow, RelationshipRow, SocialCircleRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.mind.book import mind_of
from aerona.rules.registry import Rules

router = APIRouter(tags=["bonds"])
NO_NODE = "Nothing lives there."
GROUP_TYPES = frozenset({EntityType.HOUSE, EntityType.POLITY, EntityType.FACTION, EntityType.VESSEL})
PLACE_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.REGION, EntityType.PEOPLE})
WHY_NOT = "Only mortals hold bonds and passions; households, courts, circles, warbands and crews hold pecking orders; places host circles."


def labels[K: StrEnum](table: Mapping[K, str]) -> list[LabelView]:
    return [LabelView(key=key.value, label=label) for key, label in table.items()]


def ref_of(refs: dict[int, NodeRef], node_id: int | None) -> NodeRef | None:
    return refs.get(node_id) if node_id is not None else None


async def bond_views(session: AsyncSession, node_id: int) -> list[TieView]:
    rows = list(
        await session.scalars(
            select(RelationshipRow).where(RelationshipRow.holder_node_id == node_id).order_by(RelationshipRow.familiarity.desc(), RelationshipRow.id)
        )
    )
    backs = {row.holder_node_id: row for row in await session.scalars(select(RelationshipRow).where(RelationshipRow.subject_node_id == node_id))}
    refs = await node_refs(session, [row.subject_node_id for row in rows])
    views = []
    for row in rows:
        subject = refs.get(row.subject_node_id)
        if subject is None:
            continue
        back = backs.get(row.subject_node_id)
        views.append(
            TieView(
                id=row.id,
                subject=subject,
                friendship=row.friendship,
                romance=row.romance,
                familiarity=row.familiarity,
                rivalry=row.rivalry,
                their_friendship=back.friendship if back is not None else None,
                their_romance=back.romance if back is not None else None,
                kinds=row.kinds,
                affair=row.affair,
                affair_known=row.affair_known,
                since_epoch=row.since_epoch,
                last_epoch=row.last_epoch,
                held=list(row.locked or []),
            )
        )
    return views


async def passion_views(session: AsyncSession, rules: Rules, node_id: int) -> list[PassionView]:
    rows = list(await session.scalars(select(PassionRow).where(PassionRow.holder_node_id == node_id).order_by(PassionRow.strength.desc(), PassionRow.id)))
    refs = await node_refs(session, [row.object_node_id for row in rows])
    return [
        PassionView(
            id=row.id,
            kind=row.kind,
            label=PASSION_LABELS[row.kind],
            object=refs.get(row.object_node_id),
            strength=row.strength,
            source=row.source,
            source_label=PASSION_SOURCE_LABELS[row.source],
            since_epoch=row.since_epoch,
            invoked_epoch=row.invoked_epoch,
            invocable=row.strength >= rules.passions.invoke_at,
            held="strength" in (row.locked or []),
        )
        for row in rows
    ]


async def circle_view(session: AsyncSession, row: SocialCircleRow) -> CircleView | None:
    members = list(
        await session.scalars(
            select(FactionMembershipRow.mortal_entity_id)
            .where(FactionMembershipRow.faction_entity_id == row.faction_entity_id)
            .order_by(FactionMembershipRow.mortal_entity_id)
        )
    )
    profile = await session.get(FactionProfileRow, row.faction_entity_id)
    leader = profile.leader_entity_id if profile is not None else None
    refs = await node_refs(session, [row.faction_entity_id, *members, *(item for item in (row.meeting_place_id, row.ideology_entity_id, leader) if item)])
    circle = refs.get(row.faction_entity_id)
    if circle is None:
        return None
    return CircleView(
        circle=circle,
        kind=row.kind,
        label=CIRCLES[row.kind].label,
        taste_key=row.taste_key,
        axis=row.axis,
        meeting_place=ref_of(refs, row.meeting_place_id),
        ideology=ref_of(refs, row.ideology_entity_id),
        founded_epoch=row.founded_epoch,
        members=[refs[member] for member in members if member in refs],
        leader=ref_of(refs, leader),
        held=list(row.locked or []),
    )


async def circles_for(session: AsyncSession, entity: EntityRow | None, node_id: int) -> list[CircleView]:
    if entity is None:
        return []
    if entity.entity_type is EntityType.MORTAL:
        ids = select(FactionMembershipRow.faction_entity_id).where(FactionMembershipRow.mortal_entity_id == node_id)
        query = select(SocialCircleRow).where(SocialCircleRow.faction_entity_id.in_(ids))
    elif entity.entity_type is EntityType.FACTION:
        query = select(SocialCircleRow).where(SocialCircleRow.faction_entity_id == node_id)
    else:
        query = select(SocialCircleRow).where(SocialCircleRow.meeting_place_id == node_id)
    views = [await circle_view(session, row) for row in await session.scalars(query.order_by(SocialCircleRow.faction_entity_id))]
    return [view for view in views if view is not None]


async def rank_views(session: AsyncSession, rows: list[GroupRankRow]) -> list[RankView]:
    groups = {row.group_node_id for row in rows}
    sizes = {group: len(list(await session.scalars(select(GroupRankRow.member_node_id).where(GroupRankRow.group_node_id == group)))) for group in groups}
    refs = await node_refs(session, [*groups, *(row.member_node_id for row in rows)])
    views = []
    for row in rows:
        group, member = refs.get(row.group_node_id), refs.get(row.member_node_id)
        if group is None or member is None:
            continue
        views.append(
            RankView(
                group=group,
                group_kind=row.group_kind,
                group_label=GROUP_LABELS[row.group_kind],
                member=member,
                rank=row.rank,
                dominance=row.dominance,
                size=sizes.get(row.group_node_id, 1),
                since_epoch=row.since_epoch,
                held=list(row.locked or []),
            )
        )
    return views


async def contest_views(session: AsyncSession, node_id: int) -> list[ContestView]:
    rows = list(
        await session.scalars(
            select(ContestRow)
            .where(or_(ContestRow.challenger_node_id == node_id, ContestRow.defender_node_id == node_id, ContestRow.place_node_id == node_id))
            .order_by(ContestRow.epoch.desc(), ContestRow.id.desc())
        )
    )
    wanted = [
        item
        for row in rows
        for item in (row.challenger_node_id, row.defender_node_id, row.judge_node_id, row.stake_node_id, row.place_node_id, row.work_node_id)
        if item
    ]
    refs = await node_refs(session, wanted)
    return [
        ContestView(
            id=row.id,
            kind=row.kind,
            label=CONTESTS[row.kind].label,
            stake=row.stake,
            stake_label=STAKE_LABELS[row.stake],
            challenger=refs.get(row.challenger_node_id),
            defender=refs.get(row.defender_node_id),
            judge=ref_of(refs, row.judge_node_id),
            stake_node=ref_of(refs, row.stake_node_id),
            place=ref_of(refs, row.place_node_id),
            wager=row.wager,
            rounds=row.rounds,
            outcome=row.outcome,
            famous=row.famous,
            work=ref_of(refs, row.work_node_id),
            epoch=row.epoch,
            note=row.note,
        )
        for row in rows
    ]


async def persuasion_views(session: AsyncSession, node_id: int) -> list[PersuasionView]:
    rows = list(
        await session.scalars(
            select(PersuasionRow)
            .where(or_(PersuasionRow.speaker_node_id == node_id, PersuasionRow.target_node_id == node_id))
            .order_by(PersuasionRow.epoch.desc(), PersuasionRow.id.desc())
        )
    )
    refs = await node_refs(session, [item for row in rows for item in (row.speaker_node_id, row.target_node_id, row.subject_node_id) if item])
    return [
        PersuasionView(
            id=row.id,
            speaker=refs.get(row.speaker_node_id),
            target=refs.get(row.target_node_id),
            appeal=row.appeal,
            appeal_label=APPEALS[row.appeal].label,
            aim=row.aim,
            aim_label=AIM_LABELS[row.aim],
            axis=row.axis,
            subject=ref_of(refs, row.subject_node_id),
            score=row.score,
            success=row.success,
            epoch=row.epoch,
        )
        for row in rows
    ]


@router.get("/bonds/{node_id}", response_model=BondsView)
async def bonds_view(services: ServicesDep, node_id: int = Path(ge=1)) -> BondsView:
    async with reader(services) as session:
        ref = await node_ref(session, node_id)
        if ref is None:
            raise NotFoundError(NO_NODE)
        rules = services.rules.current
        entity = await session.get(EntityRow, node_id)
        kind = entity.entity_type if entity is not None else None
        mortal = kind is EntityType.MORTAL
        grouped = kind in GROUP_TYPES
        applies = mortal or grouped or kind in PLACE_TYPES
        mind = await mind_of(session, node_id)
        locks = set(mind.locked or []) if mind is not None else set()
        mine = list(await session.scalars(select(GroupRankRow).where(GroupRankRow.member_node_id == node_id).order_by(GroupRankRow.group_node_id)))
        order = list(await session.scalars(select(GroupRankRow).where(GroupRankRow.group_node_id == node_id).order_by(GroupRankRow.rank)))
        return BondsView(
            node_id=node_id,
            name=ref.name,
            applies=applies,
            mortal=mortal,
            place=kind in PLACE_TYPES,
            reason=None if applies else WHY_NOT,
            bonds_held="relations" in locks,
            passions_held="passions" in locks,
            bonds=await bond_views(session, node_id) if mortal else [],
            passions=await passion_views(session, rules, node_id) if mortal else [],
            circles=await circles_for(session, entity, node_id) if applies else [],
            ranks=await rank_views(session, mine) if mortal else [],
            order=await rank_views(session, order) if grouped else [],
            contests=await contest_views(session, node_id) if applies else [],
            persuasions=await persuasion_views(session, node_id) if mortal else [],
            circle_kinds=[LabelView(key=key.value, label=spec.label) for key, spec in CIRCLES.items()],
            passion_kinds=labels(PASSION_LABELS),
            passion_sources=labels(PASSION_SOURCE_LABELS),
            appeals=[LabelView(key=key.value, label=spec.label) for key, spec in APPEALS.items()],
            aims=labels(AIM_LABELS),
            contest_kinds=[LabelView(key=key.value, label=spec.label) for key, spec in CONTESTS.items()],
            stakes=labels(STAKE_LABELS),
        )
