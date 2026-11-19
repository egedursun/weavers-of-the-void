from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from aerona.constants.units import PERCENT
from aerona.db.fast_session import rows_by_prefix
from aerona.db.read_memo import memoized
from aerona.db.tables.communication import APPROVAL_MAX, APPROVAL_MIN, PublicOpinionRow
from aerona.db.tables.culture import ArtworkProfileRow, IdeologyAdherentRow, RumourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultHoldingRow
from aerona.db.tables.interconnect import IncidentParticipantRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.communication import OpinionSubject
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EngineKind, EntityStatus
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LawKind, OfficeKind
from aerona.domain.enums.war import WarStatus
from aerona.engine.belonging.mockery import sting
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import tech_factor
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import values_for
from aerona.engine.polity.laws import LawBook, discord
from aerona.engine.primitives.faith import patron_node
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat, stat_or

HALF = PERCENT // 2
APPROVAL = "approval"
TEMPLE = aliased(EntityRow)


@dataclass
class OpinionTally:
    formed: int = 0
    censorship_found: int = 0


async def realm_of_member(ctx: TickContext, community_id: int) -> int | None:
    found: int | None = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    return found


@memoized(OfficeRow)
async def realm_ruler(session: AsyncSession, realm_id: int) -> int | None:
    found: int | None = await session.scalar(
        select(OfficeRow.holder_entity_id).where(OfficeRow.polity_entity_id == realm_id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    return found


async def ruler_of(ctx: TickContext, realm_id: int) -> int | None:
    return await realm_ruler(ctx.session, realm_id)


async def has_office(ctx: TickContext, realm_id: int, kind: OfficeKind) -> bool:
    found = await ctx.session.scalar(
        select(OfficeRow.id).where(OfficeRow.polity_entity_id == realm_id, OfficeRow.kind == kind, OfficeRow.holder_entity_id.is_not(None)).limit(1)
    )
    return found is not None


async def renown_tone(ctx: TickContext, subject_id: int) -> int:
    profile = await ctx.session.get(MortalProfileRow, subject_id)
    if profile is None:
        return 0
    gap = profile.renown - profile.infamy
    return (gap > 0) - (gap < 0)


@memoized(RumourRow, IncidentParticipantRow)
async def rumours_heard(session: AsyncSession, epoch: int) -> dict[tuple[int, int], int]:
    statement = (
        select(RumourRow.carrier_entity_id, IncidentParticipantRow.node_id, func.count(RumourRow.id))
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == RumourRow.incident_id)
        .where(RumourRow.epoch == epoch)
        .group_by(RumourRow.carrier_entity_id, IncidentParticipantRow.node_id)
    )
    return {(carrier, node): count for carrier, node, count in await session.execute(statement)}


async def rumours_of(ctx: TickContext, community_id: int, subject_id: int) -> int:
    return (await rumours_heard(ctx.session, ctx.epoch)).get((community_id, subject_id), 0)


@memoized(ArtworkProfileRow)
async def artworks_about(session: AsyncSession) -> dict[int, int]:
    statement = select(ArtworkProfileRow.subject_node_id, func.count(ArtworkProfileRow.artwork_entity_id)).group_by(ArtworkProfileRow.subject_node_id)
    return {subject: count for subject, count in await session.execute(statement) if subject is not None}


async def propaganda(ctx: TickContext, subject_id: int) -> int:
    return (await artworks_about(ctx.session)).get(subject_id, 0)


async def voice(ctx: TickContext, community: EntityRow, subject_id: int, laws: LawBook, realm_id: int | None) -> float:
    table = ctx.rules.communication
    heard = await rumours_of(ctx, community.id, subject_id)
    tone = await renown_tone(ctx, subject_id)
    weight: float = heard * table.rumour_weight * tone
    if await has_technique(ctx.session, community.id, Technique.PRINTING):
        weight *= 1 + table.broadsheet_pct / PERCENT
    law = laws.in_force(realm_id, LawKind.CENSORSHIP) if realm_id is not None else None
    if law is not None and weight < 0:
        strictness = int(law.params.get("strictness") or 0)
        weight *= max(0.0, 1 - strictness / PERCENT * table.censorship_pct / PERCENT)
    return weight + await propaganda(ctx, subject_id) * table.propaganda_approval


async def sermons(ctx: TickContext, community: EntityRow, god: int) -> float:
    cults = await ctx.session.scalars(
        select(EntityRow)
        .join(CultHoldingRow, CultHoldingRow.cult_entity_id == EntityRow.id)
        .join(TEMPLE, TEMPLE.id == CultHoldingRow.holding_entity_id)
        .where(TEMPLE.engine_kind == EngineKind.TEMPLE, TEMPLE.status == EntityStatus.CANON, TEMPLE.location_id == community.id)
        .where(EntityRow.status == EntityStatus.CANON)
    )
    zeal = 0.0
    for cult in cults:
        if await patron_node(ctx.session, cult) == god:
            zeal += (stat(cult, "zeal") or 0) / PERCENT
    return zeal * ctx.rules.communication.sermon_approval


async def ruler_target(ctx: TickContext, community: EntityRow, ruler_id: int, realm_id: int) -> float:
    town = await ctx.session.get(SettlementProfileRow, community.id)
    unrest = town.unrest if town is not None else HALF
    prosperity = stat_or(community, "prosperity", HALF)
    profile = await ctx.session.get(MortalProfileRow, ruler_id)
    fame = (profile.renown - profile.infamy) / 4 if profile is not None else 0
    herald = ctx.rules.communication.herald_approval if await has_office(ctx, realm_id, OfficeKind.HERALD) else 0
    realm = await ctx.session.get(PolityProfileRow, realm_id)
    graft = realm.corruption * ctx.rules.affairs.disapproval_pct / PERCENT if realm is not None else 0
    mocked = await sting(ctx.session, ctx.rules, ruler_id, ctx.epoch)
    return (prosperity - HALF) / 2 + (HALF - unrest) / 2 + fame + herald - graft - mocked


async def subjects_of(ctx: TickContext, community: EntityRow, realm_id: int | None, laws: LawBook) -> list[tuple[int, OpinionSubject, float]]:
    found: list[tuple[int, OpinionSubject, float]] = []
    values = await values_for(ctx.session, community.id)
    if realm_id is not None:
        ruler = await ruler_of(ctx, realm_id)
        if ruler is not None:
            found.append((ruler, OpinionSubject.RULER, await ruler_target(ctx, community, ruler, realm_id)))
        sides = await ctx.session.scalars(
            select(WarSideRow)
            .join(WarRow, WarRow.id == WarSideRow.war_id)
            .where(WarSideRow.entity_id == realm_id, WarSideRow.left_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
        )
        for side in list(sides):
            enemy = await ctx.session.scalar(
                select(WarSideRow.entity_id).where(WarSideRow.war_id == side.war_id, WarSideRow.side != side.side).order_by(WarSideRow.entity_id).limit(1)
            )
            if enemy is not None:
                found.append((enemy, OpinionSubject.WAR, values.get(ValueAxis.MARTIAL, 0) / 2 - side.weariness / 2))
        for law_id in laws.by_node.get(realm_id, []):
            profile = laws.profiles.get(law_id)
            if profile is not None:
                found.append((law_id, OpinionSubject.LAW, HALF / 2 - discord(profile.kind, profile.params, values)))
    for creed in await ctx.session.scalars(
        select(IdeologyAdherentRow).where(IdeologyAdherentRow.adherent_entity_id == community.id).order_by(IdeologyAdherentRow.ideology_entity_id)
    ):
        found.append((creed.ideology_entity_id, OpinionSubject.IDEOLOGY, creed.strength - HALF / 2))
    god = await patron_node(ctx.session, community)
    if god is not None:
        piety = stat_or(community, "piety", HALF)
        found.append((god, OpinionSubject.GOD, piety - HALF + values.get(ValueAxis.PIETY, 0) / 4 + await sermons(ctx, community, god)))
    return found


async def tend_community(ctx: TickContext, community: EntityRow, laws: LawBook, tally: OpinionTally) -> None:
    table = ctx.rules.communication
    realm_id = await realm_of_member(ctx, community.id)
    subjects = await subjects_of(ctx, community, realm_id, laws)
    stored = {row.subject_node_id: row for row in await rows_by_prefix(ctx.session, PublicOpinionRow, community.id)}
    for subject_id, subject, target in subjects:
        aim = clamp_int(target + await voice(ctx, community, subject_id, laws, realm_id), APPROVAL_MIN, APPROVAL_MAX)
        row = stored.get(subject_id)
        if row is None:
            row = PublicOpinionRow(community_node_id=community.id, subject_node_id=subject_id, subject=subject, approval=0, epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
            stored[subject_id] = row
        if APPROVAL in (row.locked or []):
            continue
        row.subject, row.epoch = subject, ctx.epoch
        drift = table.opinion_drift_pct * await tech_factor(ctx.session, ctx.rules, community.id, EraChannel.OPINION)
        row.approval = clamp_int(row.approval + round_half_up((aim - row.approval) * min(PERCENT, drift) / PERCENT), APPROVAL_MIN, APPROVAL_MAX)
        tally.formed += 1
        law = laws.in_force(realm_id, LawKind.CENSORSHIP) if realm_id is not None else None
        noticed = ctx.rng(f"opinion.censored.{community.id}.{ctx.epoch}").chance(table.censorship_found_pct)
        if subject is OpinionSubject.RULER and law is not None and not row.censored and noticed:
            row.censored = True
            row.approval = clamp_int(row.approval - table.censorship_distrust, APPROVAL_MIN, APPROVAL_MAX)
            tally.censorship_found += 1


async def tend_opinion(ctx: TickContext, communities: list[EntityRow], tally: OpinionTally) -> None:
    laws = await LawBook.load(ctx.session)
    for community in communities:
        if not held(community.id):
            await tend_community(ctx, community, laws, tally)


async def mean_approval(ctx: TickContext, members: list[int], subject_id: int | None) -> float:
    if subject_id is None or not members:
        return 0.0
    found = await ctx.session.scalar(
        select(func.avg(PublicOpinionRow.approval)).where(PublicOpinionRow.community_node_id.in_(members), PublicOpinionRow.subject_node_id == subject_id)
    )
    return float(found or 0)


async def approval_of(ctx: TickContext, community_id: int, subject_id: int) -> int:
    row = await ctx.session.get(PublicOpinionRow, (community_id, subject_id))
    return row.approval if row is not None else 0
