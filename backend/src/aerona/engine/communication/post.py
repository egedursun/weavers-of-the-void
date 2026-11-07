from typing import Any

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.communication import CipherRow, SignalLinkRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.lore import MessageRow
from aerona.db.write_guard import held
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.communication import DispatchContent, DispatchState, Medium, SignalState
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import spoken_language

INSTANT = frozenset({Medium.DREAM, Medium.MAGIC_SENDING})
OVERLAND = frozenset({Medium.ENVOY, Medium.LETTER, Medium.HERALD})
SPEED_RULES = {
    Medium.ENVOY: "envoy_hops",
    Medium.LETTER: "letter_hops",
    Medium.HERALD: "herald_hops",
    Medium.BIRD: "bird_hops",
    Medium.SIGNAL_FIRE: "signal_fire_hops",
}
FACTS = "facts"
CLAUSES = "clauses"
TREATY = "treaty_id"
COMMODITY = "commodity"
FORGER = "forger"
SPIED = "spied"
TEXTS = {
    DispatchContent.PROPOSAL: "a proposal",
    DispatchContent.DEMAND: "a demand",
    DispatchContent.THREAT: "a threat",
    DispatchContent.INSULT: "an insult",
    DispatchContent.GIFT_NOTICE: "word of a gift",
    DispatchContent.DECLARATION: "a declaration",
    DispatchContent.REPORT: "a report",
    DispatchContent.PLEA: "a plea",
    DispatchContent.INTELLIGENCE: "intelligence",
}
LOCKED_STATE = "state"


async def winter(ctx: TickContext, world_id: int | None) -> bool:
    if world_id is None:
        return False
    seasons = list(await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))
    return bool(seasons) and seasons[ctx.epoch % len(seasons)].temperature_shift < 0


async def signalled(ctx: TickContext, owner_id: int) -> bool:
    found = await ctx.session.scalar(
        select(SignalLinkRow.id).where(SignalLinkRow.owner_node_id == owner_id, SignalLinkRow.state == SignalState.ACTIVE).limit(1)
    )
    return found is not None


async def delay(ctx: TickContext, atlas: RegionAtlas, origin_id: int, recipient_id: int, *, medium: Medium, owner_id: int) -> int:
    if medium in INSTANT:
        return 0
    table = ctx.rules.communication
    origin = await ctx.session.get(EntityRow, origin_id)
    target = await ctx.session.get(EntityRow, recipient_id)
    if origin is None or target is None or origin.world_id != target.world_id:
        return table.interworld_epochs
    hops = atlas.region_hops(atlas.top_region(origin.id), atlas.top_region(target.id)) or 0
    epochs = -(-hops // int(getattr(table, SPEED_RULES[medium])))
    if medium in OVERLAND and await winter(ctx, origin.world_id):
        epochs = -(-epochs * (PERCENT + table.winter_delay_pct) // PERCENT)
    if await signalled(ctx, owner_id):
        epochs = max(0, epochs - table.signal_cut)
    return epochs


async def send(
    ctx: TickContext,
    sender_id: int,
    recipient_id: int,
    content: DispatchContent,
    medium: Medium,
    *,
    payload: dict[str, Any] | None = None,
    origin_id: int | None = None,
    envoy_id: int | None = None,
    forged: bool = False,
    atlas: RegionAtlas | None = None,
) -> MessageRow | None:
    if held(sender_id) or sender_id == recipient_id:
        return None
    atlas = atlas or await RegionAtlas.load(ctx.session)
    language = await spoken_language(ctx.session, sender_id)
    cipher = await ctx.session.get(CipherRow, sender_id)
    row = MessageRow(
        epoch=ctx.epoch,
        sender_node_id=sender_id,
        recipient_node_id=recipient_id,
        intent=MessageIntent.DISPATCH,
        text=TEXTS[content],
        medium=medium,
        content=content,
        state=DispatchState.UNDER_WAY,
        language_node_id=language.id if language is not None else None,
        envoy_node_id=envoy_id,
        payload=payload or {},
        arrival_epoch=ctx.epoch + await delay(ctx, atlas, origin_id or sender_id, recipient_id, medium=medium, owner_id=sender_id),
        forged=forged,
        enciphered=cipher is not None and medium is not Medium.HERALD,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def herald_war(ctx: TickContext, attacker_id: int, defender_id: int, reason: str) -> None:
    await send(ctx, attacker_id, defender_id, DispatchContent.DECLARATION, Medium.HERALD, payload={"reason": reason})


async def offer_treaty(ctx: TickContext, proposer_id: int, party_ids: list[int], treaty_id: int, clauses: list[str]) -> None:
    for party in party_ids:
        if party != proposer_id:
            await send(ctx, proposer_id, party, DispatchContent.PROPOSAL, Medium.ENVOY, payload={TREATY: treaty_id, CLAUSES: clauses})


async def proposal_pending(ctx: TickContext, treaty_id: int) -> bool:
    found = await ctx.session.scalar(
        select(MessageRow.id)
        .where(
            MessageRow.intent == MessageIntent.DISPATCH,
            MessageRow.content == DispatchContent.PROPOSAL,
            MessageRow.state == DispatchState.UNDER_WAY,
            MessageRow.payload[TREATY].as_integer() == treaty_id,
        )
        .limit(1)
    )
    return found is not None
