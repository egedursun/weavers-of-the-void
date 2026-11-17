from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stats import max_essence, max_hp
from aerona.core.random import SeededRandom
from aerona.db.record_context import Term
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import PowerEffect
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import has_unlocked_power
from aerona.engine.recording.record import FactInput, RoleValue, StepDraft, record
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.agent import ActionsSpentContext, PerEpochLimitContext, StatusLineContext
from aerona.prompts.tools.results import CommonResult, result
from aerona.rules.registry import Rules
from aerona.tools.framework.errors import RejectionError
from aerona.tools.framework.ports import ToolPorts
from aerona.tools.framework.turn import TurnState, bump_counter, counter_value


@dataclass
class CallEnvironment:
    session: AsyncSession
    rules: Rules
    tick: TickContext
    turn: TurnState
    ports: ToolPorts
    tool: str


@dataclass
class CallLog:
    actions_charged: int | None = None
    essence_spent: int = 0
    target_node_id: int | None = None
    detail: list[str] = field(default_factory=list)


class ToolCall:
    agent: AgentKind
    actor_kind: ActorKind

    def __init__(self, environment: CallEnvironment) -> None:
        self.environment = environment
        self.log = CallLog()
        self._atlas: RegionAtlas | None = None

    @property
    def session(self) -> AsyncSession:
        return self.environment.session

    @property
    def rules(self) -> Rules:
        return self.environment.rules

    @property
    def tick(self) -> TickContext:
        return self.environment.tick

    @property
    def turn(self) -> TurnState:
        return self.environment.turn

    @property
    def ports(self) -> ToolPorts:
        return self.environment.ports

    @property
    def epoch(self) -> int:
        return self.tick.epoch

    @property
    def actor_id(self) -> int:
        raise NotImplementedError

    @property
    def actor_name(self) -> str:
        raise NotImplementedError

    @property
    def world_id(self) -> int | None:
        raise NotImplementedError

    @property
    def chronicle_son_id(self) -> int | None:
        return None

    def rng(self, stream: str = "main") -> SeededRandom:
        return self.tick.rng(stream)

    def die(self, faces: int, stream: str = "dice") -> int:
        return self.rng(stream).die(max(1, faces))

    def target(self, node_id: int | None) -> None:
        if node_id is not None and self.log.target_node_id is None:
            self.log.target_node_id = node_id

    def note(self, text: str) -> None:
        self.log.detail.append(text)

    def actions_spent_text(self) -> str:
        return render(PromptId.ACTIONS_SPENT, ActionsSpentContext(agent=self.agent, remaining=self.turn.action_points))

    def require_actions(self, amount: int) -> None:
        if amount > 0 and self.turn.action_points < amount:
            raise RejectionError(self.actions_spent_text())

    def charge_actions(self, amount: int) -> None:
        self.require_actions(amount)
        self.turn.spend(amount)
        self.log.actions_charged = (self.log.actions_charged or 0) + max(0, amount)

    def waive_actions(self) -> None:
        if self.log.actions_charged is None:
            self.log.actions_charged = 0

    async def count(self, counter: TurnCounter) -> int:
        return await counter_value(self.session, self.actor_id, self.epoch, counter)

    async def bump(self, counter: TurnCounter, amount: int = 1) -> int:
        value = await bump_counter(self.session, self.actor_id, self.epoch, counter, amount)
        context = self.turn.context
        self.turn.row.context = context.model_copy(update={"counters": {**context.counters, counter: value}})
        return value

    async def target_uses(self, kind: ActionKind, target_id: int) -> int:
        statement = select(func.count(ActionRecordRow.id)).where(
            ActionRecordRow.actor_node_id == self.actor_id,
            ActionRecordRow.epoch == self.epoch,
            ActionRecordRow.kind == kind,
            ActionRecordRow.target_node_id == target_id,
        )
        return int(await self.session.scalar(statement) or 0)

    def limit_text(self, rule_path: str, value: int) -> str:
        return render(PromptId.PER_EPOCH_LIMIT, PerEpochLimitContext(rule_path=rule_path, value=value))

    async def within_limit(self, counter: TurnCounter, cap: int, rule_path: str, template: StrEnum, **values: object) -> None:
        if await self.count(counter) >= cap:
            raise RejectionError(result(CommonResult.LIMIT_REACHED, message=result(template, **values), limit=self.limit_text(rule_path, cap)))

    async def record(
        self,
        key: str,
        /,
        *,
        roles: Mapping[IncidentRole, RoleValue] | None = None,
        facts: Mapping[str, FactInput] | None = None,
        place: int | None = None,
        origin: int | None = None,
        destination: int | None = None,
        world_id: int | None = None,
        feed: FeedCategory | None = None,
        kind: ChronicleKind | None = None,
        about: int | None = None,
        cause: int | None = None,
        steps: Sequence[StepDraft] = (),
        terms: Sequence[Term] | None = None,
    ) -> str:
        written = await record(
            self.tick,
            key,
            roles=roles,
            facts=facts,
            steps=steps,
            terms=terms,
            place=place,
            origin=origin,
            destination=destination,
            son_id=about if about is not None else self.chronicle_son_id,
            world_id=world_id if world_id is not None else self.world_id,
            feed=feed,
            kind=kind,
            cause=cause,
        )
        return written.text

    def remember_creation(self, entity_id: int) -> None:
        self.turn.remember_creation(entity_id)

    async def atlas(self) -> RegionAtlas:
        if self._atlas is None:
            self._atlas = await RegionAtlas.load(self.session)
        return self._atlas

    async def reachable_world(self, world_id: int) -> bool:
        own = self.world_id
        return own is None or await WorldRepository(self.session).connected(own, world_id)

    def status_text(self) -> str:
        raise NotImplementedError


class SonCall(ToolCall):
    agent = AgentKind.SON
    actor_kind = ActorKind.SON

    def __init__(self, environment: CallEnvironment, son: SonRow, world_id: int | None) -> None:
        super().__init__(environment)
        self.son = son
        self._world_id = world_id

    @property
    def actor_id(self) -> int:
        return self.son.id

    @property
    def actor_name(self) -> str:
        return self.son.name

    @property
    def world_id(self) -> int | None:
        return self._world_id

    @property
    def chronicle_son_id(self) -> int | None:
        return self.son.id

    @property
    def max_essence(self) -> int:
        return max_essence(self.rules, self.son.might)

    @property
    def max_hp(self) -> int:
        return max_hp(self.rules, self.son.endurance)

    def spend_essence(self, amount: int) -> None:
        paid = max(0, amount)
        self.son.essence = max(0, self.son.essence - paid)
        self.log.essence_spent += paid

    def gain_essence(self, amount: int, *, capped: bool = True) -> int:
        before = self.son.essence
        raised = before + max(0, amount)
        self.son.essence = min(max(before, self.max_essence), raised) if capped else raised
        return self.son.essence - before

    async def has_power(self, effect: PowerEffect, son: SonRow | None = None) -> bool:
        return await has_unlocked_power(self.session, self.rules, son or self.son, effect)

    def status_text(self) -> str:
        return render(PromptId.STATUS_LINE, StatusLineContext(remaining=self.turn.action_points, essence=self.son.essence, max_essence=self.max_essence))


class MortalCall(ToolCall):
    agent = AgentKind.MORTAL
    actor_kind = ActorKind.MORTAL

    def __init__(self, environment: CallEnvironment, me: EntityRow) -> None:
        super().__init__(environment)
        self.me = me
        self.died = False

    @property
    def actor_id(self) -> int:
        return self.me.id

    @property
    def actor_name(self) -> str:
        return self.me.name

    @property
    def world_id(self) -> int | None:
        return self.me.world_id

    def status_text(self) -> str:
        return result(CommonResult.MORTAL_STATUS, remaining=self.turn.action_points)
