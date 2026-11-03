from sqlalchemy import select

from aerona.catalog.mind import MEMORIES
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import MemoryRow, MindRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.mind import CareerChange, MemoryKind, TraitEffect, ValueHolder
from aerona.domain.enums.war import HeroQuestKind
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.mind.book import (
    Holder,
    ValueIndex,
    ensure_mind_row,
    holder_kind,
    living_minds,
    scaled_by,
    trait_effect,
    traits_of,
    write_values,
)
from aerona.engine.mind.memories import forget_faded, kin_of, remember, strength_of
from aerona.engine.mind.needs import update_needs, update_pressures
from aerona.engine.mind.opinion import OpinionContext
from aerona.engine.mind.skills import choose_career, seed_skills, teach_apprentices, weather_skills
from aerona.engine.mind.traits import seed_traits
from aerona.engine.mind.values import drift_culture, drift_person, seed_values
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.heroes import active_quest, start_quest
from aerona.engine.phases.remembrance import disaster_toll
from aerona.engine.phases.society_support.quests import QuestOption
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.services.community_relations import lend_settlement_values, refresh_relations

HISTORY_FIXUP = "mind.relation_history"
HISTORY_NOTE = "the weight of older history"
VENGEFUL_MEMORIES = (MemoryKind.KILLED_KIN, MemoryKind.MAIMED_ME)
SEED_ORDER = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT, EntityType.FACTION, EntityType.MORTAL)
COMMUNITY_MINDS = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})


async def seed_mind(ctx: TickContext, node: Holder) -> bool:
    row, created = await ensure_mind_row(ctx.session, node, ctx.epoch)
    if not created:
        return False
    rng = ctx.rng(seed_of("backfill.mind", node.id))
    kind = holder_kind(node)
    divine = kind is ValueHolder.DIVINE
    if kind is ValueHolder.PERSONAL or divine:
        culture_hint = await seed_values(ctx.session, ctx.rules, node, rng) or {}
        await seed_traits(ctx.session, ctx.rules, node.id, culture_hint, rng=rng, epoch=ctx.epoch, divine=divine)
    values = await seed_values(ctx.session, ctx.rules, node, rng)
    if values is not None and kind is not None and kind is not ValueHolder.COMMUNITY:
        await write_values(ctx.session, kind, node.id, values)
    if isinstance(node, EntityRow) and node.entity_type is EntityType.MORTAL:
        await seed_skills(ctx.session, ctx.rules, node, rng, ctx.epoch)
        await backfill_mortal_memories(ctx, node)
    if isinstance(node, EntityRow) and node.entity_type in COMMUNITY_MINDS:
        await backfill_community_memories(ctx, node)
    row.updated_epoch = ctx.epoch
    return True


async def backfill_mortal_memories(ctx: TickContext, mortal: EntityRow) -> None:
    table = ctx.rules.memory
    for relative in await kin_of(ctx.session, mortal.id):
        for bond in await active_bonds(ctx.session, [BondKind.KILLED], targets=[relative.id]):
            await remember(
                ctx.session,
                ctx.rules,
                holder_id=mortal.id,
                subject_id=bond.source_node_id,
                kind=MemoryKind.KILLED_KIN,
                magnitude=-table.killed_kin_magnitude,
                epoch=bond.epoch,
                note=relative.name,
            )
    for bond in await active_bonds(ctx.session, [BondKind.HOLDS_CAPTIVE], targets=[mortal.id]):
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=mortal.id,
            subject_id=bond.source_node_id,
            kind=MemoryKind.HELD_CAPTIVE,
            magnitude=-table.backfill_magnitude,
            epoch=bond.epoch,
        )
    for bond in await active_bonds(ctx.session, [BondKind.APPRENTICE_OF], sources=[mortal.id]):
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=mortal.id,
            subject_id=bond.target_node_id,
            kind=MemoryKind.TAUGHT_ME,
            magnitude=table.backfill_magnitude,
            epoch=bond.epoch,
        )


async def backfill_community_memories(ctx: TickContext, community: EntityRow) -> None:
    table = ctx.rules.memory
    for bond in [
        *await active_bonds(ctx.session, [BondKind.ENEMY], sources=[community.id]),
        *await active_bonds(ctx.session, [BondKind.ENEMY], targets=[community.id]),
    ]:
        other = bond.other_end(community.id)
        await remember(
            ctx.session, ctx.rules, holder_id=community.id, subject_id=other, kind=MemoryKind.FOUGHT_US, magnitude=-table.backfill_magnitude, epoch=bond.epoch
        )
    for bond in await active_bonds(ctx.session, [BondKind.PAYS_TRIBUTE], sources=[community.id]):
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=community.id,
            subject_id=bond.target_node_id,
            kind=MemoryKind.DEMANDED_TRIBUTE,
            magnitude=-table.backfill_magnitude,
            epoch=bond.epoch,
        )


async def mind_survey(ctx: TickContext) -> None:
    known = set(await ctx.session.scalars(select(MindRow.node_id)))
    created = 0
    minds = await living_minds(ctx.session)
    for entity_type in SEED_ORDER:
        for entity in minds:
            if entity.entity_type is entity_type and entity.id not in known and await seed_mind(ctx, entity):
                created += 1
    for son in await ctx.session.scalars(select(SonRow).order_by(SonRow.id)):
        if son.id not in known and await seed_mind(ctx, son):
            created += 1
    for god in await ctx.session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)):
        if god.id not in known and await seed_mind(ctx, god):
            created += 1
    ctx.count("minds", created)
    settled = await settle_history(ctx)
    ctx.count("histories_settled", settled)
    if created or settled:
        await mind_needs(ctx)
        ctx.count("relations_refreshed", await refresh_relations(ctx.session, ctx.rules, ctx.epoch))


async def settle_history(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, HISTORY_FIXUP) is not None:
        return 0
    rows = list(await ctx.session.scalars(select(CommunityRelationRow)))
    settled = 0
    if rows:
        values = await ValueIndex.load(ctx.session)
        nodes = {node for row in rows for node in (row.entity_a_id, row.entity_b_id)}
        await lend_settlement_values(ctx.session, values, nodes)
        context = await OpinionContext.load(ctx.session, ctx.rules, ctx.epoch, nodes, values)
        for row in rows:
            gap = row.value - context.relation(row.entity_a_id, row.entity_b_id)
            if abs(gap) < ctx.rules.memory.forget_below:
                continue
            for holder, subject in ((row.entity_a_id, row.entity_b_id), (row.entity_b_id, row.entity_a_id)):
                await remember(
                    ctx.session,
                    ctx.rules,
                    holder_id=holder,
                    subject_id=subject,
                    kind=MemoryKind.LONG_HISTORY,
                    magnitude=gap,
                    epoch=ctx.epoch,
                    note=HISTORY_NOTE,
                    forced=True,
                )
            settled += 1
    ctx.session.add(AppliedFixupRow(key=HISTORY_FIXUP, result={"pairs": settled}))
    await ctx.session.flush()
    return settled


async def plagued_communities(ctx: TickContext) -> set[int]:
    plagues = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind == EngineKind.PLAGUE, EntityRow.birth_epoch == ctx.epoch)
    )
    struck: set[int] = set()
    for plague in list(plagues):
        _, communities = await disaster_toll(ctx, plague)
        struck.update(community.id for community in communities)
    return struck


async def mind_values(ctx: TickContext) -> None:
    index = await ValueIndex.load(ctx.session)
    plagued = await plagued_communities(ctx)
    moved = 0
    for entity in await living_minds(ctx.session):
        if entity.entity_type is EntityType.PEOPLE:
            moved += 1 if await drift_culture(ctx, entity, index, plagued) else 0
        elif entity.entity_type is EntityType.MORTAL:
            moved += 1 if await drift_person(ctx, entity, index, await traits_of(ctx.session, entity.id)) else 0
    ctx.count("values_drifted", moved)


async def mind_skills(ctx: TickContext) -> None:
    ctx.count("lessons", await teach_apprentices(ctx))
    index = await ValueIndex.load(ctx.session)
    rusted = changed = 0
    for mortal in await living_minds(ctx.session):
        if mortal.entity_type is not EntityType.MORTAL:
            continue
        rusted += await weather_skills(ctx, mortal)
        move = await choose_career(ctx, mortal, index.of(mortal.id))
        if move is None:
            continue
        mortal.mortal_role = move.new
        changed += 1
        if move.reason is CareerChange.INJURED:
            mind = await ctx.session.get(MindRow, mortal.id)
            if mind is not None:
                mind.career_ended_epoch = ctx.epoch
        if is_notable(ctx.rules, mortal, await EntityRepository(ctx.session).flags(mortal.id)):
            text = (
                f"{mortal.name} could no longer live as a {move.old.value} and became a {move.new.value}."
                if move.reason is CareerChange.INJURED
                else f"{mortal.name} gave up the life of a {move.old.value} to become a {move.new.value}."
            )
            await note(ctx, text, key=f"skill.career_{move.reason.value}", ids=[mortal.id])
    await ctx.session.flush()
    ctx.count("skills_rusted", rusted)
    ctx.count("careers_changed", changed)


async def vengeance(ctx: TickContext) -> int:
    table = ctx.rules.memory
    sworn = 0
    grudges = await ctx.session.scalars(
        select(MemoryRow).where(MemoryRow.kind.in_(VENGEFUL_MEMORIES), MemoryRow.magnitude <= -table.vengeance_threshold).order_by(MemoryRow.id)
    )
    for row in list(grudges):
        if -strength_of(row, ctx.epoch) < table.vengeance_threshold:
            continue
        avenger = await ctx.session.get(EntityRow, row.holder_node_id)
        target = await ctx.session.get(EntityRow, row.subject_node_id)
        if avenger is None or target is None or avenger.status is not EntityStatus.CANON or target.status is not EntityStatus.CANON:
            continue
        if avenger.entity_type is not EntityType.MORTAL or target.entity_type is not EntityType.MORTAL or await active_quest(ctx.session, avenger.id):
            continue
        drive = scaled_by(trait_effect(await traits_of(ctx.session, avenger.id), TraitEffect.MEMORY_DECAY, ctx.rules.traits.effect_scale_pct) * -1)
        if not ctx.rng(seed_of("vengeance", row.id)).chance(table.vengeance_chance * drive):
            continue
        reason = row.note or MEMORIES[row.kind].label.lower()
        await start_quest(ctx, avenger, QuestOption(HeroQuestKind.VENGEANCE, target.id, 1.0, f"to avenge {reason} on {target.name}"))
        await note(ctx, f"{avenger.name} swore vengeance on {target.name} for {reason}.", key="memory.vengeance", ids=[avenger.id, target.id])
        sworn += 1
    return sworn


async def mind_memories(ctx: TickContext) -> None:
    ctx.count("vengeance_sworn", await vengeance(ctx))
    ctx.count("memories_forgotten", await forget_faded(ctx.session, ctx.rules, ctx.epoch))


async def mind_needs(ctx: TickContext) -> None:
    index = await ValueIndex.load(ctx.session)
    minds = await living_minds(ctx.session)
    communities = [entity for entity in minds if entity.entity_type in COMMUNITY_MINDS]
    await lend_settlement_values(ctx.session, index, {community.id for community in communities})
    plagued = await plagued_communities(ctx)
    pressed = needy = 0
    for community in communities:
        if await update_pressures(ctx, community, index.of(community.id), plagued):
            pressed += 1
    for mortal in minds:
        if mortal.entity_type is EntityType.MORTAL and await update_needs(ctx, mortal, index.of(mortal.id), await traits_of(ctx.session, mortal.id)):
            needy += 1
    ctx.count("pressures", pressed)
    ctx.count("needs", needy)


async def mind_opinion(ctx: TickContext) -> None:
    ctx.count("relations_refreshed", await refresh_relations(ctx.session, ctx.rules, ctx.epoch))


SURVEY_PHASES = (Phase("mind_survey", mind_survey),)
MIND_PHASES = (
    Phase("mind_values", mind_values),
    Phase("mind_skills", mind_skills),
    Phase("mind_memories", mind_memories),
    Phase("mind_needs", mind_needs),
    Phase("mind_opinion", mind_opinion),
)
PHASES = (*SURVEY_PHASES, *MIND_PHASES)
