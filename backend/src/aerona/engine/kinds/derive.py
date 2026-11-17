from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import select

from aerona.catalog.commodities import COMMODITIES
from aerona.constants.units import PERCENT
from aerona.db.kind_concepts.registry import CONCEPTS
from aerona.db.kind_concepts.spec import ConceptSpec
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kinds import GoodKindRow, KindHoldingRow, KindRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kinds import KindConcept, KindSpread, KindStance
from aerona.domain.enums.loops import BalanceLoop
from aerona.engine.context import TickContext
from aerona.engine.demography.prices import market_index
from aerona.engine.kinds.acts import filled
from aerona.engine.kinds.life import CARRIED
from aerona.engine.loops.delay import lagged
from aerona.engine.notes import note
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.language.generator import NameKind

Tied = Callable[[TickContext, KindRow], Awaitable[set[CommodityKind]]]
Swap = Callable[[TickContext, KindRow, KindRow, CommodityKind, CommodityKind], Awaitable[None]]


@dataclass
class DeriveTally:
    substituted: int = 0
    fused: int = 0
    prestige_moved: int = 0


async def good_ties(_ctx: TickContext, kind: KindRow) -> set[CommodityKind]:
    stocked = kind.stocked_as if isinstance(kind, GoodKindRow) else None
    return {stocked} if stocked is not None else set()


async def good_swap(_ctx: TickContext, _old: KindRow, new: KindRow, _scarce: CommodityKind, plenty: CommodityKind) -> None:
    if isinstance(new, GoodKindRow):
        new.stocked_as = plenty


TIES: Mapping[KindConcept, tuple[Tied, Swap]] = {KindConcept.GOOD: (good_ties, good_swap)}
OWN_DERIVATION = frozenset({KindConcept.DISH, KindConcept.DRINK, KindConcept.CUISINE})


PRICES = "kind_prices"


async def prices_of(ctx: TickContext, holder_id: int) -> dict[CommodityKind, int]:
    cache: dict[int, dict[CommodityKind, int]] = ctx.session.info.setdefault(PRICES, {})
    if holder_id not in cache:
        cache[holder_id] = await read_prices(ctx, holder_id)
    return cache[holder_id]


async def read_prices(ctx: TickContext, holder_id: int) -> dict[CommodityKind, int]:
    holder = await ctx.session.get(EntityRow, holder_id)
    if holder is None:
        return {}
    towns = [holder.id] if holder.entity_type is EntityType.SETTLEMENT else await towns_of_people(ctx.session, holder.id)
    found: dict[CommodityKind, int] = {}
    for town in towns:
        for commodity, index in (await market_index(ctx.session, town)).items():
            found[commodity] = max(found.get(commodity, 0), index)
    return found


def plentiful(prices: Mapping[CommodityKind, int], scarce: CommodityKind) -> CommodityKind | None:
    family = COMMODITIES[scarce].family
    options = [kind for kind, index in prices.items() if kind is not scarce and COMMODITIES[kind].family is family and index < prices[scarce]]
    return min(options, key=lambda kind: (prices[kind], kind.value), default=None)


def copied(spec: ConceptSpec, source: KindRow, target: KindRow) -> None:
    for item in spec.properties:
        setattr(target, item.column, getattr(source, item.column))


async def derived(ctx: TickContext, spec: ConceptSpec, source: KindRow, holder_id: int, salt: str) -> KindRow | None:
    name = await Namer(ctx.session, ctx.rules).from_speaker(holder_id, seed_of(salt, spec.concept.value, source.id, holder_id, ctx.epoch), NameKind.GENERAL)
    if name is None:
        return None
    row = spec.table(name=name, category=spec.category(source.category_key()), world_id=source.world_id, origin_node_id=holder_id)
    copied(spec, source, row)
    filled(spec, row)
    row.derived_from_id = source.id
    row.created_epoch = ctx.epoch
    row.locked = []
    ctx.session.add(row)
    await ctx.session.flush()
    ctx.session.add(
        KindHoldingRow(
            concept=spec.concept,
            kind_id=row.id,
            holder_node_id=holder_id,
            stance=KindStance.MAKES,
            strength=ctx.rules.kinds.founding_strength,
            spread=KindSpread.INVENTED,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    await ctx.session.flush()
    return row


def lowered(row: KindRow, column: str, pct: int) -> None:
    value = getattr(row, column, None)
    if isinstance(value, int) and column not in row.locked:
        setattr(row, column, max(0, value * (PERCENT - pct) // PERCENT))


async def substitute(ctx: TickContext, holding: KindHoldingRow, tally: DeriveTally) -> None:
    table = ctx.rules.kinds
    ties = TIES.get(holding.concept)
    spec = CONCEPTS.get(holding.concept)
    if ties is None or spec is None:
        return
    kind = await ctx.session.get(spec.table, holding.kind_id)
    if kind is None or kind.retired:
        return
    tied, swap = ties
    prices = await prices_of(ctx, holding.holder_node_id)
    scarce = max((item for item in await tied(ctx, kind) if item in prices), key=lambda item: prices[item], default=None)
    if scarce is None:
        return
    felt = await lagged(ctx, BalanceLoop.KIND_SUBSTITUTION, holding.holder_node_id, prices[scarce], subject=kind.id)
    if felt < table.scarcity_index:
        return
    plenty = plentiful(prices, scarce)
    if plenty is None or not ctx.rng(seed_of("kind.substitute", holding.id, ctx.epoch)).chance(table.substitution_pct):
        return
    row = await derived(ctx, spec, kind, holding.holder_node_id, "kind.substitute.name")
    if row is None:
        return
    await swap(ctx, kind, row, scarce, plenty)
    lowered(row, "base_value", table.substitute_value_pct)
    lowered(row, "prestige", table.substitute_value_pct)
    if "strength" not in holding.locked:
        holding.strength = clamp_int(holding.strength - table.substitution_fade, 0, PERCENT)
    tally.substituted += 1
    await note(
        ctx,
        f"{row.name} came into use in place of {kind.name} while {COMMODITIES[scarce].label.lower()} stayed dear.",
        key="kinds.substituted",
        ids=[holding.holder_node_id],
    )


def averaged(spec: ConceptSpec, first: KindRow, second: KindRow, target: KindRow) -> None:
    for item in spec.properties:
        one, other = getattr(first, item.column), getattr(second, item.column)
        if item.options is None and isinstance(one, int) and isinstance(other, int):
            setattr(target, item.column, (one + other) // 2)


async def fuse(ctx: TickContext, holder_id: int, holdings: list[KindHoldingRow], tally: DeriveTally) -> None:
    table = ctx.rules.kinds
    strong = [row for row in holdings if row.stance in CARRIED and row.strength >= table.fusion_strength]
    by_concept: dict[KindConcept, list[tuple[KindHoldingRow, KindRow]]] = {}
    for holding in strong:
        if holding.concept in OWN_DERIVATION:
            continue
        spec = CONCEPTS.get(holding.concept)
        kind = await ctx.session.get(spec.table, holding.kind_id) if spec is not None else None
        if kind is not None and not kind.retired:
            by_concept.setdefault(holding.concept, []).append((holding, kind))
    for concept, pairs in sorted(by_concept.items()):
        spec = CONCEPTS[concept]
        for index, (first_holding, first) in enumerate(pairs):
            match = next(
                (
                    (other_holding, other)
                    for other_holding, other in pairs[index + 1 :]
                    if other.category_key() == first.category_key() and other.origin_node_id != first.origin_node_id and other.derived_from_id != first.id
                ),
                None,
            )
            if match is None:
                continue
            if not ctx.rng(seed_of("kind.fuse", holder_id, first.id, match[1].id, ctx.epoch)).chance(table.fusion_pct):
                continue
            stronger = first if first_holding.strength >= match[0].strength else match[1]
            weaker = match[1] if stronger is first else first
            row = await derived(ctx, spec, stronger, holder_id, "kind.fuse.name")
            if row is None:
                return
            averaged(spec, stronger, weaker, row)
            tally.fused += 1
            await note(ctx, f"{row.name} grew out of {stronger.name} and {weaker.name}.", key="kinds.fused", ids=[holder_id])
            return


async def tend_prestige(ctx: TickContext, tally: DeriveTally) -> None:
    table = ctx.rules.kinds
    counts: dict[tuple[KindConcept, int], int] = {}
    for concept, kind_id in await ctx.session.execute(select(KindHoldingRow.concept, KindHoldingRow.kind_id).where(KindHoldingRow.stance.in_(sorted(CARRIED)))):
        counts[concept, kind_id] = counts.get((concept, kind_id), 0) + 1
    for concept, spec in CONCEPTS.items():
        if "prestige" not in {item.column for item in spec.properties}:
            continue
        for kind in list(await ctx.session.scalars(select(spec.table).where(spec.table.retired.is_(False)).order_by(spec.table.id))):
            prestige = getattr(kind, "prestige", None)
            if not isinstance(prestige, int) or "prestige" in kind.locked or (kind.origin_node_id is not None and held(kind.origin_node_id)):
                continue
            seen = await lagged(ctx, BalanceLoop.KIND_PRESTIGE, kind.origin_node_id, counts.get((concept, kind.id), 0), subject=kind.id)
            shift = -table.prestige_fade if seen >= table.prestige_saturation else table.prestige_gain * seen // table.prestige_saturation
            if shift:
                cast(Any, kind).prestige = clamp_int(prestige + shift, 0, PERCENT)
                tally.prestige_moved += 1


async def derive_kinds(ctx: TickContext) -> DeriveTally:
    tally = DeriveTally()
    await tend_prestige(ctx, tally)
    holdings = [row for row in await ctx.session.scalars(select(KindHoldingRow).order_by(KindHoldingRow.id)) if not held(row.holder_node_id)]
    by_holder: dict[int, list[KindHoldingRow]] = {}
    for holding in holdings:
        by_holder.setdefault(holding.holder_node_id, []).append(holding)
        if holding.stance in CARRIED:
            await substitute(ctx, holding, tally)
    for holder_id, rows in sorted(by_holder.items()):
        await fuse(ctx, holder_id, rows, tally)
    await ctx.session.flush()
    return tally
