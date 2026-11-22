from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.diets import GRAZERS, MEAT_EATERS
from aerona.catalog.domestication import HOUSED_STAGES, KEPT_STAGES, WILDISH_STAGES
from aerona.catalog.methods import HERD_PROCESSES
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.read_memo import memoized
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.ecology import (
    BeastProfileRow,
    HerdRow,
    SpeciesCustomUseRow,
    SpeciesProductRow,
    SpeciesProfileRow,
    SpeciesUseKindRow,
    SpeciesUseRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.ecology import SIZE_ORDER, STAGE_ORDER, AnimalRole, BeastTemper, DomesticationStage, HerdTraining, SizeClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.industry import ProcessKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.nature_kinds import ProductPart
from aerona.domain.enums.society import CreatureTrait
from aerona.domain.models.entity_stats import SpeciesStats, revised
from aerona.engine.context import TickContext
from aerona.engine.cosmos.fauna import traits_of
from aerona.engine.ecology.biochemistry import can_live_on
from aerona.engine.ecology.evolution import inherit_marks
from aerona.engine.ecology.profiles import profile_of
from aerona.engine.economy.stocks import DEFAULT_QUALITY, GoodsLedger, holding
from aerona.engine.industry.chosen import method_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up, scaled_cap
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import FactInput, RoleValue, record
from aerona.rules.registry import Rules
from aerona.rules.registry.wilds import DomesticationRules

S = DomesticationStage
KEPT = KEPT_STAGES
HUNTING_DIETS = MEAT_EATERS
HOUSED = HOUSED_STAGES
TEN = 10
PRODUCT_PROCESS = {product: process for process, product in HERD_PROCESSES.items()}
PART_PROCESS = {ProductPart.MILK: ProcessKind.MILKING, ProductPart.FIBRE: ProcessKind.SHEARING, ProductPart.EGGS: ProcessKind.EGG_LAYING}


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


async def fertility(ctx: TickContext, species_id: int) -> float:
    table = ctx.rules.husbandry
    profile = await ctx.session.get(SpeciesProfileRow, species_id)
    if profile is None:
        return 1.0
    young = profile.breeding_seasons * profile.litter_size / table.litter_norm
    return max(0.0, min(table.litter_growth_cap_pct / PERCENT, young))


def fodder_for(table: DomesticationRules, head: int) -> int:
    return max(1, round_half_up(head / TEN * table.fodder_per_head))


def fed_head(table: DomesticationRules, head: int, grown: int, eaten: int, *, fed: bool) -> int:
    feeds = grown if table.fodder_per_head <= 0 else eaten * TEN // table.fodder_per_head
    if fed:
        return max(head, min(grown, feeds))
    return max(0, head - round_half_up(max(0, head - feeds) * table.starve_pct / PERCENT))


async def feed(ctx: TickContext, herd: HerdRow) -> bool:
    table = ctx.rules.domestication
    need = fodder_for(table, herd.head)
    yearly = table.growth_pct * await fertility(ctx, herd.species_entity_id) / PERCENT
    grown = max(herd.head, round_half_up(herd.head * (1 + yearly) ** table.years_per_epoch))
    wanted = fodder_for(table, grown) if "head" not in herd.locked else need
    eaten = await GoodsLedger(ctx.session, ctx.epoch).take_units(herd.community_entity_id, CommodityKind.FODDER, wanted, GoodsFlow.CONSUMPTION)
    fed = eaten >= need
    if "head" not in herd.locked:
        herd.head = fed_head(table, herd.head, grown, eaten, fed=fed)
    herd.fed_epochs = herd.fed_epochs + 1 if fed else 0
    return fed


BRED_BIG = frozenset({AnimalRole.MOUNT, AnimalRole.DRAFT, AnimalRole.WAR})
BRED_SMALL = frozenset({AnimalRole.COMPANION})


def drifted_size(size: SizeClass, kinds: set[AnimalRole], rng: SeededRandom, chance: int) -> SizeClass:
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
        stats = revised(stats, {"danger": clamp_int((stat(parent, "danger") or 0) - table.tame_drift, 0, PERCENT)})
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
    for item in await ctx.session.scalars(select(SpeciesProductRow).where(SpeciesProductRow.species_entity_id == child.id)):
        item.rate = max(item.rate, round_half_up(item.rate * (1 + table.yield_gain_pct / PERCENT)))
    for use in await ctx.session.scalars(select(SpeciesUseRow.use).where(SpeciesUseRow.species_entity_id == parent.id)):
        if await ctx.session.get(SpeciesUseRow, (child.id, use)) is None:
            ctx.session.add(SpeciesUseRow(species_entity_id=child.id, use=use))
    inherited = await traits_of(ctx.session, child.id)
    for trait in await traits_of(ctx.session, parent.id):
        if trait is not CreatureTrait.SACRED_ANIMAL and trait not in inherited:
            await EntityRepository(ctx.session).add_trait(child.id, trait)
    await inherit_marks(ctx.session, parent.id, child.id, ctx.epoch)
    return child


async def master_herder(ctx: TickContext, keeper_id: int) -> int:
    mortals = select(EntityRow.id).where(
        await present_among(ctx.session, [keeper_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    found = await ctx.session.scalar(
        select(SkillRow.level).where(SkillRow.holder_node_id.in_(mortals), SkillRow.skill == SkillKind.BEAST_HANDLING).order_by(SkillRow.level.desc()).limit(1)
    )
    return int(found or 0)


@dataclass(frozen=True)
class Advanced:
    key: str
    roles: dict[IncidentRole, RoleValue]
    facts: dict[str, FactInput]


async def advance(ctx: TickContext, herd: HerdRow, made: int, most: int | None = None) -> Advanced | None:
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
        return Advanced(
            "ecology.domestication",
            {IncidentRole.ACTOR: keeper.id, IncidentRole.SUBJECT: species.id},
            {"head": herd.head, "fed_epochs": herd.fed_epochs},
        )
    if made >= (table.cap if most is None else most):
        return None
    tamed = rng.chance(table.domesticate_chance * profile.tameability / PERCENT)
    return await promote(ctx, herd, species, keeper, tamed=tamed, bred=rng.chance(table.breed_chance), tameability=profile.tameability)


async def promote(ctx: TickContext, herd: HerdRow, species: EntityRow, keeper: EntityRow, *, tamed: bool, bred: bool, tameability: int) -> Advanced | None:
    table = ctx.rules.domestication
    if herd.stage is S.HERDED and ctx.epoch - herd.since_epoch >= table.domesticate_epochs and tamed:
        child = await offspring(ctx, species, keeper, stage=S.DOMESTICATED)
        await rehome(ctx, herd, child, S.DOMESTICATED)
        return Advanced(
            "ecology.domesticated",
            {IncidentRole.ACTOR: keeper.id, IncidentRole.SUBJECT: species.id, IncidentRole.PRODUCT: child.id},
            {"head": herd.head, "tameability": tameability},
        )
    skill = await master_herder(ctx, keeper.id) if herd.stage is S.DOMESTICATED and bred else 0
    if herd.stage is S.DOMESTICATED and bred and skill >= table.breed_skill:
        child = await offspring(ctx, species, keeper, stage=S.BREED)
        await rehome(ctx, herd, child, S.BREED)
        return Advanced(
            "ecology.breed_raised",
            {IncidentRole.ACTOR: keeper.id, IncidentRole.SUBJECT: species.id, IncidentRole.PRODUCT: child.id},
            {"head": herd.head, "skill": skill},
        )
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


async def use_boosts(ctx: TickContext, species_id: int) -> dict[AnimalRole, int]:
    rows = await ctx.session.execute(
        select(SpeciesUseKindRow.base_use, SpeciesUseKindRow.output_pct)
        .join(SpeciesCustomUseRow, SpeciesCustomUseRow.kind_id == SpeciesUseKindRow.id)
        .where(SpeciesCustomUseRow.species_entity_id == species_id)
    )
    found: dict[AnimalRole, int] = {}
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
        ((AnimalRole.MEAT,), CommodityKind.LIVESTOCK, table.livestock_per_head),
        ((AnimalRole.MOUNT, AnimalRole.WAR), CommodityKind.MOUNTS, table.mounts_per_head),
        ((AnimalRole.SACRED,), CommodityKind.SACRED_GOODS, table.sacred_per_head),
        ((AnimalRole.REAGENT_SOURCE,), CommodityKind.MAGICAL_REAGENTS, table.reagents_per_head),
        ((AnimalRole.DAIRY,), CommodityKind.MILK, table.dairy_per_head),
        ((AnimalRole.FIBRE,), CommodityKind.WOOL, table.fibre_per_head),
        ((AnimalRole.HUNTING,), CommodityKind.MEAT, table.hunting_per_head),
    )
    for wanted, commodity, rate in outputs:
        present = [use for use in wanted if use in kinds]
        if present:
            scale = max(boost.get(use, PERCENT) for use in present) / PERCENT
            made += await ledger.add(herd.community_entity_id, commodity, round_half_up(tens * rate * scale), GoodsFlow.PRODUCTION)
    calm = (table.companion_calm if AnimalRole.COMPANION in kinds else 0) + (table.entertainment_calm if AnimalRole.ENTERTAINMENT in kinds else 0)
    if calm:
        town = await ctx.session.get(SettlementProfileRow, herd.community_entity_id)
        if town is not None and "unrest" not in town.locked:
            town.unrest = clamp_int(town.unrest - calm, 0, PERCENT)
    if AnimalRole.MESSENGER in kinds:
        community = await ctx.session.get(EntityRow, herd.community_entity_id)
        if community is not None:
            add_prosperity(ctx.rules, community, table.messenger_prosperity)
    for item in await ctx.session.scalars(select(SpeciesProductRow).where(SpeciesProductRow.species_entity_id == herd.species_entity_id)):
        process = PART_PROCESS.get(item.part) if item.part is not None else PRODUCT_PROCESS.get(item.product)
        if process is not None and item.commodity is not None:
            spec = await method_of(ctx.session, herd.community_entity_id, process)
            made += await ledger.add(
                herd.community_entity_id,
                item.commodity,
                round_half_up(tens * item.rate * spec.output_pct / PERCENT),
                GoodsFlow.PRODUCTION,
                quality=DEFAULT_QUALITY + spec.quality_bonus,
                material=item.material,
                world_material_id=item.world_material_id,
            )
    return made


WILDISH = WILDISH_STAGES


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
    herds = list(await ctx.session.scalars(select(HerdRow).order_by(HerdRow.community_entity_id, HerdRow.species_entity_id)))
    most = scaled_cap(ctx.rules.domestication.cap, ctx.rules.domestication.herds_per_extra, len(herds))
    for herd in ctx.rng("husbandry.order").shuffled(herds):
        if await feed(ctx, herd):
            counts["fed"] += 1
        else:
            counts["starving"] += 1
        if herd.head <= 0 and "head" not in herd.locked:
            await ctx.session.delete(herd)
            counts["lost"] += 1
            continue
        counts["goods"] += await produce(ctx, herd)
        if "trained" not in herd.locked:
            herd.trained = min(herd.trained, herd.head)
        counts["trained"] = counts.get("trained", 0) + await train(ctx, herd)
        advanced = await advance(ctx, herd, made, most)
        if advanced is not None:
            counts["advanced"] += 1
            made += 1
            await record(ctx, advanced.key, roles=advanced.roles, facts=advanced.facts)
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
        if AnimalRole.MOUNT in uses and CreatureTrait.FLYING in await traits_of(ctx.session, herd.species_entity_id):
            found.add("sky_mount")
    if await holding(ctx.session, community_id, CommodityKind.MOUNTS) > 0:
        found.add(AnimalRole.MOUNT.value)
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


@memoized(HerdRow, SpeciesUseRow)
async def heads_kept_for(session: AsyncSession, use: AnimalRole) -> dict[int, int]:
    uses = select(SpeciesUseRow.species_entity_id).where(SpeciesUseRow.use == use)
    found: dict[int, int] = {}
    statement = select(HerdRow.community_entity_id, HerdRow.head).where(HerdRow.species_entity_id.in_(uses), HerdRow.stage.in_(list(KEPT)))
    for community_id, head in await session.execute(statement):
        found[community_id] = found.get(community_id, 0) + head
    return found


async def kept_for(ctx: TickContext, community_id: int, use: AnimalRole) -> int:
    return (await heads_kept_for(ctx.session, use)).get(community_id, 0)


async def draught(ctx: TickContext, community_id: int) -> float:
    table = ctx.rules.domestication
    return 1 + table.labour_pct / PERCENT * min(1.0, await kept_for(ctx, community_id, AnimalRole.DRAFT) / table.labour_head)


async def trained_heads(session: AsyncSession, community_id: int, training: HerdTraining) -> int:
    heads = await session.scalars(select(HerdRow.trained).where(HerdRow.community_entity_id == community_id, HerdRow.training == training))
    return sum(heads)


def trained_effect(rules: Rules, trained: int) -> float:
    return min(1.0, trained / rules.husbandry.trained_full_head)


async def guarded(ctx: TickContext, community_id: int) -> float:
    kept = ctx.rules.domestication.guard_pct if await kept_for(ctx, community_id, AnimalRole.GUARD) > 0 else 0
    kept += ctx.rules.domestication.sensing_pct if await kept_for(ctx, community_id, AnimalRole.SENSING) > 0 else 0
    drilled = ctx.rules.husbandry.guard_pct * trained_effect(ctx.rules, await trained_heads(ctx.session, community_id, HerdTraining.GUARD))
    return max(0.0, 1 - (kept + drilled) / PERCENT)


def drill(rules: Rules, herd: HerdRow, skill: int) -> int:
    gained = max(0, round_half_up((herd.head - herd.trained) * rules.husbandry.train_pct / PERCENT * skill / PERCENT))
    herd.trained = min(herd.head, herd.trained + gained)
    return gained


async def training_for(ctx: TickContext, herd: HerdRow) -> HerdTraining | None:
    uses = set(await ctx.session.scalars(select(SpeciesUseRow.use).where(SpeciesUseRow.species_entity_id == herd.species_entity_id)))
    if AnimalRole.WAR in uses:
        return HerdTraining.WAR
    if AnimalRole.GUARD in uses:
        return HerdTraining.GUARD
    profile = await ctx.session.get(SpeciesProfileRow, herd.species_entity_id)
    return HerdTraining.HUNTING if profile is not None and profile.diet in HUNTING_DIETS else None


async def train(ctx: TickContext, herd: HerdRow) -> int:
    if herd.stage not in KEPT or held(herd.community_entity_id):
        return 0
    skill = await master_herder(ctx, herd.community_entity_id)
    if skill < ctx.rules.husbandry.train_skill:
        return 0
    if herd.training is None and "training" not in herd.locked:
        herd.training = await training_for(ctx, herd)
    if herd.training is None or "trained" in herd.locked:
        return 0
    return drill(ctx.rules, herd, skill)


async def carry_herds(ctx: TickContext, source_id: int, colony: EntityRow) -> tuple[int, int]:
    carried = left = 0
    if held(source_id) or held(colony.id):
        return carried, left
    for herd in list(
        await ctx.session.scalars(select(HerdRow).where(HerdRow.community_entity_id == source_id, HerdRow.head > 0).order_by(HerdRow.species_entity_id))
    ):
        head = round_half_up(herd.head * ctx.rules.domestication.colony_herd_pct / PERCENT)
        if head <= 0:
            continue
        if not await can_live_on(ctx.session, herd.species_entity_id, colony.world_id):
            left += 1
            continue
        if "head" not in herd.locked:
            herd.head -= head
        ctx.session.add(
            HerdRow(
                community_entity_id=colony.id,
                species_entity_id=herd.species_entity_id,
                head=head,
                stage=herd.stage,
                since_epoch=ctx.epoch,
                fed_epochs=0,
                locked=[],
            )
        )
        carried += 1
    await ctx.session.flush()
    return carried, left


async def grazing_heads(session: AsyncSession) -> dict[int, int]:
    atlas = await RegionAtlas.load(session)
    grazers = select(SpeciesProfileRow.species_entity_id).where(SpeciesProfileRow.diet.in_(list(GRAZERS)))
    found: dict[int, int] = {}
    rows = select(HerdRow.community_entity_id, HerdRow.head).where(HerdRow.head > 0, HerdRow.stage.in_(list(KEPT)), HerdRow.species_entity_id.in_(grazers))
    for community_id, head in await session.execute(rows):
        region = atlas.top_region(community_id)
        if region is not None:
            found[region] = found.get(region, 0) + head
    return found
