from dataclasses import dataclass, field

from aerona.catalog.materials import ARMOUR_MATERIALS, LUXURY_MATERIALS, TOOL_MATERIALS, WEAPON_MATERIALS
from aerona.catalog.production import CHAIN_STEPS, SHIP_INPUTS, ChainStep
from aerona.constants.units import PERCENT
from aerona.db.tables.economy import ProductionRunRow, WorkshopDesignRow, WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import Job
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, WorkshopKind
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw, SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.economy.materials import alloy_inputs, workable
from aerona.engine.economy.stocks import epoch_need, goods_of, holding, lots_of
from aerona.engine.economy.workshop_designs import capacity_scale, output_scale, quality_bonus
from aerona.engine.eras.effects import tech_factor
from aerona.engine.factions.guilds import guild_standard
from aerona.engine.industry.energy import scale_by_energy
from aerona.engine.industry.methods import feed, method_for, process_of_step
from aerona.engine.military.war_lines import war_output
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import headcount
from aerona.engine.recording.record import record
from aerona.engine.structures.readers import workshop_output
from aerona.rules.registry import Rules

M = MaterialKind
UPGRADES: dict[MaterialKind, MaterialKind] = {M.COPPER: M.BRONZE, M.IRON: M.STEEL}
EXOTIC_FROM_IRON = M.SKYSTEEL
KITCHEN_STEPS = frozenset({"butcher", "cheese"})
PREFERENCE: dict[CommodityKind, tuple[MaterialKind, ...]] = {
    CommodityKind.WEAPONS: WEAPON_MATERIALS,
    CommodityKind.ARMOUR: ARMOUR_MATERIALS,
    CommodityKind.TOOLS: TOOL_MATERIALS,
    CommodityKind.LUXURIES: LUXURY_MATERIALS,
}


@dataclass
class RefiningTally:
    batches: int = 0
    bottlenecks: dict[str, int] = field(default_factory=dict)
    built: int = 0
    ships: int = 0
    noted: int = 0


def artisan_pool(ctx: TickContext, book: EconomyBook, community: EntityRow) -> int:
    hands = book.hands(community.id, Job.CRAFTING)
    if hands is not None:
        return hands
    row = book.societies.get(community.id)
    share = row.share(SocialClass.ARTISAN) if row is not None else PERCENT / len(SocialClass)
    free = PERCENT - ctx.rules.extraction.artisan_labour_pct
    return round_half_up(headcount(community) * share / PERCENT * free / PERCENT)


def target_units(ctx: TickContext, community: EntityRow, commodity: CommodityKind) -> int:
    need = epoch_need(ctx.rules, headcount(community), commodity)
    return round_half_up(max(1, need) * ctx.rules.refining.target_index / ctx.rules.economy.supply_index_epoch)


def lit(ctx: TickContext, book: EconomyBook, community_id: int) -> float:
    row = book.industry.get(community_id)
    return 1 + (row.light if row is not None else 0) * ctx.rules.energy.light_work_pct / PERCENT / PERCENT


def capacity(ctx: TickContext, step: ChainStep, workshop: WorkshopRow | None, design: WorkshopDesignRow | None = None) -> int:
    table = ctx.rules.refining
    if step.workshop is None:
        return round_half_up(table.batches_per_level * table.household_batches_pct / PERCENT)
    return round_half_up(workshop.level * table.batches_per_level * capacity_scale(design)) if workshop is not None else 0


async def best_input(ctx: TickContext, book: EconomyBook, community: EntityRow, step: ChainStep) -> tuple[MaterialKind | None, int | None]:
    if step.keeps_material is None:
        return step.material, None
    lots = [row for row in await lots_of(ctx.session, community.id, step.keeps_material) if row.quantity > 0]
    levels = book.levels(community.id)
    density = book.magic_density(community.id)
    order = PREFERENCE.get(step.output, ())
    candidates: list[tuple[int, MaterialKind | None, int | None]] = []
    for row in lots:
        if row.world_material_id is not None:
            props = book.materials.props(community.world_id, world_material_id=row.world_material_id)
            if props is not None and workable(ctx.rules, props, levels, density):
                candidates.append((-props.hardness - props.edge, None, row.world_material_id))
            continue
        if row.material is None:
            continue
        target = forged_material(ctx, book, community, row.material, levels=levels, density=density)
        if target is None or (order and target not in order):
            continue
        rank = order.index(target) if target in order else len(order)
        candidates.append((rank, target, None))
    if not candidates:
        return None, None
    _, material, world_material = min(candidates, key=lambda item: (item[0], str(item[1])))
    return material, world_material


MATERIAL_TECHNIQUES = {
    M.BRONZE: (Technique.BRONZE,),
    M.IRON: (Technique.IRON,),
    M.STEEL: (Technique.STEEL,),
    M.SKYSTEEL: (Technique.SKYSTEEL,),
}


def forged_material(
    ctx: TickContext, book: EconomyBook, community: EntityRow, raw: MaterialKind, *, levels: dict[KnowledgeBranch, int], density: int
) -> MaterialKind | None:
    props = book.materials.props(community.world_id, raw)
    if props is None or not workable(ctx.rules, props, levels, density):
        return None
    if any(book.lacks(community.id, technique) for technique in MATERIAL_TECHNIQUES.get(raw, ())):
        return None
    if raw is M.IRON and not book.lacks(community.id, Technique.SKYSTEEL):
        sky = book.materials.props(community.world_id, EXOTIC_FROM_IRON)
        if sky is not None and workable(ctx.rules, sky, levels, density):
            return EXOTIC_FROM_IRON
    upgrade = UPGRADES.get(raw)
    if upgrade is not None and any(book.lacks(community.id, technique) for technique in MATERIAL_TECHNIQUES.get(upgrade, ())):
        upgrade = None
    if upgrade is not None:
        better = book.materials.props(community.world_id, upgrade)
        if better is not None and workable(ctx.rules, better, levels, density):
            return upgrade
    return raw


async def inputs_for(
    ctx: TickContext, community: EntityRow, step: ChainStep, material: MaterialKind | None, world_material: int | None
) -> dict[CommodityKind, int]:
    held: dict[CommodityKind, int] = {}
    for commodity, _ in step.inputs:
        if commodity is step.keeps_material and (material is not None or world_material is not None):
            raws = alloy_inputs(material) if material is not None else ()
            lots = await lots_of(ctx.session, community.id, commodity)
            if world_material is not None:
                held[commodity] = sum(row.quantity for row in lots if row.world_material_id == world_material)
            else:
                held[commodity] = min(sum(row.quantity for row in lots if row.material is raw) for raw in raws) if raws else 0
        else:
            held[commodity] = await holding(ctx.session, community.id, commodity)
    return held


async def consume_inputs(
    ctx: TickContext, community: EntityRow, step: ChainStep, batches: int, *, material: MaterialKind | None, world_material: int | None
) -> tuple[dict[str, int], int]:
    used: dict[str, int] = {}
    qualities: list[tuple[int, int]] = []
    for commodity, per_batch in step.inputs:
        amount = per_batch * batches
        if commodity is step.keeps_material and material is not None:
            raws = alloy_inputs(material)
            for raw in raws:
                for lot in await goods_of(ctx.session, ctx.epoch).take(community.id, commodity, amount, GoodsFlow.INPUT, material=raw):
                    qualities.append((lot.quality, lot.quantity))
        elif commodity is step.keeps_material and world_material is not None:
            for lot in await goods_of(ctx.session, ctx.epoch).take(community.id, commodity, amount, GoodsFlow.INPUT, world_material_id=world_material):
                qualities.append((lot.quality, lot.quantity))
        else:
            for lot in await goods_of(ctx.session, ctx.epoch).take(community.id, commodity, amount, GoodsFlow.INPUT):
                qualities.append((lot.quality, lot.quantity))
        used[commodity.value] = amount
    total = sum(quantity for _, quantity in qualities)
    quality = round_half_up(sum(value * quantity for value, quantity in qualities) / total) if total else 50
    return used, quality


async def note_bottleneck(ctx: TickContext, community: EntityRow, step: ChainStep, missing: CommodityKind, tally: RefiningTally) -> None:
    tally.bottlenecks[missing.value] = tally.bottlenecks.get(missing.value, 0) + 1
    tally.noted += 1
    await record(
        ctx,
        "refining.bottleneck",
        roles={IncidentRole.SUBJECT: community.id},
        facts={"workshop": step.workshop, "missing": missing, "output": step.output, "output_qty": step.output_qty},
        place=community.id,
    )


async def run_step(ctx: TickContext, book: EconomyBook, community: EntityRow, step: ChainStep, *, artisans: int, tally: RefiningTally) -> int:
    table = ctx.rules.refining
    workshop = book.workshop(community.id, step.workshop) if step.workshop is not None else None
    design = book.design_of(workshop)
    room = round_half_up(capacity(ctx, step, workshop, design) * await workshop_output(ctx.session, ctx.rules, workshop) * lit(ctx, book, community.id))
    room = round_half_up(room * await tech_factor(ctx.session, ctx.rules, community.id, EraChannel.INDUSTRY))
    if room <= 0 or (step.branch is not None and book.level(community.id, step.branch) < step.level):
        return 0
    wanted = target_units(ctx, community, step.output) - await holding(ctx.session, community.id, step.output)
    if wanted <= 0:
        return 0
    material, world_material = await best_input(ctx, book, community, step)
    if material is MaterialKind.IRON and (await ctx.laws()).has(NaturalLaw.NO_IRON, community.world_id):
        return 0
    held = await inputs_for(ctx, community, step, material, world_material)
    short = [commodity for commodity, per_batch in step.inputs if held.get(commodity, 0) < per_batch]
    process = process_of_step(step.key)
    method = method_for(book, community.id, process) if process is not None else None
    crew = max(1, round_half_up(table.workers_per_batch * (method.labour_pct if method is not None else PERCENT) / PERCENT))
    hands = artisans // crew
    batches = min(room, hands, -(-wanted // step.output_qty), *(held.get(commodity, 0) // per_batch for commodity, per_batch in step.inputs))
    if method is not None and batches > 0:
        batches = int(batches * scale_by_energy(book, community.id, method.energy, method.energy_need * batches))
        batches = int(batches * await feed(ctx, community.id, method, batches))
    if short and step.workshop is not None and workshop is not None:
        await note_bottleneck(ctx, community, step, short[0], tally)
        ctx.session.add(
            ProductionRunRow(
                epoch=ctx.epoch,
                community_entity_id=community.id,
                step=step.key,
                workshop=step.workshop,
                output=step.output,
                quantity=0,
                quality=0,
                inputs={},
                workers=0,
                bottleneck=short[0],
            )
        )
    if batches <= 0:
        if workshop is not None and not workshop.held:
            workshop.idle_epochs += 1
        return 0
    used, input_quality = await consume_inputs(ctx, community, step, batches, material=material, world_material=world_material)
    skill = book.skill(community.id, step.skill)
    quality = clamp_int(
        round_half_up(input_quality * table.material_quality_pct / PERCENT)
        + skill * table.skill_quality_per_level
        + step.quality_gain
        + quality_bonus(design)
        + (method.quality_bonus if method is not None else 0)
        + await guild_standard(ctx, community.id)
        + round_half_up(await ctx.hook_pct(community.id, DomainHook.CRAFT_SKILL) * ctx.rules.domains.quality_points_pct / PERCENT),
        0,
        PERCENT,
    )
    made = round_half_up(batches * step.output_qty * output_scale(design) * (method.output_pct / PERCENT if method is not None else 1.0))
    made = round_half_up(made * await war_output(ctx, community.id, step.output))
    out_material = material if step.keeps_material is not None else step.material
    await goods_of(ctx.session, ctx.epoch).add(
        community.id, step.output, made, GoodsFlow.PRODUCTION, material=out_material, world_material_id=world_material, quality=quality
    )
    ctx.session.add(
        ProductionRunRow(
            epoch=ctx.epoch,
            community_entity_id=community.id,
            step=step.key,
            workshop=step.workshop,
            output=step.output,
            material=out_material,
            quantity=made,
            quality=quality,
            inputs=used,
            workers=batches * crew,
            method=method.kind if method is not None else None,
        )
    )
    if workshop is not None and not workshop.held:
        workshop.idle_epochs = 0
        if batches >= room and workshop.level < level_cap(ctx.rules, headcount(community)) and ctx.rng(f"upgrade.{workshop.id}").chance(table.upgrade_chance):
            workshop.level += 1
    tally.batches += batches
    return batches * crew


def level_cap(rules: Rules, population: int) -> int:
    table = rules.refining
    return table.max_level + (population // table.people_per_level if table.people_per_level > 0 else 0)


def fleet_room(rules: Rules, population: int) -> int:
    table = rules.refining
    return table.fleet_cap + (population // table.people_per_ship if table.people_per_ship > 0 else 0)


def needed_workshops(ctx: TickContext, book: EconomyBook, community: EntityRow) -> list[WorkshopKind]:
    wanted: list[WorkshopKind] = []
    for step in CHAIN_STEPS:
        if step.workshop is None or book.workshop(community.id, step.workshop) is not None or step.workshop in wanted:
            continue
        if step.branch is not None and book.level(community.id, step.branch) < step.level:
            continue
        wanted.append(step.workshop)
    return wanted


async def build_workshops(ctx: TickContext, book: EconomyBook, community: EntityRow, tally: RefiningTally) -> None:
    table = ctx.rules.refining
    rng = ctx.rng(f"workshop.{community.id}")
    for kind in needed_workshops(ctx, book, community):
        inputs = [step for step in CHAIN_STEPS if step.workshop is kind]
        has_inputs = False
        for step in inputs:
            if all([await holding(ctx.session, community.id, commodity) >= per_batch for commodity, per_batch in step.inputs]):
                has_inputs = True
        if not has_inputs or not rng.chance(table.build_chance):
            continue
        if (
            await holding(ctx.session, community.id, CommodityKind.TIMBER) < table.build_timber
            or await holding(ctx.session, community.id, CommodityKind.STONE) < table.build_stone
        ):
            continue
        await goods_of(ctx.session, ctx.epoch).take(community.id, CommodityKind.TIMBER, table.build_timber, GoodsFlow.CONSTRUCTION)
        await goods_of(ctx.session, ctx.epoch).take(community.id, CommodityKind.STONE, table.build_stone, GoodsFlow.CONSTRUCTION)
        row = WorkshopRow(community_entity_id=community.id, kind=kind, level=1, built_epoch=ctx.epoch)
        ctx.session.add(row)
        book.workshops.setdefault(community.id, {})[kind] = row
        tally.built += 1
        await record(
            ctx,
            "refining.workshop_built",
            roles={IncidentRole.MAKER: community.id},
            facts={"workshop": kind, "timber": table.build_timber, "stone": table.build_stone},
            place=community.id,
        )
        return


async def launch_ships(ctx: TickContext, book: EconomyBook, community: EntityRow, tally: RefiningTally) -> None:
    table = ctx.rules.refining
    yard = book.workshop(community.id, WorkshopKind.SHIPYARD)
    if (
        yard is None
        or yard.held
        or yard.fleet >= fleet_room(ctx.rules, headcount(community))
        or not ctx.rng(f"ship.{community.id}").chance(table.ship_chance * await workshop_output(ctx.session, ctx.rules, yard))
    ):
        return
    for commodity, amount in SHIP_INPUTS:
        if await holding(ctx.session, community.id, commodity) < amount:
            return
    for commodity, amount in SHIP_INPUTS:
        await goods_of(ctx.session, ctx.epoch).take(community.id, commodity, amount, GoodsFlow.INPUT)
    yard.fleet += 1
    tally.ships += 1


async def tend_workshops(ctx: TickContext, book: EconomyBook, community: EntityRow) -> None:
    limit = ctx.rules.refining.upgrade_idle_limit
    for workshop in book.workshops.get(community.id, {}).values():
        if not workshop.held and workshop.idle_epochs > limit and workshop.level > 1:
            workshop.level -= 1
            workshop.idle_epochs = 0


async def kitchen(ctx: TickContext, book: EconomyBook, community: EntityRow, tally: RefiningTally) -> int:
    artisans = artisan_pool(ctx, book, community)
    worked = 0
    for step in CHAIN_STEPS:
        if step.key not in KITCHEN_STEPS or artisans < ctx.rules.refining.workers_per_batch:
            continue
        used = await run_step(ctx, book, community, step, artisans=artisans, tally=tally)
        artisans -= used
        worked += used
    return worked


async def refine_community(ctx: TickContext, book: EconomyBook, community: EntityRow, tally: RefiningTally) -> None:
    artisans = artisan_pool(ctx, book, community)
    for step in CHAIN_STEPS:
        if step.key in KITCHEN_STEPS:
            continue
        if artisans < ctx.rules.refining.workers_per_batch:
            break
        artisans -= await run_step(ctx, book, community, step, artisans=artisans, tally=tally)
    await launch_ships(ctx, book, community, tally)
    await build_workshops(ctx, book, community, tally)
    await tend_workshops(ctx, book, community)
