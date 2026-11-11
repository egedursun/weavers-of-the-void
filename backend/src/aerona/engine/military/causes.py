from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import WarAimRow
from aerona.db.tables.warfare import WarRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.military import WarAimKind
from aerona.domain.enums.mind import ActKind, ValueAxis
from aerona.domain.enums.war import WarCause
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import solidarity
from aerona.engine.cycles.indenture import captive_price
from aerona.engine.intrigue.beliefs import BeliefView
from aerona.engine.mind.book import values_for
from aerona.engine.mind.hooks import judged
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.services.war import current_war, declare_war, ongoing_wars, open_war


async def declared_war(
    ctx: TickContext,
    attacker_id: int,
    defender_id: int,
    cause: WarCause,
    reason: str,
    *,
    aim: WarAimKind | None = None,
    params: dict[str, int | str | bool] | None = None,
    open_now: bool = True,
) -> WarRow | None:
    existing = await current_war(ctx.session, attacker_id, defender_id)
    if existing is not None:
        return existing
    if not await declare_war(ctx, attacker_id, defender_id, reason, cause=cause, world_cap=False):
        return None
    attacker, defender = await living_entity(ctx.session, attacker_id), await living_entity(ctx.session, defender_id)
    if not open_now or attacker is None or defender is None or attacker.entity_type not in COMMUNITY_TYPES or defender.entity_type not in COMMUNITY_TYPES:
        return None
    war = await open_war(ctx, attacker, defender, cause=cause, cause_text=reason)
    if aim is not None:
        ctx.session.add(
            WarAimRow(war_id=war.id, side_entity_id=attacker.id, kind=aim, target_entity_id=defender.id, params=dict(params or {}), achieved=0, locked=[])
        )
        await ctx.session.flush()
    return war


async def press_claim_war(
    ctx: TickContext, claimant_id: int, holder_id: int, *, claim_id: int | None = None, succession: bool = False, reason: str | None = None
) -> WarRow | None:
    cause = WarCause.SUCCESSION if succession else WarCause.CLAIM
    text = reason or ("a war of succession" if succession else "a claim pressed by arms")
    params: dict[str, int | str | bool] = {"claim": claim_id} if claim_id is not None else {}
    return await declared_war(ctx, claimant_id, holder_id, cause, text, aim=WarAimKind.PRESS_CLAIM, params=params)


NEAR_HOPS = frozenset({0, 1})


async def raiders(ctx: TickContext) -> int:
    table = ctx.rules.campaign_depth
    atlas = await RegionAtlas.load(ctx.session)
    at_war = {side for item in await ongoing_wars(ctx.session) for side in item.sides}
    communities = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES))).order_by(EntityRow.id)
        )
    )
    raids = 0
    for raider in communities:
        if raider.id in at_war or not ctx.rng(f"raid_war.{raider.id}.{ctx.epoch}").chance(
            table.raid_war_chance
            * await captive_price(ctx.session, ctx.rules, raider.id)
            * await solidarity(ctx.session, raider, ctx.rules.asabiyya.conquest_weight)
        ):
            continue
        martial = (await values_for(ctx.session, raider.id)).get(ValueAxis.MARTIAL, 0)
        if martial < table.raid_martial:
            continue
        home = atlas.top_region(raider.id)
        wealth = stat_or(raider, "wealth", stat(raider, "prosperity") or 0)
        seen = BeliefView(ctx.session, ctx.rules, raider.id)
        believed = {
            other.id: await seen.of(other.id, "wealth", stat_or(other, "wealth", stat(other, "prosperity") or 0))
            for other in communities
            if other.id != raider.id
            and other.world_id == raider.world_id
            and other.id not in at_war
            and (atlas.region_hops(home, atlas.top_region(other.id)) if home is not None else None) in NEAR_HOPS
        }
        victims = [other for other in communities if other.id in believed and believed[other.id] - wealth >= table.raid_wealth_gap]
        if not victims:
            continue
        victim = max(victims, key=lambda item: (believed[item.id], -item.id))
        if await declare_war(ctx, raider.id, victim.id, f"{raider.name} went raiding for the riches of {victim.name}", cause=WarCause.RAID, world_cap=False):
            await judged(ctx, raider.id, victim.id, ActKind.RAIDING)
            raids += 1
        at_war.update({raider.id, victim.id})
    return raids
