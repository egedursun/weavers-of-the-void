from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.kinds import CARRIED_STANCES, KindConcept, KindSpread, KindStance
from aerona.engine.context import TickContext
from aerona.engine.crafts.games import neighbours
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds

CARRIED = CARRIED_STANCES


@dataclass
class KindTally:
    spread: int = 0
    faded: int = 0
    retired: int = 0


@dataclass
class SpreadBook:
    holders: dict[tuple[KindConcept, int], set[int]] = field(default_factory=dict)
    reach: dict[int, list[tuple[int, KindSpread]]] = field(default_factory=dict)


async def contacts(ctx: TickContext, holder_id: int) -> list[tuple[int, KindSpread]]:
    found = {target: KindSpread.CONTACT for target in await neighbours(ctx, holder_id)}
    for bond in await active_bonds(ctx.session, [BondKind.TRADES_WITH], sources=[holder_id]):
        found[bond.target_node_id] = KindSpread.TRADE
    return sorted(found.items())


async def kind_row(ctx: TickContext, concept: KindConcept, kind_id: int) -> object | None:
    return await ctx.session.get(CONCEPTS[concept].table, kind_id)


async def reach_of(ctx: TickContext, book: SpreadBook, holder_id: int) -> list[tuple[int, KindSpread]]:
    found = book.reach.get(holder_id)
    if found is None:
        found = await contacts(ctx, holder_id)
        book.reach[holder_id] = found
    return found


async def load_kinds(ctx: TickContext, holdings: list[KindHoldingRow]) -> None:
    wanted: dict[KindConcept, set[int]] = {}
    for row in holdings:
        wanted.setdefault(row.concept, set()).add(row.kind_id)
    for concept, ids in wanted.items():
        spec = CONCEPTS.get(concept)
        if spec is not None:
            list(await ctx.session.scalars(select(spec.table).where(spec.table.id.in_(sorted(ids)))))


def prestige_of(row: object) -> int:
    value = getattr(row, "prestige", None)
    return value if isinstance(value, int) else 0


async def spread_holding(ctx: TickContext, book: SpreadBook, row: KindHoldingRow, kind: object, tally: KindTally) -> None:
    table = ctx.rules.kinds
    chance = table.spread_pct + prestige_of(kind) * table.prestige_spread_pct // PERCENT
    rng = ctx.rng(seed_of("kind.spread", row.concept.value, row.kind_id, row.holder_node_id, ctx.epoch))
    if not rng.chance(clamp_int(chance * row.strength // PERCENT, 0, PERCENT)):
        return
    known = book.holders.setdefault((row.concept, row.kind_id), set())
    targets = [(target, how) for target, how in await reach_of(ctx, book, row.holder_node_id) if target not in known and not held(target)]
    if not targets:
        return
    target, how = rng.pick(targets)
    known.add(target)
    ctx.session.add(
        KindHoldingRow(
            concept=row.concept,
            kind_id=row.kind_id,
            holder_node_id=target,
            stance=KindStance.USES,
            strength=table.adoption_strength,
            spread=how,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    tally.spread += 1


def fade(ctx: TickContext, row: KindHoldingRow, kind: object, tally: KindTally) -> None:
    if "strength" in row.locked or row.stance not in CARRIED:
        return
    table = ctx.rules.kinds
    gain = table.novelty_gain if ctx.epoch - row.since_epoch < table.novelty_epochs else -table.novelty_fade
    row.strength = clamp_int(row.strength + gain + prestige_of(kind) * table.prestige_hold_pct // PERCENT, 0, PERCENT)
    if gain < 0:
        tally.faded += 1


async def retire_unused(ctx: TickContext, tally: KindTally) -> None:
    held_kinds = {(concept, kind_id) for concept, kind_id in await ctx.session.execute(select(KindHoldingRow.concept, KindHoldingRow.kind_id))}
    for concept, spec in CONCEPTS.items():
        for kind in list(await ctx.session.scalars(select(spec.table).where(spec.table.retired.is_(False)))):
            if kind.built_in or "retired" in kind.locked or (concept, kind.id) in held_kinds:
                continue
            if ctx.epoch - kind.created_epoch >= ctx.rules.kinds.retire_epochs:
                kind.retired = True
                tally.retired += 1


async def keep_kinds(ctx: TickContext) -> KindTally:
    tally = KindTally()
    holdings = list(await ctx.session.scalars(select(KindHoldingRow).order_by(KindHoldingRow.id)))
    book = SpreadBook()
    for row in holdings:
        book.holders.setdefault((row.concept, row.kind_id), set()).add(row.holder_node_id)
    await load_kinds(ctx, holdings)
    with ctx.session.no_autoflush:
        for row in holdings:
            if held(row.holder_node_id):
                continue
            kind = await kind_row(ctx, row.concept, row.kind_id)
            if kind is None or getattr(kind, "retired", False):
                continue
            fade(ctx, row, kind, tally)
            if row.stance in CARRIED:
                await spread_holding(ctx, book, row, kind, tally)
    await ctx.session.flush()
    for row in holdings:
        if row.strength == 0 and not held(row.holder_node_id) and "strength" not in row.locked:
            await ctx.session.delete(row)
    await retire_unused(ctx, tally)
    await ctx.session.flush()
    return tally
