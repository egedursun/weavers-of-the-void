from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.polity import LawKind, LegitimacyBasis
from aerona.engine.context import TickContext
from aerona.engine.law.systems import written_code
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import found_polity
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.queries import canon
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import bind, end


@memoized(PolityMemberRow)
async def member_realm(session: AsyncSession, community_id: int) -> int | None:
    found: int | None = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    return found


async def realm_of(ctx: TickContext, community_id: int) -> int | None:
    return await member_realm(ctx.session, community_id)


async def landless_holder(ctx: TickContext, title: TitleProfileRow) -> EntityRow | None:
    if title.holder_node_id is None or title.polity_entity_id is not None or title.destroyed_epoch is not None:
        return None
    holder = await ctx.session.get(EntityRow, title.holder_node_id)
    if holder is None or holder.status is not EntityStatus.CANON or holder.entity_type not in COMMUNITY_TYPES:
        return None
    return holder if await realm_of(ctx, holder.id) is None else None


async def realm_title_pressures(ctx: TickContext) -> dict[int, int]:
    found: dict[int, int] = {}
    for title in await ctx.session.scalars(select(TitleProfileRow).order_by(TitleProfileRow.title_entity_id)):
        if await landless_holder(ctx, title) is not None:
            found[title.title_entity_id] = PERCENT
    return found


async def title_check(ctx: TickContext, title_id: int) -> str | None:
    title = await ctx.session.get(TitleProfileRow, title_id)
    if title is None:
        return "Only a title can be made a realm."
    if await landless_holder(ctx, title) is None:
        return "Only a title held by a community outside any realm can be made a realm."
    return None


async def title_to_realm(ctx: TickContext, title_id: int, ledger: Ledger) -> int:
    title = await ctx.session.get_one(TitleProfileRow, title_id)
    holder = await landless_holder(ctx, title)
    if holder is None:
        return title_id
    realm = await found_polity(ctx, await RealmBook.load(ctx.session), holder, told=False)
    ledger.made(realm.entity.id)
    ledger.set(title, "polity_entity_id", realm.entity.id)
    return realm.entity.id


@memoized(BondRow)
async def celebrants(session: AsyncSession, tradition_id: int) -> tuple[int, ...]:
    statement = select(BondRow.source_node_id).where(
        BondRow.target_node_id == tradition_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    return tuple(await session.scalars(statement.order_by(BondRow.source_node_id)))


async def keepers_by_realm(ctx: TickContext, tradition_id: int) -> dict[int, list[int]]:
    keepers: dict[int, list[int]] = defaultdict(list)
    for community_id in await celebrants(ctx.session, tradition_id):
        realm = await realm_of(ctx, community_id)
        if realm is not None:
            keepers[realm].append(community_id)
    return keepers


async def codifying_realm(ctx: TickContext, tradition_id: int) -> int | None:
    need = ctx.rules.transform.codified_keepers
    for realm, keepers in sorted((await keepers_by_realm(ctx, tradition_id)).items()):
        if len(keepers) >= need and await written_code(ctx.session, [realm, *keepers]):
            return realm
    return None


async def codified_pressures(ctx: TickContext) -> dict[int, int]:
    found: dict[int, int] = {}
    for tradition in await canon(ctx.session, [EntityType.TRADITION]):
        if await codifying_realm(ctx, tradition.id) is not None:
            found[tradition.id] = PERCENT
    return found


async def tradition_check(ctx: TickContext, tradition_id: int) -> str | None:
    tradition = await ctx.session.get(EntityRow, tradition_id)
    if tradition is None or tradition.entity_type is not EntityType.TRADITION or tradition.status is not EntityStatus.CANON:
        return "Only a living custom can be written down as law."
    if await codifying_realm(ctx, tradition.id) is None:
        return f"No realm that writes its laws keeps {tradition.name} widely enough."
    return None


async def codify(ctx: TickContext, tradition_id: int, ledger: Ledger) -> int:
    tradition = await ctx.session.get_one(EntityRow, tradition_id)
    realm_id = await codifying_realm(ctx, tradition.id)
    realm = await ctx.session.get_one(EntityRow, realm_id)
    law = await enact(
        ctx,
        realm,
        LawKind.CUSTOM,
        {},
        basis=LegitimacyBasis.CUSTOM,
        name=await NameRepository(ctx.session).unique_name(f"Law of {tradition.name}"),
    )
    ledger.made(law.id)
    await bind(ctx, ledger, (law.id, tradition.id, BondKind.DESCENDS_FROM), f"the custom {tradition.name} written down")
    end(ctx, ledger, tradition, EntityStatus.FULFILLED)
    return law.id
