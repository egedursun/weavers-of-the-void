from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.war_causes import WAR_CAUSES
from aerona.catalog.life.polity import ENVOYS
from aerona.catalog.life_traits import TREATY_KIND_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow, TreatyPartyRow, TreatyProfileRow
from aerona.db.tables.settlement import DistrictRow
from aerona.db.tables.statecraft import DiplomacyProfileRow, PolityRegardRow, SphereRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import TreatyKindTrait
from aerona.domain.enums.mind import MemoryKind, SkillKind
from aerona.domain.enums.polity import OfficeKind, TreatyKind, TreatyStatus
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.mind.book import Values, skill_level, values_for
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.services.community_relations import change_relation

THREAT = "threat"
TRUST = "trust"
MIDDLE = PERCENT // 2
KEPT_KINDS = having(TREATY_KIND_TRAITS, TreatyKindTrait.KEPT_KINDS)


@dataclass
class RegardTally:
    strained: int = 0


async def regard_of(ctx: TickContext, holder_id: int, subject_id: int) -> PolityRegardRow:
    row = await ctx.session.get(PolityRegardRow, (holder_id, subject_id))
    if row is None:
        row = PolityRegardRow(holder_entity_id=holder_id, subject_entity_id=subject_id, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


def borders(book: RealmBook, first: Realm, second: Realm) -> bool:
    for mine in first.territory:
        for theirs in second.territory:
            hops = book.atlas.region_hops(mine, theirs)
            if hops is not None and hops <= 1:
                return True
    return False


UNKNOWN_DISTANCE = PERCENT // 2


def value_distance(first: Values, second: Values) -> int:
    axes = set(first) | set(second)
    if not axes:
        return UNKNOWN_DISTANCE
    return round_half_up(sum(abs(first.get(axis, 0) - second.get(axis, 0)) for axis in axes) / len(axes) / 2)


async def core_values(ctx: TickContext, realm: Realm) -> Values:
    core = realm.profile.core_entity_id
    return await values_for(ctx.session, core) if core is not None else {}


async def shift_regard(ctx: TickContext, holder_id: int, subject_id: int, *, threat: int = 0, trust: int = 0) -> None:
    if holder_id == subject_id or held(holder_id):
        return
    row = await regard_of(ctx, holder_id, subject_id)
    if threat and THREAT not in row.locked:
        row.threat = clamp_int(row.threat + threat, 0, PERCENT)
    if trust and TRUST not in row.locked:
        row.trust = clamp_int(row.trust + trust, 0, PERCENT)
    row.epoch = ctx.epoch


async def alarm(ctx: TickContext, aggressor_id: int, amount: int, book: RealmBook | None = None) -> int:
    book = book or await RealmBook.load(ctx.session)
    aggressor = book.realm_for(aggressor_id)
    if aggressor is None or amount <= 0:
        return 0
    table = ctx.rules.statecraft
    theirs = await core_values(ctx, aggressor)
    heard = 0
    for realm in book.realms.values():
        if realm.entity.id == aggressor.entity.id or realm.entity.world_id != aggressor.entity.world_id:
            continue
        near = 1.0 if borders(book, realm, aggressor) else table.far_threat_pct / PERCENT
        distance = value_distance(await core_values(ctx, realm), theirs)
        felt = round_half_up(amount * near * (1 + distance * table.distance_threat_pct / PERCENT / PERCENT))
        await shift_regard(ctx, realm.entity.id, aggressor.entity.id, threat=felt)
        heard += 1
    return heard


async def on_conquest(ctx: TickContext, conqueror_id: int) -> int:
    return await alarm(ctx, conqueror_id, ctx.rules.statecraft.conquest_threat)


async def on_war(ctx: TickContext, aggressor_id: int, cause: WarCause | None) -> int:
    if cause is not None and WAR_CAUSES[cause].within_realm:
        return 0
    return await alarm(ctx, aggressor_id, ctx.rules.statecraft.war_threat)


async def living_realm(ctx: TickContext, polity_id: int) -> bool:
    entity = await ctx.session.get(EntityRow, polity_id)
    found = entity is not None and entity.entity_type is EntityType.POLITY and entity.status is EntityStatus.CANON
    return found and await ctx.session.get(PolityProfileRow, polity_id) is not None


@memoized(PolityMemberRow)
async def member_polities(session: AsyncSession, node_id: int) -> tuple[int, ...]:
    return tuple(await session.scalars(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == node_id)))


async def realm_ids(ctx: TickContext, node_id: int | None) -> int | None:
    if node_id is None:
        return None
    if await living_realm(ctx, node_id):
        return node_id
    for polity_id in await member_polities(ctx.session, node_id):
        if await living_realm(ctx, polity_id):
            return polity_id
    return None


async def on_breach(ctx: TickContext, breaker_id: int, wronged: list[int]) -> None:
    table = ctx.rules.statecraft
    breaker = await realm_ids(ctx, breaker_id)
    if breaker is None:
        return
    book = await RealmBook.load(ctx.session)
    await alarm(ctx, breaker, table.breach_threat, book)
    for realm in book.realms.values():
        if realm.entity.id != breaker and realm.entity.world_id == book.realms[breaker].entity.world_id:
            await shift_regard(ctx, realm.entity.id, breaker, trust=-table.witness_trust)
    for party in wronged:
        victim = await realm_ids(ctx, party)
        if victim is not None and victim != breaker:
            await shift_regard(ctx, victim, breaker, trust=-table.breach_trust)


async def on_kept(ctx: TickContext, parties: list[int], kind: TreatyKind) -> None:
    if kind not in KEPT_KINDS:
        return
    realms = [found for party in parties if (found := await realm_ids(ctx, party)) is not None]
    for first in realms:
        for second in realms:
            if first != second:
                await shift_regard(ctx, first, second, trust=ctx.rules.statecraft.kept_trust)


async def on_marriage(ctx: TickContext, first: int, second: int) -> None:
    one, two = await realm_ids(ctx, first), await realm_ids(ctx, second)
    if one is None or two is None or one == two:
        return
    soothe = -ctx.rules.statecraft.marriage_threat
    await shift_regard(ctx, one, two, threat=soothe)
    await shift_regard(ctx, two, one, threat=soothe)


async def fade(ctx: TickContext) -> None:
    table = ctx.rules.statecraft
    for row in await ctx.session.scalars(select(PolityRegardRow)):
        if held(row.holder_entity_id) or held(row.subject_entity_id):
            continue
        if THREAT not in row.locked:
            row.threat = clamp_int(row.threat - table.threat_decay, 0, PERCENT)
        if TRUST not in row.locked and row.trust != MIDDLE:
            step = min(table.trust_drift, abs(row.trust - MIDDLE))
            row.trust += step if row.trust < MIDDLE else -step


async def embassies_of(ctx: TickContext, realm: Realm) -> int:
    posted = sum(1 for office in realm.offices if office.kind is OfficeKind.AMBASSADOR and office.holder_entity_id is not None)
    members = list(realm.members)
    quarters = (
        len(
            list(
                await ctx.session.scalars(
                    select(DistrictRow.id).where(DistrictRow.settlement_entity_id.in_(members), DistrictRow.kind == DistrictKind.FOREIGN_QUARTER)
                )
            )
        )
        if members
        else 0
    )
    return posted + quarters


async def relations_of(ctx: TickContext, realm: Realm) -> list[int]:
    core = realm.profile.core_entity_id
    if core is None:
        return []
    return list(await partners_of(ctx.session, core, realm.entity.id))


@memoized(TreatyProfileRow, TreatyPartyRow, SphereRow)
async def partners_of(session: AsyncSession, core: int, realm_id: int) -> tuple[int, ...]:
    treaties = await session.scalars(
        select(TreatyProfileRow.treaty_entity_id)
        .join(TreatyPartyRow, TreatyPartyRow.treaty_entity_id == TreatyProfileRow.treaty_entity_id)
        .where(TreatyPartyRow.party_node_id == core, TreatyProfileRow.status == TreatyStatus.IN_FORCE, TreatyProfileRow.kind.in_(list(KEPT_KINDS)))
    )
    partners: list[int] = []
    for treaty_id in treaties:
        for party in await session.scalars(select(TreatyPartyRow.party_node_id).where(TreatyPartyRow.treaty_entity_id == treaty_id)):
            if party != core:
                partners.append(party)
    clients = await session.scalars(select(SphereRow.client_entity_id).where(SphereRow.power_entity_id == realm_id))
    return (*partners, *clients)


async def capacity_of(ctx: TickContext, realm: Realm) -> int:
    table = ctx.rules.statecraft
    skill = 0
    for office in realm.offices:
        if office.kind in ENVOYS and office.holder_entity_id is not None:
            skill += await skill_level(ctx.session, office.holder_entity_id, SkillKind.NEGOTIATION)
    return (
        table.capacity_base
        + realm.profile.administration // table.capacity_admin
        + skill // table.capacity_skill
        + await embassies_of(ctx, realm) * table.capacity_embassy
    )


async def weigh_capacity(ctx: TickContext, book: RealmBook, realm: Realm, tally: RegardTally) -> None:
    row = await ctx.session.get(DiplomacyProfileRow, realm.entity.id)
    if row is None:
        row = DiplomacyProfileRow(polity_entity_id=realm.entity.id, locked=[])
        ctx.session.add(row)
    partners = await relations_of(ctx, realm)
    if "capacity" not in row.locked:
        row.capacity = await capacity_of(ctx, realm)
    if "relations" not in row.locked:
        row.relations = len(partners)
    if "strain" not in row.locked:
        row.strain = max(0, row.relations - row.capacity)
    row.epoch = ctx.epoch
    core = realm.profile.core_entity_id
    if row.strain <= 0 or core is None:
        return
    for partner in partners:
        if not held(partner):
            await change_relation(ctx, core, partner, -row.strain * ctx.rules.statecraft.strain_decay, MemoryKind.ILL_WILL, note="a relation left untended")
    tally.strained += 1


async def tend_regard(ctx: TickContext, tally: RegardTally) -> None:
    await fade(ctx)
    book = await RealmBook.load(ctx.session)
    for realm in list(book.realms.values()):
        if held(realm.entity.id):
            continue
        await weigh_capacity(ctx, book, realm, tally)
