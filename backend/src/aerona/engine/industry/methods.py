from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.catalog.eras import TECHNIQUE_ERAS
from aerona.catalog.methods import (
    ALWAYS_PRACTISED,
    EXTRACTION_PROCESS,
    HERD_PROCESSES,
    METHODS,
    PROCESS_JOB,
    PROCESS_METHODS,
    PROCESS_OUTPUT,
    PROCESS_WORKSHOP,
    STEP_PROCESS,
    MethodSpec,
    default_method,
)
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.read_memo import memoized
from aerona.db.record_context import Term
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyTenetRow
from aerona.db.tables.demography import LabourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionGoalRow, FactionProfileRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import IdeologyTenet, Technique
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, ExtractionKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.environment import CoastKind, RiverClass, TemperatureBand
from aerona.domain.enums.faction import FactionGoalKind, FactionKind
from aerona.domain.enums.industry import EnergyKind, MethodKind, ProcessKind
from aerona.domain.enums.loops import BalanceLoop
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.agrarian.book import method_lift
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.eras.effects import era_order, world_start
from aerona.engine.industry.energy import available
from aerona.engine.industry.quality import premium
from aerona.engine.intrigue.beliefs import BeliefView, price_key
from aerona.engine.loops.delay import lagged
from aerona.engine.mind.book import values_for
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

TENTH = 10
CELLAR_LEVEL = 2
CELLAR_METHODS = frozenset({MethodKind.ICING, MethodKind.CAVE_AGEING})
CELLARS = (WorkshopKind.WAREHOUSE, WorkshopKind.GRANARY)
INTENSIVE = frozenset({MethodKind.IRRIGATED_TERRACES, MethodKind.CROP_ROTATION})


@dataclass
class MethodTally:
    chosen: int = 0
    changed: int = 0
    displaced: int = 0
    resisted: int = 0
    changes: dict[str, int] = field(default_factory=dict)


async def feed(ctx: TickContext, community_id: int, spec: MethodSpec, units: int) -> float:
    if not spec.inputs or units <= 0:
        return 1.0
    ledger = goods_of(ctx.session, ctx.epoch)
    wanted = {commodity: -(-units * per // TENTH) for commodity, per, _ in spec.inputs}
    stocked = {commodity: await holding(ctx.session, community_id, commodity, material) for commodity, _, material in spec.inputs}
    share = min(1.0, *(stocked[commodity] / need for commodity, need in wanted.items() if need > 0))
    for commodity, _, material in spec.inputs:
        take = round_half_up(wanted[commodity] * share)
        if take > 0:
            await ledger.take(community_id, commodity, take, GoodsFlow.INPUT, material=material)
    return share


@memoized(IdeologyAdherentRow, IdeologyTenetRow)
async def nature_revering(session: AsyncSession) -> frozenset[int]:
    creeds = select(IdeologyTenetRow.ideology_entity_id).where(IdeologyTenetRow.tenet == IdeologyTenet.NATURE_HARMONY)
    statement = select(IdeologyAdherentRow.adherent_entity_id).where(IdeologyAdherentRow.state.is_(True), IdeologyAdherentRow.ideology_entity_id.in_(creeds))
    return frozenset(await session.scalars(statement))


async def reveres_nature(ctx: TickContext, community_id: int) -> bool:
    return community_id in await nature_revering(ctx.session)


def process_of_step(step_key: str) -> ProcessKind | None:
    return STEP_PROCESS.get(step_key)


def outdated(book: EconomyBook, rules: Rules, community_id: int, process: ProcessKind) -> float:
    row = book.methods.get(community_id, {}).get(process)
    return 1 - rules.discovery.obsolete_pct / PERCENT if row is not None and row.obsolete_since is not None else 1.0


def refit(ctx: TickContext, community: EntityRow) -> bool:
    cost = ctx.rules.discovery.refit_cost
    if (stat(community, "wealth") or 0) < cost:
        return False
    shift_stat(community, "wealth", -cost)
    return True


def process_of_kind(kind: ExtractionKind) -> ProcessKind | None:
    return EXTRACTION_PROCESS.get(kind)


def method_for(book: EconomyBook, community_id: int, process: ProcessKind) -> MethodSpec:
    row = book.methods.get(community_id, {}).get(process)
    return METHODS[row.method] if row is not None else default_method(process)


def local_price(book: EconomyBook, community_id: int, commodity: CommodityKind) -> float:
    spec = COMMODITIES[commodity]
    row = book.societies.get(community_id)
    return spec.base_price * (row.price(spec.aggregate) / PERCENT if row is not None else 1.0)


def practised(book: EconomyBook, community: EntityRow, process: ProcessKind) -> bool:
    if process in ALWAYS_PRACTISED:
        return True
    if process in HERD_PROCESSES:
        return HERD_PROCESSES[process] in book.herd_products.get(community.id, set())
    workshop = PROCESS_WORKSHOP.get(process)
    if workshop is not None and book.workshop(community.id, workshop) is not None:
        return True
    if process is ProcessKind.FISHING:
        region = book.ground.region_of(community.id)
        return region is not None and (region.coast_kind is not CoastKind.NONE or region.river_class is not RiverClass.NONE)
    return False


def blocked_by(
    spec: MethodSpec,
    *,
    techniques: set[Technique],
    levels: dict[KnowledgeBranch, int],
    band: TemperatureBand | None,
    coastal: bool,
    supply: int,
    banned: bool = False,
    cellar: bool = False,
) -> str | None:
    checks = (
        (banned and spec.energy is EnergyKind.MAGIC, "the law forbids magic here"),
        (spec.technique is not None and spec.technique not in techniques, f"needs the technique of {(spec.technique or '').replace('_', ' ')}"),
        (spec.branch is not None and levels.get(spec.branch, 0) < spec.level, f"needs {(spec.branch or '').replace('_', ' ')} at level {spec.level}"),
        (spec.climate is not None and band not in spec.climate and not (cellar and spec.kind in CELLAR_METHODS), "the climate does not allow it"),
        (spec.coast and not coastal, "needs a coast"),
        (spec.energy is not EnergyKind.MUSCLE and supply < spec.energy_need, f"too little {spoken(spec.energy)} energy"),
    )
    return next((reason for failed, reason in checks if failed), None)


def allowed(book: EconomyBook, community: EntityRow, spec: MethodSpec, *, banned: bool = False) -> str | None:
    region = book.ground.region_of(community.id)
    row = book.industry.get(community.id)
    return blocked_by(
        spec,
        techniques=book.techniques.get(community.id, set()),
        levels={spec.branch: book.level(community.id, spec.branch)} if spec.branch is not None else {},
        band=region.temperature_band if region is not None else None,
        coastal=region is not None and region.coast_kind is not CoastKind.NONE,
        supply=int(getattr(row, spec.energy.value)) if row is not None else 0,
        banned=banned,
        cellar=has_cellar(book, community.id),
    )


def has_cellar(book: EconomyBook, community_id: int) -> bool:
    return any((store := book.workshop(community_id, kind)) is not None and store.level >= CELLAR_LEVEL for kind in CELLARS)


def profit(ctx: TickContext, book: EconomyBook, community: EntityRow, spec: MethodSpec, *, nature: bool) -> float:
    table = ctx.rules.methods
    price = local_price(book, community.id, PROCESS_OUTPUT[spec.process])
    gross = price * spec.output_pct / PERCENT * premium(ctx.rules, PERCENT // 2 + spec.quality_bonus)
    row = book.industry.get(community.id)
    supply = int(getattr(row, spec.energy.value)) if row is not None else 0
    scarcity = 2 if supply < spec.energy_need * TENTH else 1
    cost = spec.energy_need * table.energy_price * scarcity / TENTH
    cost += spec.tool_wear * local_price(book, community.id, CommodityKind.TOOLS) * table.wear_price_pct / PERCENT / TENTH
    cost += sum(units * local_price(book, community.id, commodity) for commodity, units, _ in spec.inputs) / TENTH
    cost += (spec.labour_pct - PERCENT) * table.labour_price / PERCENT
    if nature:
        cost += spec.fouls * price * table.nature_pollution_pct / PERCENT / TENTH
    return gross - cost


def expected_runs(ctx: TickContext, book: EconomyBook, community: EntityRow, spec: MethodSpec) -> int:
    job = PROCESS_JOB.get(spec.process)
    if job is not None:
        working = book.labour.get(community.id, {}).get(job)
        workers = working.workers if working is not None else 0
        return max(1, round_half_up(workers * ctx.rules.energy.extraction_per_100_workers / PERCENT))
    site = book.workshop(community.id, PROCESS_WORKSHOP[spec.process]) if spec.process in PROCESS_WORKSHOP else None
    return max(1, site.level * ctx.rules.refining.batches_per_level if site is not None else 1)


async def runnable_share(ctx: TickContext, book: EconomyBook, community: EntityRow, spec: MethodSpec) -> float:
    runs = expected_runs(ctx, book, community, spec)
    share = 1.0
    need = spec.energy_need * runs
    if need > 0:
        share = min(share, available(book.industry.get(community.id), spec.energy) / need) if community.id in book.industry else share
    for commodity, per, material in spec.inputs:
        wanted = -(-runs * per // TENTH)
        if wanted > 0:
            share = min(share, await holding(ctx.session, community.id, commodity, material) / wanted)
    return max(0.0, share)


async def expected_profit(ctx: TickContext, book: EconomyBook, community: EntityRow, spec: MethodSpec, *, nature: bool) -> float:
    price = local_price(book, community.id, PROCESS_OUTPUT[spec.process])
    believed = await BeliefView(ctx.session, ctx.rules, community.id).of(community.id, price_key(PROCESS_OUTPUT[spec.process].value), round_half_up(price))
    gross = profit(ctx, book, community, spec, nature=nature) + (believed - price) * spec.output_pct / PERCENT
    if spec.energy is EnergyKind.MUSCLE and not spec.inputs:
        return gross
    share = await runnable_share(ctx, book, community, spec)
    return gross - believed * spec.output_pct / PERCENT * (1 - share)


async def craft_guilds(ctx: TickContext, community_id: int) -> list[FactionProfileRow]:
    statement = select(FactionProfileRow).where(FactionProfileRow.home_entity_id == community_id, FactionProfileRow.kind == FactionKind.CRAFT_GUILD)
    return [row for row in await ctx.session.scalars(statement.order_by(FactionProfileRow.faction_entity_id)) if not held(row.faction_entity_id)]


async def resist(ctx: TickContext, community: EntityRow, process: ProcessKind) -> int:
    table = ctx.rules.methods
    stirred = 0
    for guild in await craft_guilds(ctx, community.id):
        goal = await ctx.session.scalar(
            select(FactionGoalRow).where(
                FactionGoalRow.faction_entity_id == guild.faction_entity_id,
                FactionGoalRow.kind == FactionGoalKind.PROTECT_CRAFT,
                FactionGoalRow.achieved_epoch.is_(None),
            )
        )
        if goal is None:
            goal = FactionGoalRow(
                faction_entity_id=guild.faction_entity_id,
                kind=FactionGoalKind.PROTECT_CRAFT,
                target_node_id=community.id,
                target_key=process.value,
                priority=PERCENT // 2,
                progress=0,
                since_epoch=ctx.epoch,
                set_by_player=False,
                locked=[],
            )
            ctx.session.add(goal)
        if "progress" not in goal.locked:
            goal.progress = clamp_int(goal.progress + table.guild_progress, 0, PERCENT)
        if "priority" not in goal.locked:
            goal.priority = clamp_int(goal.priority + table.guild_priority, 0, PERCENT)
        stirred += 1
    return stirred


def displace(ctx: TickContext, book: EconomyBook, community: EntityRow, process: ProcessKind, gain_pct: int) -> int:
    table = ctx.rules.methods
    rows = book.labour.get(community.id, {})
    job = PROCESS_JOB.get(process, Job.CRAFTING)
    working = rows.get(job)
    if working is None or working.held or gain_pct <= 0:
        return 0
    freed = min(
        round_half_up(working.workers * gain_pct / PERCENT * table.displace_pct / PERCENT), round_half_up(working.workers * table.displace_cap_pct / PERCENT)
    )
    if freed <= 0:
        return 0
    idle = rows.get(Job.IDLE)
    if idle is None:
        idle = LabourRow(community_entity_id=community.id, job=Job.IDLE, workers=0, output_pct=PERCENT, epoch=ctx.epoch)
        ctx.session.add(idle)
        rows[Job.IDLE] = idle
    if idle.held or working.held or not move_amount(working, idle, "workers", freed):
        return 0
    return freed


async def adopt(ctx: TickContext, book: EconomyBook, community: EntityRow, spec: MethodSpec, tally: MethodTally) -> CommunityMethodRow:
    rows = book.methods.setdefault(community.id, {})
    row = rows.get(spec.process)
    if row is None:
        row = CommunityMethodRow(community_node_id=community.id, process=spec.process, method=spec.kind, adopted_epoch=ctx.epoch, displaced=0, locked=[])
        ctx.session.add(row)
        rows[spec.process] = row
        tally.chosen += 1
        return row
    if row.method is spec.kind:
        return row
    before = METHODS[row.method]
    row.method, row.adopted_epoch, row.displaced = spec.kind, ctx.epoch, 0
    tally.changed += 1
    tally.changes[spec.kind.value] = tally.changes.get(spec.kind.value, 0) + 1
    gain = max(spec.output_pct - before.output_pct, round_half_up((before.labour_pct - spec.labour_pct) * PERCENT / max(1, before.labour_pct)))
    if gain > 0:
        row.displaced = displace(ctx, book, community, spec.process, gain)
        tally.displaced += row.displaced
        if await lagged(ctx, BalanceLoop.MILL_RIOTS, community.id, row.displaced, subject=list(ProcessKind).index(spec.process)) > 0:
            tally.resisted += await resist(ctx, community, spec.process)
    await record(
        ctx,
        "industry.method_changed",
        roles={IncidentRole.SUBJECT: community.id},
        facts={"process": spec.process, "before": before.kind, "after": spec.kind, "gain": gain, "displaced": row.displaced},
        terms=(
            Term(f"method.{spec.kind.value}.output_pct", spec.output_pct - before.output_pct),
            Term(f"method.{spec.kind.value}.labour_pct", before.labour_pct - spec.labour_pct),
        ),
        place=community.id,
    )
    return row


async def owner_reveres(ctx: TickContext, owner_id: int, cache: dict[int, bool]) -> bool:
    if owner_id not in cache:
        values = await values_for(ctx.session, owner_id)
        cache[owner_id] = await reveres_nature(ctx, owner_id) or values.get(ValueAxis.NATURE, 0) >= ctx.rules.methods.nature_value_at
    return cache[owner_id]


def method_era(spec: MethodSpec) -> TechnologyEra:
    era = TECHNIQUE_ERAS.get(spec.technique) if spec.technique is not None else None
    return era or TechnologyEra.STONE


def founded_past(current: MethodSpec, best: MethodSpec, start: TechnologyEra) -> bool:
    return era_order(method_era(current)) < era_order(start) and era_order(method_era(best)) <= era_order(start) and method_era(best) is not method_era(current)


async def choose_methods(ctx: TickContext, book: EconomyBook, community: EntityRow, tally: MethodTally, *, banned: bool = False) -> None:
    beliefs: dict[int, bool] = {}
    start = await world_start(ctx.session)
    margin = 1 + ctx.rules.methods.switch_margin_pct / PERCENT
    for process in ProcessKind:
        if not practised(book, community, process):
            continue
        site = book.workshop(community.id, PROCESS_WORKSHOP[process]) if process in PROCESS_WORKSHOP else None
        nature = await owner_reveres(ctx, site.owner_node_id if site is not None and site.owner_node_id is not None else community.id, beliefs)
        row = book.methods.get(community.id, {}).get(process)
        if row is not None and "method" in row.locked:
            continue
        options = [spec for spec in PROCESS_METHODS[process] if allowed(book, community, spec, banned=banned) is None] or [default_method(process)]
        current = METHODS[row.method] if row is not None else None
        candidates = dict.fromkeys([*options, *([current] if current else [])])
        worth = {spec.kind: await expected_profit(ctx, book, community, spec, nature=nature) for spec in candidates}
        if process is ProcessKind.FARMING:
            lift = await method_lift(ctx.session, ctx.rules, community)
            worth = {kind: value * lift if kind in INTENSIVE and value > 0 else value for kind, value in worth.items()}
        best = min(options, key=lambda spec: (-worth[spec.kind], spec.kind.value))
        if current is not None and current in options and worth[best.kind] <= worth[current.kind] * margin:
            continue
        if row is not None and current is not None and current is not best and not founded_past(current, best, start) and not refit(ctx, community):
            if row.obsolete_since is None and "obsolete_since" not in row.locked:
                row.obsolete_since = ctx.epoch
            continue
        adopted = await adopt(ctx, book, community, best, tally)
        if "obsolete_since" not in adopted.locked:
            adopted.obsolete_since = None
