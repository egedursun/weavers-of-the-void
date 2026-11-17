from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.discovery import DANGEROUS_BRANCHES
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import BookContentRow, IdeologyAdherentRow
from aerona.db.tables.discovery import BannedWorkRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import held_by
from aerona.engine.lore.learning import realm_of
from aerona.engine.polity.laws import LawBook
from aerona.engine.recording.record import record as record_incident
from aerona.rules.registry import Rules

PRINTED = (Technique.PRINTING, Technique.PRINTING_PRESS)


async def printed(session: AsyncSession, holder_id: int | None) -> bool:
    if holder_id is None:
        return False
    return not (await held_by(session, holder_id)).isdisjoint(PRINTED)


async def scribe_pace(session: AsyncSession, rules: Rules, community_id: int | None) -> float:
    if await printed(session, community_id):
        return 1.0
    society = await session.get(CommunitySocietyRow, community_id) if community_id is not None else None
    share = society.share_scribe if society is not None else 0.0
    return min(1.0, share / rules.discovery.copy_scribes_pct)


async def banned_in(session: AsyncSession, realm_id: int | None, work_id: int) -> bool:
    if realm_id is None:
        return False
    return await session.get(BannedWorkRow, (realm_id, work_id)) is not None


async def banned_for(session: AsyncSession, community_id: int | None, work_id: int) -> bool:
    if community_id is None:
        return False
    return await banned_in(session, await realm_of(session, community_id), work_id)


async def read_in_secret(ctx: TickContext, reader_id: int, work_id: int) -> bool:
    return ctx.rng(f"banned_reading.{reader_id}.{work_id}.{ctx.epoch}").chance(ctx.rules.discovery.ban_reading_pct)


async def forbidden_books(session: AsyncSession, members: list[int]) -> set[int]:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id.in_(members), BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    dark = select(EntityRow.id).where(EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.knowledge_branch.in_(list(DANGEROUS_BRANCHES)))
    rows = await session.scalars(
        select(BookContentRow.book_entity_id).where(BookContentRow.book_entity_id.in_(owned), BookContentRow.knowledge_entity_id.in_(dark))
    )
    return set(rows)


async def rival_creeds(session: AsyncSession, members: list[int], state_creed: int | None) -> set[int]:
    rows = await session.scalars(select(IdeologyAdherentRow.ideology_entity_id).where(IdeologyAdherentRow.adherent_entity_id.in_(members)))
    return {creed for creed in rows if creed != state_creed}


async def censor(ctx: TickContext) -> int:
    table = ctx.rules.discovery
    laws = await LawBook.load(ctx.session)
    banned = 0
    for profile in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        realm = await ctx.session.get(EntityRow, profile.polity_entity_id)
        law = laws.in_force(profile.polity_entity_id, LawKind.CENSORSHIP)
        if realm is None or realm.status is not EntityStatus.CANON or law is None or held(realm.id):
            continue
        strictness = law.params.get("strictness", 0)
        if not isinstance(strictness, int) or strictness < table.ban_strictness:
            continue
        members = [realm.id, *await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm.id))]
        works = await forbidden_books(ctx.session, members) | await rival_creeds(ctx.session, members, profile.ideology_entity_id)
        for work in sorted(works):
            if await banned_in(ctx.session, realm.id, work):
                continue
            ctx.session.add(BannedWorkRow(polity_entity_id=realm.id, work_entity_id=work, since_epoch=ctx.epoch, locked=[]))
            banned += 1
            await record_incident(ctx, "discovery.work_banned", roles={IncidentRole.AUTHORITY: realm.id, IncidentRole.TARGET: work})
    await ctx.session.flush()
    return banned
