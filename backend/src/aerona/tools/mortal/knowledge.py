from typing import Any

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, TurnCounter
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.phases.knowledge_levels import DevelopmentKind, development_for, empty_branch_hint, empty_branches, shift_level
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.engine.primitives.stats import stat_or
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action, no_cost
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines
from aerona.tools.mortal.inputs import DevelopKnowledgeInput, LearnInput
from aerona.tools.mortal.support import MortalCreation, craft_of, create_record, name_free, same_region

LEARNING_BONDS = (BondKind.TRADES_WITH, BondKind.ALLY, BondKind.RULES)


async def knows_record(call: MortalCall, holder_id: int, knowledge_id: int) -> bool:
    return any(bond.target_node_id == knowledge_id for bond in await BondRepository(call.session).outgoing(holder_id, BondKind.KNOWS))


async def _deepen_held(call: MortalCall, knowledge: EntityRow, branch: str) -> str:
    table = call.rules.knowledge
    gain = table.develop_level_gain + (table.craft_level_bonus if (await craft_of(call)) > call.rules.mortal_tools.knowledge_craft_threshold else 0)
    level = shift_level(call.rules, knowledge, gain)
    if level is None:
        empty = await empty_branches(call.session, call.me.world_id)
        hint = lines.EMPTY_BRANCHES.format(branches=empty_branch_hint(call.rules, empty)) if empty else ""
        fail(MortalResult.KNOWLEDGE_AT_CAP, name=knowledge.name, cap=table.level_cap, hint=hint)
    call.target(knowledge.id)
    await call.chronicle(
        ChronicleKind.KNOWLEDGE,
        lines.KNOWLEDGE_DEEPENED,
        entity_ids=[call.me.id, knowledge.id],
        me=call.me.name,
        name=knowledge.name,
        branch=branch,
        level=level,
    )
    return result(MortalResult.KNOWLEDGE_DEEPENED, id=knowledge.id, name=knowledge.name, level=level)


async def _find_existing(call: MortalCall, knowledge: EntityRow, branch: str) -> str:
    await teach(call.tick, call.me.id, knowledge, lines.FOUND_ALONE)
    call.target(knowledge.id)
    await call.chronicle(
        ChronicleKind.KNOWLEDGE, lines.KNOWLEDGE_FOUND, entity_ids=[call.me.id, knowledge.id], me=call.me.name, name=knowledge.name, branch=branch
    )
    return result(MortalResult.KNOWLEDGE_FOUND, id=knowledge.id, name=knowledge.name, level=knowledge_level(call.rules, knowledge))


async def develop_knowledge(call: MortalCall, args: DevelopKnowledgeInput) -> str:
    tools = call.rules.mortal_tools
    decision = await development_for(call.session, call.rules, call.me, args.branch)
    label = args.branch.value.replace("_", " ")
    if decision.kind is DevelopmentKind.DEEPEN and decision.knowledge is not None:
        return await _deepen_held(call, decision.knowledge, label)
    if decision.kind is DevelopmentKind.LEARN and decision.knowledge is not None:
        return await _find_existing(call, decision.knowledge, label)
    await name_free(call, args.name)
    bases: list[EntityRow] = []
    for base_id in (args.base_ids or [])[: tools.knowledge_max_prereqs]:
        base = await call.session.get(EntityRow, base_id)
        if (
            base is not None
            and base.entity_type is EntityType.KNOWLEDGE
            and base.status is EntityStatus.CANON
            and await knows_record(call, call.me.id, base.id)
        ):
            bases.append(base)
    deepest = max((stat_or(base, "level", 0) for base in bases), default=0)
    skilled = 1 if (await craft_of(call)) > tools.knowledge_craft_threshold else 0
    level = max(1, min(tools.knowledge_level_cap, 1 + deepest + skilled))
    knowledge = await create_record(
        call,
        MortalCreation(
            args.name,
            EntityType.KNOWLEDGE,
            args.description,
            subtype=args.branch.value.replace("_", " "),
            stats={"level": level, "spread": tools.knowledge_spread},
            power=max(1, min(level, tools.creation_power_cap)),
            image_prompt=args.image_prompt,
            knowledge_branch=args.branch,
        ),
    )
    bonds = BondRepository(call.session)
    for base in bases:
        await bonds.connect(BondDraft(knowledge.id, base.id, BondKind.DESCENDS_FROM, call.epoch, lines.BUILT_UPON))
    resource = await call.session.get(EntityRow, args.resource_id) if args.resource_id is not None else None
    if resource is not None and resource.entity_type is EntityType.RESOURCE and resource.status is EntityStatus.CANON:
        await bonds.connect(BondDraft(knowledge.id, resource.id, BondKind.SOURCE_OF, call.epoch))
    await teach(call.tick, call.me.id, knowledge, lines.DEVELOPED)
    await call.chronicle(
        ChronicleKind.KNOWLEDGE,
        lines.KNOWLEDGE,
        entity_ids=[call.me.id, knowledge.id],
        me=call.me.name,
        name=knowledge.name,
        branch=args.branch.value.replace("_", " "),
        level=level,
    )
    return result(MortalResult.KNOWLEDGE_DEVELOPED, id=knowledge.id, name=knowledge.name, level=level)


async def may_learn_from(call: MortalCall, teacher: EntityRow) -> bool:
    if await BondRepository(call.session).active_between(call.me.id, teacher.id, LEARNING_BONDS):
        return True
    return await same_region(call, teacher)


async def learn_knowledge(call: MortalCall, args: LearnInput) -> str:
    tools = call.rules.mortal_tools
    await call.within_limit(TurnCounter.LEARNING, tools.learn_per_epoch, "mortal_tools.learn_per_epoch", MortalResult.LEARN_LIMIT)
    knowledge = await call.session.get(EntityRow, args.knowledge_id)
    teacher = await call.session.get(EntityRow, args.from_id)
    if knowledge is None or teacher is None or knowledge.entity_type is not EntityType.KNOWLEDGE:
        fail(MortalResult.LEARN_INVALID)
    if knowledge.status is not EntityStatus.CANON or teacher.status is not EntityStatus.CANON:
        fail(MortalResult.LEARN_INVALID)
    if not await knows_record(call, teacher.id, knowledge.id):
        fail(MortalResult.TEACHER_IGNORANT, name=teacher.name)
    if not await may_learn_from(call, teacher):
        fail(MortalResult.NO_LEARNING_BOND, name=teacher.name)
    if not await teach(call.tick, call.me.id, knowledge, lines.LEARNED_FROM.format(teacher=teacher.name)):
        fail(MortalResult.ALREADY_KNOWN)
    await call.bump(TurnCounter.LEARNING)
    call.target(knowledge.id)
    await call.chronicle(
        ChronicleKind.KNOWLEDGE,
        lines.LEARNED,
        entity_ids=[call.me.id, knowledge.id, teacher.id],
        me=call.me.name,
        knowledge=knowledge.name,
        teacher=teacher.name,
    )
    return result(MortalResult.LEARNED, knowledge=knowledge.name, teacher=teacher.name)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    return [
        ToolSpec(
            MortalToolId.DEVELOP_KNOWLEDGE, mortal, DevelopKnowledgeInput, ToolMeta(ActionKind.DEVELOP_KNOWLEDGE, mortal_standard_action), develop_knowledge
        ),
        ToolSpec(MortalToolId.LEARN_KNOWLEDGE, mortal, LearnInput, ToolMeta(ActionKind.LEARN, no_cost), learn_knowledge),
    ]
