from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.db.tables.dominion import MagicSiteRow
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.finance import TradePolicyRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.polity import ClaimRow, TreatyBreachRow, TreatyPartyRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import CasusBelliRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.finance import TradePolicyKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.renown import Currency
from aerona.domain.enums.war import CasusBelliKind, WarCause
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.regard import shift_regard
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.renown.currencies import bump, purse_of, ruler_of_realm

PERCENT = 100
WARRING_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.POLITY})
REVOLT_CAUSES = frozenset({WarCause.UPRISING, WarCause.TRIBUTE_REVOLT, WarCause.INDEPENDENCE, WarCause.FOREIGN_GOD, WarCause.BEAST})
Grievance = tuple[int, int, CasusBelliKind, int | None]


@dataclass
class CasusBelliTally:
    found: dict[str, int] = field(default_factory=dict)
    justified: int = 0
    lapsed: int = 0


async def warring(ctx: TickContext, entity_id: int | None) -> bool:
    if entity_id is None:
        return False
    entity = await ctx.session.get(EntityRow, entity_id)
    return entity is not None and entity.status is EntityStatus.CANON and entity.entity_type in WARRING_TYPES


async def claims(ctx: TickContext) -> list[Grievance]:
    found: list[Grievance] = []
    rows = await ctx.session.scalars(select(ClaimRow).where(ClaimRow.ended_epoch.is_(None), ClaimRow.strength >= ctx.rules.war_conduct.claim_strength))
    for claim in rows:
        claimant = await ctx.session.get(EntityRow, claim.claimant_entity_id)
        holder = claim.backer_entity_id or (claimant.location_id if claimant is not None else None)
        if holder is not None:
            found.append((holder, claim.polity_entity_id, CasusBelliKind.CLAIM, claim.claimant_entity_id))
    return found


async def remembered(ctx: TickContext, kind: MemoryKind, cause: CasusBelliKind) -> list[Grievance]:
    rows = await ctx.session.scalars(select(MemoryRow).where(MemoryRow.kind == kind))
    return [(row.holder_node_id, row.subject_node_id, cause, None) for row in rows if abs(row.magnitude) >= ctx.rules.war_conduct.vendetta_magnitude]


async def broken_treaties(ctx: TickContext) -> list[Grievance]:
    since = ctx.epoch - ctx.rules.war_conduct.casus_belli_epochs
    found: list[Grievance] = []
    for breach in await ctx.session.scalars(select(TreatyBreachRow).where(TreatyBreachRow.epoch >= since, TreatyBreachRow.breaker_node_id.is_not(None))):
        parties = await ctx.session.scalars(select(TreatyPartyRow.party_node_id).where(TreatyPartyRow.treaty_entity_id == breach.treaty_entity_id))
        breaker = breach.breaker_node_id
        if breaker is not None:
            found.extend((party, breaker, CasusBelliKind.BROKEN_TREATY, breach.treaty_entity_id) for party in parties if party != breaker)
    return found


async def embargoes(ctx: TickContext) -> list[Grievance]:
    rows = await ctx.session.scalars(select(TradePolicyRow).where(TradePolicyRow.partner_node_id.is_not(None)))
    tolls = ctx.rules.war_conduct.toll_dispute_pct
    return [
        (row.partner_node_id, row.issuer_node_id, CasusBelliKind.TRADE_DISPUTE, None)
        for row in rows
        if row.partner_node_id is not None and (row.kind is TradePolicyKind.EMBARGO or (row.kind is TradePolicyKind.TARIFF and row.rate_pct >= tolls))
    ]


async def defaults(ctx: TickContext) -> list[Grievance]:
    rows = await ctx.session.scalars(select(LoanRow).where(LoanRow.status == LoanStatus.DEFAULTED))
    return [(row.lender_entity_id, row.borrower_entity_id, CasusBelliKind.DEBT_DEFAULT, None) for row in rows]


async def liberations(ctx: TickContext, book: RealmBook) -> list[Grievance]:
    found: list[Grievance] = []
    folks: dict[int, int | None] = {}
    for realm in book.realms.values():
        core = realm.profile.core_entity_id
        if core is None:
            continue
        for other in book.realms.values():
            if other.entity.id == realm.entity.id:
                continue
            kin = 0
            for member in other.members:
                if member not in folks:
                    entity = await ctx.session.get(EntityRow, member)
                    folk = await people_of(ctx.session, entity) if entity is not None else None
                    folks[member] = folk.id if folk is not None else None
                kin += int(folks[member] == core)
            if kin >= max(1, ctx.rules.war_conduct.liberation_share):
                found.append((realm.entity.id, other.entity.id, CasusBelliKind.LIBERATION, core))
    return found


async def neighbours_of(ctx: TickContext, book: RealmBook, community: EntityRow) -> list[int]:
    region = book.atlas.top_region(community.id)
    if region is None:
        return []
    near = {region, *book.atlas.neighbour_regions(region)}
    return [other for place in sorted(near) for other in book.atlas.communities_in(place) if other != community.id]


async def holy_wars_and_hunger(ctx: TickContext, book: RealmBook) -> list[Grievance]:
    found: list[Grievance] = []
    table = ctx.rules.war_conduct
    communities = list(
        await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON))
    )
    patrons: dict[int, int | None] = {}
    for community in communities:
        zealous = TenetKind.HOLY_WAR in await faith_tenets(ctx.session, community.id)
        society = await ctx.session.get(CommunitySocietyRow, community.id)
        hungry = society is not None and society.stock_food < table.hunger_food
        if not zealous and not hungry:
            continue
        patron = await patron_node(ctx.session, community.id) if zealous else None
        for other in await neighbours_of(ctx, book, community):
            if zealous and patron is not None and other not in patrons:
                patrons[other] = await patron_node(ctx.session, other)
            if zealous and patron is not None and patrons[other] not in {patron, None}:
                found.append((community.id, other, CasusBelliKind.HOLY_WAR, patron))
            neighbour = await ctx.session.get(CommunitySocietyRow, other) if hungry else None
            if neighbour is not None and neighbour.stock_food >= table.hunger_food * 3:
                found.append((community.id, other, CasusBelliKind.RESOURCE_NEED, None))
    return found


async def coveted_sites(ctx: TickContext, book: RealmBook) -> list[Grievance]:
    found: list[Grievance] = []
    table = ctx.rules.magic_sites
    statement = select(MagicSiteRow).where(MagicSiteRow.found_epoch.is_not(None), MagicSiteRow.holder_node_id.is_not(None)).order_by(MagicSiteRow.id)
    for site in await ctx.session.scalars(statement):
        holder = await ctx.session.get(EntityRow, site.holder_node_id) if site.holder_node_id is not None else None
        if holder is None or holder.status is not EntityStatus.CANON or holder.entity_type not in COMMUNITY_TYPES:
            continue
        for other in await neighbours_of(ctx, book, holder):
            if ctx.rng(f"magic_site.covet.{site.id}.{other}.{ctx.epoch}").chance(table.war_aim_pct):
                found.append((other, holder.id, CasusBelliKind.RESOURCE_NEED, site.place_entity_id))
    return found


async def grievances(ctx: TickContext) -> list[Grievance]:
    book = await RealmBook.load(ctx.session)
    return [
        *await claims(ctx),
        *await remembered(ctx, MemoryKind.KILLED_KIN, CasusBelliKind.VENDETTA),
        *await remembered(ctx, MemoryKind.HUMILIATED_ME, CasusBelliKind.INSULT),
        *await broken_treaties(ctx),
        *await embargoes(ctx),
        *await defaults(ctx),
        *await liberations(ctx, book),
        *await holy_wars_and_hunger(ctx, book),
        *await coveted_sites(ctx, book),
    ]


async def open_casus_belli(ctx: TickContext, holder_id: int, target_id: int) -> list[CasusBelliRow]:
    rows = await ctx.session.scalars(
        select(CasusBelliRow)
        .where(CasusBelliRow.holder_entity_id == holder_id, CasusBelliRow.target_entity_id == target_id, CasusBelliRow.used_war_id.is_(None))
        .order_by(CasusBelliRow.justification.desc(), CasusBelliRow.id)
    )
    return list(rows)


async def open_kinds(ctx: TickContext) -> dict[tuple[int, int], set[CasusBelliKind]]:
    found: dict[tuple[int, int], set[CasusBelliKind]] = defaultdict(set)
    rows = await ctx.session.execute(
        select(CasusBelliRow.holder_entity_id, CasusBelliRow.target_entity_id, CasusBelliRow.kind).where(CasusBelliRow.used_war_id.is_(None))
    )
    for holder, target, kind in rows:
        found[(holder, target)].add(kind)
    return found


async def record(ctx: TickContext, found: Iterable[Grievance], tally: CasusBelliTally) -> None:
    seen: set[tuple[int, int, CasusBelliKind]] = set()
    opened = await open_kinds(ctx)
    for holder, target, kind, source in found:
        if holder == target or (holder, target, kind) in seen or held(holder):
            continue
        seen.add((holder, target, kind))
        if not await warring(ctx, holder) or not await warring(ctx, target):
            continue
        if kind in opened[(holder, target)]:
            continue
        opened[(holder, target)].add(kind)
        ctx.session.add(
            CasusBelliRow(
                holder_entity_id=holder,
                target_entity_id=target,
                kind=kind,
                source_node_id=source,
                justification=0,
                since_epoch=ctx.epoch,
                expires_epoch=ctx.epoch + ctx.rules.war_conduct.casus_belli_epochs,
                locked=[],
            )
        )
        tally.found[kind.value] = tally.found.get(kind.value, 0) + 1
    await ctx.session.flush()


async def tend(ctx: TickContext, tally: CasusBelliTally) -> None:
    table = ctx.rules.war_conduct
    for row in list(await ctx.session.scalars(select(CasusBelliRow).where(CasusBelliRow.used_war_id.is_(None)).order_by(CasusBelliRow.id))):
        if held(row.holder_entity_id):
            continue
        if row.expires_epoch is not None and row.expires_epoch < ctx.epoch and "expires_epoch" not in row.locked:
            await ctx.session.delete(row)
            tally.lapsed += 1
            continue
        if "justification" not in row.locked and row.justification < PERCENT:
            row.justification = clamp_int(row.justification + table.justify_gain, 0, PERCENT)
            tally.justified += 1


async def gather_casus_belli(ctx: TickContext) -> CasusBelliTally:
    tally = CasusBelliTally()
    await tend(ctx, tally)
    await record(ctx, await grievances(ctx), tally)
    return tally


async def press_casus_belli(ctx: TickContext, war: WarRow, attacker: EntityRow, defender: EntityRow) -> bool:
    table = ctx.rules.war_conduct
    book = await RealmBook.load(ctx.session)
    targets = [defender.id, *([realm.entity.id] if (realm := book.realm_of(defender.id)) is not None else [])]
    holders = [attacker.id, *([realm.entity.id] if (realm := book.realm_of(attacker.id)) is not None else [])]
    found = [row for holder in holders for target in targets for row in await open_casus_belli(ctx, holder, target)]
    best = max(found, key=lambda row: (row.justification, -row.id)) if found else None
    if best is not None:
        best.used_war_id = war.id
        war.casus_belli_id = best.id
    war.justified = war.cause in REVOLT_CAUSES or (best is not None and best.justification >= table.justified_at and best.kind is not CasusBelliKind.CONQUEST)
    if not war.justified:
        await condemn(ctx, war, attacker, book)
    return war.justified


async def condemn(ctx: TickContext, war: WarRow, attacker: EntityRow, book: RealmBook) -> None:
    table = ctx.rules.war_conduct
    side = await ctx.session.get(WarSideRow, (war.id, attacker.id))
    if side is not None and "support" not in side.locked:
        side.support = clamp_int(side.support - table.unjustified_support, 0, PERCENT)
    realm = book.realm_of(attacker.id) or book.realms.get(attacker.id)
    if realm is None:
        return
    ruler = await ruler_of_realm(ctx.session, realm.entity.id)
    purse = await purse_of(ctx.session, ruler, ctx.epoch) if ruler is not None else None
    if purse is not None:
        bump(purse, Currency.TYRANNY, table.unjustified_tyranny)
    for other in book.realms.values():
        if other.entity.id != realm.entity.id and other.entity.world_id == realm.entity.world_id:
            await shift_regard(ctx, other.entity.id, realm.entity.id, threat=table.unjustified_threat)
