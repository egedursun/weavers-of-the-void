from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.urban import MERCHANT_HOUSES
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.urban import TradingPostRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.intrigue.secrets import learn
from aerona.engine.lore.research_depth import trade_partners
from aerona.engine.notes import note
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.services.war import foe_realms
from aerona.engine.structures.construction import Commission, begin


@dataclass
class PostTally:
    opened: int = 0
    secrets: int = 0
    settled: int = 0


async def merchant_houses(ctx: TickContext) -> list[tuple[EntityRow, FactionProfileRow]]:
    rows = await ctx.session.execute(
        select(EntityRow, FactionProfileRow)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind.in_(list(MERCHANT_HOUSES)), EntityRow.status == EntityStatus.CANON, FactionProfileRow.home_entity_id.is_not(None))
        .order_by(EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows.all() if not held(entity.id)]


async def open_post(ctx: TickContext, owner: EntityRow, host: EntityRow) -> TradingPostRow:
    post, _ = await begin(ctx, Commission(site=host, kind=StructureKind.KONTOR, builder=owner, name=f"the trading post of {owner.name} at {host.name}"))
    row = TradingPostRow(
        structure_entity_id=post.id, owner_entity_id=owner.id, host_settlement_id=host.id, informants=0, goods=0, since_epoch=ctx.epoch, locked=[]
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def found_posts(ctx: TickContext, tally: PostTally) -> None:
    table = ctx.rules.trading_posts
    for house, profile in await merchant_houses(ctx):
        home = profile.home_entity_id
        if home is None:
            continue
        realm = await realm_of_community(ctx.session, home)
        foes = await foe_realms(ctx.session, realm) if realm is not None else set()
        held_hosts = set(await ctx.session.scalars(select(TradingPostRow.host_settlement_id).where(TradingPostRow.owner_entity_id == house.id)))
        for partner_id in sorted(await trade_partners(ctx.session, home)):
            host_realm = await realm_of_community(ctx.session, partner_id)
            if partner_id in held_hosts or held(partner_id) or host_realm == realm or host_realm in foes:
                continue
            if not ctx.rng(f"trading_post.{house.id}.{partner_id}").chance(table.open_pct):
                continue
            host = await ctx.session.get(EntityRow, partner_id)
            if host is None or host.status is not EntityStatus.CANON:
                continue
            await open_post(ctx, house, host)
            tally.opened += 1
            await note(ctx, f"{house.name} opened a trading post in {host.name}.", key="trade.trading_post", ids=[house.id, host.id])
            break


async def gather(ctx: TickContext, row: TradingPostRow, tally: PostTally) -> None:
    table = ctx.rules.trading_posts
    if "informants" not in row.locked:
        row.informants = min(table.informant_cap, row.informants + table.informant_gain)
    if "goods" not in row.locked:
        row.goods = min(table.goods_cap, row.goods + table.stock_gain)
    if row.owner_entity_id is None:
        return
    host = await ctx.session.get(EntityRow, row.host_settlement_id)
    town = await ctx.session.get(SettlementProfileRow, row.host_settlement_id)
    owner = await ctx.session.get(FactionProfileRow, row.owner_entity_id)
    home = await ctx.session.get(EntityRow, owner.home_entity_id) if owner is not None and owner.home_entity_id is not None else None
    people = await people_of(ctx.session, home) if home is not None else None
    if town is not None and people is not None and "foreigners" not in town.locked and host is not None:
        foreigners = dict(town.foreigners)
        foreigners[str(people.id)] = foreigners.get(str(people.id), 0) + table.diaspora
        town.foreigners = foreigners
        tally.settled += table.diaspora
    rng = ctx.rng(f"post_secrets.{row.structure_entity_id}")
    for _ in range(row.informants):
        if not rng.chance(table.secret_pct):
            continue
        secret = await ctx.session.scalar(
            select(SecretRow)
            .join(EntityRow, EntityRow.id == SecretRow.holder_node_id)
            .where(EntityRow.location_id == row.host_settlement_id, SecretRow.exposed_epoch.is_(None))
            .order_by(SecretRow.id)
            .limit(1)
        )
        if secret is not None and await learn(ctx, secret, row.owner_entity_id):
            tally.secrets += 1


async def keep_posts(ctx: TickContext, tally: PostTally) -> None:
    await found_posts(ctx, tally)
    for row in list(await ctx.session.scalars(select(TradingPostRow).order_by(TradingPostRow.structure_entity_id))):
        if not held(row.structure_entity_id, row.host_settlement_id):
            await gather(ctx, row, tally)
    await ctx.session.flush()
