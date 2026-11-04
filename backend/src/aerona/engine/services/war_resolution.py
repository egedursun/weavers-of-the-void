from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow, WarRow
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.war import SiegeStatus, WarEnding, WarStatus
from aerona.engine.context import TickContext
from aerona.engine.faith.church import holy_peace
from aerona.engine.lore.taboos import forbidden
from aerona.engine.military.aims import peace_terms, white_peace
from aerona.engine.military.captivity import exchange_at_peace
from aerona.engine.mind.book import values_for
from aerona.engine.mind.hooks import converted, judged, witnessed
from aerona.engine.mind.space import value_reading
from aerona.engine.primitives.faith import change_religion, faith_dominance, faith_shares, living_patron
from aerona.engine.primitives.levies import stand_down
from aerona.engine.primitives.queries import living_entity, spoken_language
from aerona.engine.primitives.records import retire_in
from aerona.engine.services.community_relations import change_relation, remember_relation
from aerona.engine.services.war import (
    ACTIVE_WAR_STATUSES,
    OngoingWar,
    current_war,
    ever_fought,
    grant_truce,
    impose_tribute,
    is_community,
    last_clash,
    ongoing_wars,
    sides_of,
    unordered,
    war_event,
    war_sides,
)
from aerona.rules.registry import Rules

RELATION_EFFECTS: dict[WarEnding, Callable[[Rules], int]] = {
    WarEnding.CONQUEST: lambda rules: -rules.campaigns.conquest_relation,
    WarEnding.TRIBUTE: lambda rules: -rules.campaigns.tribute_relation,
    WarEnding.WHITE_PEACE: lambda rules: rules.campaigns.white_peace_relation,
    WarEnding.EXHAUSTION: lambda rules: rules.diplomacy.exhaustion_peace_relation,
    WarEnding.PEACE: lambda rules: rules.diplomacy.peace_relation,
    WarEnding.MIRACLE: lambda rules: rules.diplomacy.peace_relation,
}

ENDING_MEMORIES: dict[WarEnding, MemoryKind] = {
    WarEnding.VICTORY: MemoryKind.HUMILIATED_ME,
    WarEnding.CONQUEST: MemoryKind.CONQUERED_US,
    WarEnding.TRIBUTE: MemoryKind.DEMANDED_TRIBUTE,
    WarEnding.EXHAUSTION: MemoryKind.MADE_PEACE,
    WarEnding.PEACE: MemoryKind.MADE_PEACE,
    WarEnding.WHITE_PEACE: MemoryKind.MADE_PEACE,
    WarEnding.BETRAYAL: MemoryKind.BETRAYED_ME,
    WarEnding.MIRACLE: MemoryKind.DIVINE_WILL,
}
ENDING_LABELS: dict[WarEnding, str] = {
    WarEnding.VICTORY: "victory",
    WarEnding.CONQUEST: "conquest",
    WarEnding.TRIBUTE: "tribute",
    WarEnding.EXHAUSTION: "exhaustion peace",
    WarEnding.PEACE: "peace",
    WarEnding.WHITE_PEACE: "white peace",
    WarEnding.BETRAYAL: "betrayal",
    WarEnding.SAME_FRONT: "front of the same war",
    WarEnding.NO_SIDE_LEFT: "no side left",
    WarEnding.MIRACLE: "peace miracle",
}


def relation_effect(rules: Rules, ending: WarEnding) -> int:
    effect = RELATION_EFFECTS.get(ending)
    return effect(rules) if effect is not None else 0


@dataclass
class WarSettlement:
    ending: WarEnding
    victor_id: int | None = None
    loser_id: int | None = None
    notes: list[str] = field(default_factory=list)


async def make_peace(ctx: TickContext, first: int, second: int, reason: str, truce: bool = False) -> bool:
    await remember_relation(ctx.session, ctx.rules, first, second)
    await BondRepository(ctx.session).close_between(first, second, [BondKind.ENEMY], ctx.epoch, reason)
    if not truce and not ctx.rules.diplomacy.truce_without_war and not await ever_fought(ctx.session, first, second):
        return False
    await grant_truce(ctx, first, second, reason)
    return True


async def close_war(ctx: TickContext, war: WarRow, ending: WarEnding, victor_id: int | None = None, loser_id: int | None = None) -> None:
    if war.status not in ACTIVE_WAR_STATUSES:
        return
    war.status = WarStatus.ENDED
    war.ending = ending
    war.ended_epoch = ctx.epoch
    war.victor_entity_id = victor_id
    war.loser_entity_id = loser_id
    event = await war_event(ctx.session, war)
    label = ENDING_LABELS[ending]
    for row in await war_sides(ctx.session, war.id):
        row.left_epoch = ctx.epoch
    for siege in await ctx.session.scalars(select(SiegeRow).where(SiegeRow.war_id == war.id, SiegeRow.status == SiegeStatus.ONGOING)):
        siege.status = SiegeStatus.LIFTED
        siege.ended_epoch = ctx.epoch
    for army_row in await ctx.session.scalars(select(ArmyRow).where(ArmyRow.war_id == war.id, ArmyRow.disbanded_epoch.is_(None))):
        army_row.disbanded_epoch = ctx.epoch
        army = await living_entity(ctx.session, army_row.entity_id)
        if army is not None:
            stand_down(ctx.rules, army, await living_entity(ctx.session, army_row.owner_entity_id))
            await retire_in(ctx, army, f"disbanded when {event.name} ended ({label})", close_bonds=True)
    await ctx.session.flush()
    ctx.count("wars_ended")


BOOK_KINDS = frozenset({EngineKind.LIBRARY, EngineKind.SCHOOL})


async def _conquer(ctx: TickContext, war: WarRow, victor: EntityRow, loser: EntityRow) -> list[str]:
    event = await war_event(ctx.session, war)
    bonds = BondRepository(ctx.session)
    for bond in await bonds.incoming(loser.id, BondKind.RULES):
        await bonds.deactivate(bond, ctx.epoch, f"conquest of {event.name}")
    await bonds.connect(BondDraft(victor.id, loser.id, BondKind.RULES, ctx.epoch, f"conquest of {event.name}"))
    notes: list[str] = []
    language = await spoken_language(ctx.session, victor.id)
    loser_languages = {bond.target_node_id for bond in await bonds.outgoing(loser.id, BondKind.SPEAKS)}
    if language is not None and language.status is EntityStatus.CANON and language.id not in loser_languages:
        await bonds.connect(BondDraft(loser.id, language.id, BondKind.SPEAKS, ctx.epoch, "came with conquest"))
    wonders = await ctx.session.scalars(
        select(EntityRow)
        .join(EntityFlagRow, EntityFlagRow.entity_id == EntityRow.id)
        .where(EntityFlagRow.flag == EntityFlag.WONDER, EntityRow.location_id == loser.id, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    wonder = wonders.first()
    if wonder is not None:
        notes.append(f"The wonder {wonder.name} is now in the hands of {victor.name}.")
    notes.extend(await burn_books(ctx, victor, loser))
    return notes


async def burn_books(ctx: TickContext, victor: EntityRow, loser: EntityRow) -> list[str]:
    if value_reading(await values_for(ctx.session, victor.id), ActKind.BURNING_BOOKS) < ctx.rules.campaigns.book_burning_reading:
        return []
    if await forbidden(ctx, victor.id, ActKind.BURNING_BOOKS):
        return []
    keeps = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.location_id == loser.id, EntityRow.status == EntityStatus.CANON, EntityRow.engine_kind.in_(list(BOOK_KINDS)))
        .order_by(EntityRow.id)
    )
    notes: list[str] = []
    for keep in keeps:
        await retire_in(ctx, keep, f"burned by {victor.name} after the conquest", close_bonds=True)
        await witnessed(ctx, loser.id, victor.id, ActKind.BURNING_BOOKS, base=ctx.rules.memory.outrage_magnitude, note=keep.name)
        await judged(ctx, victor.id, loser.id, ActKind.BURNING_BOOKS, note=keep.name)
        notes.append(f"{victor.name} burned {keep.name}; its books went up in smoke.")
    return notes


async def _convert_loser(ctx: TickContext, war: WarRow, victor: EntityRow, loser: EntityRow, ending: WarEnding) -> list[str]:
    campaigns = ctx.rules.campaigns
    victor_god = await living_patron(ctx.session, victor)
    loser_god = await BondRepository(ctx.session).patron(loser.id)
    if victor_god is None or victor_god.id == loser_god:
        return []
    base = campaigns.conquest_conversion_chance if ending is WarEnding.CONQUEST else campaigns.tribute_conversion_chance
    chance = base * faith_dominance(ctx.rules, victor_god.id, await faith_shares(ctx.session))
    rng = ctx.rng("conversion")
    if not rng.chance(chance):
        return []
    syncretic = loser_god is not None and rng.chance(campaigns.conquest_syncretism_pct)
    event = await war_event(ctx.session, war)
    if not await change_religion(ctx.session, loser, victor_god.id, ctx.epoch, f"came with the {ENDING_LABELS[ending]} of {event.name}", syncretic=syncretic):
        return []
    await converted(ctx, loser.id, victor.id, note=event.name)
    if syncretic:
        return [f"{loser.name} began to revere {victor_god.name} beside its own god."]
    return [f"{loser.name} converted to the faith of {victor_god.name}."]


async def impose_victory(ctx: TickContext, war: WarRow, victor: EntityRow, loser: EntityRow) -> WarSettlement:
    event = await war_event(ctx.session, war)
    if victor.entity_type in (EntityType.FACTION, EntityType.PEOPLE) and loser.entity_type is EntityType.SETTLEMENT:
        ending = WarEnding.CONQUEST
        notes = await _conquer(ctx, war, victor, loser)
    else:
        ending = WarEnding.TRIBUTE
        await impose_tribute(ctx, loser, victor, war, event.name)
        notes = []
    notes.extend(await _convert_loser(ctx, war, victor, loser, ending))
    notes.extend(await peace_terms(ctx, war, victor, loser))
    return WarSettlement(ending, victor.id, loser.id, notes)


async def end_war(
    ctx: TickContext,
    war: WarRow,
    ending: WarEnding,
    *,
    victor_id: int | None = None,
    loser_id: int | None = None,
    reason: str | None = None,
    close_hostility: bool = True,
    apply_relation: bool = True,
) -> WarSettlement:
    sides = await sides_of(ctx.session, war)
    settlement = WarSettlement(ending, victor_id, loser_id)
    if sides is None:
        await close_war(ctx, war, ending, victor_id, loser_id)
        return settlement
    first, second = sides
    event = await war_event(ctx.session, war)
    victor, loser = await living_entity(ctx.session, victor_id), await living_entity(ctx.session, loser_id)
    if close_hostility:
        await make_peace(ctx, first, second, f"end of {event.name}" if victor is not None else reason or ENDING_LABELS[ending])
    if ending is WarEnding.VICTORY and victor is not None and loser is not None:
        settlement = await impose_victory(ctx, war, victor, loser)
    elif ending is WarEnding.WHITE_PEACE:
        first_side, second_side = await living_entity(ctx.session, first), await living_entity(ctx.session, second)
        if first_side is not None and second_side is not None:
            await white_peace(ctx, first_side, second_side)
    ctx.count("captives_exchanged", await exchange_at_peace(ctx, war.id))
    ctx.count("holy_peace", await holy_peace(ctx, first, second))
    if apply_relation:
        delta = relation_effect(ctx.rules, settlement.ending)
        if settlement.victor_id is not None and settlement.loser_id is not None:
            await change_relation(
                ctx,
                settlement.loser_id,
                settlement.victor_id,
                delta,
                ENDING_MEMORIES.get(settlement.ending, MemoryKind.FOUGHT_US),
                note=ENDING_LABELS[settlement.ending],
                reverse=MemoryKind.FOUGHT_US,
                event_id=war.event_entity_id,
            )
        else:
            await change_relation(
                ctx,
                first,
                second,
                delta,
                ENDING_MEMORIES.get(settlement.ending, MemoryKind.MADE_PEACE),
                note=ENDING_LABELS[settlement.ending],
                event_id=war.event_entity_id,
            )
    await close_war(ctx, war, settlement.ending, settlement.victor_id, settlement.loser_id)
    if settlement.victor_id is not None and settlement.loser_id is not None:
        await BondRepository(ctx.session).connect(
            BondDraft(
                war.event_entity_id,
                settlement.victor_id,
                BondKind.PARTY_TO,
                ctx.epoch,
                f"victor ({ENDING_LABELS[settlement.ending]})",
                role=BondRole.VICTOR,
                war_id=war.id,
            )
        )
    return settlement


async def settle_peace(ctx: TickContext, first: int, second: int, ending: WarEnding, reason: str, *, truce: bool = False, apply_relation: bool = True) -> bool:
    war = await current_war(ctx.session, first, second)
    if war is not None:
        await make_peace(ctx, first, second, reason, truce)
        await end_war(ctx, war, ending, reason=reason, close_hostility=False, apply_relation=apply_relation)
        return True
    hostile = await BondRepository(ctx.session).exists_between(first, second, BondKind.ENEMY)
    await make_peace(ctx, first, second, reason, truce)
    if apply_relation:
        await change_relation(
            ctx, first, second, relation_effect(ctx.rules, ending), ENDING_MEMORIES.get(ending, MemoryKind.MADE_PEACE), note=ENDING_LABELS[ending]
        )
    return hostile


async def _note_cap_closure(ctx: TickContext, item: OngoingWar, idle_since: int) -> None:
    first, second = await living_entity(ctx.session, item.attacker_id), await living_entity(ctx.session, item.defender_id)
    names = (first.name if first else "one side", second.name if second else "the other")
    idle = ctx.epoch - idle_since
    if idle >= ctx.rules.diplomacy.cap_close_idle_epochs:
        text = f"The war between {names[0]} and {names[1]}, with no sword drawn for {idle} epochs, burnt out in exhaustion; the two sides made a truce."
        key = "war.cap_closed_idle"
    else:
        text = f"The war between {names[0]} and {names[1]} burnt out in exhaustion as the fronts multiplied; the two sides made a truce."
        key = "war.cap_closed_fronts"
    await ctx.chronicle(ChronicleKind.WAR, text, template_key=key, entity_ids=(item.war.event_entity_id, *item.sides), feed_category=FeedCategory.WAR)


async def close_wars_over_caps(ctx: TickContext) -> int:
    diplomacy = ctx.rules.diplomacy
    open_wars = [(await last_clash(ctx.session, item.war), item.war.id, item) for item in await ongoing_wars(ctx.session)]
    open_wars.sort(key=lambda entry: (entry[0], entry[1]))
    closed = 0

    async def close(entry: tuple[int, int, OngoingWar]) -> None:
        nonlocal closed
        open_wars.remove(entry)
        await end_war(ctx, entry[2].war, WarEnding.EXHAUSTION, reason="exhaustion peace")
        await _note_cap_closure(ctx, entry[2], entry[0])
        closed += 1

    while True:
        counts: dict[int, int] = {}
        for _, _, item in open_wars:
            for side in item.sides:
                counts[side] = counts.get(side, 0) + 1
        over = [entry for entry in open_wars if any(counts[side] > diplomacy.community_war_cap for side in entry[2].sides)]
        if not over:
            break
        both = next((entry for entry in over if all(counts[side] > diplomacy.community_war_cap for side in entry[2].sides)), None)
        await close(both if both is not None else over[0])
    while len(open_wars) > diplomacy.world_war_cap:
        await close(open_wars[0])
    return closed


async def close_stale_wars(ctx: TickContext) -> int:
    seen: set[frozenset[int]] = set()
    closed = 0
    bonds = BondRepository(ctx.session)
    for war in list(await ctx.session.scalars(select(WarRow).where(WarRow.status.in_(ACTIVE_WAR_STATUSES)).order_by(WarRow.id))):
        sides = await sides_of(ctx.session, war)
        if sides is None:
            await close_war(ctx, war, WarEnding.NO_SIDE_LEFT)
            closed += 1
            continue
        pair = unordered(*sides)
        if pair in seen:
            await close_war(ctx, war, WarEnding.SAME_FRONT)
            closed += 1
            continue
        seen.add(pair)
        first, second = await living_entity(ctx.session, sides[0]), await living_entity(ctx.session, sides[1])
        both_alive = is_community(first) and is_community(second)
        if both_alive and await bonds.exists_between(sides[0], sides[1], BondKind.ENEMY):
            continue
        await close_war(ctx, war, WarEnding.PEACE if both_alive else WarEnding.NO_SIDE_LEFT)
        closed += 1
    return closed + await close_wars_over_caps(ctx)
