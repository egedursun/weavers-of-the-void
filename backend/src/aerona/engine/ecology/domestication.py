from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.ecology import (
    BeastProfileRow,
    HerdRow,
    SpeciesCustomUseRow,
    SpeciesProfileRow,
    SpeciesUseKindRow,
    SpeciesUseRow,
    SpeciesYieldRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import SIZE_ORDER, STAGE_ORDER, BeastTemper, DomesticationStage, SizeClass, SpeciesUse
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.economy.stocks import GoodsLedger, holding
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat

S = DomesticationStage
KEPT = frozenset({S.HERDED, S.DOMESTICATED, S.BREED})
HOUSED = frozenset({S.DOMESTICATED, S.BREED})
TEN = 10
HERD_PRODUCTS = frozenset({"wool", "milk"})


async def keeper_of(ctx: TickContext, tamer: EntityRow) -> EntityRow | None:
    if tamer.entity_type in COMMUNITY_TYPES:
        return tamer
    return await living_entity(ctx.session, tamer.location_id)


async def ensure_herds(ctx: TickContext) -> int:
    opened = 0
    for bond in await active_bonds(ctx.session, [BondKind.TAMED]):
        tamer = await living_entity(ctx.session, bond.source_node_id)
        species = await living_entity(ctx.session, bond.target_node_id)
        if tamer is None or species is None or species.entity_type is not EntityType.SPECIES:
            continue
        keeper = await keeper_of(ctx, tamer)
        if keeper is None or keeper.entity_type not in COMMUNITY_TYPES:
            continue
        if await ctx.session.get(HerdRow, (keeper.id, species.id)) is not None:
            continue
        ctx.session.add(
            HerdRow(
                community_entity_id=keeper.id,
                species_entity_id=species.id,
                head=ctx.rules.domestication.starting_head,
                stage=S.TAMED,
                since_epoch=ctx.epoch,
                fed_epochs=0,
                locked=[],
            )
        )
        opened += 1
    await ctx.session.flush()
    return opened


async def feed(ctx: TickContext, herd: HerdRow) -> bool:
    table = ctx.rules.domestication
    need = max(1, round_half_up(herd.head / TEN * table.fodder_per_head))
    eaten = await GoodsLedger(ctx.session, ctx.epoch).take_units(herd.community_entity_id, CommodityKind.FODDER, need, GoodsFlow.CONSUMPTION)
    fed = eaten >= need
    if "head" not in herd.locked:
        change = table.growth_pct if fed else -table.starve_pct
        herd.head = max(0, round_half_up(herd.head * (1 + change / PERCENT)))
    herd.fed_epochs = herd.fed_epochs + 1 if fed else 0
    return fed


BRED_BIG = frozenset({SpeciesUse.MOUNT, SpeciesUse.LABOUR, SpeciesUse.WAR})
BRED_SMALL = frozenset({SpeciesUse.COMPANION})


def drifted_size(size: SizeClass, kinds: set[SpeciesUse], rng: SeededRandom, chance: int) -> SizeClass:
    index = SIZE_ORDER.index(size)
    if kinds & BRED_BIG:
        index += 1
    elif kinds & BRED_SMALL:
        index -= 1
    elif rng.chance(chance):
        index += 1 if rng.chance(PERCENT // 2) else -1
    return SIZE_ORDER[max(0, min(len(SIZE_ORDER) - 1, index))]


async def offspring(ctx: TickContext, parent: EntityRow, keeper: EntityRow, *, stage: DomesticationStage) -> EntityRow:
    table = ctx.rules.domestication
    word = "Domestic" if stage is S.DOMESTICATED else keeper.name
    stats = parent.stats
    if isinstance(stats, SpeciesStats):
        stats = stats.model_copy(update={"danger": clamp_int((stat(parent, "danger") or 0) - table.tame_drift, 0, PERCENT)})
    child = await create_record(
        ctx,
        RecordSpec(
            name=f"{word} {parent.name}",
            entity_type=EntityType.SPECIES,
            stats=stats,
            body=f"Bred from {parent.name} by the herders of {keeper.name}.",
            power=parent.power_level,
            world_id=keeper.world_id,
            location_id=keeper.id,
            subtype="domesticated" if stage is S.DOMESTICATED else "breed",
            engine_kind=EngineKind.DOMESTICATED,
        ),
    )
    await BondRepository(ctx.session).connect(BondDraft(child.id, parent.id, BondKind.DESCENDS_FROM, ctx.epoch, "bred by herders"))
    source = await profile_of(ctx, parent)
    row = await profile_of(ctx, child)
    for key in ("body_plan", "lifespan_years", "maturity_years", "litter_size", "breeding_seasons", "diet", "metabolism", "habitat"):
        setattr(row, key, getattr(source, key))
    kinds = set(await ctx.session.scalars(select(SpeciesUseRow.use).where(SpeciesUseRow.species_entity_id == parent.id)))
    row.size_class = drifted_size(source.size_class, kinds, ctx.rng(f"domestic_size.{child.id}"), table.size_drift_chance)
    row.aggression = clamp_int(source.aggression - table.tame_drift, 0, PERCENT)
    row.fear_of_people = clamp_int(source.fear_of_people - table.tame_drift, 0, PERCENT)
    row.tameability = clamp_int(source.tameability + table.tame_gain, 0, PERCENT)
    row.stage, row.stage_epoch, row.domesticated_from_id = stage, ctx.epoch, parent.id
    for item in await ctx.session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == child.id)):
        item.rate = max(item.rate, round_half_up(item.rate * (1 + table.yield_gain_pct / PERCENT)))
    for use in await ctx.session.scalars(select(SpeciesUseRow.use).where(SpeciesUseRow.species_entity_id == parent.id)):
        if await ctx.session.get(SpeciesUseRow, (child.id, use)) is None:
            ctx.session.add(SpeciesUseRow(species_entity_id=child.id, use=use))
    inherited = await traits_of(ctx.session, child.id)
    for trait in await traits_of(ctx.session, parent.id):
        if trait is not CreatureTrait.SACRED_ANIMAL and trait not in inherited:
            await EntityRepository(ctx.session).add_trait(child.id, trait)
    return child


async def master_herder(ctx: TickContext, keeper_id: int) -> int:
    mortals = select(EntityRow.id).where(EntityRow.location_id == keeper_id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    found = await ctx.session.scalar(
        select(SkillRow.level).where(SkillRow.holder_node_id.in_(mortals), SkillRow.skill == SkillKind.BEAST_HANDLING).order_by(SkillRow.level.desc()).limit(1)
    )
    return int(found or 0)


async def advance(ctx: TickContext, herd: HerdRow, made: int) -> str | None:
    table = ctx.rules.domestication
    if "stage" in herd.locked:
        return None
    species = await living_entity(ctx.session, herd.species_entity_id)
    keeper = await living_entity(ctx.session, herd.community_entity_id)
    if species is None or keeper is None:
        return None
    profile = await profile_of(ctx, species)
    rng = ctx.rng(f"domestication.{herd.community_entity_id}.{herd.species_entity_id}.{ctx.epoch}")
    if herd.stage is S.TAMED and herd.fed_epochs >= table.herd_epochs:
        herd.stage, herd.since_epoch = S.HERDED, ctx.epoch
        return f"{keeper.name} now keeps herds of {species.name}"
    if made >= table.cap:
        return None
    tamed = rng.chance(table.domesticate_chance * profile.tameability / PERCENT)
    return await promote(ctx, herd, species, keeper, tamed=tamed, bred=rng.chance(table.breed_chance))


async def promote(ctx: TickContext, herd: HerdRow, species: EntityRow, keeper: EntityRow, *, tamed: bool, bred: bool) -> str | None:
    table = ctx.rules.domestication
    if herd.stage is S.HERDED and ctx.epoch - herd.since_epoch >= table.domesticate_epochs and tamed:
        child = await offspring(ctx, species, keeper, stage=S.DOMESTICATED)
        await rehome(ctx, herd, child, S.DOMESTICATED)
        return f"the herders of {keeper.name} tamed {species.name} into {child.name}"
    if herd.stage is S.DOMESTICATED and bred and await master_herder(ctx, keeper.id) >= table.breed_skill:
        child = await offspring(ctx, species, keeper, stage=S.BREED)
        await rehome(ctx, herd, child, S.BREED)
        return f"a master herder of {keeper.name} raised a new breed, {child.name}"
    return None


async def rehome(ctx: TickContext, herd: HerdRow, child: EntityRow, stage: DomesticationStage) -> None:
    fresh = HerdRow(
        community_entity_id=herd.community_entity_id,
        species_entity_id=child.id,
        head=herd.head,
        stage=stage,
        since_epoch=ctx.epoch,
        fed_epochs=herd.fed_epochs,
        locked=[],
    )
    await ctx.session.delete(herd)
    ctx.session.add(fresh)
    await ctx.session.flush()


async def use_boosts(ctx: TickContext, species_id: int) -> dict[SpeciesUse, int]:
    rows = await ctx.session.execute(
        select(SpeciesUseKindRow.base_use, SpeciesUseKindRow.output_pct)
        .join(SpeciesCustomUseRow, SpeciesCustomUseRow.kind_id == SpeciesUseKindRow.id)
        .where(SpeciesCustomUseRow.species_entity_id == species_id)
    )
    found: dict[SpeciesUse, int] = {}
    for use, output in rows:
        found[use] = max(found.get(use, 0), output)
    return found


async def produce(ctx: TickContext, herd: HerdRow) -> int:
    if herd.stage not in KEPT or herd.head <= 0:
        return 0
    table = ctx.rules.domestication
    kinds = set(await ctx.session.scalars(select(SpeciesUseRow.use).where(SpeciesUseRow.species_entity_id == herd.species_entity_id)))
    boost = await use_boosts(ctx, herd.species_entity_id)
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    tens = herd.head / TEN
    made = 0
    outputs = (
        ((SpeciesUse.FOOD,), CommodityKind.LIVESTOCK, table.livestock_per_head),
        ((SpeciesUse.MOUNT, SpeciesUse.WAR), CommodityKind.MOUNTS, table.mounts_per_head),
        ((SpeciesUse.SACRIFICE,), CommodityKind.SACRED_GOODS, table.sacred_per_head),
        ((SpeciesUse.MAGIC,), CommodityKind.MAGICAL_REAGENTS, table.reagents_per_head),
    )
    for wanted, commodity, rate in outputs:
        held = [use for use in wanted if use in kinds]
        if held:
            scale = max(boost.get(use, PERCENT) for use in held) / PERCENT
            made += await ledger.add(herd.community_entity_id, commodity, round_half_up(tens * rate * scale), GoodsFlow.PRODUCTION)
    if SpeciesUse.COMPANION in kinds:
        town = await ctx.session.get(SettlementProfileRow, herd.community_entity_id)
        if town is not None and "unrest" not in town.locked:
            town.unrest = clamp_int(town.unrest - table.companion_calm, 0, PERCENT)
    for item in await ctx.session.scalars(select(SpeciesYieldRow).where(SpeciesYieldRow.species_entity_id == herd.species_entity_id)):
        if item.product in HERD_PRODUCTS and item.commodity is not None:
            made += await ledger.add(
                herd.community_entity_id,
                item.commodity,
                round_half_up(tens * item.rate),
                GoodsFlow.PRODUCTION,
                material=item.material,
                world_material_id=item.world_material_id,
            )
    return made


WILDISH = frozenset({S.WILD, S.TAMED, S.HERDED})


async def stage_from_herds(ctx: TickContext) -> int:
    kept: dict[int, DomesticationStage] = {}
    for species_id, stage in await ctx.session.execute(select(HerdRow.species_entity_id, HerdRow.stage).where(HerdRow.head > 0)):
        if stage in WILDISH and STAGE_ORDER.index(stage) > STAGE_ORDER.index(kept.get(species_id, S.WILD)):
            kept[species_id] = stage
    changed = 0
    for profile in list(await ctx.session.scalars(select(SpeciesProfileRow).where(SpeciesProfileRow.stage.in_(list(WILDISH))))):
        stage = kept.get(profile.species_entity_id, S.WILD)
        if profile.stage is stage or "stage" in profile.locked:
            continue
        profile.stage, profile.stage_epoch = stage, ctx.epoch
        changed += 1
    return changed


async def husbandry(ctx: TickContext) -> dict[str, int]:
    counts = {"herds_opened": await ensure_herds(ctx), "fed": 0, "starving": 0, "goods": 0, "advanced": 0, "lost": 0}
    made = 0
    for herd in list(await ctx.session.scalars(select(HerdRow).order_by(HerdRow.community_entity_id, HerdRow.species_entity_id))):
        if await feed(ctx, herd):
            counts["fed"] += 1
        else:
            counts["starving"] += 1
        if herd.head <= 0 and "head" not in herd.locked:
            await ctx.session.delete(herd)
            counts["lost"] += 1
            continue
        counts["goods"] += await produce(ctx, herd)
        text = await advance(ctx, herd, made)
        if text:
            counts["advanced"] += 1
            made += 1
            await note(ctx, f"{text[0].upper()}{text[1:]}.", key="ecology.domestication", ids=[herd.community_entity_id, herd.species_entity_id])
    await ctx.session.flush()
    counts["stages"] = await stage_from_herds(ctx)
    return counts


async def herd_uses(ctx: TickContext, community_id: int) -> set[str]:
    found: set[str] = set()
    herds = await ctx.session.scalars(select(HerdRow).where(HerdRow.community_entity_id == community_id, HerdRow.head > 0))
    for herd in list(herds):
        if herd.stage not in KEPT:
            continue
        uses = set(await ctx.session.scalars(select(SpeciesUseRow.use).where(SpeciesUseRow.species_entity_id == herd.species_entity_id)))
        found |= {use.value for use in uses}
        if SpeciesUse.MOUNT in uses and CreatureTrait.FLYING in await traits_of(ctx.session, herd.species_entity_id):
            found.add("sky_mount")
    if await holding(ctx.session, community_id, CommodityKind.MOUNTS) > 0:
        found.add(SpeciesUse.MOUNT.value)
    bound = await ctx.session.scalar(
        select(BeastProfileRow.beast_entity_id).where(BeastProfileRow.bound_to_node_id == community_id, BeastProfileRow.temper == BeastTemper.BOUND).limit(1)
    )
    if bound is not None:
        found.add("bound_beast")
    return found


async def domestic_head(ctx: TickContext, species_id: int) -> int | None:
    profile = await ctx.session.get(SpeciesProfileRow, species_id)
    if profile is None or profile.stage not in HOUSED:
        return None
    heads = await ctx.session.scalars(select(HerdRow.head).where(HerdRow.species_entity_id == species_id))
    return sum(heads)


async def kept_for(ctx: TickContext, community_id: int, use: SpeciesUse) -> int:
    uses = select(SpeciesUseRow.species_entity_id).where(SpeciesUseRow.use == use)
    heads = await ctx.session.scalars(
        select(HerdRow.head).where(HerdRow.community_entity_id == community_id, HerdRow.species_entity_id.in_(uses), HerdRow.stage.in_(list(KEPT)))
    )
    return sum(heads)


async def draught(ctx: TickContext, community_id: int) -> float:
    table = ctx.rules.domestication
    return 1 + table.labour_pct / PERCENT * min(1.0, await kept_for(ctx, community_id, SpeciesUse.LABOUR) / table.labour_head)


async def guarded(ctx: TickContext, community_id: int) -> float:
    return 1 - ctx.rules.domestication.guard_pct / PERCENT if await kept_for(ctx, community_id, SpeciesUse.GUARD) > 0 else 1.0
