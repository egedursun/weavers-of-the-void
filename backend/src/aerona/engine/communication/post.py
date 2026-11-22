from typing import Any

from sqlalchemy import select

from aerona.catalog.life.communication import CARRIER_MEDIUM, MEDIUM_RANK, SPEED_RULES, TEXTS
from aerona.catalog.life_traits import MEDIUM_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.communication import CipherRow, SignalLinkRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.communication import DispatchContent, DispatchState, Medium, SignalState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.life_traits import MediumTrait
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import tech_bonus
from aerona.engine.lore.civics import holders_know
from aerona.engine.networks.book import message_epochs, shared_networks
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import spoken_language

INSTANT = having(MEDIUM_TRAITS, MediumTrait.INSTANT)
OPEN_MEDIA = having(MEDIUM_TRAITS, MediumTrait.OPEN_MEDIA)
OVERLAND = having(MEDIUM_TRAITS, MediumTrait.OVERLAND)
YEAR_SEASONS = 4
FACTS = "facts"
CLAUSES = "clauses"
TREATY = "treaty_id"
COMMODITY = "commodity"
FORGER = "forger"
SPIED = "spied"
LOCKED_STATE = "state"


async def year_seasons(ctx: TickContext, world_id: int | None) -> list[WorldSeasonRow]:
    if world_id is None:
        return []
    return list(await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))


async def epoch_reach(ctx: TickContext, world_id: int | None, per_season: float, overland: bool) -> float:
    table = ctx.rules.communication
    seasons = await year_seasons(ctx, world_id)
    slowed = PERCENT / (PERCENT + table.winter_delay_pct)
    yearly = sum(per_season * slowed if overland and row.temperature_shift < 0 else per_season for row in seasons) if seasons else per_season * YEAR_SEASONS
    return yearly * table.years_per_epoch


async def seasons_in_epoch(ctx: TickContext, world_id: int | None) -> int:
    return max(1, len(await year_seasons(ctx, world_id)) or YEAR_SEASONS) * ctx.rules.communication.years_per_epoch


async def signalled(ctx: TickContext, owner_id: int) -> bool:
    found = await ctx.session.scalar(
        select(SignalLinkRow.id).where(SignalLinkRow.owner_node_id == owner_id, SignalLinkRow.state == SignalState.ACTIVE).limit(1)
    )
    return found is not None


async def posted(ctx: TickContext, owner_id: int) -> bool:
    owner = await ctx.session.get(EntityRow, owner_id)
    holders = [owner_id, *([owner.location_id] if owner is not None and owner.location_id is not None else [])]
    realm = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id.in_(holders)).limit(1))
    return await holders_know(ctx.session, [*holders, *([realm] if realm is not None else [])], Technique.POSTAL_SERVICE)


async def delay(ctx: TickContext, atlas: RegionAtlas, origin_id: int, recipient_id: int, *, medium: Medium, owner_id: int) -> int:
    if medium in INSTANT:
        return 0
    if medium is Medium.NETWORK:
        linked = await message_epochs(ctx.session, ctx.rules, owner_id, recipient_id, ctx.epoch)
        if linked is not None:
            return linked
        medium = Medium.LETTER
    table = ctx.rules.communication
    origin = await ctx.session.get(EntityRow, origin_id)
    target = await ctx.session.get(EntityRow, recipient_id)
    if origin is None or target is None or origin.world_id != target.world_id:
        return table.interworld_epochs // await seasons_in_epoch(ctx, origin.world_id if origin is not None else None)
    hops = atlas.region_hops(atlas.top_region(origin.id), atlas.top_region(target.id)) or 0
    speed = int(getattr(table, SPEED_RULES[medium]))
    if medium is Medium.LETTER and await posted(ctx, owner_id):
        speed += ctx.rules.technique_effects.postal_hops
    reach = await epoch_reach(ctx, origin.world_id, speed, medium in OVERLAND)
    if medium is Medium.LETTER:
        reach += await tech_bonus(ctx.session, ctx.rules, owner_id, EraChannel.MESSAGES)
    epochs = int(hops // max(1.0, reach))
    if await signalled(ctx, owner_id):
        epochs = max(0, epochs - table.signal_cut)
    return epochs


async def upgraded(ctx: TickContext, sender_id: int, recipient_id: int, medium: Medium) -> Medium:
    if medium is not Medium.LETTER:
        return medium
    offered = {CARRIER_MEDIUM[row.carrier] for row in await shared_networks(ctx.session, sender_id, recipient_id, ctx.epoch) if row.carries_messages}
    return next((item for item in MEDIUM_RANK if item in offered), medium)


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
    medium = await upgraded(ctx, sender_id, recipient_id, medium)
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
        enciphered=cipher is not None and medium not in OPEN_MEDIA,
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
