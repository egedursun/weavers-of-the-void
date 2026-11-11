from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.culture import BookContentRow, ItemProfileRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faction import CRIME_KINDS, FactionKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.mind.hooks import judged
from aerona.engine.notes import note
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up

OUTLAWS = (FactionKind.BANDITS, FactionKind.PIRATES, FactionKind.VOID_PIRATES, *sorted(CRIME_KINDS))
BOOKS = (ItemClass.BOOK, ItemClass.SCROLL, ItemClass.PRAYER_BOOK)
FORBIDDEN_LORE = (KnowledgeBranch.FORBIDDEN, KnowledgeBranch.MAGIC)
VOID_KINDS = frozenset({MaterialKind.VOID_GLASS})
PERCENT = 100
TENTH = 10


@dataclass(frozen=True)
class BannedMaterials:
    kinds: frozenset[MaterialKind] = frozenset()
    worlds: frozenset[int] = frozenset()

    def __bool__(self) -> bool:
        return bool(self.kinds or self.worlds)


async def void_worlds(ctx: TickContext) -> frozenset[int]:
    rows = await ctx.session.scalars(select(WorldMaterialRow.id).where(WorldMaterialRow.corruption >= ctx.rules.contraband.void_corruption_at))
    return frozenset(rows)


async def banned_materials(ctx: TickContext, laws: LawBook, community_ids: list[int]) -> dict[int, BannedMaterials]:
    worlds = await void_worlds(ctx)
    return {community_id: BannedMaterials(VOID_KINDS, worlds) for community_id in community_ids if laws.in_force(community_id, LawKind.MAGIC_BAN) is not None}


async def crime_at(ctx: TickContext, community_id: int | None, amount: int) -> None:
    town = await ctx.session.get(SettlementProfileRow, community_id) if community_id is not None else None
    if town is not None and "crime" not in (town.locked or []) and not held(town.settlement_entity_id):
        town.crime = clamp_int(town.crime + amount, 0, PERCENT)


async def forbidden_books(ctx: TickContext, community_id: int) -> list[EntityRow]:
    lore = select(EntityRow.id).where(EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.knowledge_branch.in_(list(FORBIDDEN_LORE)))
    tomes = select(BookContentRow.book_entity_id).where(BookContentRow.knowledge_entity_id.in_(lore))
    classes = select(ItemProfileRow.item_entity_id).where(ItemProfileRow.item_class.in_(list(BOOKS)))
    statement = select(EntityRow).where(
        EntityRow.id.in_(tomes), EntityRow.id.in_(classes), EntityRow.status == EntityStatus.CANON, EntityRow.location_id == community_id
    )
    return list(await ctx.session.scalars(statement.order_by(EntityRow.id)))


async def smuggle_books(ctx: TickContext, gang: FactionProfileRow) -> int:
    home = gang.home_entity_id
    if home is None or held(gang.faction_entity_id):
        return 0
    laws = await LawBook.load(ctx.session)
    if laws.in_force(home, LawKind.MAGIC_BAN) is None:
        return 0
    bonds = BondRepository(ctx.session)
    carried = 0
    for book in await forbidden_books(ctx, home):
        if held(book.id) or await bonds.exists_between(gang.faction_entity_id, book.id, BondKind.OWNS):
            continue
        await bonds.connect(BondDraft(gang.faction_entity_id, book.id, BondKind.OWNS, ctx.epoch, "smuggled past the ban"))
        gang.treasury += ctx.rules.contraband.book_value
        await crime_at(ctx, home, ctx.rules.contraband.book_crime)
        carried += 1
    if carried:
        town = await ctx.session.get(EntityRow, home)
        await note(
            ctx,
            f"Smugglers passed {carried} forbidden {'book' if carried == 1 else 'books'} from hand to hand in {town.name if town else 'the town'}.",
            key="contraband.books",
            ids=[gang.faction_entity_id, home],
            kind=ChronicleKind.TRADE,
        )
    return carried


async def slave_market(ctx: TickContext) -> EntityRow | None:
    laws = await LawBook.load(ctx.session)
    statement = select(EntityRow).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    for community in await ctx.session.scalars(statement):
        row = laws.in_force(community.id, LawKind.SLAVERY)
        if row is not None and laws.param(community.id, LawKind.SLAVERY, "status") == "allowed" and not held(community.id):
            return community
    return None


async def outlaw_near(ctx: TickContext, community_id: int) -> FactionProfileRow | None:
    statement = select(FactionProfileRow).where(FactionProfileRow.home_entity_id == community_id, FactionProfileRow.kind.in_(list(OUTLAWS)))
    return await ctx.session.scalar(statement.order_by(FactionProfileRow.faction_entity_id).limit(1))


async def traffic(ctx: TickContext, captor: EntityRow, count: int, origin_id: int | None) -> EntityRow | None:
    table = ctx.rules.contraband
    gang = await outlaw_near(ctx, captor.id)
    if gang is None or held(gang.faction_entity_id) or not ctx.rng(f"slave_trade.{captor.id}.{ctx.epoch}").chance(table.slave_chance):
        return None
    market = await slave_market(ctx)
    if market is None or market.id == captor.id:
        return None
    gang.treasury += round_half_up(count * table.slave_value_per_10 / TENTH)
    await crime_at(ctx, captor.id, table.slave_crime)
    if origin_id is not None:
        await judged(ctx, gang.faction_entity_id, origin_id, ActKind.SLAVERY)
    gang_entity = await ctx.session.get(EntityRow, gang.faction_entity_id)
    seller = gang_entity.name if gang_entity else "Outlaws"
    await note(
        ctx,
        f"{seller} bought {count} captives in {captor.name}, where slavery is banned, and sold them in {market.name}.",
        key="contraband.slaves",
        ids=[gang.faction_entity_id, captor.id, market.id],
        kind=ChronicleKind.TRADE,
    )
    return market
