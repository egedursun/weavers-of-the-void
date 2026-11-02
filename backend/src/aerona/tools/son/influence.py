from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.entity_types import ENTITY_TYPES
from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN, SAYING_MAX, SAYING_MIN
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityType
from aerona.domain.enums.son import PowerEffect
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.stats import set_stats, stat
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, grant, require_essence, rounded, share, shift_relation

PERCENT = 100
NOTE_SEPARATOR = ", "
CURSE_STATS = (
    "prosperity",
    "fertility",
    "defense",
    "strength",
    "martiality",
    "population",
    "followers",
    "abundance",
    "wealth",
    "influence",
    "might",
    "hp",
    "charisma",
)
THINKING = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
LEARNERS = frozenset({*THINKING, EntityType.SPECIES})


class ChangeInput(ToolInput):
    stat: str
    percent: float


class AffectInput(ToolInput):
    entity_id: int
    changes: Annotated[list[ChangeInput], Field(min_length=1)]
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class ChosenInput(ToolInput):
    mortal_id: int
    boon: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class CurseInput(ToolInput):
    entity_id: int
    curse: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class DreamInput(ToolInput):
    target_id: int
    dream: Annotated[str, Field(min_length=SAYING_MIN, max_length=SAYING_MAX)]


FIXED_STATS = frozenset({"lifespan", "age", "level"})


class TeachInput(ToolInput):
    target_id: int
    knowledge_id: int
    how: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


def foreign_creator(call: SonCall, entity: EntityRow) -> int | None:
    creator = entity.creator_son_id
    return creator if creator is not None and creator != call.son.id else None


def shifted(rules: Any, entity: EntityRow, key: str, delta_points: float, percent: float) -> tuple[int, int] | None:
    field = ENTITY_TYPES[entity.entity_type].stat(key)
    if field is None:
        return None
    low, high = field.bounds(rules)
    old = stat(entity, key) or low
    raw = old + delta_points if high is not None and high <= PERCENT else old * (1 + percent / PERCENT)
    new = max(low, round(raw)) if high is None else max(low, min(high, round(raw)))
    set_stats(entity, **{key: new})
    return old, new


async def affect_entity(call: SonCall, args: AffectInput) -> str:
    tools = call.rules.son_tools
    entity = await require_canon(call.session, args.entity_id)
    await ensure_in_reach(call, entity)
    if await call.target_uses(ActionKind.INFLUENCE, entity.id) >= tools.affect_per_target:
        fail(SonResult.AFFECT_LIMIT, name=entity.name, cap=tools.affect_per_target)
    if len({change.stat for change in args.changes}) < len(args.changes):
        fail(SonResult.AFFECT_DUPLICATE)
    creator_id = foreign_creator(call, entity)
    cost = call.rules.costs.influence * (tools.influence_foreign_cost_mult if creator_id is not None else 1) + entity.power_level
    require_essence(call, cost)
    spec = ENTITY_TYPES[entity.entity_type]
    keys = [field.key for field in spec.stats if field.key not in FIXED_STATS and getattr(entity.stats, field.key, None) is not None]
    notes: list[str] = []
    for change in args.changes[: tools.influence_max_stats]:
        field = spec.stat(change.stat)
        if field is None or change.stat not in keys:
            fail(SonResult.STAT_INVALID, stat=change.stat, available=NOTE_SEPARATOR.join(keys))
        bounded = max(-tools.influence_max_change_pct, min(tools.influence_max_change_pct, change.percent))
        moved = shifted(call.rules, entity, change.stat, bounded, bounded)
        if moved is not None:
            notes.append(lines.EFFECT_NOTE.format(label=field.label, old=moved[0], new=moved[1]))
    call.spend_essence(cost)
    call.target(entity.id)
    creator = await call.session.get(SonRow, creator_id) if creator_id is not None else None
    if creator is not None:
        await shift_relation(call, creator.id, -tools.influence_foreign_relation)
    joined = NOTE_SEPARATOR.join(notes)
    await call.chronicle(
        ChronicleKind.CREATION, lines.AFFECT, entity_ids=[entity.id], son=call.son.name, entity=entity.name, changes=joined, reason=args.reason
    )
    return result(SonResult.AFFECTED, name=entity.name, notes=joined, creator=creator.name if creator is not None else "")


async def declare_chosen(call: SonCall, args: ChosenInput) -> str:
    tools = call.rules.son_tools
    mortal = require_type(await require_canon(call.session, args.mortal_id), {EntityType.MORTAL}, SonResult.NOT_LIVING_MORTAL)
    await ensure_in_reach(call, mortal)
    entities = EntityRepository(call.session)
    if await entities.has_flag(mortal.id, EntityFlag.CHOSEN):
        fail(SonResult.ALREADY_CHOSEN, name=mortal.name)
    require_essence(call, call.rules.costs.declare_chosen)
    lifespan_field = ENTITY_TYPES[EntityType.MORTAL].stat("lifespan")
    cap = lifespan_field.bounds(call.rules)[1] if lifespan_field is not None else None
    lifespan = (stat(mortal, "lifespan") or tools.default_mortal_lifespan) + tools.chosen_lifespan
    set_stats(
        mortal,
        strength=max(0, min(PERCENT, (stat(mortal, "strength") or 0) + tools.chosen_strength)),
        charisma=max(0, min(PERCENT, (stat(mortal, "charisma") or 0) + tools.chosen_charisma)),
        lifespan=max(1, lifespan if cap is None else min(cap, lifespan)),
    )
    await entities.add_flag(mortal.id, EntityFlag.CHOSEN, call.epoch)
    bonds = BondRepository(call.session)
    for bond in await bonds.outgoing(mortal.id, BondKind.WORSHIPS):
        await bonds.deactivate(bond, call.epoch, lines.CHOSEN_BOND)
    await bonds.connect(BondDraft(mortal.id, call.son.id, BondKind.WORSHIPS, call.epoch, lines.CHOSEN_BOND))
    await bonds.connect(BondDraft(call.son.id, mortal.id, BondKind.BLESSED, call.epoch, args.boon))
    creator_id = foreign_creator(call, mortal)
    if creator_id is not None:
        await shift_relation(call, creator_id, -tools.chosen_foreign_relation)
    call.spend_essence(call.rules.costs.declare_chosen)
    call.target(mortal.id)
    await call.chronicle(ChronicleKind.CREATION, lines.CHOSEN, entity_ids=[mortal.id], son=call.son.name, mortal=mortal.name, boon=args.boon)
    return result(SonResult.CHOSEN, name=mortal.name)


async def _curse_severity(call: SonCall, patron: SonRow | None, curser: bool) -> int:
    tools = call.rules.son_tools
    resist = 0.0
    if patron is not None and patron.id != call.son.id:
        untouchable = tools.curse_untouchable_resist if await call.has_power(PowerEffect.UNTOUCHABLE, patron) else 0
        resist = patron.will / tools.curse_resist_divisor + untouchable
    scale = tools.curser_severity_pct / PERCENT if curser else 1
    raw = (tools.curse_severity_base + call.son.might / tools.curse_might_divisor - resist / tools.curse_resist_effect_divisor) * scale
    return max(tools.curse_min_severity, round(raw))


async def curse(call: SonCall, args: CurseInput) -> str:
    tools = call.rules.son_tools
    entity = await require_canon(call.session, args.entity_id)
    await ensure_in_reach(call, entity)
    entities = EntityRepository(call.session)
    if await entities.has_flag(entity.id, EntityFlag.CURSED):
        fail(SonResult.ALREADY_CURSED, name=entity.name)
    curser = await call.has_power(PowerEffect.CURSER)
    cost = round((call.rules.costs.curse + entity.power_level * tools.curse_cost_per_power) * (tools.curser_cost_pct / PERCENT if curser else 1))
    require_essence(call, cost)
    bonds = BondRepository(call.session)
    patron_id = await bonds.patron(entity.id)
    patron = await call.session.get(SonRow, patron_id) if patron_id is not None else None
    severity = await _curse_severity(call, patron, curser)
    notes: list[str] = []
    for key in CURSE_STATS:
        field = ENTITY_TYPES[entity.entity_type].stat(key)
        if field is None or stat(entity, key) is None:
            continue
        moved = shifted(call.rules, entity, key, -severity, -severity)
        if moved is not None:
            notes.append(lines.EFFECT_NOTE.format(label=field.label, old=moved[0], new=moved[1]))
    await entities.add_flag(entity.id, EntityFlag.CURSED, call.epoch)
    await bonds.connect(BondDraft(call.son.id, entity.id, BondKind.CURSED, call.epoch, args.curse))
    creator_id = foreign_creator(call, entity)
    if creator_id is not None:
        await shift_relation(call, creator_id, -tools.curse_creator_relation)
    if patron is not None and patron.id not in (call.son.id, creator_id):
        await shift_relation(call, patron.id, -tools.curse_patron_relation)
    call.spend_essence(cost)
    call.target(entity.id)
    joined = NOTE_SEPARATOR.join(notes)
    await call.chronicle(ChronicleKind.CURSE, lines.CURSE, entity_ids=[entity.id], son=call.son.name, entity=entity.name, curse=args.curse, notes=joined)
    return result(SonResult.CURSED, severity=severity, notes=joined)


async def send_dream(call: SonCall, args: DreamInput) -> str:
    tools = call.rules.son_tools
    target = require_type(await require_canon(call.session, args.target_id), THINKING, SonResult.DREAM_TARGET)
    await ensure_in_reach(call, target)
    require_essence(call, call.rules.costs.dream)
    patron_id = await BondRepository(call.session).patron(target.id)
    if patron_id == call.son.id:
        fail(SonResult.ALREADY_YOURS, name=target.name)
    old = await call.session.get(SonRow, patron_id) if patron_id is not None else None
    whisper = tools.dream_whisper_bonus_pct if await call.has_power(PowerEffect.DREAM_WHISPER) else 0
    rival = old.charisma if old is not None else tools.dream_default_rival_charisma
    raw = (
        tools.dream_base_pct + (call.son.charisma - rival) / tools.dream_charisma_divisor + whisper - (stat(target, "zeal") or 0) / tools.dream_zealotry_divisor
    )
    chance = max(tools.dream_min_pct, min(tools.dream_max_pct, rounded(raw)))
    call.spend_essence(call.rules.costs.dream)
    call.target(target.id)
    roll = call.die(PERCENT, "dream")
    if roll <= chance:
        await BondRepository(call.session).connect(BondDraft(target.id, call.son.id, BondKind.WORSHIPS, call.epoch, lines.DREAM_BOND))
        if old is not None:
            await shift_relation(call, old.id, -tools.dream_steal_relation)
        level = await grant(call, call.son, tools.dream_xp, tools.dream_renown)
        lost = lines.LOST_WORSHIPPER.format(old=old.name) if old is not None else ""
        await call.chronicle(ChronicleKind.DREAM, lines.DREAM_TAKEN, entity_ids=[target.id], son=call.son.name, target=target.name, lost=lost, dream=args.dream)
        return result(SonResult.DREAM_TAKEN, roll=roll, chance=chance, name=target.name, level=level)
    if old is not None:
        await shift_relation(call, old.id, -tools.dream_fail_relation)
    sensed = lines.SENSED.format(old=old.name) if old is not None else ""
    await call.chronicle(ChronicleKind.DREAM, lines.DREAM_FAILED, entity_ids=[target.id], son=call.son.name, target=target.name, sensed=sensed)
    return result(SonResult.DREAM_FAILED, roll=roll, chance=chance)


async def teach_knowledge(call: SonCall, args: TeachInput) -> str:
    tools = call.rules.son_tools
    target = await require_canon(call.session, args.target_id)
    knowledge = await require_canon(call.session, args.knowledge_id)
    require_type(target, LEARNERS, SonResult.TEACH_TARGET)
    require_type(knowledge, {EntityType.KNOWLEDGE}, SonResult.NOT_KNOWLEDGE)
    await ensure_in_reach(call, target)
    cost = share(call.rules.intervention_costs.teach_knowledge, tools.intervention_cost_pct)
    if call.son.essence < cost:
        fail(SonResult.TEACH_ESSENCE, cost=cost)
    if not await teach(call.tick, target.id, knowledge, lines.TEACH_NOTE.format(son=call.son.name, how=args.how)):
        fail(SonResult.ALREADY_KNOWS, name=target.name)
    bonds = BondRepository(call.session)
    if await bonds.patron(target.id) is None and target.entity_type in THINKING:
        await bonds.connect(BondDraft(target.id, call.son.id, BondKind.WORSHIPS, call.epoch, lines.KNOWLEDGE_GIFT))
    call.spend_essence(cost)
    call.target(target.id)
    level = await grant(call, call.son, tools.knowledge_xp, tools.knowledge_renown)
    await call.chronicle(
        ChronicleKind.KNOWLEDGE,
        lines.TEACH,
        entity_ids=[target.id, knowledge.id],
        son=call.son.name,
        target=target.name,
        knowledge=knowledge.name,
        how=args.how,
    )
    return result(SonResult.TAUGHT, name=target.name, knowledge=knowledge.name, level=level)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    influence = gate(Gate.INFLUENCE_TOOLS)
    rare = gate(Gate.RARE_TOOLS)
    return [
        ToolSpec(
            SonToolId.AFFECT_ENTITY,
            son,
            AffectInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action, essence_cost=lambda rules: rules.costs.influence, rarity_gate=influence),
            affect_entity,
        ),
        ToolSpec(
            SonToolId.DECLARE_CHOSEN,
            son,
            ChosenInput,
            ToolMeta(ActionKind.DECLARE_CHOSEN, son_standard_action, essence_cost=lambda rules: rules.costs.declare_chosen, rarity_gate=influence),
            declare_chosen,
        ),
        ToolSpec(
            SonToolId.CURSE,
            son,
            CurseInput,
            ToolMeta(ActionKind.CURSE, son_standard_action, essence_cost=lambda rules: rules.costs.curse, rarity_gate=influence),
            curse,
        ),
        ToolSpec(
            SonToolId.SEND_DREAM,
            son,
            DreamInput,
            ToolMeta(ActionKind.DREAM, son_standard_action, essence_cost=lambda rules: rules.costs.dream, rarity_gate=rare),
            send_dream,
        ),
        ToolSpec(
            SonToolId.TEACH_KNOWLEDGE,
            son,
            TeachInput,
            ToolMeta(
                ActionKind.TEACH_KNOWLEDGE,
                son_standard_action,
                essence_cost=lambda rules: share(rules.intervention_costs.teach_knowledge, rules.son_tools.intervention_cost_pct),
                rarity_gate=rare,
            ),
            teach_knowledge,
        ),
    ]
