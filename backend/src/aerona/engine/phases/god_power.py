from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog import god_lines
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.divine.creator import autonomy
from aerona.engine.gods.lineage import curse, curse_bloodline, make_prophet
from aerona.engine.gods.power import declare_rebellion, drain_son, drained_recently, end_rebellion
from aerona.engine.gods.queries import community_of, creator_row, flagged_ids, sons
from aerona.engine.gods.stats import Trait, trait_or
from aerona.engine.gods.worship import creator_node_id, creator_worshippers
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.faith import worship_creator
from aerona.engine.primitives.numbers import roll_top
from aerona.engine.primitives.queries import canon


@dataclass(frozen=True)
class CurseCandidate:
    mortal: EntityRow
    reason: str


async def spontaneous_rebellion(ctx: TickContext, creator: CreatorRow) -> None:
    rules = ctx.rules.god_power
    candidates = [
        son
        for son in await sons(ctx.session, [SonStatus.ACTIVE])
        if not son.rebel and son.loyalty < rules.auto_rebel_loyalty + await autonomy(ctx, son) and son.wrath >= rules.auto_rebel_wrath
    ]
    candidates.sort(key=lambda son: (son.loyalty, -son.wrath, son.id))
    if candidates and ctx.rng("rebellion").chance(rules.auto_rebel_chance + await autonomy(ctx, candidates[0])):
        await declare_rebellion(ctx, creator, candidates[0], god_lines.REBELLION_SPONTANEOUS_MANIFESTO, True)


async def angry_drain(ctx: TickContext, creator: CreatorRow) -> None:
    rules = ctx.rules.god_power
    if creator.mood_anger < rules.auto_drain_wrath:
        return
    rng = ctx.rng("auto_drain")
    active = [
        son for son in await sons(ctx.session, [SonStatus.ACTIVE]) if son.essence > 0 and not await drained_recently(ctx, son.id, rules.auto_drain_spacing)
    ]
    rebels = [son for son in active if son.rebel]
    target = rng.pick(rebels) if rebels else None
    if target is None:
        stubborn = sorted((son for son in active if son.loyalty < rules.auto_drain_loyalty), key=lambda son: (son.loyalty, -son.wrath, son.id))
        target = stubborn[0] if stubborn else None
    if target is not None and rng.chance(rules.auto_drain_chance):
        await drain_son(ctx, creator, target, spontaneous=True)


async def rebels_return(ctx: TickContext, creator: CreatorRow) -> None:
    rules = ctx.rules.god_power
    rng = ctx.rng("rebel_return")
    for son in await sons(ctx.session):
        if son.status is not SonStatus.DEAD and son.rebel and son.loyalty >= rules.auto_return_loyalty and rng.chance(rules.auto_return_chance):
            await end_rebellion(ctx, creator, son)


async def _uncursed_mortal(ctx: TickContext, entity_id: int, cursed: set[int]) -> EntityRow | None:
    entity = await ctx.session.get(EntityRow, entity_id)
    if entity is None or entity.entity_type is not EntityType.MORTAL or entity.status is not EntityStatus.CANON or entity.id in cursed:
        return None
    return entity


async def bloody_hands(ctx: TickContext, cursed: set[int]) -> list[CurseCandidate]:
    rules = ctx.rules.god_power
    creator_id = await creator_node_id(ctx.session)
    prophets = await flagged_ids(ctx.session, EntityFlag.PROPHET)
    devoted: set[int] = set()
    if creator_id is not None:
        worship = select(BondRow.source_node_id).where(BondRow.kind == BondKind.WORSHIPS, BondRow.target_node_id == creator_id)
        devoted = set(await ctx.session.scalars(worship))
    kills = select(BondRow).where(BondRow.kind == BondKind.KILLED, BondRow.epoch >= ctx.epoch - rules.auto_curse_epochs).order_by(BondRow.id)
    found: dict[int, CurseCandidate] = {}
    for bond in await ctx.session.scalars(kills):
        if (bond.target_node_id not in prophets and bond.target_node_id not in devoted) or bond.source_node_id in found:
            continue
        killer = await _uncursed_mortal(ctx, bond.source_node_id, cursed)
        victim = await ctx.session.get(EntityRow, bond.target_node_id)
        if killer is not None and victim is not None:
            found[killer.id] = CurseCandidate(killer, god_lines.CURSE_REASON_BLOODY_HAND.format(victim=victim.name))
    return list(found.values())


async def wrathful_pool(ctx: TickContext, creator: CreatorRow, cursed: set[int]) -> list[CurseCandidate]:
    rules = ctx.rules.god_power
    pool: dict[int, CurseCandidate] = {}
    statement = (
        select(BondRow.source_node_id, EntityRow.name)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.DESTROYED, EntityRow.engine_kind == EngineKind.TEMPLE)
        .order_by(BondRow.id)
    )
    for killer_id, place in await ctx.session.execute(statement):
        killer = await _uncursed_mortal(ctx, killer_id, cursed)
        if killer is not None and killer.id not in pool:
            pool[killer.id] = CurseCandidate(killer, god_lines.CURSE_REASON_TEMPLE.format(creator=creator.name, place=place))
    for mortal_id in sorted(await flagged_ids(ctx.session, EntityFlag.CURSED)):
        mortal = await _uncursed_mortal(ctx, mortal_id, cursed)
        if mortal is not None and mortal.id not in pool:
            pool[mortal.id] = CurseCandidate(mortal, god_lines.CURSE_REASON_CURSED)
    if rules.auto_curse_min_kills > 0:
        counts = await ctx.session.execute(
            select(BondRow.source_node_id, func.count(BondRow.id))
            .where(BondRow.kind == BondKind.KILLED)
            .group_by(BondRow.source_node_id)
            .having(func.count(BondRow.id) >= rules.auto_curse_min_kills)
        )
        for killer_id, count in counts:
            killer = await _uncursed_mortal(ctx, killer_id, cursed)
            if killer is not None and killer.id not in pool:
                pool[killer.id] = CurseCandidate(killer, god_lines.CURSE_REASON_KILLER.format(count=count))
    return list(pool.values())


async def spontaneous_curse(ctx: TickContext, creator: CreatorRow) -> None:
    rules = ctx.rules.god_power
    rng = ctx.rng("auto_curse")
    cursed = await flagged_ids(ctx.session, EntityFlag.BLOODLINE_CURSE)
    chosen: CurseCandidate | None = None
    hands = await bloody_hands(ctx, cursed)
    if hands and rng.chance(rules.auto_curse_chance):
        chosen = hands[0]
    if chosen is None and creator.mood_anger >= rules.auto_curse_wrath:
        pool = await wrathful_pool(ctx, creator, cursed)
        if pool and rng.chance(rules.auto_curse_wrath_chance):
            chosen = roll_top(rng, pool, rules.auto_candidates, lambda item: (-item.mortal.power_level, item.mortal.id))
    if chosen is not None:
        await curse_bloodline(ctx, creator, chosen.mortal, chosen.reason)


async def spontaneous_prophet(ctx: TickContext, creator: CreatorRow) -> None:
    rules = ctx.rules.god_power
    if rules.auto_prophet_cap <= 0 or creator.mood_contentment < rules.auto_prophet_contentment:
        return
    prophets = await flagged_ids(ctx.session, EntityFlag.PROPHET)
    mortals = await canon(ctx.session, [EntityType.MORTAL])
    if sum(1 for mortal in mortals if mortal.id in prophets) >= rules.auto_prophet_cap:
        return
    cult = {entity.id for entity in await creator_worshippers(ctx.session)}
    cursed = await flagged_ids(ctx.session, EntityFlag.CURSED)
    candidates = []
    for mortal in mortals:
        if mortal.id in prophets or mortal.id in cursed:
            continue
        community = await community_of(ctx.session, mortal)
        if mortal.id in cult or (community is not None and community.id in cult):
            candidates.append(mortal)
    rng = ctx.rng("auto_prophet")
    if candidates and rng.chance(rules.auto_prophet_chance):
        chosen = roll_top(
            rng, candidates, rules.auto_candidates, lambda mortal: (-(trait_or(mortal, Trait.CHARISMA, 0) + trait_or(mortal, Trait.INTELLECT, 0)), mortal.id)
        )
        if chosen is not None:
            await make_prophet(ctx, creator, chosen, spontaneous=True)


async def curse_newborns(ctx: TickContext) -> None:
    flagged = await flagged_ids(ctx.session, EntityFlag.BLOODLINE_CURSE)
    cursed = {entity.id for entity in await canon(ctx.session) if entity.id in flagged}
    if not cursed:
        return
    statement = select(BondRow.source_node_id).where(BondRow.kind == BondKind.DESCENDS_FROM, BondRow.target_node_id.in_(cursed)).order_by(BondRow.id)
    typed = select(BondRow.target_node_id).where(BondRow.kind == BondKind.PARENT_OF, BondRow.source_node_id.in_(cursed)).order_by(BondRow.id)
    newborns: list[EntityRow] = []
    for child_id in dict.fromkeys([*await ctx.session.scalars(statement), *await ctx.session.scalars(typed)]):
        child = await ctx.session.get(EntityRow, child_id)
        if child is not None and child.status is EntityStatus.CANON and child.id not in flagged:
            newborns.append(child)
    for child in newborns:
        await curse(ctx, child)
    if newborns:
        line = god_lines.BLOODLINE_NEWBORNS
        names = ", ".join(child.name for child in newborns[: ctx.rules.god_power.bloodline_curse_depth])
        await ctx.chronicle(
            ChronicleKind.DIVINE_SIGN, line.render(count=len(newborns), names=names), template_key=line.key, entity_ids=[child.id for child in newborns]
        )


async def prophet_conversions(ctx: TickContext, creator: CreatorRow) -> None:
    rules = ctx.rules.god_power
    rng = ctx.rng("prophet_conversion")
    prophets = await flagged_ids(ctx.session, EntityFlag.PROPHET)
    for prophet in await canon(ctx.session, [EntityType.MORTAL]):
        if prophet.id not in prophets:
            continue
        community = await community_of(ctx.session, prophet)
        if community is None or not rng.chance(rules.prophet_convert_chance):
            continue
        if await worship_creator(ctx.session, community, ctx.epoch, god_lines.PROPHET_COMMUNITY_VOW.format(prophet=prophet.name)):
            line = god_lines.PROPHET_COMMUNITY
            await ctx.chronicle(
                ChronicleKind.DIVINE_SIGN,
                line.render(community=community.name, creator=creator.name, prophet=prophet.name),
                template_key=line.key,
                entity_ids=[community.id, prophet.id],
            )


@reads("table.bonds", "table.entity_flags", "table.epoch_year_cursors", "table.nodes", "table.son_relations", "table.world_attention")
@writes("table.chronicle", "table.epoch_year_cursors", "table.incident_participants", "table.incidents", "table.son_relations", "table.sons")
async def god_power(ctx: TickContext) -> None:
    creator = await creator_row(ctx.session)
    if creator is None:
        return
    await spontaneous_rebellion(ctx, creator)
    await angry_drain(ctx, creator)
    await rebels_return(ctx, creator)
    await spontaneous_curse(ctx, creator)
    await spontaneous_prophet(ctx, creator)
    await curse_newborns(ctx)
    await prophet_conversions(ctx, creator)
    await ctx.session.flush()


PHASES = (Phase("god_power", god_power),)
