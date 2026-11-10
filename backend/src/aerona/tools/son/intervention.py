from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.entity_types import can_contain
from aerona.catalog.gates import Gate
from aerona.catalog.interventions import DISASTERS, MIRACLES
from aerona.constants.tool_inputs import (
    CREATION_DESCRIPTION_MAX,
    CREATION_DESCRIPTION_MIN,
    DESCRIPTION_MAX,
    IMAGE_PROMPT_MAX,
    NAME_MAX,
    NAME_MIN,
    REASON_MAX,
    REASON_MIN,
    SHORT_DESCRIPTION_MIN,
    SUBTYPE_MAX,
)
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, LOCATION_TYPES, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.intervention import Disaster, Miracle
from aerona.domain.enums.mind import MemoryKind, ThoughtKind
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.divine.politics import god_grudge
from aerona.engine.dominion.miracles import impress, miracle_factor
from aerona.engine.gods.interventions import MiracleEffect, MiracleOutcome, apply_miracle
from aerona.engine.mind.thoughts import think
from aerona.engine.phases.disasters import DISASTER_KINDS, after_strike, apply_disaster, joined_names, record_impact
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.renames import rewrite_name
from aerona.engine.primitives.subtypes import normalized_subtype
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, grant, require_essence, share, shift_relation

PERCENT = 100
NOTE_SEPARATOR = "; "
EXCERPT = 300
THINKING = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})


class MiracleInput(ToolInput):
    entity_id: int
    kind: Miracle
    how: Annotated[str, Field(min_length=REASON_MIN + 5, max_length=REASON_MAX)]


class DisasterInput(ToolInput):
    target_id: int
    kind: Disaster
    name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
    description: Annotated[str, Field(min_length=SHORT_DESCRIPTION_MIN, max_length=DESCRIPTION_MAX)]
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
    image_prompt: Annotated[str, Field(max_length=IMAGE_PROMPT_MAX)] | None = None


class TransformInput(ToolInput):
    entity_id: int
    new_name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)] | None = None
    new_subtype: Annotated[str, Field(max_length=SUBTYPE_MAX)] | None = None
    new_description: Annotated[str, Field(min_length=CREATION_DESCRIPTION_MIN, max_length=CREATION_DESCRIPTION_MAX)]
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class DestroyInput(ToolInput):
    entity_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


def miracle_cost(rules: Any, power: int) -> int:
    return share(rules.intervention_costs.miracle, rules.son_tools.intervention_cost_pct) + power


def miracle_notes(outcome: MiracleOutcome) -> list[str]:
    texts = {
        MiracleEffect.HEALTH: lines.MIRACLE_HEALTH,
        MiracleEffect.CURSE_LIFTED: lines.MIRACLE_CURSE,
        MiracleEffect.BOUNTY: lines.MIRACLE_BOUNTY,
        MiracleEffect.DEFENSE: lines.MIRACLE_DEFENSE,
        MiracleEffect.SHIELD: lines.MIRACLE_SHIELD,
    }
    notes: list[str] = []
    for effect in outcome.effects:
        if effect is MiracleEffect.GROWTH:
            notes.extend(lines.MIRACLE_GROWTH.format(what=key.value) for key in outcome.grown)
        elif effect is MiracleEffect.SENSES:
            notes.append(lines.MIRACLE_SENSES.format(names=joined_names(list(outcome.restored))))
        elif effect is MiracleEffect.PEACE:
            notes.append(lines.MIRACLE_PEACE.format(count=outcome.peace_made))
        else:
            notes.append(texts[effect])
    return notes


async def apply_son_miracle(call: SonCall, target: EntityRow, miracle: Miracle) -> list[str]:
    notes = miracle_notes(await apply_miracle(call.tick, target, miracle, lines.PEACE_REASON))
    book = await call.tick.divine()
    for god_id in (await book.faithful_of(call.session, target.id))[0]:
        if god_id != call.son.id:
            await god_grudge(call.tick, god_id, call.son.id, MemoryKind.AIDED_CHOSEN, f"blessed {target.name}")
    return notes


async def miracle_witnesses(call: SonCall, target: EntityRow) -> list[int]:
    if target.entity_type is EntityType.MORTAL:
        return [target.id]
    statement = select(EntityRow.id).where(
        await present_in(call.session, target), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    return list(await call.session.scalars(statement.order_by(EntityRow.id)))


async def miracle(call: SonCall, args: MiracleInput) -> str:
    tools = call.rules.son_tools
    target = await require_canon(call.session, args.entity_id)
    await ensure_in_reach(call, target)
    cost = round_half_up(miracle_cost(call.rules, target.power_level) * await miracle_factor(call.tick, call.son.id, target))
    require_essence(call, cost)
    notes = await apply_son_miracle(call, target, args.kind)
    bonds = BondRepository(call.session)
    label = MIRACLES[args.kind].label
    if target.entity_type in THINKING and await bonds.patron(target.id) is None:
        await bonds.connect(BondDraft(target.id, call.son.id, BondKind.WORSHIPS, call.epoch, lines.MIRACLE_WORSHIP.format(miracle=label)))
    await bonds.connect(BondDraft(call.son.id, target.id, BondKind.BLESSED, call.epoch, lines.MIRACLE_BOND.format(miracle=label, how=args.how)))
    call.spend_essence(cost)
    call.target(target.id)
    level = await grant(call, call.son, tools.miracle_xp, tools.miracle_renown)
    witnesses = await miracle_witnesses(call, target)
    for witness in witnesses:
        await think(call.session, call.rules, witness, ThoughtKind.SAW_MIRACLE, call.epoch, subject_id=call.son.id)
    await impress(call.tick, call.son.id, target, kind=args.kind.value, magnitude=call.son.might, witnesses=len(witnesses))
    joined = NOTE_SEPARATOR.join(notes)
    await call.chronicle(
        ChronicleKind.MIRACLE,
        lines.MIRACLE,
        entity_ids=[target.id],
        son=call.son.name,
        miracle=label.lower(),
        target=target.name,
        how=args.how,
        notes=f" ({joined})" if joined else "",
    )
    return result(SonResult.MIRACLE_DONE, notes=joined, level=level)


async def _disaster_event(call: SonCall, args: DisasterInput, target: EntityRow, severity: int, victims: list[int]) -> EntityRow:
    effects = call.rules.intervention_effects
    label = DISASTERS[args.kind].label
    event = await EntityRepository(call.session).create(
        EntityDraft(
            name=args.name,
            entity_type=EntityType.EVENT,
            description=args.description.strip(),
            stats=EventStats(severity=max(0, min(PERCENT, severity))),
            power_level=max(effects.disaster_event_power_min, min(effects.disaster_event_power_max, round(severity / effects.disaster_event_power_divisor))),
            origin=EntityOrigin.SON,
            birth_epoch=call.epoch,
            world_id=target.world_id,
            location_id=target.id if can_contain(target.entity_type, EntityType.EVENT) else target.location_id,
            creator_son_id=call.son.id,
            subtype=label.lower(),
            engine_kind=DISASTER_KINDS[args.kind],
            image_prompt=args.image_prompt,
            flags=[EntityFlag.DISASTER],
            split_title=False,
        )
    )
    bonds = BondRepository(call.session)
    for victim in [target.id, *victims]:
        if victim != event.id:
            await bonds.connect(BondDraft(event.id, victim, BondKind.CAUSED, call.epoch))
    return event


async def send_disaster(call: SonCall, args: DisasterInput) -> str:
    tools = call.rules.son_tools
    target = require_type(await require_canon(call.session, args.target_id), LOCATION_TYPES, SonResult.DISASTER_TARGET)
    await ensure_in_reach(call, target)
    if await NameRepository(call.session).is_taken(args.name):
        fail(SonResult.NAME_IN_USE)
    cost = share(call.rules.intervention_costs.disaster, tools.intervention_cost_pct) + target.power_level * tools.disaster_cost_per_power
    require_essence(call, cost)
    severity = max(
        tools.disaster_min_severity,
        min(PERCENT, round(tools.disaster_severity_base + call.son.might / tools.disaster_might_divisor + call.die(tools.disaster_die))),
    )
    impact = await apply_disaster(call.tick, target, args.kind, severity / tools.disaster_scale_divisor)
    event = await _disaster_event(call, args, target, severity, [entity.id for entity in impact.dead])
    await record_impact(call.tick, event, impact)
    await after_strike(call.tick, target, args.kind, severity, event, impact=impact)
    call.remember_creation(event.id)
    patron_id = await BondRepository(call.session).patron(target.id)
    if patron_id is not None and patron_id != call.son.id and await call.session.get(SonRow, patron_id) is not None:
        await shift_relation(call, patron_id, -tools.disaster_patron_relation)
    if target.creator_son_id is not None and target.creator_son_id != call.son.id:
        await shift_relation(call, target.creator_son_id, -tools.disaster_creator_relation)
    call.spend_essence(cost)
    call.target(target.id)
    joined = NOTE_SEPARATOR.join(impact.notes)
    await call.chronicle(
        ChronicleKind.DISASTER,
        lines.DISASTER,
        entity_ids=[target.id, event.id],
        son=call.son.name,
        disaster=DISASTERS[args.kind].label.lower(),
        target=target.name,
        name=event.name,
        reason=args.reason,
        notes=f" {joined}" if joined else "",
    )
    return result(SonResult.DISASTER_DONE, id=event.id, name=event.name, severity=severity, notes=joined)


async def transform(call: SonCall, args: TransformInput) -> str:
    tools = call.rules.son_tools
    entity = await require_canon(call.session, args.entity_id)
    await ensure_in_reach(call, entity)
    if entity.origin is EntityOrigin.CREATOR:
        fail(SonResult.CREATOR_WORK)
    new_name = " ".join(args.new_name.split()) if args.new_name else None
    renamed = new_name is not None and new_name.casefold() != entity.name.casefold()
    if renamed and new_name is not None and await NameRepository(call.session).is_taken(new_name, entity.id):
        fail(SonResult.NAME_IN_USE)
    cost = call.rules.costs.transform + tools.transform_cost_per_power * entity.power_level
    require_essence(call, cost)
    old_name, old_description = entity.name, entity.description
    if renamed and new_name is not None:
        await EntityRepository(call.session).rename(entity, new_name)
        await rewrite_name(call.session, entity.id, old_name, entity.name)
    if args.new_subtype:
        entity.subtype = await normalized_subtype(call.session, entity.entity_type, args.new_subtype) or entity.subtype
    entity.description = lines.TRANSFORM_NOTE.format(
        description=args.new_description.strip(), epoch=call.epoch, son=call.son.name, old=old_name, old_description=old_description[:EXCERPT]
    )
    await BondRepository(call.session).connect(BondDraft(call.son.id, entity.id, BondKind.CURSED, call.epoch, lines.TRANSFORM_BOND.format(reason=args.reason)))
    if entity.creator_son_id is not None and entity.creator_son_id != call.son.id:
        await shift_relation(call, entity.creator_son_id, -tools.transform_creator_relation)
    call.spend_essence(cost)
    call.target(entity.id)
    suffix = lines.RENAMED.format(new=entity.name) if renamed else ""
    await call.chronicle(ChronicleKind.CREATION, lines.TRANSFORM, entity_ids=[entity.id], son=call.son.name, old=old_name, renamed=suffix, reason=args.reason)
    return result(SonResult.TRANSFORMED)


async def destroy(call: SonCall, args: DestroyInput) -> str:
    tools = call.rules.son_tools
    entity = await require_canon(call.session, args.entity_id)
    await ensure_in_reach(call, entity)
    if entity.origin is EntityOrigin.CREATOR:
        fail(SonResult.CANNOT_DESTROY_CREATOR)
    cost = call.rules.costs.destroy + tools.destroy_cost_per_power * entity.power_level
    require_essence(call, cost)
    entities = EntityRepository(call.session)
    bonds = BondRepository(call.session)
    await entities.set_status(entity, EntityStatus.DESTROYED, call.epoch, lines.DESTROY_NOTE.format(epoch=call.epoch, son=call.son.name, reason=args.reason))
    touching: list[BondRow] = await bonds.touching(entity.id, [BondState.ACTIVE])
    for bond in touching:
        if bond.kind is not BondKind.INSIDE:
            await bonds.deactivate(bond, call.epoch, args.reason[:REASON_MAX])
    await entities.transfer_contents(entity, call.epoch)
    await bonds.connect(BondDraft(call.son.id, entity.id, BondKind.DESTROYED, call.epoch, args.reason))
    call.spend_essence(cost)
    if entity.creator_son_id is not None and entity.creator_son_id != call.son.id:
        await shift_relation(call, entity.creator_son_id, -tools.destroy_creator_relation)
    call.target(entity.id)
    await call.chronicle(ChronicleKind.CREATION, lines.DESTROY, entity_ids=[entity.id], son=call.son.name, name=entity.name, reason=args.reason)
    return result(SonResult.DESTROYED, name=entity.name)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    legendary = gate(Gate.LEGENDARY_TOOLS)
    return [
        ToolSpec(
            SonToolId.MIRACLE,
            son,
            MiracleInput,
            ToolMeta(ActionKind.MIRACLE, son_standard_action, essence_cost=lambda rules: miracle_cost(rules, 0), rarity_gate=gate(Gate.MIRACLE_TOOL)),
            miracle,
        ),
        ToolSpec(
            SonToolId.SEND_DISASTER,
            son,
            DisasterInput,
            ToolMeta(
                ActionKind.DISASTER,
                son_standard_action,
                essence_cost=lambda rules: share(rules.intervention_costs.disaster, rules.son_tools.intervention_cost_pct),
                rarity_gate=gate(Gate.RARE_TOOLS),
            ),
            send_disaster,
        ),
        ToolSpec(
            SonToolId.TRANSFORM,
            son,
            TransformInput,
            ToolMeta(ActionKind.TRANSFORM, son_standard_action, essence_cost=lambda rules: rules.costs.transform, rarity_gate=legendary),
            transform,
        ),
        ToolSpec(
            SonToolId.DESTROY,
            son,
            DestroyInput,
            ToolMeta(ActionKind.DESTROY, son_standard_action, essence_cost=lambda rules: rules.costs.destroy, rarity_gate=legendary),
            destroy,
        ),
    ]
