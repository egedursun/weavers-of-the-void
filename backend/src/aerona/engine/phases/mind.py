from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.ethics import ACT_LABELS
from aerona.catalog.mind import MELEE_SKILLS, MEMORIES, TRAITS
from aerona.catalog.mind_split import IDEAS, derived_axes
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import CultureValueRow, GriefRow, MemoryRow, MindRow, PersonalityValueRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import (
    ActKind,
    CareerChange,
    GriefStage,
    IdeaState,
    MemoryKind,
    PressureKind,
    ThoughtKind,
    TraitEffect,
    ValueAxis,
    ValueHolder,
)
from aerona.domain.enums.polity import OathKind
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.war import HeroQuestKind
from aerona.engine.body.customs import people_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.demography.promotion import dormant_ids
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.aspirations import AspirationTally, aspire
from aerona.engine.mind.book import (
    Holder,
    ValueIndex,
    ensure_mind_row,
    holder_kind,
    living_minds,
    pressures_of,
    scaled_by,
    trait_effect,
    traits_of,
    values_for,
    write_values,
)
from aerona.engine.mind.depth import backfill_depth
from aerona.engine.mind.dreams import dream, visitations
from aerona.engine.mind.ethics import SCHISM_FACTION, drift_ethics, restore, schism, seed_ethics, seed_honour, spread_shame
from aerona.engine.mind.feelings import feel
from aerona.engine.mind.grief import GriefTally, advance
from aerona.engine.mind.hooks import FIGHTING_ROLES, judged
from aerona.engine.mind.ideas import ideas_of, turn_over
from aerona.engine.mind.inspiration import resolute, tend_inspiration
from aerona.engine.mind.memories import forget_faded, kin_of, remember, strength_of
from aerona.engine.mind.needs import role_status, update_needs, update_pressures
from aerona.engine.mind.opinion import OpinionContext
from aerona.engine.mind.preferences import adopt_totem, grow, make_taboos, pull_culture, seed_culture, seed_mortal
from aerona.engine.mind.skills import choose_career, left_to_beg, practise_any, seed_skills, teach_apprentices, weather_skills
from aerona.engine.mind.space import value_reading
from aerona.engine.mind.split import (
    Bodied,
    has_attributes,
    has_facets,
    seed_split,
    temper_facets,
    weather_attributes,
)
from aerona.engine.mind.thoughts import forget_faded as forget_faded_thoughts
from aerona.engine.mind.thoughts import settle_mood, think
from aerona.engine.mind.traits import seed_traits
from aerona.engine.mind.values import drift_body, drift_culture, drift_divine, drift_person, seed_values
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.factions import found_faction
from aerona.engine.phases.heroes import active_quest, start_quest
from aerona.engine.phases.remembrance import disaster_toll
from aerona.engine.phases.society_support.quests import QuestOption
from aerona.engine.polity.oaths import swear
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import active_bonds, canon, living_entity
from aerona.engine.primitives.society import move_stock, stock
from aerona.engine.services.community_relations import change_relation, lend_settlement_values, refresh_relations
from aerona.engine.services.war import ongoing_wars

HISTORY_FIXUP = "mind.relation_history"
AXES_FIXUP = "mind.belief_axes"
AID_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})
BEGGAR_TAG = "beggar"
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
    await seed_split(ctx.session, ctx.rules, node, rng)
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


@reads(
    "beast.agility",
    "beast.cunning",
    "beast.strength",
    "cult.zeal",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "people.craft",
    "people.magic",
    "people.martiality",
    "people.piety",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "place.fertility",
    "region.fertility",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.afflictions",
    "table.applied_fixups",
    "table.bonds",
    "table.class_standing",
    "table.community_needs",
    "table.community_relations",
    "table.community_societies",
    "table.conditions",
    "table.culture_values",
    "table.entity_flags",
    "table.entity_tags",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.holder_levels",
    "table.incubating_ideas",
    "table.injuries",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.needs",
    "table.nodes",
    "table.personality_values",
    "table.preferences",
    "table.pressures",
    "table.settlement_profiles",
    "table.skills",
    "table.sons",
    "table.species_ranges",
    "table.traits",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
)
@writes(
    "beast.agility",
    "beast.cunning",
    "beast.strength",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.culture_values",
    "table.entities",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.needs",
    "table.personality_values",
    "table.pressures",
    "table.skills",
    "table.sons",
    "table.traits",
)
async def mind_survey(ctx: TickContext) -> None:
    known = set(await ctx.session.scalars(select(MindRow.node_id)))
    created = 0
    minds = unheld(await living_minds(ctx.session))
    for entity_type in SEED_ORDER:
        for entity in minds:
            if entity.entity_type is entity_type and entity.id not in known and await seed_mind(ctx, entity):
                created += 1
    for son in unheld(await ctx.session.scalars(select(SonRow).order_by(SonRow.id))):
        if son.id not in known and await seed_mind(ctx, son):
            created += 1
    for god in unheld(await ctx.session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id))):
        if god.id not in known and await seed_mind(ctx, god):
            created += 1
    ctx.count("minds", created)
    ctx.count("belief_axes", await backfill_axes(ctx))
    ctx.count("minds_split", await backfill_split(ctx, minds))
    ctx.count("depth_traits", await backfill_depth(ctx.session, ctx.rules, [entity for entity in minds if entity.entity_type is EntityType.MORTAL], ctx.epoch))
    settled = await settle_history(ctx)
    ctx.count("histories_settled", settled)
    if created or settled:
        await mind_needs(ctx)
        ctx.count("relations_refreshed", await refresh_relations(ctx.session, ctx.rules, ctx.epoch))


async def axis_vectors(ctx: TickContext) -> tuple[dict[int, dict[ValueAxis, int]], dict[int, dict[ValueAxis, int]]]:
    cultures: dict[int, dict[ValueAxis, int]] = defaultdict(dict)
    persons: dict[int, dict[ValueAxis, int]] = defaultdict(dict)
    for culture in await ctx.session.scalars(select(CultureValueRow)):
        cultures[culture.entity_id][culture.axis] = culture.value
    for person in await ctx.session.scalars(select(PersonalityValueRow)):
        persons[person.node_id][person.axis] = person.value
    return cultures, persons


async def backfill_axes(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, AXES_FIXUP) is not None:
        return 0
    cultures, persons = await axis_vectors(ctx)
    filled = 0
    for owner, vector in cultures.items():
        missing = {axis: value for axis, value in derived_axes(vector).items() if axis not in vector}
        ctx.session.add_all(CultureValueRow(entity_id=owner, axis=axis, value=value) for axis, value in missing.items())
        filled += 1 if missing else 0
    for owner, vector in persons.items():
        missing = {axis: value for axis, value in derived_axes(vector).items() if axis not in vector}
        ctx.session.add_all(PersonalityValueRow(node_id=owner, axis=axis, value=value) for axis, value in missing.items())
        filled += 1 if missing else 0
    ctx.session.add(AppliedFixupRow(key=AXES_FIXUP, result={"holders": filled}))
    await ctx.session.flush()
    return filled


async def backfill_split(ctx: TickContext, minds: list[EntityRow]) -> int:
    seeded = 0
    beasts = unheld(await canon(ctx.session, [EntityType.BEAST]))
    sons = unheld(await ctx.session.scalars(select(SonRow).order_by(SonRow.id)))
    gods = unheld(await ctx.session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)))
    nodes: list[Bodied] = [*minds, *beasts, *sons, *gods]
    for node in nodes:
        if has_attributes(node) or has_facets(node):
            seeded += 1 if await seed_split(ctx.session, ctx.rules, node, ctx.rng(seed_of("backfill.split", node.id))) else 0
    return seeded


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


@reads(
    "table.bonds",
    "table.community_relations",
    "table.culture_drift_causes",
    "table.culture_values",
    "table.drift_impositions",
    "table.entities",
    "table.ideology_adherents",
    "table.ideology_profiles",
    "table.injuries",
    "table.memories",
    "table.minds",
    "table.mortal_profiles",
    "table.nodes",
    "table.people_culture",
    "table.personality_values",
    "table.pressures",
    "table.traits",
    "table.war_sides",
)
@writes("table.culture_drift_causes", "table.culture_values", "table.drift_impositions", "table.personality_values")
async def mind_values(ctx: TickContext) -> None:
    index = await ValueIndex.load(ctx.session)
    plagued = await plagued_communities(ctx)
    moved = 0
    for entity in unheld(await living_minds(ctx.session)):
        if entity.entity_type is EntityType.PEOPLE:
            moved += 1 if await drift_culture(ctx, entity, index, plagued) else 0
        elif entity.entity_type is EntityType.MORTAL:
            moved += 1 if await drift_person(ctx, entity, index, await traits_of(ctx.session, entity.id)) else 0
        elif entity.entity_type in (EntityType.FACTION, EntityType.CULT):
            moved += 1 if await drift_body(ctx, entity, index) else 0
    for son in unheld(await ctx.session.scalars(select(SonRow).order_by(SonRow.id))):
        moved += 1 if await drift_divine(ctx, son, index) else 0
    for god in unheld(await ctx.session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id))):
        moved += 1 if await drift_divine(ctx, god, index) else 0
    ctx.count("values_drifted", moved)


async def spar(ctx: TickContext, fighter: EntityRow) -> bool:
    if fighter.mortal_role not in FIGHTING_ROLES or await at_war(ctx, fighter):
        return False
    skills = ctx.rules.skills
    await practise_any(ctx.session, ctx.rules, fighter.id, MELEE_SKILLS, skills.spar_xp, epoch=ctx.epoch)
    if not ctx.rng(f"spar.{fighter.id}").chance(skills.spar_injury_chance):
        return False
    await apply_hits(ctx, fighter, Harm(skills.spar_hp, HarmCause.ACCIDENT, "hurt while sparring", severity=1), lethal=False)
    return True


async def at_war(ctx: TickContext, fighter: EntityRow) -> bool:
    home = fighter.location_id
    return home is not None and bool(await ongoing_wars(ctx.session, home))


@reads(
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.conditions",
    "table.cult_tenets",
    "table.culture_values",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.memories",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.nodes",
    "table.personality_values",
    "table.prostheses",
    "table.skills",
    "table.thoughts",
    "table.traits",
    "table.wants",
    "table.war_sides",
    "table.wars",
)
@writes(
    "mortal.hp",
    "table.bodies",
    "table.body_customs",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.minds",
    "table.mortal_profiles",
    "table.skills",
    "table.thoughts",
    "table.traits",
)
async def mind_skills(ctx: TickContext) -> None:
    ctx.count("lessons", await teach_apprentices(ctx))
    index = await ValueIndex.load(ctx.session)
    rusted = changed = sparred = 0
    sleeping = await dormant_ids(ctx)
    for mortal in unheld(await living_minds(ctx.session)):
        if mortal.entity_type is not EntityType.MORTAL or mortal.id in sleeping:
            continue
        rusted += await weather_skills(ctx, mortal)
        sparred += 1 if await spar(ctx, mortal) else 0
        move = await choose_career(ctx, mortal, index.of(mortal.id))
        if move is None:
            continue
        mortal.mortal_role = move.new
        changed += 1
        rose = role_status(ctx.rules, move.new) >= role_status(ctx.rules, move.old)
        await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.ROSE_IN_RANK if rose else ThoughtKind.FELL_IN_RANK, ctx.epoch)
        if move.reason is CareerChange.INJURED:
            mind = await ctx.session.get(MindRow, mortal.id)
            if mind is not None:
                mind.career_ended_epoch = ctx.epoch
            if move.new is MortalRole.COMMONER and await left_to_beg(ctx, mortal):
                await EntityRepository(ctx.session).add_tags(mortal.id, [BEGGAR_TAG])
                await note(ctx, f"With no calling left and no one to keep them, {mortal.name} begs at the gates.", key="skill.career_beggar", ids=[mortal.id])
        if is_notable(ctx.rules, mortal, await EntityRepository(ctx.session).flags(mortal.id)):
            text = (
                f"{mortal.name} could no longer live as a {move.old.value} and became a {move.new.value}."
                if move.reason is CareerChange.INJURED
                else f"{mortal.name} gave up the life of a {move.old.value} to become a {move.new.value}."
            )
            await note(ctx, text, key=f"skill.career_{move.reason.value}", ids=[mortal.id])
    await ctx.session.flush()
    ctx.count("skills_rusted", rusted)
    ctx.count("sparring_wounds", sparred)
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
        if ctx.rng(seed_of("vengeance_oath", row.id)).chance(ctx.rules.oaths.vengeance_chance):
            await swear(ctx, avenger, OathKind.VENGEANCE, recipient_id=target.id, note_text=reason)
        sworn += 1
    return sworn


@reads("table.memories")
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
    "table.hero_quests",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.oaths",
)
async def mind_memories(ctx: TickContext) -> None:
    ctx.count("vengeance_sworn", await vengeance(ctx))
    ctx.count("memories_forgotten", await forget_faded(ctx.session, ctx.rules, ctx.epoch))


@reads(
    "mortal.charisma",
    "people.piety",
    "people.population",
    "people.prosperity",
    "place.fertility",
    "region.fertility",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.afflictions",
    "table.bonds",
    "table.class_standing",
    "table.community_needs",
    "table.community_societies",
    "table.conditions",
    "table.culture_values",
    "table.entity_flags",
    "table.entity_tags",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.injuries",
    "table.memories",
    "table.minds",
    "table.mortal_profiles",
    "table.needs",
    "table.personality_values",
    "table.preferences",
    "table.pressures",
    "table.settlement_profiles",
    "table.skills",
    "table.species_ranges",
    "table.traits",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.needs",
    "table.pressures",
)
async def mind_needs(ctx: TickContext) -> None:
    index = await ValueIndex.load(ctx.session)
    minds = unheld(await living_minds(ctx.session))
    communities = [entity for entity in minds if entity.entity_type in COMMUNITY_MINDS]
    await lend_settlement_values(ctx.session, index, {community.id for community in communities})
    plagued = await plagued_communities(ctx)
    pressed = needy = 0
    for community in communities:
        if await update_pressures(ctx, community, index.of(community.id), plagued):
            pressed += 1
    sleeping = await dormant_ids(ctx)
    for mortal in minds:
        if (
            mortal.entity_type is EntityType.MORTAL
            and mortal.id not in sleeping
            and await update_needs(ctx, mortal, index.of(mortal.id), await traits_of(ctx.session, mortal.id))
        ):
            needy += 1
    ctx.count("pressures", pressed)
    ctx.count("needs", needy)


@reads("table.bonds", "table.community_relations", "table.culture_values", "table.memories", "table.nodes", "table.personality_values", "table.traits")
@writes("table.community_relations")
async def mind_opinion(ctx: TickContext) -> None:
    ctx.count("relations_refreshed", await refresh_relations(ctx.session, ctx.rules, ctx.epoch))


@reads(
    "beast.agility",
    "beast.cunning",
    "beast.strength",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.conditions",
    "table.culture_values",
    "table.foreign_gods",
    "table.incubating_ideas",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.nodes",
    "table.personality_values",
    "table.skills",
    "table.sons",
    "table.traits",
)
@writes(
    "beast.agility",
    "beast.cunning",
    "beast.strength",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.foreign_gods",
    "table.mind_attributes",
    "table.mind_facets",
    "table.sons",
    "table.traits",
)
async def mind_split(ctx: TickContext) -> None:
    weathered = tempered = 0
    beasts = await canon(ctx.session, [EntityType.BEAST])
    sons = list(await ctx.session.scalars(select(SonRow).order_by(SonRow.id)))
    gods = list(await ctx.session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)))
    minds = [entity for entity in await living_minds(ctx.session) if entity.entity_type is EntityType.MORTAL]
    nodes: list[Bodied] = [*unheld(minds), *unheld(beasts), *unheld(sons), *unheld(gods)]
    for node in nodes:
        weathered += 1 if await weather_attributes(ctx.session, ctx.rules, node, ctx.epoch) else 0
        for trait in await temper_facets(ctx.session, ctx.rules, node, ctx.epoch):
            tempered += 1
            await note(ctx, f"{node.name} has grown {TRAITS[trait].label.lower()}.", key="mind.facet_trait", ids=[node.id])
    ctx.count("attributes_weathered", weathered)
    ctx.count("facet_traits", tempered)


@reads(
    "table.bonds",
    "table.cult_tenets",
    "table.entities",
    "table.entity_flags",
    "table.holder_levels",
    "table.ideology_adherents",
    "table.ideology_profiles",
    "table.incubating_ideas",
    "table.item_profiles",
    "table.knowledge",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.nodes",
    "table.personality_values",
)
@writes(
    "beast.agility",
    "beast.cunning",
    "beast.strength",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "table.chronicle",
    "table.chronicle_entities",
    "table.incubating_ideas",
    "table.mind_attributes",
    "table.mind_facets",
    "table.personality_values",
)
async def mind_ideas(ctx: TickContext) -> None:
    knowledge = await KnowledgeMap.load(ctx.session)
    sleeping = await dormant_ids(ctx)
    taken = internalised = rejected = 0
    for mortal in unheld(await living_minds(ctx.session)):
        if mortal.entity_type is not EntityType.MORTAL or mortal.id in sleeping:
            continue
        before = {row.id: row.state for row in await ideas_of(ctx.session, mortal.id)}
        tally = await turn_over(ctx, mortal, knowledge)
        taken, internalised, rejected = taken + tally.taken, internalised + tally.internalised, rejected + tally.rejected
        for row in await ideas_of(ctx.session, mortal.id):
            if before.get(row.id) is IdeaState.INCUBATING and row.state is IdeaState.INTERNALISED:
                await note(ctx, f"{mortal.name} took {IDEAS[row.idea].label.lower()} to heart.", key="idea.internalised", ids=[mortal.id])
            elif before.get(row.id) is IdeaState.INCUBATING and row.state is IdeaState.REJECTED:
                await note(ctx, f"{mortal.name} let go of {IDEAS[row.idea].label.lower()}.", key="idea.rejected", ids=[mortal.id])
    ctx.count("ideas_taken", taken)
    ctx.count("ideas_internalised", internalised)
    ctx.count("ideas_rejected", rejected)


@reads(
    "table.applied_fixups",
    "table.artwork_profiles",
    "table.bonds",
    "table.calendars",
    "table.community_stocks",
    "table.culture_ethics",
    "table.culture_values",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.entity_flags",
    "table.forced_weather",
    "table.item_profiles",
    "table.marriages",
    "table.memories",
    "table.messages",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.needs",
    "table.nodes",
    "table.offices",
    "table.personality_values",
    "table.place_environment",
    "table.preferences",
    "table.region_environment",
    "table.reputations",
    "table.sky_events",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.world_maps",
    "table.world_seasons",
)
@writes(
    "table.deed_claims",
    "table.deeds",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.personality_values",
    "table.reputations",
    "table.thoughts",
)
async def mind_thoughts(ctx: TickContext) -> None:
    sleeping = await dormant_ids(ctx)
    felt = relived = forgotten = 0
    moods: dict[str, int] = defaultdict(int)
    for mortal in unheld(await living_minds(ctx.session)):
        if mortal.entity_type is not EntityType.MORTAL or mortal.id in sleeping:
            continue
        tally = await feel(ctx, mortal)
        felt, relived = felt + tally.thoughts, relived + tally.relived
        forgotten += await forget_faded_thoughts(ctx.session, ctx.rules, mortal.id, ctx.epoch)
        state = await settle_mood(ctx.session, ctx.rules, mortal, ctx.epoch)
        if state is not None:
            moods[state.value] += 1
    ctx.count("thoughts", felt)
    ctx.count("memories_relived", relived)
    ctx.count("thoughts_forgotten", forgotten)
    for name, count in moods.items():
        ctx.count(f"mood_{name}", count)


@reads(
    "mortal.willpower",
    "table.applied_fixups",
    "table.artwork_profiles",
    "table.bonds",
    "table.entities",
    "table.entity_flags",
    "table.griefs",
    "table.item_profiles",
    "table.marriages",
    "table.memories",
    "table.messages",
    "table.mind_attributes",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.needs",
    "table.nodes",
    "table.personality_values",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
)
@writes("table.griefs", "table.memories", "table.thoughts", "table.traits")
async def mind_grief(ctx: TickContext) -> None:
    tally = GriefTally()
    mourners = set(await ctx.session.scalars(select(GriefRow.mourner_node_id).where(GriefRow.stage.in_((GriefStage.SHOCK, GriefStage.MOURNING)))))
    for mourner in unheld(await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(mourners)).order_by(EntityRow.id))):
        if mourner.status is EntityStatus.CANON:
            await advance(ctx, mourner, tally)
    ctx.count("mourning", tally.mourning)
    ctx.count("griefs_accepted", tally.accepted)
    ctx.count("griefs_complicated", tally.complicated)


@reads(
    "mortal.charisma",
    "table.applied_fixups",
    "table.artwork_profiles",
    "table.bonds",
    "table.conditions",
    "table.dreams",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.item_profiles",
    "table.marriages",
    "table.memories",
    "table.messages",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.needs",
    "table.nodes",
    "table.personality_values",
    "table.routes",
    "table.skills",
    "table.thoughts",
    "table.tradition_profiles",
    "table.traits",
    "table.war_sides",
    "table.wars",
    "table.worlds",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.dreams",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.personality_values",
    "table.thoughts",
)
async def mind_dreams(ctx: TickContext) -> None:
    visited = await visitations(ctx)
    sleeping = await dormant_ids(ctx)
    dreamt = 0
    for mortal in unheld(await living_minds(ctx.session)):
        if mortal.entity_type is not EntityType.MORTAL or mortal.id in sleeping:
            continue
        if not is_notable(ctx.rules, mortal, await EntityRepository(ctx.session).flags(mortal.id)):
            continue
        dreamt += 1 if await dream(ctx, mortal) is not None else 0
    ctx.count("visitations", visited)
    ctx.count("dreams", dreamt)


async def peoples_and_members(ctx: TickContext) -> tuple[list[EntityRow], dict[int, list[EntityRow]], list[EntityRow]]:
    minds = await living_minds(ctx.session)
    peoples = unheld(entity for entity in minds if entity.entity_type is EntityType.PEOPLE)
    sleeping = await dormant_ids(ctx)
    mortals = unheld(entity for entity in minds if entity.entity_type is EntityType.MORTAL and entity.id not in sleeping)
    members: dict[int, list[EntityRow]] = defaultdict(list)
    for mortal in mortals:
        people = await people_of(ctx.session, mortal)
        if people is not None:
            members[people.id].append(mortal)
    return peoples, members, mortals


@reads(
    "table.bonds",
    "table.culture_values",
    "table.entity_flags",
    "table.minds",
    "table.name_registry",
    "table.nodes",
    "table.people_culture",
    "table.preferences",
    "table.region_environment",
    "table.skills",
    "table.tradition_profiles",
    "table.world_maps",
)
@writes("table.bonds", "table.entities", "table.name_registry", "table.preferences", "table.tradition_profiles")
async def mind_preferences(ctx: TickContext) -> None:
    peoples, members, mortals = await peoples_and_members(ctx)
    seeded = grown = taboos = totems = pulled = 0
    for people in peoples:
        seeded += await seed_culture(ctx, people)
        taboos += await make_taboos(ctx, people)
        totems += 1 if await adopt_totem(ctx, people) else 0
        pulled += await pull_culture(ctx, people, members.get(people.id, []))
    for mortal in mortals:
        seeded += await seed_mortal(ctx, mortal)
        grown += await grow(ctx, mortal)
    ctx.count("preferences_seeded", seeded)
    ctx.count("preferences_grown", grown)
    ctx.count("preference_taboos", taboos)
    ctx.count("preference_totems", totems)
    ctx.count("preferences_pulled", pulled)


@reads(
    "mortal.charisma",
    "table.bonds",
    "table.culture_ethics",
    "table.culture_honour",
    "table.culture_values",
    "table.entity_flags",
    "table.memories",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.thoughts",
    "table.traits",
)
@writes("table.culture_ethics", "table.culture_honour", "table.memories", "table.mortal_profiles", "table.thoughts")
async def mind_ethics(ctx: TickContext) -> None:
    peoples, _, mortals = await peoples_and_members(ctx)
    cults = unheld(await canon(ctx.session, [EntityType.CULT]))
    seeded = moved = schisms = spread = restored = 0
    for culture in [*peoples, *cults]:
        seeded += await seed_ethics(ctx, culture)
        await seed_honour(ctx, culture)
        moved += await drift_ethics(ctx, culture)
    for people in peoples:
        call = await schism(ctx, people)
        if call is None or await split_already(ctx, people):
            continue
        faction = await found_faction(ctx, people, SCHISM_FACTION)
        await note(
            ctx,
            f"{faction.name} broke from the {people.name} over {ACT_LABELS[call.act].lower()}.",
            key="ethics.schism",
            ids=[faction.id, people.id],
        )
        schisms += 1
    for mortal in mortals:
        spread += await spread_shame(ctx, mortal)
        restored += await restore(ctx, mortal)
    ctx.count("ethics_seeded", seeded)
    ctx.count("ethics_drifted", moved)
    ctx.count("ethics_schisms", schisms)
    ctx.count("shame_spread", spread)
    ctx.count("shame_restored", restored)


async def split_already(ctx: TickContext, people: EntityRow) -> bool:
    found = await ctx.session.scalar(
        select(EntityRow.id)
        .where(EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON, EntityRow.affiliated_entity_id == people.id)
        .limit(1)
    )
    return found is not None


@reads(
    "table.bonds",
    "table.conditions",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.fears",
    "table.house_profiles",
    "table.injuries",
    "table.inspirations",
    "table.life_dreams",
    "table.memories",
    "table.mind_facets",
    "table.minds",
    "table.mortal_perks",
    "table.mortal_profiles",
    "table.needs",
    "table.nodes",
    "table.offices",
    "table.outbreaks",
    "table.personality_values",
    "table.region_environment",
    "table.skills",
    "table.thoughts",
    "table.traits",
    "table.wants",
    "table.world_maps",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.epoch_year_cursors",
    "table.fears",
    "table.incident_participants",
    "table.incidents",
    "table.life_dreams",
    "table.memories",
    "table.mind_facets",
    "table.modifiers",
    "table.mortal_perks",
    "table.mortal_profiles",
    "table.thoughts",
    "table.wants",
)
async def mind_aspirations(ctx: TickContext) -> None:
    _, _, mortals = await peoples_and_members(ctx)
    tally = AspirationTally()
    sparks: dict[str, int] = defaultdict(int)
    for mortal in mortals:
        await aspire(ctx, mortal, tally, resolved=await resolute(ctx.session, mortal.id))
        spark = await tend_inspiration(ctx, mortal)
        if spark is not None:
            sparks[spark] += 1
    for key, value in vars(tally).items():
        ctx.count(f"aspiration_{key}", value)
    for key, value in sparks.items():
        ctx.count(f"inspiration_{key}", value)


SURVEY_PHASES = (Phase("mind_survey", mind_survey),)


@reads(
    "people.population",
    "settlement.population",
    "table.bonds",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.cosmos",
    "table.culture_ethics",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.memories",
    "table.minds",
    "table.nodes",
    "table.personality_values",
    "table.pressures",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.speaker_cohorts",
    "table.tradition_profiles",
    "table.traits",
    "table.world_maps",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
)
async def famine_aid(ctx: TickContext) -> None:
    table = ctx.rules.needs
    atlas = await RegionAtlas.load(ctx.session)
    rng = ctx.rng("famine_aid")
    given = 0
    hungry = [
        community
        for community in await canon(ctx.session, list(AID_TYPES))
        if (await pressures_of(ctx.session, community.id)).get(PressureKind.HUNGER, 0) >= table.famine_aid_hunger
    ]
    for community in hungry:
        donor = await best_donor(ctx, atlas, community)
        if donor is None:
            continue
        kindness = max(0.0, 1 + value_reading(await values_for(ctx.session, donor.id), ActKind.HOSPITALITY) / PERCENT)
        if not rng.chance(table.famine_aid_chance * kindness):
            await judged(ctx, donor.id, community.id, ActKind.HOARDING_IN_FAMINE)
            continue
        store = await stock(ctx.session, ctx.rules, donor.id, Commodity.FOOD)
        sent = round_half_up(store * table.famine_aid_share_pct / PERCENT)
        if sent <= 0:
            continue
        await move_stock(ctx.session, ctx.rules, donor.id, community.id, Commodity.FOOD, index=sent, epoch=ctx.epoch, flow=GoodsFlow.AID)
        await change_relation(
            ctx, community.id, donor.id, table.famine_aid_relation, MemoryKind.FAMINE_AID, note="grain in the hungry year", reverse=MemoryKind.GOODWILL
        )
        await note(ctx, f"{donor.name} sent {sent} loads of grain to starving {community.name}.", key="mind.famine_aid", ids=[donor.id, community.id])
        given += 1
    ctx.count("famine_aid", given)


async def best_donor(ctx: TickContext, atlas: RegionAtlas, community: EntityRow) -> EntityRow | None:
    table = ctx.rules.needs
    home = atlas.top_region(community.id)
    if home is None:
        return None
    nearby = {home, *atlas.neighbour_regions(home)}
    best: tuple[int, EntityRow] | None = None
    for region_id in sorted(nearby):
        for other_id in atlas.communities_in(region_id):
            other = await living_entity(ctx.session, other_id)
            if other is None or other.id == community.id or other.entity_type not in AID_TYPES:
                continue
            if await BondRepository(ctx.session).exists_between(community.id, other.id, BondKind.ENEMY):
                continue
            store = await stock(ctx.session, ctx.rules, other.id, Commodity.FOOD)
            if store >= table.famine_aid_min_food and (best is None or store > best[0]):
                best = (store, other)
    return best[1] if best is not None else None


MIND_PHASES = (
    Phase("mind_values", mind_values),
    Phase("mind_skills", mind_skills),
    Phase("mind_split", mind_split),
    Phase("mind_ideas", mind_ideas),
    Phase("mind_memories", mind_memories),
    Phase("mind_needs", mind_needs),
    Phase("mind_thoughts", mind_thoughts),
    Phase("mind_grief", mind_grief),
    Phase("mind_dreams", mind_dreams),
    Phase("mind_preferences", mind_preferences),
    Phase("mind_ethics", mind_ethics),
    Phase("mind_aspirations", mind_aspirations),
    Phase("famine_aid", famine_aid),
    Phase("mind_opinion", mind_opinion),
)
PHASES = (*SURVEY_PHASES, *MIND_PHASES)
