from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.read_memo import memoized
from aerona.db.tables.polity import TreatyClauseRow, TreatyPartyRow, TreatyProfileRow
from aerona.db.tables.statecraft import PolityRegardRow
from aerona.db.write_guard import held
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind, TreatyStatus
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.war import declare_war

AGAINST = "against"


@dataclass
class CoalitionTally:
    formed: int = 0
    wars: int = 0


@memoized(TreatyClauseRow, TreatyProfileRow)
async def coalition_targets(session: AsyncSession) -> tuple[tuple[int, tuple[object, ...]], ...]:
    rows = await session.scalars(
        select(TreatyClauseRow.treaty_entity_id)
        .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyClauseRow.treaty_entity_id)
        .where(TreatyProfileRow.kind == TreatyKind.COALITION, TreatyProfileRow.status == TreatyStatus.IN_FORCE, TreatyClauseRow.kind == ClauseKind.CALL_TO_ARMS)
    )
    found: list[tuple[int, tuple[object, ...]]] = []
    for treaty_id in dict.fromkeys(rows):
        clauses = await session.scalars(select(TreatyClauseRow.params).where(TreatyClauseRow.treaty_entity_id == treaty_id))
        found.append((treaty_id, tuple(params.get(AGAINST) for params in clauses)))
    return tuple(found)


async def coalitions_against(ctx: TickContext, target_core: int) -> list[int]:
    return [treaty_id for treaty_id, targets in await coalition_targets(ctx.session) if target_core in targets]


async def members_of(ctx: TickContext, treaty_id: int) -> list[int]:
    return list(
        await ctx.session.scalars(
            select(TreatyPartyRow.party_node_id).where(TreatyPartyRow.treaty_entity_id == treaty_id).order_by(TreatyPartyRow.party_node_id)
        )
    )


async def fearful_of(ctx: TickContext, book: RealmBook, target: Realm) -> list[int]:
    threshold = ctx.rules.diplomacy.coalition_threshold
    rows = await ctx.session.scalars(
        select(PolityRegardRow.holder_entity_id)
        .where(PolityRegardRow.subject_entity_id == target.entity.id, PolityRegardRow.threat >= threshold)
        .order_by(PolityRegardRow.holder_entity_id)
    )
    return [realm_id for realm_id in rows if realm_id in book.realms and not held(realm_id)]


async def march(ctx: TickContext, treaty_id: int, target: Realm, target_core: int, tally: CoalitionTally) -> None:
    members = await members_of(ctx, treaty_id)
    lead = await living_entity(ctx.session, members[0]) if members else None
    foe = await living_entity(ctx.session, target_core)
    if lead is None or foe is None or held(lead.id):
        return
    strength = await MilitaryStrength.load(ctx.session, ctx.rules)
    combined = 0.0
    for member in members:
        found = await living_entity(ctx.session, member)
        if found is not None:
            combined += await strength.power(found)
    if combined > await strength.power(foe) and ctx.rng(f"statecraft.coalition_war.{treaty_id}.{ctx.epoch}").chance(ctx.rules.statecraft.coalition_war_pct):
        await declare_war(ctx, lead.id, foe.id, f"the coalition against {target.entity.name} marched", cause=WarCause.HOSTILITY)
        tally.wars += 1


async def band(ctx: TickContext, book: RealmBook, target: Realm, tally: CoalitionTally) -> None:
    target_core = target.profile.core_entity_id
    if target_core is None or held(target.entity.id):
        return
    existing = await coalitions_against(ctx, target_core)
    if existing:
        for treaty_id in existing:
            await march(ctx, treaty_id, target, target_core, tally)
        return
    fearful = [realm_id for realm_id in await fearful_of(ctx, book, target) if realm_id != target.entity.id]
    cores = sorted(
        {core for realm_id in fearful if (core := book.realms[realm_id].profile.core_entity_id) is not None and core != target_core and not held(core)}
    )
    fearful = [realm_id for realm_id in fearful if book.realms[realm_id].profile.core_entity_id in cores]
    if len(cores) < ctx.rules.statecraft.coalition_members:
        return
    await sign(
        ctx,
        TreatyKind.COALITION,
        [(core, PartyRole.SIGNATORY) for core in cores],
        clauses=[Clause(ClauseKind.CALL_TO_ARMS, core, None, {AGAINST: target_core}) for core in cores],
    )
    tally.formed += 1
    await record(
        ctx,
        "statecraft.coalition",
        roles={IncidentRole.TARGET: target.entity.id, IncidentRole.MEMBER: fearful},
        facts={"members": len(cores)},
        steps=tuple(StepDraft(StepAction.SIGN, actor=core) for core in cores),
    )


async def tend_coalitions(ctx: TickContext, tally: CoalitionTally) -> None:
    book = await RealmBook.load(ctx.session)
    for realm in list(book.realms.values()):
        await band(ctx, book, realm, tally)
