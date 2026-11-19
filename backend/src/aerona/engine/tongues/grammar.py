from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.tongues import COMPOUNDING, HEAD_FIRST, LOAN_RULES, NUMBER_COUNTS, ORDERS
from aerona.constants.units import PERCENT
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.culture import LanguageStandingRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.tongues import CASES_MAX, LanguageGrammarRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.tongues import MorphologyType, NumberSystem, WordOrder
from aerona.engine.context import TickContext
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat_or
from aerona.engine.tongues.sounds import contacts_of
from aerona.rules.registry import Rules

FEATURES = 7
CASES_SPAN = 10
CLASS_SPAN = 10
HONORIFIC_SPAN = 6


@dataclass
class GrammarTally:
    described: int = 0
    converged: int = 0


def drawn(seed: str, complexity: int) -> LanguageGrammarRow:
    rng = SeededRandom(RandomKey(0, 0, seed))
    morphology = rng.pick(list(MorphologyType))
    synthetic = morphology in COMPOUNDING or morphology is MorphologyType.FUSIONAL
    return LanguageGrammarRow(
        word_order=rng.pick(list(ORDERS)),
        morphology=morphology,
        cases=clamp_int(complexity // CASES_SPAN + (rng.integer(0, 4) if synthetic else 0), 0, CASES_MAX),
        noun_classes=rng.integer(0, 6),
        evidentiality=rng.chance(30),
        honorific_levels=rng.integer(0, 3),
        number_system=rng.pick(list(NumberSystem)),
        locked=[],
    )


async def grammar_of(session: AsyncSession, language_id: int, epoch: int = 0) -> LanguageGrammarRow | None:
    row = await session.get(LanguageGrammarRow, language_id)
    if row is not None:
        return row
    language = await session.get(EntityRow, language_id)
    if language is None or language.entity_type is not EntityType.LANGUAGE:
        return None
    profile = await session.get(LanguageProfileRow, language_id)
    parent = (
        await grammar_of(session, profile.parent_language_id, epoch) if profile is not None and profile.parent_language_id not in {None, language_id} else None
    )
    row = drawn(seed_of("grammar", language_id), stat_or(language, "complexity", PERCENT // 2))
    if parent is not None:
        for key in ("word_order", "morphology", "cases", "noun_classes", "evidentiality", "honorific_levels", "number_system"):
            setattr(row, key, getattr(parent, key))
        rng = SeededRandom(RandomKey(0, 0, seed_of("grammar.drift", language_id)))
        row.word_order = rng.pick(list(ORDERS)) if rng.chance(25) else row.word_order
    row.language_entity_id, row.updated_epoch = language_id, epoch
    session.add(row)
    await session.flush()
    return row


def distance(first: LanguageGrammarRow, second: LanguageGrammarRow) -> float:
    parts = (
        first.word_order is not second.word_order,
        first.morphology is not second.morphology,
        min(1.0, abs(first.cases - second.cases) / CASES_SPAN),
        min(1.0, abs(first.noun_classes - second.noun_classes) / CLASS_SPAN),
        first.evidentiality is not second.evidentiality,
        min(1.0, abs(first.honorific_levels - second.honorific_levels) / HONORIFIC_SPAN),
        abs(NUMBER_COUNTS[first.number_system] - NUMBER_COUNTS[second.number_system]) / max(NUMBER_COUNTS.values()),
    )
    return sum(float(part) for part in parts) / FEATURES


async def gap(session: AsyncSession, first: int | None, second: int | None) -> float:
    if first is None or second is None or first == second:
        return 0.0
    one, other = await grammar_of(session, first), await grammar_of(session, second)
    return distance(one, other) if one is not None and other is not None else 0.0


async def misread_factor(session: AsyncSession, rules: Rules, ours: set[int], theirs: set[int]) -> float:
    if not ours or not theirs or ours & theirs:
        return 1.0
    nearest = min([await gap(session, one, other) for one in sorted(ours) for other in sorted(theirs)])
    return 1 + nearest * rules.grammar.misread_pct / PERCENT


async def loan_factor(session: AsyncSession, rules: Rules, language_id: int) -> float:
    row = await grammar_of(session, language_id)
    key = LOAN_RULES[row.morphology] if row is not None else None
    return int(getattr(rules.grammar, key)) / PERCENT if key is not None else 1.0


async def head_first(session: AsyncSession, language_id: int | None) -> bool:
    row = await grammar_of(session, language_id) if language_id is not None else None
    return row is not None and HEAD_FIRST[row.word_order]


async def compounds(session: AsyncSession, language_id: int | None) -> bool:
    row = await grammar_of(session, language_id) if language_id is not None else None
    return row is not None and row.morphology in COMPOUNDING


async def simplify(session: AsyncSession, rules: Rules, language_id: int, epoch: int) -> LanguageGrammarRow | None:
    row = await grammar_of(session, language_id, epoch)
    if row is None:
        return None
    for key, value in (
        ("morphology", MorphologyType.ISOLATING),
        ("cases", rules.grammar.creole_cases),
        ("noun_classes", 0),
        ("number_system", NumberSystem.NONE),
        ("word_order", WordOrder.SVO),
    ):
        if key not in row.locked:
            setattr(row, key, value)
    row.updated_epoch = epoch
    return row


async def converge(ctx: TickContext, language: EntityRow, tally: GrammarTally) -> None:
    row = await grammar_of(ctx.session, language.id, ctx.epoch)
    contacts = await contacts_of(ctx, language.id)
    if row is None or not contacts or "word_order" in row.locked:
        return
    own = await ctx.session.get(LanguageStandingRow, language.id)
    floor = own.prestige if own is not None else 0
    standings = await ctx.session.scalars(
        select(LanguageStandingRow).where(LanguageStandingRow.language_entity_id.in_(sorted(contacts)), LanguageStandingRow.prestige > floor)
    )
    lead = max(standings, key=lambda item: (item.prestige, -item.language_entity_id), default=None)
    other = await grammar_of(ctx.session, lead.language_entity_id, ctx.epoch) if lead is not None else None
    if other is None or other.word_order is row.word_order:
        return
    if ctx.rng(f"grammar.converge.{language.id}.{ctx.epoch}").chance(ctx.rules.grammar.convergence_pct):
        row.word_order, row.updated_epoch = other.word_order, ctx.epoch
        tally.converged += 1


async def describe_grammars(ctx: TickContext, tally: GrammarTally) -> None:
    for language in await canon(ctx.session, [EntityType.LANGUAGE]):
        if held(language.id):
            continue
        if await ctx.session.get(LanguageGrammarRow, language.id) is None:
            await grammar_of(ctx.session, language.id, ctx.epoch)
            tally.described += 1
        await converge(ctx, language, tally)
    await ctx.session.flush()
