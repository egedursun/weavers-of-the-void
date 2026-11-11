from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.dominion import DominionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.mythic import ServitorRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mythic import ServitorRole
from aerona.engine.context import TickContext
from aerona.engine.intrigue.secrets import learn
from aerona.engine.lore.rites import countered
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among


@dataclass
class DivineSpyTally:
    posted: int = 0
    learned: int = 0
    turned_aside: int = 0


async def guarded(ctx: TickContext, god_id: int, place_id: int) -> bool:
    guard = await ctx.session.scalar(
        select(ServitorRow.spirit_entity_id)
        .where(ServitorRow.role == ServitorRole.GUARD, ServitorRow.post_entity_id == place_id, ServitorRow.god_node_id != god_id)
        .limit(1)
    )
    return guard is not None


async def outshone(ctx: TickContext, god_id: int, region_id: int) -> bool:
    rows = {row.god_node_id: row.strength for row in await ctx.session.scalars(select(DominionRow).where(DominionRow.region_entity_id == region_id))}
    mine = rows.pop(god_id, 0)
    return any(strength > mine for strength in rows.values())


async def veiled(ctx: TickContext, god_id: int, place_id: int, stream: str) -> bool:
    region = (await RegionAtlas.load(ctx.session)).top_region(place_id)
    warded = region is not None and await countered(ctx, region, None, 0) is not None
    blocked = await guarded(ctx, god_id, place_id) or warded or (region is not None and await outshone(ctx, god_id, region))
    return blocked and ctx.rng(stream).chance(ctx.rules.divine_spies.ward_pct)


async def secrets_at(ctx: TickContext, place_id: int) -> list[SecretRow]:
    folk = select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [place_id]))
    return list(
        await ctx.session.scalars(
            select(SecretRow)
            .where((SecretRow.holder_node_id == place_id) | SecretRow.holder_node_id.in_(folk))
            .order_by(SecretRow.severity.desc(), SecretRow.id)
        )
    )


async def read_dreams(ctx: TickContext, god_id: int, mortal: EntityRow) -> list[SecretRow] | None:
    if await veiled(ctx, god_id, mortal.location_id or mortal.id, f"divine.dreams.{god_id}.{mortal.id}.{ctx.epoch}"):
        return None
    learned: list[SecretRow] = []
    rows = await ctx.session.scalars(select(SecretRow).where(SecretRow.holder_node_id == mortal.id).order_by(SecretRow.severity.desc(), SecretRow.id))
    for secret in list(rows):
        if len(learned) >= ctx.rules.divine_spies.dream_secrets:
            break
        if await learn(ctx, secret, god_id):
            learned.append(secret)
    return learned


async def spy_for_gods(ctx: TickContext, tally: DivineSpyTally) -> None:
    rows = await ctx.session.scalars(
        select(ServitorRow).where(ServitorRow.role == ServitorRole.SPY, ServitorRow.post_entity_id.is_not(None)).order_by(ServitorRow.spirit_entity_id)
    )
    for row in list(rows):
        if row.post_entity_id is None or held(row.spirit_entity_id, row.god_node_id, row.post_entity_id):
            continue
        tally.posted += 1
        if not ctx.rng(f"divine.spy.{row.spirit_entity_id}.{ctx.epoch}").chance(ctx.rules.divine_spies.spy_pct):
            continue
        if await veiled(ctx, row.god_node_id, row.post_entity_id, f"divine.veil.{row.spirit_entity_id}.{ctx.epoch}"):
            tally.turned_aside += 1
            continue
        for secret in await secrets_at(ctx, row.post_entity_id):
            if await learn(ctx, secret, row.god_node_id):
                tally.learned += 1
                spirit = await ctx.session.get(EntityRow, row.spirit_entity_id)
                await note(ctx, f"{spirit.name if spirit else 'A servitor'} brought its god a secret.", key="divine.spy_secret", ids=[row.spirit_entity_id])
                break
