from aerona.agents.context.scope import load_scope
from aerona.agents.context.son_memory import son_memory
from aerona.agents.metrics import metrics_turn
from aerona.agents.mortal import MortalTurnResult, finish_mortal_turn, mortal_prompts, start_mortal_turn
from aerona.agents.roles import AgentRole, turn_label
from aerona.agents.runtime import AgentRuntime
from aerona.agents.text import extract_word
from aerona.agents.turns.ports import SpeechOnlyToolkit, ToolCatalogue, TurnToolkit
from aerona.agents.turns.session import TurnPlan, run_turn
from aerona.agents.turns.state import long_job_notes
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonStatus
from aerona.engine.body.describe import body_lines
from aerona.engine.gods.queries import worshippers_of
from aerona.events.kinds import EventKind
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.mortal import FallenSonTurnContext
from aerona.prompts.contexts.son_turn import DoneAction, TurnContinuationContext, TurnInterruption


async def fallen_system(runtime: AgentRuntime, son_id: int, points: int, catalogue: ToolCatalogue) -> str:
    async with runtime.database.read() as session:
        rules = await runtime.rules(session)
        scope = await load_scope(session, rules)
        son = await session.get(SonRow, son_id)
        body = await session.get(EntityRow, son.body_entity_id) if son is not None and son.body_entity_id is not None else None
        if son is None or body is None:
            raise NotFoundError("No such fallen son.")
        name = await session.get(TrueNameRow, body.id)
        context = FallenSonTurnContext(
            lore_language=scope.cosmos.lore_language,
            rules=rules,
            son_name=son.name,
            title=son.title,
            body_name=body.name,
            world_name=scope.world_name(body.world_id) or scope.cosmos.name,
            memory=await son_memory(scope, son),
            body=await body_lines(session, rules, body, private=True),
            remnant=[worshipper.name for worshipper in await worshippers_of(session, son.id)],
            existence=son.existence,
            restoration_existence=rules.transform.restoration_existence,
            knows_true_name=name is not None and body.id in name.known_by,
            action_points=points,
            paid_tools=catalogue.paid,
            free_tools=catalogue.free,
        )
        return render(PromptId.FALLEN_SON_TURN, context)


async def body_of(runtime: AgentRuntime, son_id: int) -> int:
    async with runtime.database.read() as session:
        son = await session.get(SonRow, son_id)
        if son is None or son.status is not SonStatus.FALLEN or son.body_entity_id is None:
            raise ValidationFailedError("Only a fallen son living in a mortal body takes a fallen turn.")
        return son.body_entity_id


async def mark_acted(runtime: AgentRuntime, son_id: int, epoch: int) -> None:
    async with runtime.database.write() as session:
        son = await session.get(SonRow, son_id)
        if son is not None:
            son.last_acted_epoch = epoch


async def run_fallen_turn(runtime: AgentRuntime, son_id: int) -> MortalTurnResult:
    runtime.require_llm("fallen son turn")
    body_id = await body_of(runtime, son_id)
    started = await start_mortal_turn(runtime, body_id)
    toolkit: TurnToolkit = SpeechOnlyToolkit()
    if runtime.toolkits is not None:
        toolkit = await runtime.toolkits.mortal_toolkit(body_id, started.epoch, started.action_points)
    catalogue = toolkit.catalogue
    system = await fallen_system(runtime, son_id, started.action_points, catalogue)
    prompt = (await mortal_prompts(runtime, started, catalogue))[1]
    rules = await runtime.current_rules()
    runtime.publish(EventKind.MORTAL_TURN_STARTED, {"entity_id": body_id, "name": started.name, "resumed": started.resumed, "model": runtime.world_model})

    async def follow_up(reason: TurnInterruption, detail: str | None, done: list[DoneAction]) -> str | None:
        async with runtime.database.read() as session:
            jobs = await long_job_notes(session, body_id, rules.model.continuation_action_summary_chars)
        note = render(PromptId.MORTAL_TURN_CONTINUATION, TurnContinuationContext(reason=reason, error_detail=detail, done=done, long_jobs=jobs))
        return (await mortal_prompts(runtime, started, catalogue, note))[1]

    plan = TurnPlan(
        label=turn_label(AgentRole.MORTAL_TURN, started.name),
        actor=started.name,
        actor_kind=ActorKind.MORTAL,
        actor_id=body_id,
        system_prompt=system,
        prompt=prompt,
        max_turns=rules.mortal_agents.max_turns,
        timeout=rules.model.agent_timeout,
        continuation=follow_up,
        is_complete=lambda text: bool(extract_word(text)),
    )
    with metrics_turn(started.epoch, started.action_points):
        outcome = await run_turn(runtime.model, plan, toolkit, rules.model, runtime.publish)
    result = await finish_mortal_turn(runtime, started, outcome, list(toolkit.created_entity_ids))
    await mark_acted(runtime, son_id, started.epoch)
    runtime.publish(
        EventKind.MORTAL_TURN_FINISHED,
        {"entity_id": body_id, "name": result.name, "word": result.word, "creations": result.creations, "status": result.status, "model": runtime.world_model},
    )
    return result
