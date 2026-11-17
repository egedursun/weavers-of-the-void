from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.knowledge import branch_label
from aerona.catalog.society import SOCIAL_CLASSES
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.society import CommunityRelationRow, CommunitySocietyRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.society import CreatureTrait, KnowledgeBranch, SocialClass
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarStatus
from aerona.domain.enums.world import Discovery
from aerona.engine.gods.behaviour_hints import mortal_behaviour_lines
from aerona.engine.gods.devotion import resurrection_state
from aerona.engine.gods.opportunities import is_multi_world, land_measure, named
from aerona.engine.gods.queries import cosmos_row
from aerona.engine.gods.stats import Trait, trait, trait_or
from aerona.engine.gods.world_view import WorldView, load_world_view
from aerona.engine.phases.knowledge_levels import empty_branches
from aerona.prompts.contexts.common import NamedRecord, SonBrief
from aerona.prompts.contexts.opportunities import (
    AtWar,
    BloodFeuds,
    BurdensomeGod,
    DangerousCreatures,
    DeadGod,
    DefyGod,
    Discontent,
    Enemies,
    ExplorationReasonKind,
    GranaryEmptying,
    LandResources,
    LearnableKnowledge,
    LovingNeighbours,
    MortalOpportunity,
    NoGod,
    NoKnowledge,
    NoLanguage,
    OpenRoute,
    PatronedRecord,
    Remains,
    SkyOpen,
    SkyUnknown,
    TenseNeighbours,
    TradePartners,
    UnknownBranches,
    UnknownLands,
    ValuedRecord,
)
from aerona.rules.registry import Rules

SABOTEUR_TYPES = frozenset({EntityType.FACTION, EntityType.CULT, EntityType.MORTAL})
SOCIETY_TYPES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
EXPLORER_TYPES = frozenset(COMMUNITY_TYPES | {EntityType.MORTAL})
ROAD_BRANCHES = frozenset({KnowledgeBranch.GATE_LORE, KnowledgeBranch.PATHFINDING, KnowledgeBranch.SKY_NAVIGATION, KnowledgeBranch.MAGIC})
EXPLORATION_BRANCHES = frozenset({KnowledgeBranch.SEAFARING, KnowledgeBranch.PATHFINDING, KnowledgeBranch.ASTRONOMY})


@dataclass(frozen=True)
class MortalScope:
    session: AsyncSession
    rules: Rules
    view: WorldView
    entity: EntityRow
    near: list[EntityRow]


async def community_relation(session: AsyncSession, first: int, second: int) -> int:
    row = await session.get(CommunityRelationRow, (min(first, second), max(first, second)))
    return row.value if row is not None else 0


async def _bonded(session: AsyncSession, first: int, second: int, kind: BondKind) -> bool:
    return await BondRepository(session).exists_between(first, second, kind)


async def _at_war_together(session: AsyncSession, first: int, second: int) -> bool:
    statement = (
        select(WarSideRow.war_id).join(WarRow, WarRow.id == WarSideRow.war_id).where(WarRow.status == WarStatus.ONGOING, WarSideRow.left_epoch.is_(None))
    )
    first_wars = set(await session.scalars(statement.where(WarSideRow.entity_id == first)))
    second_wars = set(await session.scalars(statement.where(WarSideRow.entity_id == second)))
    return bool(first_wars & second_wars)


async def _neighbour_lines(scope: MortalScope) -> list[MortalOpportunity]:
    session, table, entity = scope.session, scope.rules.opportunities, scope.entity
    lines: list[MortalOpportunity] = []
    community = entity.entity_type in COMMUNITY_TYPES
    partners: list[NamedRecord] = []
    enemies: list[EntityRow] = []
    tense: list[ValuedRecord] = []
    loving: list[ValuedRecord] = []
    for other in scope.near:
        trade = await _bonded(session, entity.id, other.id, BondKind.TRADES_WITH)
        enemy = await _bonded(session, entity.id, other.id, BondKind.ENEMY)
        both = community and other.entity_type in COMMUNITY_TYPES
        relation = await community_relation(session, entity.id, other.id) if both else 0
        if not trade and not enemy:
            partners.append(named(other))
        if enemy and (not both or relation < 0):
            enemies.append(other)
        if both and not enemy and relation <= -table.tense_neighbor:
            tense.append(ValuedRecord(id=other.id, name=other.name, value=relation))
        if both and relation >= table.friendly_neighbor and not enemy and not await _bonded(session, entity.id, other.id, BondKind.ALLY):
            loving.append(ValuedRecord(id=other.id, name=other.name, value=relation))
    if partners:
        lines.append(TradePartners(communities=partners[: table.list_max]))
    if enemies:
        chosen = enemies[: table.list_max]
        can_war = not any([await _at_war_together(session, entity.id, other.id) for other in chosen])
        lines.append(Enemies(enemies=[named(other) for other in chosen], can_declare_war=can_war, can_sabotage=entity.entity_type in SABOTEUR_TYPES))
    if tense:
        lines.append(TenseNeighbours(neighbours=tense[: table.list_short], can_sabotage=entity.entity_type in SABOTEUR_TYPES))
    if community and loving:
        lines.append(LovingNeighbours(neighbours=loving[: table.list_short]))
    return lines


async def _land_lines(scope: MortalScope) -> list[MortalOpportunity]:
    session, table, view, entity = scope.session, scope.rules.opportunities, scope.view, scope.entity
    lines: list[MortalOpportunity] = []
    known = view.knows.get(entity.id, set())
    learnable: dict[int, PatronedRecord] = {}
    for other in scope.near:
        if await _bonded(session, entity.id, other.id, BondKind.ENEMY):
            continue
        for knowledge_id in sorted(view.knows.get(other.id, set()) - known):
            knowledge = view.entities.get(knowledge_id)
            if knowledge is not None and knowledge.living and knowledge_id not in learnable:
                learnable[knowledge_id] = PatronedRecord(id=knowledge.id, name=knowledge.name, patron=other.name)
    if learnable:
        lines.append(LearnableKnowledge(knowledge=list(learnable.values())[: table.list_max]))
    region = view.top_region_id(entity.id)
    local = [other for other in view.canon() if region is not None and other.id != entity.id and view.top_region_id(other.id) == region]
    owned = set(
        await session.scalars(
            select(BondRow.target_node_id).where(BondRow.source_node_id == entity.id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        )
    )
    resources = [named(other) for other in local if other.entity_type is EntityType.RESOURCE and other.id not in owned]
    if resources:
        lines.append(LandResources(resources=resources[: table.list_max]))
    beasts = [named(other) for other in local if other.entity_type is EntityType.SPECIES and trait_or(other, Trait.DANGER, 0) >= table.monster_danger]
    if beasts:
        lines.append(DangerousCreatures(species=beasts))
    if not known:
        lines.append(NoKnowledge())
    empty = await empty_branches(session, entity.world_id)
    if empty:
        lines.append(UnknownBranches(branches=[branch_label(branch) for branch in empty[: scope.rules.knowledge.hint_empty_branches]]))
    speaks = await session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == entity.id, BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE).limit(1)
    )
    if speaks is None:
        lines.append(NoLanguage())
    remains = [
        named(other)
        for other in view.entities.values()
        if region is not None
        and view.top_region_id(other.id) == region
        and other.id != entity.id
        and (
            (
                other.status is EntityStatus.CANON
                and (view.has_flag(other.id, EntityFlag.RUIN) or view.has_flag(other.id, EntityFlag.EMPTY_TOMB) or other.engine_kind is EngineKind.DEAD_GOD)
            )
            or (other.status is EntityStatus.DEAD and view.has_flag(other.id, EntityFlag.RUIN))
        )
    ]
    if remains:
        lines.append(Remains(remains=remains[: table.list_short]))
    return lines


async def _community_lines(scope: MortalScope) -> list[MortalOpportunity]:
    session, rules, entity = scope.session, scope.rules, scope.entity
    table = rules.opportunities
    lines: list[MortalOpportunity] = []
    if entity.entity_type in COMMUNITY_TYPES:
        feuds = await session.scalars(
            select(CommunityRelationRow).where(
                or_(CommunityRelationRow.entity_a_id == entity.id, CommunityRelationRow.entity_b_id == entity.id),
                CommunityRelationRow.blood_feud_since_epoch.is_not(None),
            )
        )
        rivals = [scope.view.entities.get(row.entity_b_id if row.entity_a_id == entity.id else row.entity_a_id) for row in feuds]
        feud_records = [named(other) for other in rivals if other is not None and other.living]
        if feud_records:
            lines.append(BloodFeuds(communities=feud_records))
        wars = await session.scalars(
            select(EntityRow)
            .join(WarRow, WarRow.event_entity_id == EntityRow.id)
            .join(WarSideRow, WarSideRow.war_id == WarRow.id)
            .where(WarRow.status == WarStatus.ONGOING, WarSideRow.entity_id == entity.id, WarSideRow.left_epoch.is_(None))
        )
        war_records = [named(war) for war in dict.fromkeys(wars)]
        if war_records:
            lines.append(AtWar(wars=war_records))
    if entity.entity_type in SOCIETY_TYPES:
        society = await session.get(CommunitySocietyRow, entity.id)
        if society is not None:
            if society.stock_food < table.granary_food:
                lines.append(GranaryEmptying(food=society.stock_food, bread_price=society.price_food))
            worst = min(SocialClass, key=society.satisfaction)
            if society.satisfaction(worst) < table.discontented:
                lines.append(Discontent(class_label=SOCIAL_CLASSES[worst].singular.lower(), satisfaction=society.satisfaction(worst)))
    return lines


async def _god_lines(scope: MortalScope) -> list[MortalOpportunity]:
    session, rules, view, entity = scope.session, scope.rules, scope.view, scope.entity
    lines: list[MortalOpportunity] = []
    statement = (
        select(SonRow)
        .join(BondRow, BondRow.target_node_id == SonRow.id)
        .where(BondRow.source_node_id == entity.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, SonRow.status == SonStatus.DEAD)
    )
    cosmos = await cosmos_row(session)
    epoch = cosmos.epoch if cosmos is not None else 0
    for dead in dict.fromkeys(await session.scalars(statement)):
        state = await resurrection_state(session, rules, dead, epoch)
        if state is not None:
            lines.append(
                DeadGod(
                    name=dead.name, death_age=dead.death_epoch or 0, devotion=state.devotion, corpse=state.corpse.name if state.corpse is not None else None
                )
            )
    multi = await is_multi_world(session)
    sons = [
        son
        for son in await session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id))
        if not multi or son.current_world_id == entity.world_id
    ]
    if (
        entity.entity_type is EntityType.MORTAL
        and trait_or(entity, Trait.STRENGTH, 0) + trait_or(entity, Trait.AGILITY, 0) >= rules.opportunities.challenge_god_strength
        and sons
    ):
        lines.append(DefyGod(sons=[NamedRecord(id=son.id, name=son.name) for son in sons]))
    patron_id = view.patron_son(entity.id)
    patron = await session.get(SonRow, patron_id) if patron_id is not None else None
    if patron is not None:
        cursed = await _bonded(session, patron.id, entity.id, BondKind.CURSED)
        if cursed or patron.rebel:
            lines.append(BurdensomeGod(name=patron.name))
    elif view.patrons.get(entity.id) is None and sons:
        lines.append(
            NoGod(
                candidates=[
                    SonBrief(id=son.id, name=son.name, title=son.title, domain_1=son.domain_primary.value, domain_2=son.domain_secondary.value) for son in sons
                ]
            )
        )
    return lines


async def _exploration_reasons(scope: MortalScope) -> list[ExplorationReasonKind]:
    session, rules, view, entity = scope.session, scope.rules, scope.view, scope.entity
    reasons: list[ExplorationReasonKind] = []
    exploration = rules.exploration
    if entity.entity_type in COMMUNITY_TYPES:
        if entity.entity_type in SOCIETY_TYPES and land_measure(rules, view, entity.world_id).narrow:
            reasons.append(ExplorationReasonKind(kind="narrow_lands"))
        society = await session.get(CommunitySocietyRow, entity.id)
        prosperity = trait(entity, Trait.PROSPERITY)
        if society is not None and society.stock_food < rules.world_effects.hungry_food:
            reasons.append(ExplorationReasonKind(kind="hunger"))
        elif prosperity is not None and prosperity < exploration.poor_prosperity:
            reasons.append(ExplorationReasonKind(kind="poverty"))
        region = view.top_region_id(entity.id)
        explorer = next(
            (
                other
                for other in view.canon(EntityType.MORTAL)
                if other.mortal_role is MortalRole.EXPLORER and region is not None and view.top_region_id(other.id) == region
            ),
            None,
        )
        if explorer is not None:
            reasons.append(ExplorationReasonKind(kind="explorer", explorer_name=explorer.name))
    elif entity.mortal_role is MortalRole.EXPLORER:
        reasons.append(ExplorationReasonKind(kind="explorer_spirited"))
    if any(view.knows_branch(entity.id, branch) for branch in EXPLORATION_BRANCHES):
        reasons.append(ExplorationReasonKind(kind="road_knowledge"))
    return reasons


async def has_route_method(session: AsyncSession, view: WorldView, entity: EntityRow) -> bool:
    if any(view.knows_branch(entity.id, branch) for branch in ROAD_BRANCHES):
        return True
    tamed = await session.scalars(
        select(BondRow.target_node_id).where(BondRow.source_node_id == entity.id, BondRow.kind == BondKind.TAMED, BondRow.state == BondState.ACTIVE)
    )
    for beast_id in tamed:
        beast = view.entities.get(beast_id)
        if beast is None or not beast.living:
            continue
        flying = await session.get(EntityTraitRow, (beast_id, CreatureTrait.FLYING))
        if flying is not None or view.has_flag(beast_id, EntityFlag.MEGAFAUNA):
            return True
    return False


async def _horizon_lines(scope: MortalScope) -> list[MortalOpportunity]:
    session, rules, view, entity = scope.session, scope.rules, scope.view, scope.entity
    lines: list[MortalOpportunity] = []
    if entity.entity_type not in EXPLORER_TYPES:
        return lines
    if rules.exploration.tool_per_epoch > 0:
        lines.append(UnknownLands(reasons=await _exploration_reasons(scope), can_settle=entity.entity_type in SOCIETY_TYPES))
    routes = list(
        await session.scalars(
            select(RouteRow).where(
                RouteRow.active.is_(True), RouteRow.known.is_(True), or_(RouteRow.world_a_id == entity.world_id, RouteRow.world_b_id == entity.world_id)
            )
        )
    )
    linked = {route.world_b_id if route.world_a_id == entity.world_id else route.world_a_id for route in routes}
    known = select(WorldRow.name, WorldRow.id).where(WorldRow.id != entity.world_id, WorldRow.discovery == Discovery.KNOWN).order_by(WorldRow.id)
    roadless = [name for name, world_id in await session.execute(known) if world_id not in linked]
    if await has_route_method(session, view, entity):
        lines.append(SkyOpen(roadless_worlds=roadless[: rules.opportunities.list_short]))
    elif roadless:
        lines.append(SkyUnknown(worlds=roadless[: rules.opportunities.list_short]))
    if routes:
        lines.append(OpenRoute())
    return lines


async def mortal_opportunities(session: AsyncSession, rules: Rules, entity: EntityRow) -> list[MortalOpportunity]:
    view = await load_world_view(session, rules)
    near = [other for other in view.canon(*COMMUNITY_TYPES) if other.id != entity.id and view.near(entity, other)]
    scope = MortalScope(session, rules, view, entity, near)
    cosmos = await cosmos_row(session)
    epoch = cosmos.epoch if cosmos is not None else 0

    async def relation(other_id: int) -> int:
        return await community_relation(session, entity.id, other_id)

    return [
        *await _neighbour_lines(scope),
        *await _land_lines(scope),
        *await _community_lines(scope),
        *await _god_lines(scope),
        *await _horizon_lines(scope),
        *await mortal_behaviour_lines(session, rules, entity, near, relation=relation, epoch=epoch),
    ]
