from sqlalchemy import func, or_, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import BattleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import EntityFlag, EntityType, MortalRole
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import MemoryKind, TraitKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.context import TickContext
from aerona.engine.faith.book import Church, FaithBook
from aerona.engine.faith.doctrine import clergy_of, liturgy_reach
from aerona.engine.mind.book import traits_of
from aerona.engine.mind.memories import remember
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat

HALF = 2
TENTH = 10
VICES = frozenset({TraitKind.GREEDY, TraitKind.LUSTFUL, TraitKind.GLUTTONOUS, TraitKind.CRUEL, TraitKind.DECEITFUL})
DOOM_SKIES = frozenset({SkyEventKind.ECLIPSE, SkyEventKind.BLACK_SUN, SkyEventKind.SUPERNOVA, SkyEventKind.VOID_STORM})


async def persecutors(ctx: TickContext, church: Church, book: FaithBook, laws: LawBook) -> list[tuple[EntityRow, int]]:
    god = church.god.id if church.god is not None else None
    found: list[tuple[EntityRow, int]] = []
    for member in church.members:
        if laws.param(member.id, LawKind.RELIGIOUS_TOLERANCE, "level") != "persecution":
            continue
        realm_id = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == member.id).limit(1))
        realm = await ctx.session.get(PolityProfileRow, realm_id) if realm_id is not None else None
        if realm is not None and realm.state_religion_id is not None and book.faith.patron(realm.state_religion_id) != god:
            found.append((member, realm.polity_entity_id))
    return found


async def persecuted(ctx: TickContext, church: Church, book: FaithBook, laws: LawBook) -> bool:
    table = ctx.rules.zeal
    for member, polity in await persecutors(ctx, church, book, laws):
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=member.id,
            subject_id=polity,
            kind=MemoryKind.DESECRATED_HOLY,
            magnitude=-table.persecution_grievance,
            epoch=ctx.epoch,
            note="persecuted for the faith",
        )
    homes = [member.id for member in church.members]
    if not homes:
        return False
    fresh = await ctx.session.scalar(
        select(MemoryRow.id)
        .where(
            MemoryRow.holder_node_id.in_(homes),
            MemoryRow.kind == MemoryKind.DESECRATED_HOLY,
            MemoryRow.magnitude < 0,
            MemoryRow.epoch >= ctx.epoch - table.persecution_memory_epochs,
        )
        .limit(1)
    )
    return fresh is not None


async def doom_omens(ctx: TickContext, church: Church) -> int:
    world = church.cult.world_id
    skies = await ctx.session.scalar(
        select(func.count(SkyEventRow.id)).where(
            SkyEventRow.kind.in_(list(DOOM_SKIES)),
            SkyEventRow.epoch <= ctx.epoch,
            or_(SkyEventRow.until_epoch.is_(None), SkyEventRow.until_epoch >= ctx.epoch),
            SkyEventRow.epoch >= ctx.epoch - 1,
            or_(SkyEventRow.world_id == world, SkyEventRow.world_id.is_(None)),
        )
    )
    omens = await ctx.session.scalar(
        select(func.count())
        .select_from(EntityFlagRow)
        .join(EntityRow, EntityRow.id == EntityFlagRow.entity_id)
        .where(EntityFlagRow.flag == EntityFlag.OMEN, EntityFlagRow.epoch == ctx.epoch, EntityRow.world_id == world)
    )
    return int(skies or 0) + int(omens or 0)


async def scandals(ctx: TickContext, church: Church) -> list[EntityRow]:
    revealed: list[EntityRow] = []
    for priest in await clergy_of(ctx, church):
        if not set(await traits_of(ctx.session, priest.id)) & VICES:
            continue
        if ctx.rng(f"scandal.{church.cult.id}.{priest.id}.{ctx.epoch}").chance(ctx.rules.zeal.scandal_chance):
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=church.cult.id,
                subject_id=priest.id,
                kind=MemoryKind.BETRAYED_ME,
                magnitude=-ctx.rules.zeal.scandal,
                epoch=ctx.epoch,
                note="a vice of the clergy came to light",
            )
            revealed.append(priest)
    return revealed


async def martyrs(ctx: TickContext, church: Church) -> int:
    homes = [member.id for member in church.members]
    if not homes:
        return 0
    killed = select(BondRow.target_node_id).where(BondRow.kind == BondKind.KILLED, BondRow.epoch == ctx.epoch)
    found = await ctx.session.scalar(
        select(func.count(EntityRow.id)).where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.location_id.in_(homes),
            EntityRow.mortal_role.in_([MortalRole.PRIEST, MortalRole.SAINT]),
            EntityRow.end_epoch == ctx.epoch,
            EntityRow.id.in_(killed),
        )
    )
    return int(found or 0)


async def miracles(ctx: TickContext, church: Church) -> int:
    if church.god is None:
        return 0
    found = await ctx.session.scalar(select(func.count(ChronicleRow.id)).where(ChronicleRow.son_id == church.god.id, ChronicleRow.epoch == ctx.epoch))
    return int(found or 0)


async def holy_victories(ctx: TickContext, church: Church, book: FaithBook) -> int:
    if not church.holds(TenetKind.HOLY_WAR) or church.god is None:
        return 0
    homes = {member.id for member in church.members}
    rows = await ctx.session.scalars(select(BattleRow).where(BattleRow.epoch == ctx.epoch, BattleRow.winner_entity_id.in_(list(homes))))
    return sum(1 for row in rows if book.faith.patron(row.loser_entity_id) != church.god.id)


async def crisis(ctx: TickContext, church: Church, atlas: RegionAtlas) -> bool:
    regions = {atlas.top_region(member.id) for member in church.members} - {None}
    if regions:
        raging = await ctx.session.scalar(
            select(func.count(OutbreakRow.id)).where(OutbreakRow.region_entity_id.in_(list(regions)), OutbreakRow.status != OutbreakStatus.ENDED)
        )
        if raging:
            return True
    for member in church.members:
        society = await ctx.session.get(CommunitySocietyRow, member.id)
        if society is not None and society.stock_food <= 0:
            return True
    return False


async def mocked(ctx: TickContext, church: Church) -> int:
    if church.god is None:
        return 0
    prophecies = select(EntityRow.id).where(EntityRow.entity_type == EntityType.PROPHECY, EntityRow.creator_son_id == church.god.id)
    found = await ctx.session.scalar(
        select(func.count()).where(EntityFlagRow.flag == EntityFlag.MOCKED, EntityFlagRow.epoch == ctx.epoch, EntityFlagRow.entity_id.in_(prophecies))
    )
    return int(found or 0)


async def zeal_parts(ctx: TickContext, church: Church, book: FaithBook, *, laws: LawBook, atlas: RegionAtlas) -> dict[str, int]:
    table = ctx.rules.zeal
    doctrine = church.doctrine
    parts: dict[str, int] = {"quiet years": -table.decay}
    if await persecuted(ctx, church, book, laws):
        parts["persecution"] = table.persecution
    fallen = await martyrs(ctx, church)
    if fallen:
        parts["martyrs"] = fallen * table.martyrdom * (HALF if church.holds(TenetKind.MARTYRDOM_GLORY) else 1)
    if await miracles(ctx, church):
        parts["miracles of the god"] = table.miracle
    won = await holy_victories(ctx, church, book)
    if won:
        parts["holy victories"] = won * table.holy_victory
    if doctrine is not None and doctrine.clergy_quality:
        preaching = round_half_up(doctrine.clergy_quality * table.preaching_pct / PERCENT / TENTH * HALF)
        parts["preaching"] = round_half_up(preaching * await liturgy_reach(ctx, church) / PERCENT)
    if await crisis(ctx, church, atlas):
        parts["plague and hunger"] = table.crisis
    omens = await doom_omens(ctx, church)
    if omens:
        parts["doom omens"] = omens * table.doom_omen
    if church.members and not church.holds(TenetKind.ASCETICISM):
        wealth = sum(stat(member, "prosperity") or 0 for member in church.members) / len(church.members)
        comfort = round_half_up(wealth * table.prosperity_pct / PERCENT / TENTH * HALF)
        if comfort:
            parts["comfort"] = -comfort
    fallen_clergy = await scandals(ctx, church)
    if fallen_clergy:
        parts["a clergy scandal"] = -table.scandal * len(fallen_clergy)
    failed = await mocked(ctx, church)
    if failed:
        parts["failed prophecy"] = -failed * table.failed_prophecy
    return parts


async def stir(ctx: TickContext, church: Church, book: FaithBook, *, laws: LawBook, atlas: RegionAtlas) -> int:
    held = church.doctrine is not None and "zeal_parts" in church.doctrine.locked
    parts = dict(church.doctrine.zeal_parts or {}) if held and church.doctrine is not None else await zeal_parts(ctx, church, book, laws=laws, atlas=atlas)
    zeal = stat(church.cult, "zeal") or 0
    if church.doctrine is not None and not held:
        church.doctrine.zeal_parts = parts
    if church.doctrine is not None and "zeal" in church.doctrine.locked:
        return zeal
    zeal = clamp_int(zeal + sum(parts.values()), 0, PERCENT)
    set_stats(church.cult, zeal=zeal)
    return zeal
