import re
from collections import Counter
from collections.abc import Awaitable, Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyTenetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.ledger import LedgerEntryRow
from aerona.db.tables.lore import ThreadRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ThreadStatus
from aerona.domain.enums.culture import IdeologyTenet
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityType
from aerona.domain.enums.son import Stat
from aerona.engine.gods.world_view import WorldView
from aerona.engine.primitives.numbers import stable_roll
from aerona.engine.primitives.stats import stat
from aerona.prompts.contexts.common import NamedRecord
from aerona.prompts.contexts.opportunities import (
    Covenants,
    GodlessCreeds,
    KnowledgePairs,
    OverusedTool,
    RecordPair,
    RivalOptions,
    StalePlan,
    SuggestionReason,
    ToolSuggestion,
    UntriedTools,
)
from aerona.rules.registry import Rules

R = SuggestionReason
THREAD_MENTION = re.compile(r"thread\s*#?\s*(\d+)", re.IGNORECASE)
WAR_PARTIES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.FACTION})
THINKING = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
DUEL_STATS = (Stat.STRENGTH, Stat.WISDOM, Stat.CUNNING, Stat.CHARISMA, Stat.WILL)
WEALTH_KEYS = ("wealth", "prosperity")


def named(entity: EntityRow) -> NamedRecord:
    return NamedRecord(id=entity.id, name=entity.name)


async def tool_usage(session: AsyncSession, actor_id: int, epoch: int, window: int) -> Counter[str]:
    statement = (
        select(LedgerEntryRow.tool, func.count(LedgerEntryRow.id))
        .where(LedgerEntryRow.actor_node_id == actor_id, LedgerEntryRow.epoch > epoch - window, LedgerEntryRow.undone.is_(False))
        .group_by(LedgerEntryRow.tool)
    )
    return Counter({tool: int(count) for tool, count in await session.execute(statement)})


def overused(rules: Rules, usage: Counter[str]) -> OverusedTool | None:
    if not usage:
        return None
    tool, uses = usage.most_common(1)[0]
    window = rules.opportunities.untried_epochs
    return OverusedTool(tool=tool, uses=uses, epochs=window) if uses >= rules.opportunities.overused_uses else None


def rotated(names: list[str], seed: str) -> list[str]:
    return sorted(names, key=lambda name: (stable_roll(seed, name), name))


class SonHints:
    def __init__(self, session: AsyncSession, rules: Rules, view: WorldView, son: SonRow, *, visible: list[EntityRow], epoch: int) -> None:
        self.session = session
        self.rules = rules
        self.view = view
        self.son = son
        self.visible = visible
        self.epoch = epoch

    def own(self) -> list[EntityRow]:
        return [entity for entity in self.visible if entity.entity_type in THINKING and self.view.patron_son(entity.id) == self.son.id]

    def creations_of(self, son_id: int) -> list[EntityRow]:
        return sorted((entity for entity in self.visible if entity.creator_son_id == son_id), key=lambda entity: (-entity.power_level, entity.id))

    def worshippers_of(self, son_id: int) -> list[EntityRow]:
        return [entity for entity in self.visible if entity.entity_type in THINKING and self.view.patron_son(entity.id) == son_id]

    def neighbour_pair(self) -> tuple[EntityRow, EntityRow] | None:
        for mine in (entity for entity in self.own() if entity.entity_type in WAR_PARTIES):
            for other in self.visible:
                if other.id != mine.id and other.entity_type in WAR_PARTIES and self.view.patron_son(other.id) != self.son.id and self.view.near(mine, other):
                    return mine, other
        return None

    def rival_options(self, rival: SonRow) -> RivalOptions:
        options: list[ToolSuggestion] = []
        edge = max(DUEL_STATS, key=lambda item: (self.son.stat(item) - rival.stat(item), item.value))
        options.append(ToolSuggestion(tool="challenge", reason=R.BEST_STAT, label=edge.value, value=self.son.stat(edge)))
        believers = self.worshippers_of(rival.id)
        if believers:
            options.append(ToolSuggestion(tool="send_dream", reason=R.RIVAL_WORSHIPPER, target=named(believers[0])))
        made = self.creations_of(rival.id)
        if made:
            options.append(ToolSuggestion(tool="curse", reason=R.RIVAL_CREATION, target=named(made[0])))
        pair = next(
            (
                (first, other)
                for first in believers
                if first.entity_type in WAR_PARTIES
                for other in self.visible
                if other.entity_type in WAR_PARTIES and other.id != first.id and self.view.patron_son(other.id) != rival.id and self.view.near(first, other)
            ),
            None,
        )
        if pair is not None:
            options.append(ToolSuggestion(tool="incite_war", reason=R.OWN_AND_NEIGHBOUR, target=named(pair[0]), second=named(pair[1])))
        home = next((entity for entity in believers if entity.entity_type is EntityType.SETTLEMENT), None)
        if home is not None:
            options.append(ToolSuggestion(tool="send_disaster", reason=R.RIVAL_SETTLEMENT, target=named(home), label=rival.name))
        if made:
            options.append(ToolSuggestion(tool="transform", reason=R.RIVAL_CREATION, target=named(made[0])))
        options.append(ToolSuggestion(tool="call_sibling", reason=R.SPEAK, target=NamedRecord(id=rival.id, name=rival.name)))
        return RivalOptions(rival=NamedRecord(id=rival.id, name=rival.name), options=options[: self.rules.opportunities.rival_options])

    async def _hostile_pair(self) -> ToolSuggestion | None:
        visible = {entity.id for entity in self.visible}
        statement = select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE).order_by(BondRow.id.desc())
        for bond in await self.session.scalars(statement):
            if bond.source_node_id in visible and bond.target_node_id in visible:
                first, second = self.view.entities[bond.source_node_id], self.view.entities[bond.target_node_id]
                return ToolSuggestion(tool="start_event", reason=R.HOSTILE_PAIR, target=named(first), second=named(second))
        return None

    async def _enemy(self) -> ToolSuggestion | None:
        for bond in await BondRepository(self.session).incoming(self.son.id, BondKind.ENEMY):
            entity = self.view.entities.get(bond.source_node_id)
            if entity is not None and entity.living:
                return ToolSuggestion(tool="destroy", reason=R.REBELLED_AGAINST_YOU, target=named(entity))
        return None

    async def _no_road(self) -> ToolSuggestion | None:
        world = self.son.current_world_id
        if world is None:
            return None
        statement = select(RouteRow.id).where(RouteRow.active.is_(True), (RouteRow.world_a_id == world) | (RouteRow.world_b_id == world))
        if await self.session.scalar(statement.limit(1)) is not None:
            return None
        return ToolSuggestion(tool="create_vessel", reason=R.NO_ROAD)

    async def _hungry(self) -> ToolSuggestion | None:
        for entity in self.own():
            society = await self.session.get(CommunitySocietyRow, entity.id)
            if society is not None and society.stock_food < self.rules.opportunities.hungry_food:
                return ToolSuggestion(tool="miracle", reason=R.HUNGRY, target=named(entity))
        godless = next((entity for entity in self.visible if self.view.has_flag(entity.id, EntityFlag.GODLESS)), None)
        return ToolSuggestion(tool="miracle", reason=R.GODLESS, target=named(godless)) if godless is not None else None

    def _poor(self) -> ToolSuggestion | None:
        poor = sorted(
            (entity for entity in self.own() if stat(entity, "prosperity") is not None), key=lambda entity: (stat(entity, "prosperity") or 0, entity.id)
        )
        return ToolSuggestion(tool="affect_entity", reason=R.POOR_WORSHIPPER, target=named(poor[0]), value=stat(poor[0], "prosperity")) if poor else None

    def _counted(self, entity_type: EntityType, tool: str, reason: SuggestionReason, few: int) -> ToolSuggestion | None:
        count = sum(1 for entity in self.visible if entity.entity_type is entity_type)
        return ToolSuggestion(tool=tool, reason=reason, value=count) if count < few else None

    def _no_faction(self) -> ToolSuggestion | None:
        factions = {entity.location_id for entity in self.visible if entity.entity_type is EntityType.FACTION}
        home = next((entity for entity in self.own() if entity.entity_type is EntityType.SETTLEMENT and entity.id not in factions), None)
        return ToolSuggestion(tool="found_faction", reason=R.NO_FACTION, target=named(home)) if home is not None else None

    def _rich(self, tool: str, cost: int) -> ToolSuggestion | None:
        return (
            ToolSuggestion(tool=tool, reason=R.RICH_ESSENCE, value=self.son.essence)
            if self.son.essence >= cost + self.rules.opportunities.essence_margin
            else None
        )

    async def untried(self, rivals: list[SonRow], usage: Counter[str]) -> UntriedTools | None:
        rival_ids = {rival.id for rival in rivals}
        names = {rival.id: rival.name for rival in rivals}
        rival_made = [entity for entity in self.visible if entity.creator_son_id in rival_ids]
        rival_town = next(
            (entity for entity in self.visible if entity.entity_type is EntityType.SETTLEMENT and self.view.patron_son(entity.id) in rival_ids), None
        )
        unclaimed = next((entity for entity in self.visible if entity.entity_type in THINKING and self.view.patrons.get(entity.id) is None), None)
        mortal = next(
            (entity for entity in self.own() if entity.entity_type is EntityType.MORTAL and not self.view.has_flag(entity.id, EntityFlag.CHOSEN)), None
        )
        pair = self.neighbour_pair()
        builders: dict[str, Callable[[], Awaitable[ToolSuggestion | None]]] = {
            "curse": self._wrap(ToolSuggestion(tool="curse", reason=R.RIVAL_CREATION, target=named(rival_made[0])) if rival_made else None),
            "transform": self._wrap(ToolSuggestion(tool="transform", reason=R.RIVAL_CREATION, target=named(rival_made[0])) if rival_made else None),
            "send_disaster": self._wrap(
                ToolSuggestion(
                    tool="send_disaster", reason=R.RIVAL_SETTLEMENT, target=named(rival_town), label=names.get(self.view.patron_son(rival_town.id) or 0)
                )
                if rival_town is not None
                else None
            ),
            "incite_war": self._wrap(
                ToolSuggestion(tool="incite_war", reason=R.OWN_AND_NEIGHBOUR, target=named(pair[0]), second=named(pair[1])) if pair else None
            ),
            "affect_entity": self._wrap(self._poor()),
            "destroy": self._enemy,
            "start_event": self._hostile_pair,
            "birth_child": self._wrap(self._rich("birth_child", self.rules.costs.bear_child)),
            "birth_world": self._wrap(self._rich("birth_world", self.rules.balance.birth_world)),
            "hang_celestial": self._wrap(self._counted(EntityType.CELESTIAL, "hang_celestial", R.FEW_CELESTIALS, self.rules.opportunities.few_celestials)),
            "decree_natural_law": self._wrap(self._counted(EntityType.NATURAL_LAW, "decree_natural_law", R.FEW_LAWS, self.rules.opportunities.few_laws)),
            "create_vessel": self._no_road,
            "found_faction": self._wrap(self._no_faction()),
            "send_dream": self._wrap(ToolSuggestion(tool="send_dream", reason=R.UNCLAIMED, target=named(unclaimed)) if unclaimed is not None else None),
            "declare_chosen": self._wrap(ToolSuggestion(tool="declare_chosen", reason=R.OWN_MORTAL, target=named(mortal)) if mortal is not None else None),
            "miracle": self._hungry,
        }
        found: list[ToolSuggestion] = []
        for tool in rotated([tool for tool in builders if tool not in usage], f"{self.epoch}:{self.son.id}"):
            if len(found) >= self.rules.opportunities.untried_count:
                break
            suggestion = await builders[tool]()
            if suggestion is not None:
                found.append(suggestion)
        return UntriedTools(suggestions=found) if found else None

    @staticmethod
    def _wrap(value: ToolSuggestion | None) -> Callable[[], Awaitable[ToolSuggestion | None]]:
        async def give() -> ToolSuggestion | None:
            return value

        return give

    async def covenants(self) -> Covenants | None:
        allies: list[NamedRecord] = []
        bonds = BondRepository(self.session)
        for bond in await bonds.outgoing(self.son.id, BondKind.ALLY) + await bonds.incoming(self.son.id, BondKind.ALLY):
            other = await self.session.get(SonRow, bond.other_end(self.son.id))
            if other is not None and other.alive:
                allies.append(NamedRecord(id=other.id, name=other.name))
        return Covenants(sons=allies) if allies else None

    async def stale_plan(self) -> StalePlan | None:
        mentioned = sorted({int(found) for found in THREAD_MENTION.findall(self.son.plan or "")})
        if not mentioned:
            return None
        closed = list(await self.session.scalars(select(ThreadRow.id).where(ThreadRow.id.in_(mentioned), ThreadRow.status != ThreadStatus.OPEN)))
        return StalePlan(thread_ids=sorted(closed)) if closed else None

    async def godless_creeds(self) -> GodlessCreeds | None:
        mine = [entity.id for entity in self.own()]
        if not mine:
            return None
        godless = select(IdeologyTenetRow.ideology_entity_id).where(IdeologyTenetRow.tenet == IdeologyTenet.ANTI_GOD)
        rows = list(
            await self.session.execute(
                select(IdeologyAdherentRow.ideology_entity_id, func.max(IdeologyAdherentRow.strength))
                .where(IdeologyAdherentRow.adherent_entity_id.in_(mine), IdeologyAdherentRow.ideology_entity_id.in_(godless))
                .group_by(IdeologyAdherentRow.ideology_entity_id)
                .order_by(func.max(IdeologyAdherentRow.strength).desc())
            )
        )
        creeds = [await self.session.get(EntityRow, creed) for creed, _ in rows]
        named_creeds = [named(creed) for creed in creeds if creed is not None]
        return GodlessCreeds(creeds=named_creeds, strongest=int(rows[0][1])) if named_creeds else None

    def knowledge_pairs(self) -> KnowledgePairs | None:
        knowledge = [entity for entity in self.visible if entity.entity_type is EntityType.KNOWLEDGE]
        pairs: list[RecordPair] = []
        for believer in self.own():
            lacking = sorted(
                (item for item in knowledge if item.id not in self.view.knows.get(believer.id, set())), key=lambda item: (stat(item, "spread") or 0, item.id)
            )
            if lacking:
                pairs.append(RecordPair(a=named(lacking[0]), b=named(believer)))
        return KnowledgePairs(pairs=pairs[: self.rules.opportunities.list_max]) if pairs else None


async def son_behaviour_lines(
    hints: SonHints, rivals: list[SonRow]
) -> list[RivalOptions | UntriedTools | OverusedTool | Covenants | StalePlan | KnowledgePairs | GodlessCreeds]:
    usage = await tool_usage(hints.session, hints.son.id, hints.epoch, hints.rules.opportunities.untried_epochs)
    lines: list[RivalOptions | UntriedTools | OverusedTool | Covenants | StalePlan | KnowledgePairs | GodlessCreeds] = []
    if rivals:
        lines.append(hints.rival_options(rivals[0]))
    for line in (
        await hints.untried(rivals, usage),
        overused(hints.rules, usage),
        await hints.covenants(),
        await hints.stale_plan(),
        hints.knowledge_pairs(),
        await hints.godless_creeds(),
    ):
        if line is not None:
            lines.append(line)
    return lines


def wealth(entity: EntityRow) -> int | None:
    return next((value for value in (stat(entity, key) for key in WEALTH_KEYS) if value is not None), None)


async def mortal_untried(
    session: AsyncSession, rules: Rules, me: EntityRow, near: list[EntityRow], *, relation: Callable[[int], Awaitable[int]], epoch: int
) -> UntriedTools | None:
    usage = await tool_usage(session, me.id, epoch, rules.opportunities.untried_epochs)
    bonds = BondRepository(session)
    builders: dict[str, Callable[[], Awaitable[ToolSuggestion | None]]] = {}

    async def war() -> ToolSuggestion | None:
        for other in near:
            if other.entity_type in COMMUNITY_TYPES and not await bonds.exists_between(me.id, other.id, BondKind.ENEMY):
                value = await relation(other.id)
                if value <= -rules.opportunities.tense_neighbor:
                    return ToolSuggestion(tool="declare_war", reason=R.TENSE_NEIGHBOUR, target=named(other), value=value)
        return None

    async def lend() -> ToolSuggestion | None:
        mine = wealth(me)
        if mine is None or mine < rules.opportunities.lend_min_wealth:
            return None
        poorer = sorted((other for other in near if (wealth(other) or mine) < mine), key=lambda other: (wealth(other) or 0, other.id))
        return ToolSuggestion(tool="lend", reason=R.POORER_NEIGHBOUR, target=named(poorer[0]), value=wealth(poorer[0])) if poorer else None

    async def preach() -> ToolSuggestion | None:
        mine = await bonds.patron(me.id)
        other: EntityRow | None = None
        for item in near:
            if item.entity_type in COMMUNITY_TYPES and await bonds.patron(item.id) != mine:
                other = item
                break
        return ToolSuggestion(tool="preach", reason=R.OTHER_FAITH, target=named(other), label=other.name) if other is not None and mine is not None else None

    async def hostile(tool: str) -> ToolSuggestion | None:
        for other in near:
            if await bonds.exists_between(me.id, other.id, BondKind.ENEMY) or (other.entity_type in COMMUNITY_TYPES and await relation(other.id) < 0):
                return ToolSuggestion(tool=tool, reason=R.ENEMY, target=named(other))
        return None

    async def sabotage() -> ToolSuggestion | None:
        return await hostile("sabotage")

    async def spies() -> ToolSuggestion | None:
        return await hostile("build_spy_network")

    builders.update({"declare_war": war, "lend": lend, "preach": preach, "sabotage": sabotage, "build_spy_network": spies})
    found: list[ToolSuggestion] = []
    for tool in rotated([tool for tool in builders if tool not in usage], f"{epoch}:{me.id}"):
        if len(found) >= rules.opportunities.untried_count:
            break
        suggestion = await builders[tool]()
        if suggestion is not None:
            found.append(suggestion)
    return UntriedTools(suggestions=found) if found else None


async def mortal_behaviour_lines(
    session: AsyncSession, rules: Rules, me: EntityRow, near: list[EntityRow], *, relation: Callable[[int], Awaitable[int]], epoch: int
) -> list[UntriedTools | OverusedTool]:
    lines: list[UntriedTools | OverusedTool] = []
    untried = await mortal_untried(session, rules, me, near, relation=relation, epoch=epoch)
    if untried is not None:
        lines.append(untried)
    repeated = overused(rules, await tool_usage(session, me.id, epoch, rules.opportunities.untried_epochs))
    if repeated is not None:
        lines.append(repeated)
    return lines
