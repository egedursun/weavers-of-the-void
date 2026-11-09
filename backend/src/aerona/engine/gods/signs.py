from collections.abc import Callable, Sequence

from sqlalchemy import select

from aerona.catalog import god_lines
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleEntityRow, ChronicleRow, MessageRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityFlag, EntityType, MortalRole
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.node import NodeKind
from aerona.engine.context import TickContext
from aerona.engine.divine.standing import standing_of_pair
from aerona.engine.gods.interventions import apply_abundance
from aerona.engine.gods.queries import active_sons, flagged_ids, place_of
from aerona.engine.gods.stats import Trait, trait_or
from aerona.engine.gods.worship import creator_worshippers
from aerona.engine.phases.disasters import apply_disaster, disaster_phrase, record_disaster_event
from aerona.engine.primitives.faith import worship_creator
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import canon

SINNER_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT)
ESTRANGED_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT)
DREAM_ROLES = frozenset({MortalRole.SEER, MortalRole.SAGE, MortalRole.PRIEST})

SIGN_DISASTERS = (Disaster.STORM, Disaster.EARTHQUAKE, Disaster.DROUGHT)


async def struck_ids(ctx: TickContext) -> set[int]:
    horizon = ctx.epoch - ctx.rules.creator.sign_exclusion_epochs
    statement = (
        select(ChronicleEntityRow.entity_id)
        .join(ChronicleRow, ChronicleRow.id == ChronicleEntityRow.chronicle_id)
        .where(ChronicleRow.kind == ChronicleKind.DIVINE_SIGN, ChronicleRow.epoch > horizon)
    )
    return set(await ctx.session.scalars(statement))


def sign_target(
    rng: SeededRandom,
    count: int,
    candidates: Sequence[EntityRow],
    struck: set[int],
    *,
    sorter: Callable[[EntityRow], tuple[int, ...]] | None = None,
    last_resort: bool = True,
) -> EntityRow | None:
    fresh = [entity for entity in candidates if entity.id not in struck]
    pool = fresh if fresh or not last_resort else list(candidates)
    if sorter is not None:
        pool = sorted(pool, key=sorter)
    head = pool[: max(1, count)]
    return rng.pick(head) if head else None


async def wrath_sign(ctx: TickContext, creator: CreatorRow, target: EntityRow | None = None) -> EntityRow | None:
    rules = ctx.rules.creator
    rng = ctx.rng("wrath_sign")
    struck = await struck_ids(ctx)
    if target is None:
        cursed = await flagged_ids(ctx.session, EntityFlag.GODLESS) | await flagged_ids(ctx.session, EntityFlag.CURSED)
        sinners = []
        for entity in await canon(ctx.session, SINNER_TYPES):
            place = await place_of(ctx.session, entity)
            if entity.id in cursed and place is not None and place.id not in struck:
                sinners.append(entity)
        target = sign_target(rng, rules.sign_candidates, sinners, struck, last_resort=False)
        if target is None:
            regions = await canon(ctx.session, [EntityType.REGION])
            target = sign_target(rng, rules.sign_candidates, regions, struck, sorter=lambda region: (-trait_or(region, Trait.DANGER, 0), region.id))
    place = await place_of(ctx.session, target) if target is not None else None
    if place is None:
        return None
    kind = rng.pick(SIGN_DISASTERS)
    impact = await apply_disaster(ctx, place, kind, rules.wrath_disaster_severity / PERCENT)
    event = await record_disaster_event(ctx, place, kind, rules.wrath_event_severity_base + rng.die(rules.wrath_event_severity_die), impact)
    creator.mood_anger = clamp_percent(creator.mood_anger - rules.wrath_discharge)
    line = rng.pick(god_lines.WRATH_SIGNS)
    await ctx.chronicle(
        ChronicleKind.DIVINE_SIGN,
        line.render(creator=creator.name, place=place.name, disaster=disaster_phrase(kind)),
        template_key=line.key,
        entity_ids=[place.id, event.id],
    )
    ctx.count("wrath_signs")
    return place


async def grace_sign(ctx: TickContext, creator: CreatorRow, target: EntityRow | None = None) -> EntityRow | None:
    rules = ctx.rules.creator
    rng = ctx.rng("grace_sign")
    struck = await struck_ids(ctx)
    if target is None:
        cult = [entity for entity in await creator_worshippers(ctx.session) if entity.entity_type is not EntityType.MORTAL]
        target = sign_target(rng, rules.sign_candidates, cult, struck, last_resort=False)
        if target is None:
            communities = await canon(ctx.session, SINNER_TYPES)
            target = sign_target(rng, rules.sign_candidates, communities, struck, sorter=lambda entity: (-trait_or(entity, Trait.PIETY, 0), entity.id))
    if target is None:
        return None
    await apply_abundance(ctx, target)
    line = rng.pick(god_lines.GRACE_SIGNS)
    await ctx.chronicle(ChronicleKind.DIVINE_SIGN, line.render(creator=creator.name, place=target.name), template_key=line.key, entity_ids=[target.id])
    ctx.count("grace_signs")
    return target


async def silence(ctx: TickContext, creator: CreatorRow, announce: bool) -> list[SonRow]:
    rules = ctx.rules.creator
    affected = await active_sons(ctx.session)
    for son in affected:
        son.loyalty = clamp_percent(son.loyalty - rules.indifferent_loyalty_loss)
        son.ambition = clamp_percent(son.ambition + rules.indifferent_ambition_gain)
    if announce:
        line = ctx.rng("silence_sign").pick(god_lines.SILENCE_SIGNS)
        await ctx.chronicle(ChronicleKind.DIVINE_SIGN, line.render(creator=creator.name), template_key=line.key)
        ctx.count("silence_signs")
    await ctx.session.flush()
    return affected


async def lonely_dream(ctx: TickContext, creator: CreatorRow, target: EntityRow | None = None) -> EntityRow | None:
    rules = ctx.rules.creator
    rng = ctx.rng("lonely_dream")
    if target is None:
        struck = await struck_ids(ctx)
        mortals = await canon(ctx.session, [EntityType.MORTAL])
        seers = [mortal for mortal in mortals if mortal.mortal_role in DREAM_ROLES]
        target = sign_target(rng, rules.sign_candidates, seers, struck, last_resort=False) or sign_target(rng, rules.sign_candidates, mortals, struck)
    if target is None:
        return None
    ctx.session.add(
        MessageRow(
            epoch=ctx.epoch,
            sender_node_id=creator.id,
            recipient_node_id=target.id,
            intent=MessageIntent.DREAM,
            text=god_lines.LONELY_DREAM.text,
        )
    )
    creator.mood_loneliness = clamp_percent(creator.mood_loneliness - rules.lonely_discharge)
    line = rng.pick(god_lines.LONELINESS_SIGNS)
    await ctx.chronicle(ChronicleKind.DIVINE_SIGN, line.render(creator=creator.name, mortal=target.name), template_key=line.key, entity_ids=[target.id])
    ctx.count("lonely_dreams")
    return target


async def estranged_candidates(ctx: TickContext) -> list[EntityRow]:
    godless = await flagged_ids(ctx.session, EntityFlag.GODLESS)
    cursed_statement = (
        select(BondRow.target_node_id)
        .join(NodeRow, NodeRow.id == BondRow.source_node_id)
        .where(BondRow.kind == BondKind.CURSED, BondRow.state == BondState.ACTIVE, NodeRow.kind == NodeKind.SON)
    )
    cursed = set(await ctx.session.scalars(cursed_statement))
    return [entity for entity in await canon(ctx.session, ESTRANGED_TYPES) if entity.id in godless or entity.id in cursed]


async def estranged_turn(ctx: TickContext, creator: CreatorRow) -> EntityRow | None:
    rules = ctx.rules.creator
    rng = ctx.rng("estranged")
    bonus = rules.estranged_content_bonus_pct if creator.mood_contentment >= rules.estranged_content_threshold else 0
    for entity in await estranged_candidates(ctx):
        warmth = await standing_of_pair(ctx, entity.id, creator.id)
        lift = (warmth.love - warmth.fear) * ctx.rules.divine_standing.creator_turn_pct / PERCENT if warmth is not None else 0
        if rng.chance(rules.estranged_turn_chance + bonus + lift) and await worship_creator(ctx.session, entity, ctx.epoch, god_lines.ESTRANGED_VOW):
            line = god_lines.ESTRANGED_TURN
            await ctx.chronicle(ChronicleKind.DIVINE_SIGN, line.render(entity=entity.name, creator=creator.name), template_key=line.key, entity_ids=[entity.id])
            ctx.count("estranged_turned")
            return entity
    return None
