from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.knowledge import KNOWLEDGE_BRANCHES, branch_label
from aerona.catalog.worlds import WORLD_TYPES
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LegendaryQuestRow, MessageRow, ThreadLinkRow, ThreadRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ThreadLinkRole, ThreadStatus
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarStatus
from aerona.domain.enums.world import Discovery
from aerona.engine.gods.behaviour_hints import SonHints, son_behaviour_lines
from aerona.engine.gods.devotion import resurrection_state
from aerona.engine.gods.mortality import kill_chance, kill_cost
from aerona.engine.gods.queries import cosmos_row, creator_row, worshippers_of
from aerona.engine.gods.stats import Trait, trait_or
from aerona.engine.gods.world_view import WorldView, load_world_view
from aerona.engine.phases.knowledge_levels import empty_branches
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.prompts.contexts.common import NamedRecord
from aerona.prompts.contexts.opportunities import (
    BranchRecord,
    BreatheLife,
    DeadSibling,
    DeepenableKnowledge,
    Existence,
    FadingSon,
    Godless,
    Hostilities,
    HungryWorshippers,
    IsolatedWorld,
    Languageless,
    LeveledRecord,
    LongThreads,
    LowLoyalty,
    NarrowLands,
    NewEmptyWorld,
    OpenThreads,
    OwnWorshippers,
    PatronedRecord,
    PendingProphecies,
    ProphecyRecord,
    RebelsAgainstYou,
    RebelSiblings,
    RecordPair,
    RivalCreations,
    RivalMortals,
    RivalSiblings,
    RivalWorshippers,
    Silence,
    SonOpportunity,
    StagnantCosmos,
    StaleThread,
    StaleThreads,
    TargetMortal,
    TeachableKnowledge,
    Unclaimed,
    UnknownBranches,
    UnownedResources,
    ValuedRecord,
    Wonders,
    WorshipperWars,
    YourEnemies,
)
from aerona.rules.registry import Rules

THINKING_TYPES = frozenset(COMMUNITY_TYPES | {EntityType.MORTAL})
LIVING_LAND_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT)
ORGANIZATION_TYPES = (EntityType.CULT, EntityType.FACTION)
LANGUAGE_HOLDER_TYPES = (EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT)
SETTLED_TYPES = (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL)


@dataclass(frozen=True)
class ThreadState:
    id: int
    text: str
    stagnation: int
    advances: int
    world_id: int | None


@dataclass(frozen=True)
class SonScope:
    session: AsyncSession
    rules: Rules
    view: WorldView
    son: SonRow
    visible: list[EntityRow]
    epoch: int
    multi: bool


@dataclass(frozen=True)
class LandMeasure:
    world_id: int
    regions: int
    communities: int
    per_region: float
    narrow: bool
    crowded: tuple[ValuedRecord, ...]


@dataclass(frozen=True)
class CreatorHints:
    unanswered_prayers: int
    unclaimed: tuple[str, ...]
    rebel_sons: tuple[str, ...]
    fading_sons: tuple[FadingSon, ...]
    doom: int
    doom_threshold: int
    godless_worlds: tuple[str, ...]
    stale_threads: int
    essence: int


def named(entity: EntityRow) -> NamedRecord:
    return NamedRecord(id=entity.id, name=entity.name)


def land_measure(rules: Rules, view: WorldView, world_id: int) -> LandMeasure:
    regions = view.canon(EntityType.REGION, world_id=world_id)
    communities = view.canon(*LIVING_LAND_TYPES, world_id=world_id)
    counts = Counter(view.top_region_id(entity.id) for entity in communities)
    threshold = rules.exploration.crowded_communities_per_region
    per_region = len(communities) / max(1, len(regions))
    crowded = sorted(
        (ValuedRecord(id=region.id, name=region.name, value=counts.get(region.id, 0)) for region in regions if counts.get(region.id, 0) >= threshold),
        key=lambda record: -record.value,
    )
    return LandMeasure(world_id, len(regions), len(communities), round(per_region, 2), not regions or per_region >= threshold, tuple(crowded))


async def thread_states(session: AsyncSession, view: WorldView, epoch: int) -> list[ThreadState]:
    quests = set(await session.scalars(select(LegendaryQuestRow.thread_id)))
    threads = list(await session.scalars(select(ThreadRow).where(ThreadRow.status == ThreadStatus.OPEN).order_by(ThreadRow.id)))
    states: list[ThreadState] = []
    for thread in threads:
        if thread.id in quests:
            continue
        links = list(await session.scalars(select(ThreadLinkRow).where(ThreadLinkRow.thread_id == thread.id)))
        advanced = [link.epoch for link in links if link.role is ThreadLinkRole.ADVANCED]
        last = max([thread.epoch, *advanced])
        worlds = Counter(view.entities[link.entity_id].world_id for link in links if link.entity_id in view.entities)
        world = worlds.most_common(1)[0][0] if worlds else None
        states.append(ThreadState(thread.id, thread.text, epoch - last, max(thread.progress, len(advanced)), world))
    return sorted(states, key=lambda state: -state.stagnation)


async def is_multi_world(session: AsyncSession) -> bool:
    return int(await session.scalar(select(func.count(WorldRow.id))) or 0) > 1


async def empty_worlds(session: AsyncSession, view: WorldView, rules: Rules, epoch: int) -> list[NewEmptyWorld]:
    lines: list[NewEmptyWorld] = []
    for world in await session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)):
        if view.canon(*SETTLED_TYPES, world_id=world.id):
            continue
        regions = sorted(view.canon(EntityType.REGION, world_id=world.id), key=lambda region: -trait_or(region, Trait.FERTILITY, 0))
        spec = WORLD_TYPES.get(world.world_type)
        lines.append(
            NewEmptyWorld(
                world_id=world.id,
                world_name=world.name,
                world_type_label=spec.label if spec is not None else world.world_type.value,
                empty_ages=max(0, epoch - world.created_epoch) or None,
                regions=[
                    ValuedRecord(id=region.id, name=region.name, value=trait_or(region, Trait.FERTILITY, 0))
                    for region in regions[: rules.empty_world.opportunity_regions]
                ],
            )
        )
    return lines


async def _routes_touching(session: AsyncSession, world_id: int, known: bool) -> bool:
    statement = select(RouteRow.id).where(RouteRow.known.is_(known), (RouteRow.world_a_id == world_id) | (RouteRow.world_b_id == world_id))
    if known:
        statement = statement.where(RouteRow.active.is_(True))
    return await session.scalar(statement.limit(1)) is not None


async def _life_lines(scope: SonScope) -> list[SonOpportunity]:
    session, rules, view, son, visible, epoch, multi = scope.session, scope.rules, scope.view, scope.son, scope.visible, scope.epoch, scope.multi
    table = rules.opportunities
    count = Counter(entity.entity_type for entity in visible)
    regions = [entity for entity in visible if entity.entity_type is EntityType.REGION]
    settled_regions = {view.top_region_id(entity.id) for entity in visible if entity.entity_type in LIVING_LAND_TYPES}
    empty = [named(region) for region in regions if region.id not in settled_regions]
    peoples = count[EntityType.PEOPLE]
    lifeless = (
        peoples < len(regions) + table.life_people_surplus
        or count[EntityType.MORTAL] < table.life_mortals_below
        or count[EntityType.SETTLEMENT] < peoples
        or count[EntityType.SPECIES] < table.life_species_below
    )
    lines: list[SonOpportunity] = [
        BreatheLife(
            lifeless=lifeless,
            peoples=peoples,
            settlements=count[EntityType.SETTLEMENT],
            mortals=count[EntityType.MORTAL],
            species=count[EntityType.SPECIES],
            organizations=count[EntityType.CULT] + count[EntityType.FACTION],
            empty_regions=empty[: table.list_short] if lifeless else [],
            few_mortals=lifeless and count[EntityType.MORTAL] < table.life_mortals_below,
        )
    ]
    home = son.current_world_id
    if multi:
        lines.extend(line for line in await empty_worlds(session, view, rules, epoch) if line.world_id != home)
    if home is not None:
        measure = land_measure(rules, view, home)
        if measure.narrow:
            world = await session.get(WorldRow, home)
            lines.append(
                NarrowLands(
                    world_name=world.name if world else None,
                    regions=measure.regions,
                    communities=measure.communities,
                    per_region=measure.per_region,
                    crowded=list(measure.crowded[: table.list_short]),
                )
            )
        if multi and not await _routes_touching(session, home, True):
            lines.append(IsolatedWorld(hidden_route=await _routes_touching(session, home, False)))
    newest = await session.scalar(select(func.max(WorldRow.created_epoch)))
    if newest is not None and epoch - newest >= rules.exploration.cosmos_stagnant_epochs:
        lines.append(StagnantCosmos(last_birth_age=newest))
    return lines


async def _sibling_lines(scope: SonScope) -> list[SonOpportunity]:
    session, rules, view, son, visible, epoch = scope.session, scope.rules, scope.view, scope.son, scope.visible, scope.epoch
    table = rules.opportunities
    relations = SonRepository(session)
    others = [other for other in await session.scalars(select(SonRow).order_by(SonRow.id)) if other.id != son.id]
    relation = {other.id: await relations.relation(son.id, other.id) for other in others}
    names = {other.id: other.name for other in others}
    lines: list[SonOpportunity] = []
    for dead in (other for other in others if other.status is SonStatus.DEAD):
        state = await resurrection_state(session, rules, dead, epoch)
        if state is None:
            continue
        strongest = max(state.orders, key=lambda order: order.devotion, default=None)
        lines.append(
            DeadSibling(
                name=dead.name,
                death_age=dead.death_epoch or epoch,
                devotion=state.devotion,
                remaining=state.remaining or None,
                enemy=relation[dead.id] <= -rules.death.auto_scatter_relation,
                corpse_id=state.corpse.id if state.corpse is not None else None,
                cult=ValuedRecord(id=strongest.id, name=strongest.name, value=strongest.devotion) if strongest is not None else None,
            )
        )
    rivals = sorted(
        (other for other in others if other.status is SonStatus.ACTIVE and relation[other.id] <= -table.rival_relation), key=lambda other: relation[other.id]
    )
    if rivals:
        lines.append(RivalSiblings(rivals=[ValuedRecord(id=other.id, name=other.name, value=relation[other.id]) for other in rivals[: table.list_short]]))
    targets: list[TargetMortal] = []
    mortals = sorted((entity for entity in visible if entity.entity_type is EntityType.MORTAL), key=lambda mortal: -trait_or(mortal, Trait.CHARISMA, 0))
    for mortal in mortals:
        patron = view.patron_son(mortal.id)
        if patron is None or patron == son.id or relation.get(patron, 0) >= -table.target_sibling_relation:
            continue
        chance = await kill_chance(session, rules, mortal, son)
        targets.append(
            TargetMortal(id=mortal.id, name=mortal.name, patron=names.get(patron, ""), cost=await kill_cost(session, rules, mortal), chance=chance.percent)
        )
        if len(targets) >= table.list_narrow:
            break
    if targets:
        lines.append(RivalMortals(mortals=targets))
    thinking = [entity for entity in visible if entity.entity_type in THINKING_TYPES]
    unclaimed = [named(entity) for entity in thinking if view.patrons.get(entity.id) is None]
    if unclaimed:
        lines.append(Unclaimed(communities=unclaimed[: table.list_max]))
    rival_worshippers = [
        PatronedRecord(id=entity.id, name=entity.name, patron=names.get(patron, ""))
        for entity in thinking
        if (patron := view.patron_son(entity.id)) is not None and patron != son.id and relation.get(patron, 0) < -table.rival_relation
    ]
    if rival_worshippers:
        lines.append(RivalWorshippers(communities=rival_worshippers[: table.list_max]))
    rebels = [named_son for named_son in others if named_son.rebel and named_son.status is not SonStatus.DEAD]
    if rebels:
        lines.append(RebelSiblings(siblings=[NamedRecord(id=other.id, name=other.name) for other in rebels]))
    if not son.rebel and son.loyalty < table.rebel_loyalty:
        lines.append(LowLoyalty())
    creations = [
        named(entity)
        for entity in visible
        if entity.creator_son_id not in (None, son.id) and relation.get(entity.creator_son_id or 0, 0) < -table.target_sibling_relation
    ]
    if creations:
        lines.append(RivalCreations(creations=creations[-table.list_wide :]))
    return lines


async def _branch_lines(scope: SonScope, own: list[EntityRow], knowledge: list[EntityRow]) -> list[SonOpportunity]:
    rules = scope.rules
    lines: list[SonOpportunity] = []
    world_id = scope.son.current_world_id
    if world_id is not None:
        empty = await empty_branches(scope.session, world_id)
        if empty:
            lines.append(UnknownBranches(branches=[branch_label(branch) for branch in empty[: rules.knowledge.hint_empty_branches]]))
    held = set().union(*(scope.view.knows.get(entity.id, set()) for entity in own)) if own else set()
    deepenable = sorted(
        (entity for entity in knowledge if entity.id in held and knowledge_level(rules, entity) < rules.knowledge.level_cap),
        key=lambda entity: (knowledge_level(rules, entity), entity.id),
    )
    if deepenable:
        records = [LeveledRecord(id=entity.id, name=entity.name, level=knowledge_level(rules, entity)) for entity in deepenable[: rules.opportunities.list_max]]
        lines.append(DeepenableKnowledge(knowledge=records))
    return lines


async def _knowledge_lines(scope: SonScope, own: list[EntityRow]) -> list[SonOpportunity]:
    session, rules, view, visible = scope.session, scope.rules, scope.view, scope.visible
    table = rules.opportunities
    lines: list[SonOpportunity] = []
    knowledge = [entity for entity in visible if entity.entity_type is EntityType.KNOWLEDGE]
    known = {entity.id for entity in knowledge}
    if not knowledge:
        lines.append(TeachableKnowledge())
    elif any(known - view.knows.get(entity.id, set()) for entity in own):
        lines.append(
            TeachableKnowledge(
                knowledge=[
                    BranchRecord(
                        id=entity.id,
                        name=entity.name,
                        branch_label=KNOWLEDGE_BRANCHES[entity.knowledge_branch].label if entity.knowledge_branch is not None else None,
                    )
                    for entity in knowledge[: table.list_max]
                ]
            )
        )
    lines.extend(await _branch_lines(scope, own, knowledge))
    languages = {entity.id for entity in visible if entity.entity_type is EntityType.LANGUAGE}
    speakers = set(
        await session.scalars(
            select(BondRow.source_node_id).where(BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(languages))
        )
    )
    mute = [named(entity) for entity in visible if entity.entity_type in LANGUAGE_HOLDER_TYPES and entity.id not in speakers]
    if mute or not languages:
        lines.append(Languageless(communities=mute[: table.list_short] if languages else []))
    owned = set(await session.scalars(select(BondRow.target_node_id).where(BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)))
    resources = [named(entity) for entity in visible if entity.entity_type is EntityType.RESOURCE and entity.id not in owned]
    if resources:
        lines.append(UnownedResources(resources=resources[: table.list_max]))
    return lines


async def _worshipper_need_lines(scope: SonScope, own: list[EntityRow]) -> list[SonOpportunity]:
    session, table = scope.session, scope.rules.opportunities
    lines: list[SonOpportunity] = []
    own_ids = [entity.id for entity in own]
    if own_ids:
        wars = await session.scalars(
            select(EntityRow)
            .join(WarRow, WarRow.event_entity_id == EntityRow.id)
            .join(WarSideRow, WarSideRow.war_id == WarRow.id)
            .where(WarRow.status == WarStatus.ONGOING, WarSideRow.entity_id.in_(own_ids), WarSideRow.left_epoch.is_(None))
            .order_by(WarRow.id)
        )
        war_records = [named(war) for war in dict.fromkeys(wars)]
        if war_records:
            lines.append(WorshipperWars(wars=war_records[: table.list_short]))
        hungry: list[NamedRecord] = []
        for entity in own:
            society = await session.get(CommunitySocietyRow, entity.id) if entity.entity_type in LIVING_LAND_TYPES else None
            if society is not None and society.stock_food < table.hungry_food:
                hungry.append(named(entity))
        if hungry:
            lines.append(HungryWorshippers(communities=hungry))
    return lines


async def _world_lines(scope: SonScope) -> list[SonOpportunity]:
    session, rules, view, son, visible = scope.session, scope.rules, scope.view, scope.son, scope.visible
    table = rules.opportunities
    lines: list[SonOpportunity] = []
    ids = {entity.id for entity in visible}
    own = [entity for entity in visible if entity.entity_type in THINKING_TYPES and view.patron_son(entity.id) == son.id]
    if own:
        lines.append(OwnWorshippers(communities=[named(entity) for entity in own[: table.list_max]]))
    enmities = await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id)
        .where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.epoch.desc(), BondRow.id.desc())
    )
    pairs = [
        RecordPair(a=named(view.entities[first]), b=named(view.entities[second]))
        for first, second in enmities
        if first in ids and second in ids and view.entities[first].living and view.entities[second].living
    ]
    if pairs:
        lines.append(Hostilities(pairs=pairs[: table.list_wide]))
    lines.extend(await _knowledge_lines(scope, own))
    risen = await session.scalars(
        select(BondRow.source_node_id).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == son.id)
    )
    against = [named(view.entities[node]) for node in risen if node in view.entities and view.entities[node].living]
    if against:
        lines.append(RebelsAgainstYou(records=against))
    hated = await session.scalars(
        select(BondRow.target_node_id).where(
            BondRow.kind.in_([BondKind.ENEMY, BondKind.CURSED]), BondRow.state == BondState.ACTIVE, BondRow.source_node_id == son.id
        )
    )
    enemies = [named(view.entities[node]) for node in dict.fromkeys(hated) if node in view.entities and view.entities[node].living]
    if enemies:
        lines.append(YourEnemies(records=enemies))
    godless = [named(entity) for entity in visible if view.has_flag(entity.id, EntityFlag.GODLESS)]
    if godless:
        lines.append(Godless(communities=godless[: table.list_max]))
    if son.existence <= table.fading_existence:
        lines.append(Existence(fading=True, value=son.existence))
    elif not own:
        lines.append(Existence(fading=False, value=son.existence))
    lines.extend(await _worshipper_need_lines(scope, own))
    wonders = [named(entity) for entity in visible if view.has_flag(entity.id, EntityFlag.WONDER)]
    if wonders:
        lines.append(Wonders(wonders=wonders[: table.list_short]))
    return lines


async def _story_lines(scope: SonScope) -> list[SonOpportunity]:
    session, rules, view, son, visible, epoch, multi = scope.session, scope.rules, scope.view, scope.son, scope.visible, scope.epoch, scope.multi
    table = rules.opportunities
    lines: list[SonOpportunity] = []
    threads = [state for state in await thread_states(session, view, epoch) if not multi or state.world_id in (None, son.current_world_id)]
    stale = [state for state in threads if state.stagnation >= table.stale_epochs]
    if stale:
        lines.append(StaleThreads(threads=[StaleThread(id=state.id, text=state.text) for state in stale[: table.list_short]]))
    long_threads = [state.id for state in threads if state.advances >= table.long_thread_steps]
    if long_threads:
        lines.append(LongThreads(thread_ids=long_threads[: table.list_narrow]))
    prophecies = sorted(
        (entity for entity in visible if entity.entity_type is EntityType.PROPHECY),
        key=lambda entity: (entity.creator_son_id != son.id, entity.birth_epoch, entity.id),
    )
    if prophecies:
        lines.append(
            PendingProphecies(
                prophecies=[
                    ProphecyRecord(id=entity.id, name=entity.name, age=entity.birth_epoch, own=entity.creator_son_id == son.id)
                    for entity in prophecies[: table.list_narrow]
                ]
            )
        )
    if threads:
        lines.append(OpenThreads(thread_ids=[state.id for state in threads]))
    statement = (
        select(func.max(MessageRow.epoch))
        .join(NodeRow, NodeRow.id == MessageRow.recipient_node_id)
        .where(MessageRow.sender_node_id == son.id, NodeRow.kind == NodeKind.SON)
    )
    last = await session.scalar(statement)
    if last is None or epoch - last >= table.silence_epochs:
        lines.append(Silence(never_spoken=last is None, ages=0 if last is None else epoch - last))
    return lines


async def son_opportunities(session: AsyncSession, rules: Rules, son: SonRow, epoch: int) -> list[SonOpportunity]:
    multi = await is_multi_world(session)
    view = await load_world_view(session, rules)
    visible = [entity for entity in view.canon() if not multi or son.current_world_id is None or entity.world_id == son.current_world_id]
    scope = SonScope(session, rules, view, son, visible, epoch, multi)
    hints = SonHints(session, rules, view, son, visible=visible, epoch=epoch)
    behaviour = await son_behaviour_lines(hints, await rival_sons(session, rules, son))
    return [*await _life_lines(scope), *await _sibling_lines(scope), *await _world_lines(scope), *await _story_lines(scope), *behaviour]


async def rival_sons(session: AsyncSession, rules: Rules, son: SonRow) -> list[SonRow]:
    relations = SonRepository(session)
    found: list[tuple[int, SonRow]] = []
    for other in await session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.id != son.id).order_by(SonRow.id)):
        value = await relations.relation(son.id, other.id)
        if value <= -rules.opportunities.rival_relation:
            found.append((value, other))
    return [other for _value, other in sorted(found, key=lambda item: (item[0], item[1].id))]


async def creator_hints(session: AsyncSession, rules: Rules, epoch: int) -> CreatorHints:
    table = rules.opportunities
    creator = await creator_row(session)
    cosmos = await cosmos_row(session)
    view = await load_world_view(session, rules)
    unanswered = 0
    if creator is not None:
        statement = select(func.count(MessageRow.id)).where(
            MessageRow.recipient_node_id == creator.id, MessageRow.answered.is_(False), MessageRow.intent != MessageIntent.CHAT
        )
        unanswered = int(await session.scalar(statement) or 0)
    unclaimed = tuple(entity.name for entity in view.canon(*THINKING_TYPES) if view.patrons.get(entity.id) is None)
    sons = list(await session.scalars(select(SonRow).order_by(SonRow.id)))
    fading = tuple(
        FadingSon(name=son.name, existence=son.existence) for son in sons if son.status is not SonStatus.DEAD and son.existence <= table.fading_sons_existence
    )
    godless_worlds: list[str] = []
    guarded = {son.current_world_id for son in sons if son.status is SonStatus.ACTIVE}
    for world in await session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)):
        if view.canon(EntityType.PEOPLE, world_id=world.id) and world.id not in guarded:
            godless_worlds.append(world.name)
    stale = [state for state in await thread_states(session, view, epoch) if state.stagnation >= table.stale_epochs]
    return CreatorHints(
        unanswered_prayers=unanswered,
        unclaimed=unclaimed,
        rebel_sons=tuple(son.name for son in sons if son.rebel),
        fading_sons=fading,
        doom=cosmos.doom_clock if cosmos is not None else 0,
        doom_threshold=max(1, rules.balance.apocalypse_threshold),
        godless_worlds=tuple(godless_worlds),
        stale_threads=len(stale),
        essence=creator.essence if creator is not None else 0,
    )


async def worshipper_count(session: AsyncSession, son_id: int) -> int:
    return len([entity for entity in await worshippers_of(session, son_id) if entity.status is EntityStatus.CANON])
