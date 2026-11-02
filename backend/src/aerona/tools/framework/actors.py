from typing import Any

from aerona.core.errors import NotFoundError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.son import SonStatus
from aerona.engine.services.war import held_captive
from aerona.prompts import MortalToolId, PromptId, render
from aerona.prompts.contexts.agent import CaptiveGateContext, MortalGateContext, SleepNoticeContext, SonGateContext
from aerona.prompts.tools.results import CommonResult, result
from aerona.tools.framework.call import CallEnvironment, MortalCall, SonCall
from aerona.tools.framework.errors import RejectionError
from aerona.tools.framework.runtime import GateRejection, ToolRuntime, attribute_lines
from aerona.tools.framework.spec import ToolSpec
from aerona.tools.framework.validation import label_of


class SonToolRuntime(ToolRuntime[SonCall]):
    agent = AgentKind.SON

    async def build_call(self, environment: CallEnvironment) -> SonCall:
        son = await environment.session.get(SonRow, self.settings.actor_node_id)
        if son is None:
            raise NotFoundError("No such son.")
        world_id = son.current_world_id
        if world_id is None:
            cosmos = await CosmosRepository(environment.session).get()
            world_id = cosmos.primary_world_id if cosmos is not None else None
        return SonCall(environment, son, world_id)

    async def gate(self, call: SonCall, spec: ToolSpec[SonCall, Any]) -> GateRejection | None:
        son = call.son
        if son.status is SonStatus.ACTIVE:
            return None
        sleep_left = son.sleep_epochs_left if son.status is SonStatus.ASLEEP and son.sleep_epochs_left else None
        text = render(PromptId.SON_GATE_REJECTION, SonGateContext(name=son.name, state_label=label_of(son.status), sleep_left=sleep_left))
        return GateRejection(text, exhaust=True)

    def precheck(self, call: SonCall, spec: ToolSpec[SonCall, Any]) -> None:
        minimum = spec.meta.minimum_rarity(self.rules)
        if minimum is not None and not call.son.rarity.at_least(minimum):
            raise RejectionError(result(CommonResult.NOT_AVAILABLE, tool=spec.name))
        horror = self.rules.cosmic_horror
        cost = spec.meta.actions(self.rules)
        mad = call.son.sanity is not None and call.son.sanity < horror.son_madness_threshold
        if mad and cost > horror.mad_son_max_tool_actions:
            raise RejectionError(result(CommonResult.MADNESS_LIMIT, tool=spec.name, limit=horror.mad_son_max_tool_actions))
        if not spec.meta.flexible_actions:
            call.require_actions(cost)

    def epilogue(self, call: SonCall, text: str) -> str:
        son = call.son
        parts = [text]
        if son.status is not SonStatus.ACTIVE:
            call.turn.exhaust()
            parts.append(render(PromptId.SLEEP_NOTICE, SleepNoticeContext(asleep=son.status is SonStatus.ASLEEP, state_label=label_of(son.status))))
        parts.append(call.status_text())
        return " ".join(part for part in parts if part)

    async def attribute_chronicle(self, call: SonCall, marker: int) -> None:
        await attribute_lines(call.session, marker, call.son.id)

    async def refund_essence(self, call: SonCall, amount: int) -> None:
        call.son.essence += max(0, amount)


class MortalToolRuntime(ToolRuntime[MortalCall]):
    agent = AgentKind.MORTAL

    async def build_call(self, environment: CallEnvironment) -> MortalCall:
        me = await environment.session.get(EntityRow, self.settings.actor_node_id)
        if me is None:
            raise NotFoundError("No such mortal.")
        return MortalCall(environment, me)

    async def gate(self, call: MortalCall, spec: ToolSpec[MortalCall, Any]) -> GateRejection | None:
        me = call.me
        if me.status is not EntityStatus.CANON:
            text = render(PromptId.MORTAL_GATE_REJECTION, MortalGateContext(name=me.name, status_label=label_of(me.status)))
            return GateRejection(text, exhaust=True)
        if spec.tool_id is MortalToolId.ESCAPE:
            return None
        captivity = await held_captive(call.session, me.id)
        if captivity is None:
            return None
        captor = await call.session.get(EntityRow, captivity.captor_entity_id)
        text = render(PromptId.CAPTIVE_GATE_REJECTION, CaptiveGateContext(captor=captor.name if captor is not None else ""))
        return GateRejection(text, exhaust=False)

    def precheck(self, call: MortalCall, spec: ToolSpec[MortalCall, Any]) -> None:
        if not spec.meta.flexible_actions:
            call.require_actions(spec.meta.actions(self.rules))

    def epilogue(self, call: MortalCall, text: str) -> str:
        if call.me.status is not EntityStatus.CANON or call.died:
            call.turn.exhaust()
        return " ".join(part for part in (text, call.status_text()) if part)
