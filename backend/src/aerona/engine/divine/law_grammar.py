from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from sqlalchemy import select

from aerona.catalog.law_grammar import LEGACY_GRAMMAR, PRESET_TARGETS, ROW_TARGETS, Grammar, preset_of
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.concealment import HiddenTruthRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_grammar import LawExceptionRow, LawTheoryRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.made import MadeRealmRow
from aerona.db.tables.minds import MindProfileRow, MindStateRow
from aerona.db.tables.powers import PowerRow, PowerSourceRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import LawException, LawScope
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.law_grammar import LawCondition, LawExceptionKind, LawOperator, LawTarget
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.cosmos.placement import cosmography_of
from aerona.engine.notes import note
from aerona.engine.primitives.derivation import Origin, replace_derived, shaped_draft
from aerona.engine.primitives.knowledge import footprint
from aerona.engine.primitives.modifiers import ModifierDraft
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.stats import base_stat, has_stat, stat_or

ROW_CLASSES: Mapping[str, Any] = {
    "mind_profiles": MindProfileRow,
    "mind_states": MindStateRow,
    "powers": PowerRow,
    "power_sources": PowerSourceRow,
    "hidden_truths": HiddenTruthRow,
    "living_lines": LivingLineRow,
    "made_realm_profiles": MadeRealmRow,
}
FIELD_BOUNDS: Mapping[str, tuple[int, int]] = {"maker_bond": (-PERCENT, PERCENT)}
REASON = "modifier.natural_law.grammar"
THEORY_REASON = "modifier.natural_law.theory"
WORKS_KEY = "craft"
OPEN_FIELD = 100


def grammar_of(row: NaturalLawProfileRow) -> Grammar | None:
    if row.target is not None and row.operator is not None and row.key is not None:
        return Grammar(row.target, row.operator, row.key, row.value)
    return LEGACY_GRAMMAR[row.effect]


def fill_grammar(row: NaturalLawProfileRow) -> None:
    legacy = LEGACY_GRAMMAR[row.effect]
    if legacy is None:
        return
    current = preset_of(row.target, row.operator, row.key, row.value)
    if row.target is not None and current is row.effect:
        return
    for field in ("target", "operator", "key", "value"):
        if field not in row.locked:
            setattr(row, field, getattr(legacy, field))


def desired(operator: LawOperator, value: int, current: int, bound: bool) -> int:
    if operator is LawOperator.FORBID:
        return 0
    if operator is LawOperator.REQUIRE:
        return max(current, value)
    if operator is LawOperator.MULTIPLY:
        return round(current * value / PERCENT)
    if operator is LawOperator.INVERT:
        return OPEN_FIELD - current
    if operator is LawOperator.BIND_TO_CONDITION:
        return value if bound else OPEN_FIELD - value
    return value


async def at_war(ctx: TickContext, world_id: int | None) -> bool:
    found = select(WarRow.id).where(WarRow.status != WarStatus.ENDED)
    if world_id is not None:
        found = found.where(WarRow.world_id == world_id)
    return await ctx.session.scalar(found.limit(1)) is not None


async def author_worshipped(ctx: TickContext, row: NaturalLawProfileRow, world_id: int | None) -> bool:
    if row.author_node_id is None:
        return False
    found = select(BondRow.id).where(BondRow.target_node_id == row.author_node_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    if world_id is not None:
        found = found.where(BondRow.source_node_id.in_(select(EntityRow.id).where(EntityRow.world_id == world_id)))
    return await ctx.session.scalar(found.limit(1)) is not None


async def doom_rising(ctx: TickContext) -> bool:
    cosmos = await ctx.session.scalar(select(CosmosRow).limit(1))
    return cosmos is not None and cosmos.doom_clock * 2 >= ctx.rules.balance.apocalypse_threshold


Check = Callable[[TickContext, NaturalLawProfileRow, int | None], Awaitable[bool]]


async def always(_ctx: TickContext, _row: NaturalLawProfileRow, _world: int | None) -> bool:
    return True


async def warring(ctx: TickContext, _row: NaturalLawProfileRow, world: int | None) -> bool:
    return await at_war(ctx, world)


async def peaceful(ctx: TickContext, _row: NaturalLawProfileRow, world: int | None) -> bool:
    return not await at_war(ctx, world)


async def cold(ctx: TickContext, _row: NaturalLawProfileRow, _world: int | None) -> bool:
    return ctx.epoch % 4 == 3


async def dooming(ctx: TickContext, _row: NaturalLawProfileRow, _world: int | None) -> bool:
    return await doom_rising(ctx)


async def worshipped(ctx: TickContext, row: NaturalLawProfileRow, world: int | None) -> bool:
    return await author_worshipped(ctx, row, world)


async def forgotten(ctx: TickContext, row: NaturalLawProfileRow, world: int | None) -> bool:
    return not await author_worshipped(ctx, row, world)


CONDITIONS: Mapping[LawCondition, Check] = total(
    LawCondition,
    {
        LawCondition.ALWAYS: always,
        LawCondition.AT_WAR: warring,
        LawCondition.AT_PEACE: peaceful,
        LawCondition.COLD_SEASON: cold,
        LawCondition.DOOM_RISING: dooming,
        LawCondition.AUTHOR_WORSHIPPED: worshipped,
        LawCondition.AUTHOR_FORGOTTEN: forgotten,
    },
)


async def holds(ctx: TickContext, row: NaturalLawProfileRow, world_id: int | None) -> bool:
    return await CONDITIONS[row.condition](ctx, row, world_id)


async def bonded_to(ctx: TickContext, entity_id: int, node_id: int | None) -> bool:
    if node_id is None:
        return False
    found = select(BondRow.id).where(
        BondRow.source_node_id == entity_id,
        BondRow.target_node_id == node_id,
        BondRow.kind.in_([BondKind.MEMBER_OF, BondKind.SWORN_KIN]),
        BondRow.state == BondState.ACTIVE,
    )
    return await ctx.session.scalar(found.limit(1)) is not None


async def spared(ctx: TickContext, law_id: int, entity: EntityRow) -> bool:
    for row in list(await ctx.session.scalars(select(LawExceptionRow).where(LawExceptionRow.law_entity_id == law_id))):
        if await SPARES[row.kind](ctx, row, entity):
            return True
    return False


async def spare_person(_ctx: TickContext, row: LawExceptionRow, entity: EntityRow) -> bool:
    return row.node_id == entity.id


async def spare_line(ctx: TickContext, row: LawExceptionRow, entity: EntityRow) -> bool:
    return await bonded_to(ctx, entity.id, row.node_id)


async def spare_people(ctx: TickContext, row: LawExceptionRow, entity: EntityRow) -> bool:
    return row.node_id in {entity.id, entity.affiliated_entity_id} or await bonded_to(ctx, entity.id, row.node_id)


async def spare_kind(_ctx: TickContext, row: LawExceptionRow, entity: EntityRow) -> bool:
    return row.entity_type is entity.entity_type


async def spare_place(_ctx: TickContext, row: LawExceptionRow, entity: EntityRow) -> bool:
    return row.node_id is not None and row.node_id in {entity.id, entity.location_id}


SPARES: Mapping[LawExceptionKind, Callable[[TickContext, LawExceptionRow, EntityRow], Awaitable[bool]]] = total(
    LawExceptionKind,
    {
        LawExceptionKind.PERSON: spare_person,
        LawExceptionKind.LINE: spare_line,
        LawExceptionKind.PEOPLE: spare_people,
        LawExceptionKind.KIND: spare_kind,
        LawExceptionKind.PLACE: spare_place,
    },
)


async def reach(ctx: TickContext, row: NaturalLawProfileRow) -> set[int]:
    ladder = await cosmography_of(ctx.session)
    worlds = list(await ctx.session.scalars(select(WorldRow.id)))
    return footprint(ladder, worlds, row)


async def stat_drafts(ctx: TickContext, row: NaturalLawProfileRow, grammar: Grammar, worlds: set[int]) -> list[ModifierDraft]:
    if row.scope is LawScope.REGION and row.region_entity_id is not None:
        scope = (EntityRow.location_id == row.region_entity_id) | (EntityRow.id == row.region_entity_id)
    else:
        scope = EntityRow.world_id.in_(sorted(worlds)) & (EntityRow.entity_type != EntityType.MORTAL)
    drafts: list[ModifierDraft] = []
    origin = Origin(ModifierSource.LAW_GRAMMAR, REASON, ctx.epoch, source_node_id=row.law_entity_id, group=f"law_grammar.{row.law_entity_id}")
    for entity in list(await ctx.session.scalars(select(EntityRow).where(scope, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id))):
        if not has_stat(entity, grammar.key) or held(entity.id) or await spared(ctx, row.law_entity_id, entity):
            continue
        bound = await holds(ctx, row, entity.world_id)
        if not bound and grammar.operator is not LawOperator.BIND_TO_CONDITION:
            continue
        current = base_stat(entity, grammar.key) or 0
        draft = shaped_draft(
            entity, grammar.key, ModifierOp.ADD, desired(grammar.operator, grammar.value, current, bound) - current, origin, factor=row.strength / PERCENT
        )
        if draft is not None:
            drafts.append(draft)
    return drafts


async def holder_world(ctx: TickContext, holder: int | None) -> int | None:
    if holder is None:
        return None
    if await ctx.session.get(WorldRow, holder) is not None:
        return holder
    entity = await ctx.session.get(EntityRow, holder)
    return entity.world_id if entity is not None else None


async def pull_rows(ctx: TickContext, row: NaturalLawProfileRow, grammar: Grammar, worlds: set[int]) -> int:
    spec = ROW_TARGETS[grammar.target]
    if spec is None or grammar.key not in spec.fields:
        return 0
    table = ROW_CLASSES[spec.table]
    low, high = FIELD_BOUNDS.get(grammar.key, (spec.low, spec.high))
    moved = 0
    for item in list(await ctx.session.scalars(select(table))):
        holder = getattr(item, spec.holder)
        world = await holder_world(ctx, holder)
        if world not in worlds or grammar.key in (item.locked or []) or (holder is not None and held(holder)):
            continue
        entity = await ctx.session.get(EntityRow, holder) if holder is not None else None
        if entity is not None and await spared(ctx, row.law_entity_id, entity):
            continue
        bound = await holds(ctx, row, world)
        if not bound and grammar.operator is not LawOperator.BIND_TO_CONDITION:
            continue
        current = int(getattr(item, grammar.key))
        goal = desired(grammar.operator, grammar.value, current, bound)
        setattr(item, grammar.key, clamp_int(current + round((goal - current) * row.strength / PERCENT), low, high))
        moved += 1
    return moved


def signature(row: NaturalLawProfileRow) -> tuple[LawTarget, str] | None:
    grammar = grammar_of(row)
    if grammar is None or grammar.target in PRESET_TARGETS:
        return None
    return grammar.target, grammar.key


def contrary(first: NaturalLawProfileRow, second: NaturalLawProfileRow) -> bool:
    return (first.operator, first.value) != (second.operator, second.value)


async def feud(ctx: TickContext, first: NaturalLawProfileRow, second: NaturalLawProfileRow) -> None:
    if first.author_node_id is None or second.author_node_id is None or first.author_node_id == second.author_node_id:
        return
    one, other = await ctx.session.get(SonRow, first.author_node_id), await ctx.session.get(SonRow, second.author_node_id)
    if one is not None and other is not None and not held(one.id, other.id):
        await SonRepository(ctx.session).change_relation(one.id, other.id, -ctx.rules.natural_laws.feud_relation, "their laws contested")


async def contest_grammar(ctx: TickContext, rows: list[NaturalLawProfileRow], reaches: Mapping[int, set[int]]) -> int:
    margin = ctx.rules.natural_laws.stalemate_margin
    broken = 0
    for index, first in enumerate(rows):
        for second in rows[index + 1 :]:
            if signature(first) is None or signature(first) != signature(second) or not contrary(first, second):
                continue
            if not reaches.get(first.law_entity_id, set()) & reaches.get(second.law_entity_id, set()):
                continue
            await feud(ctx, first, second)
            if abs(first.strength - second.strength) <= margin:
                for row in (first, second):
                    if "contested" not in row.locked:
                        row.contested = True
                continue
            loser = second if first.strength > second.strength else first
            if "suspended" not in loser.locked:
                loser.suspended = True
                broken += 1
                await note(
                    ctx,
                    "A natural law gave way to a stronger one and was suspended where they met.",
                    key="law.natural_broken",
                    ids=[loser.law_entity_id],
                    kind=ChronicleKind.COSMIC_LAW,
                )
    return broken


async def adopt(ctx: TickContext, row: NaturalLawProfileRow, worlds: set[int]) -> None:
    author = await ctx.session.get(SonRow, row.author_node_id) if row.author_node_id is not None else None
    if author is not None and author.status is not SonStatus.DEAD:
        return
    if row.author_node_id is not None and author is None:
        return
    if "author_node_id" in row.locked or not ctx.rng(f"law.adopt.{row.law_entity_id}.{ctx.epoch}").chance(ctx.rules.natural_laws.adopt_pct):
        return
    heir = await ctx.session.scalar(
        select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id.in_(sorted(worlds))).order_by(SonRow.essence.desc(), SonRow.id).limit(1)
    )
    if heir is not None and not held(heir.id):
        row.author_node_id = heir.id
        await note(ctx, f"{heir.name} took up a law no one kept.", key="law.natural_set", ids=[row.law_entity_id, heir.id], kind=ChronicleKind.COSMIC_LAW)


async def keep_condition(ctx: TickContext, row: NaturalLawProfileRow, worlds: set[int]) -> None:
    grammar = grammar_of(row)
    if grammar is None or grammar.target not in PRESET_TARGETS or "suspended" in row.locked:
        return
    home = row.world_id if row.world_id is not None else (min(worlds) if worlds else None)
    if not await holds(ctx, row, home):
        row.suspended = True


async def expire(ctx: TickContext, row: NaturalLawProfileRow) -> bool:
    if row.until_epoch is None or ctx.epoch < row.until_epoch:
        return False
    law = await ctx.session.get(EntityRow, row.law_entity_id)
    if law is None or law.status is not EntityStatus.CANON or held(law.id):
        return False
    law.status, law.end_epoch = EntityStatus.DESTROYED, ctx.epoch
    await note(ctx, f"{law.name} ran its course and ended.", key="law.natural_broken", ids=[law.id], kind=ChronicleKind.COSMIC_LAW)
    return True


def true_value(row: NaturalLawProfileRow) -> tuple[LawOperator, int] | None:
    grammar = grammar_of(row)
    return (grammar.operator, grammar.value) if grammar is not None else None


def gap_of(theory: LawTheoryRow, truth: tuple[LawOperator, int]) -> int:
    return min(PERCENT, abs(theory.believed_value - truth[1]) + (PERCENT // 2 if theory.believed_operator is not truth[0] else 0))


async def theorise(ctx: TickContext, rows: list[NaturalLawProfileRow], reaches: Mapping[int, set[int]]) -> list[ModifierDraft]:
    table = ctx.rules.natural_laws
    drafts: list[ModifierDraft] = []
    peoples = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    for people in peoples:
        if held(people.id):
            continue
        for row in rows:
            truth = true_value(row)
            if truth is None or people.world_id not in reaches.get(row.law_entity_id, set()):
                continue
            theory = await ctx.session.scalar(
                select(LawTheoryRow).where(LawTheoryRow.holder_node_id == people.id, LawTheoryRow.law_entity_id == row.law_entity_id)
            )
            rng = ctx.rng(f"law.theory.{people.id}.{row.law_entity_id}.{ctx.epoch}")
            if theory is None:
                offset = round(rng.uniform(-table.theory_offset, table.theory_offset))
                operator = truth[0] if rng.chance(stat_or(people, WORKS_KEY, 0)) else rng.pick(list(LawOperator))
                theory = LawTheoryRow(
                    holder_node_id=people.id,
                    law_entity_id=row.law_entity_id,
                    believed_operator=operator,
                    believed_value=max(0, truth[1] + offset),
                    updated_epoch=ctx.epoch,
                    locked=[],
                )
                ctx.session.add(theory)
            learn = max(1, table.theory_learn * stat_or(people, WORKS_KEY, PERCENT // 2) // PERCENT)
            if "believed_value" not in theory.locked:
                step = max(-learn, min(learn, truth[1] - theory.believed_value))
                theory.believed_value += step
            if "believed_operator" not in theory.locked and theory.believed_operator is not truth[0] and rng.chance(theory.confidence):
                theory.believed_operator = truth[0]
            if "confidence" not in theory.locked:
                theory.confidence = clamp_percent(theory.confidence + table.theory_confidence)
            if "adapted_epochs" not in theory.locked:
                theory.adapted_epochs += 1
            theory.updated_epoch = ctx.epoch
            origin = Origin(ModifierSource.LAW_GRAMMAR, THEORY_REASON, ctx.epoch, source_node_id=row.law_entity_id, group=f"law_theory.{row.law_entity_id}")
            shift = table.adapt_bonus if theory.adapted_epochs >= table.adapt_epochs else -gap_of(theory, truth) * table.reliability_pct // PERCENT
            draft = shaped_draft(people, WORKS_KEY, ModifierOp.ADD, shift, origin)
            if draft is not None:
                drafts.append(draft)
    return drafts


async def tend_grammar(ctx: TickContext, rows: list[NaturalLawProfileRow]) -> int:
    reaches = {row.law_entity_id: await reach(ctx, row) for row in rows}
    live: list[NaturalLawProfileRow] = []
    for row in rows:
        if "suspended" not in row.locked:
            row.suspended = False
        if await expire(ctx, row):
            continue
        fill_grammar(row)
        await adopt(ctx, row, reaches[row.law_entity_id])
        await keep_condition(ctx, row, reaches[row.law_entity_id])
        live.append(row)
    await contest_grammar(ctx, live, reaches)
    drafts: list[ModifierDraft] = []
    moved = 0
    for row in live:
        grammar = grammar_of(row)
        if grammar is None or row.suspended or row.contested or row.strength <= 0 or held(row.law_entity_id):
            continue
        if grammar.target is LawTarget.STAT:
            drafts.extend(await stat_drafts(ctx, row, grammar, reaches[row.law_entity_id]))
        elif ROW_TARGETS[grammar.target] is not None:
            moved += await pull_rows(ctx, row, grammar, reaches[row.law_entity_id])
    drafts.extend(await theorise(ctx, [row for row in live if not row.suspended and row.strength > 0], reaches))
    await replace_grammar_modifiers(ctx, drafts)
    return moved


async def replace_grammar_modifiers(ctx: TickContext, drafts: list[ModifierDraft]) -> None:
    await replace_derived(ctx.session, {ModifierSource.LAW_GRAMMAR}, drafts)


def refusal(target: LawTarget, operator: LawOperator, key: str, value: int) -> str | None:
    if target in PRESET_TARGETS:
        if preset_of(target, operator, key, value) is not None:
            return None
        fits = sorted({f"{grammar.operator.value} {grammar.key}" for grammar in LEGACY_GRAMMAR.values() if grammar is not None and grammar.target is target})
        return f"A law over {spoken(target)} takes one of: {'; '.join(fits)}."
    spec = ROW_TARGETS[target]
    if spec is not None and key not in spec.fields:
        return f"A law over {spoken(target)} works on one of: {', '.join(spec.fields)}."
    return None if key.strip() else "Name the field the law works on."


async def set_grammar(
    ctx: TickContext, law: EntityRow, grammar: Grammar, condition: LawCondition, until_epoch: int | None, *, hold: bool
) -> NaturalLawProfileRow:
    reason = refusal(grammar.target, grammar.operator, grammar.key, grammar.value)
    if reason is not None:
        raise ValidationFailedError(reason)
    row = await ctx.session.get(NaturalLawProfileRow, law.id)
    if row is None:
        table = ctx.rules.natural_laws
        row = NaturalLawProfileRow(
            law_entity_id=law.id,
            effect=NaturalLaw.NONE,
            scope=LawScope.WORLD,
            world_id=law.world_id,
            strength=table.start_strength,
            stability=table.start_stability,
            author_node_id=law.creator_son_id,
            exception=LawException.NONE,
            contested=False,
            updated_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(row)
    preset = preset_of(grammar.target, grammar.operator, grammar.key, grammar.value)
    law.natural_law = preset if preset is not None else NaturalLaw.NONE
    row.effect = law.natural_law
    row.target, row.operator, row.key, row.value = grammar.target, grammar.operator, grammar.key, grammar.value
    row.condition, row.until_epoch, row.updated_epoch = condition, until_epoch, ctx.epoch
    if hold:
        row.locked = sorted({*row.locked, "target", "operator", "key", "value", "condition"})
    await ctx.session.flush()
    return row
