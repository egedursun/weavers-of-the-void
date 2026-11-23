from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.line_outcomes import LINE_OUTCOMES
from aerona.catalog.life.living import CRAFTS
from aerona.catalog.life_traits import CULTIVATION_METHOD_TRAITS, LINE_TRAIT_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import spoken
from aerona.core.random import SeededRandom
from aerona.db.tables.ecology import SpeciesProfileRow, SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.living import LivingLineRow, LivingLineSourceRow, LivingLineTraitRow
from aerona.db.tables.powers import SourceDensityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import RangeTrend
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import CultivationMethodTrait, LineTraitTrait
from aerona.domain.enums.living import CultivationMethod, Fertility, LineOutcome, LineTrait
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.genetics.genome import line_traits
from aerona.engine.living.society import faith_on_maker, regulated
from aerona.engine.living.traits import traits_of
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.book import best_skill
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining, term
from aerona.rules.registry import Rules

M = CultivationMethod
WORKS = frozenset({StructureKind.CLONING_FACILITY, StructureKind.LABORATORY})
CRAFT_STEP = 20
PERSONS = frozenset({EntityType.MORTAL, EntityType.PEOPLE})
SPREADING = having(LINE_TRAIT_TRAITS, LineTraitTrait.SPREADING)
RITE_PATHS = having(CULTIVATION_METHOD_TRAITS, CultivationMethodTrait.RITE_PATHS)


@dataclass(frozen=True)
class LineDraft:
    name: str
    method: CultivationMethod
    maker_id: int
    owner_id: int | None
    source_ids: tuple[int, ...]
    traits: tuple[tuple[LineTrait, int], ...]
    fertility: Fertility = Fertility.BREEDS_TRUE


async def missing_craft(session: AsyncSession, rules: Rules, maker_id: int, method: CultivationMethod) -> str | None:
    skills, technique = CRAFTS[method]
    skilled = await best_skill(session, maker_id, skills) >= rules.living_methods.skill_floor
    if not skilled:
        return "the maker lacks the craft this way of living craft calls for"
    maker = await session.get(EntityRow, maker_id)
    holders = [maker_id] + ([maker.location_id] if maker is not None and maker.location_id is not None else [])
    knows = technique is None or any([await has_technique(session, holder, technique) for holder in holders])
    if not knows and not (method in RITE_PATHS and await best_skill(session, maker_id, (SkillKind.SPELLCRAFT,)) >= rules.living_methods.skill_floor):
        return "no one here knows the technique this way of living craft needs"
    if method is M.INDUCTION and maker is not None and not await dense_land(session, maker):
        return "induction needs a dense source or a phenomenon nearby"
    return None


async def dense_land(session: AsyncSession, maker: EntityRow) -> bool:
    atlas = await RegionAtlas.load(session)
    region = atlas.top_region(maker.id)
    found = await session.scalar(
        select(SourceDensityRow.id).where(SourceDensityRow.region_entity_id == region, SourceDensityRow.density >= PERCENT * 3 // 4).limit(1)
    )
    return found is not None


async def lawful(session: AsyncSession, maker: EntityRow, method: CultivationMethod) -> str | None:
    if maker.location_id is None:
        return None
    named = await law_param(session, maker.location_id, LawKind.LIVING_CRAFT_LAW, method.value)
    level = named if named is not None else await law_param(session, maker.location_id, LawKind.LIVING_CRAFT_LAW, "level")
    return f"{spoken(method)} is banned here" if str(level) == "banned" else None


async def from_persons(session: AsyncSession, source_ids: tuple[int, ...]) -> bool:
    if not source_ids:
        return False
    found = await session.scalar(select(EntityRow.id).where(EntityRow.id.in_(source_ids), EntityRow.entity_type.in_(list(PERSONS))).limit(1))
    return found is not None


async def germline_banned(session: AsyncSession, maker: EntityRow, germline: bool) -> str | None:
    if not germline or maker.location_id is None:
        return None
    level = await law_param(session, maker.location_id, LawKind.GERMLINE_LAW, "level")
    return "changing what passes to descendants is banned here" if str(level) == "banned" else None


async def sacred_source(session: AsyncSession, source_ids: tuple[int, ...]) -> str | None:
    if not source_ids:
        return None
    found = await session.scalar(
        select(SpeciesProfileRow.species_entity_id)
        .where(SpeciesProfileRow.species_entity_id.in_(source_ids), SpeciesProfileRow.sacred_to_node_id.is_not(None))
        .limit(1)
    )
    return "a sacred species is shielded from design" if found is not None else None


async def precision(ctx: TickContext, maker: EntityRow, method: CultivationMethod) -> int:
    table = ctx.rules.living_methods
    skills, _ = CRAFTS[method]
    works = await ctx.session.scalar(
        select(StructureProfileRow.structure_entity_id)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(StructureProfileRow.kind.in_(list(WORKS)), EntityRow.location_id == maker.location_id)
        .limit(1)
    )
    return clamp_percent(table.base_precision + await best_skill(ctx.session, maker.id, skills) // 2 + (table.works_bonus if works is not None else 0))


def lost_stability(ctx: TickContext, outcome: LineOutcome) -> int:
    stability_rule = LINE_OUTCOMES[outcome].stability_rule
    return int(getattr(ctx.rules.living_methods, stability_rule)) if stability_rule is not None else 0


def outcome_of(ctx: TickContext, line_key: str, aim: int) -> LineOutcome:
    table = ctx.rules.living_methods
    rng = ctx.rng(f"living.make.{line_key}")
    if aim >= table.failure_below:
        return LineOutcome.EXCEEDED if aim >= PERCENT and rng.chance(table.exceeded_pct) else LineOutcome.AS_MEANT
    if not rng.chance(table.failure_below - aim + 10):
        return LineOutcome.AS_MEANT
    weights = {outcome: int(getattr(table, result.weight_rule)) for outcome, result in LINE_OUTCOMES.items() if result.weight_rule is not None}
    roll = rng.random() * sum(weights.values())
    for outcome, weight in weights.items():
        roll -= weight
        if roll <= 0:
            return outcome
    return LineOutcome.UNSTABLE


async def germline_traits(ctx: TickContext, source_ids: Sequence[int]) -> dict[LineTrait, int]:
    found: dict[LineTrait, int] = {}
    for source in dict.fromkeys(source_ids):
        genome = await ctx.session.get(GenomeRow, source)
        for trait, strength in line_traits(ctx.rules, genome.genes).items() if genome is not None else []:
            found[trait] = clamp_int(found.get(trait, 0) + strength, -PERCENT, PERCENT)
    return found


async def make_line(ctx: TickContext, draft: LineDraft, *, forced: bool = False) -> LivingLineRow:
    maker = await ctx.session.get(EntityRow, draft.maker_id)
    if maker is None or maker.status is not EntityStatus.CANON:
        raise ValidationFailedError("There is no living maker to make the line.")
    design = ctx.rules.genome_design
    germline = await from_persons(ctx.session, draft.source_ids)
    if not forced:
        reason = (
            await missing_craft(ctx.session, ctx.rules, maker.id, draft.method)
            or await lawful(ctx.session, maker, draft.method)
            or await germline_banned(ctx.session, maker, germline)
            or await sacred_source(ctx.session, draft.source_ids)
        )
        if reason is not None:
            raise ValidationFailedError(f"The line cannot be made: {reason}.")
        await faith_on_maker(ctx, maker, germline)
    allowed = (
        design.trait_cap
        if forced
        else min(design.trait_cap, design.traits_per_level * max(1, await best_skill(ctx.session, maker.id, CRAFTS[draft.method][0]) // CRAFT_STEP))
    )
    if len(draft.traits) > allowed:
        raise ValidationFailedError(f"This making can carry at most {allowed} designed traits.")
    aim = await precision(ctx, maker, draft.method)
    outcome = LineOutcome.AS_MEANT if forced else outcome_of(ctx, f"{maker.id}.{draft.name}.{ctx.epoch}", aim)
    line = LivingLineRow(
        name=draft.name.strip() or f"the line of {maker.name}",
        method=draft.method,
        outcome=outcome,
        stability=clamp_percent(aim - len(draft.traits) * design.instability_per_trait - lost_stability(ctx, outcome)),
        generation=0,
        drift_pct=0,
        fertility=Fertility.STERILE if LINE_OUTCOMES[outcome].sterile else draft.fertility,
        owner_node_id=draft.owner_id if draft.owner_id is not None else maker.id,
        maker_node_id=maker.id,
        species_entity_id=None,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(line)
    await ctx.session.flush()
    for source in dict.fromkeys(draft.source_ids):
        organism = await ctx.session.get(EntityRow, source)
        if organism is not None:
            ctx.session.add(LivingLineSourceRow(line_id=line.id, organism_node_id=source, locked=[]))
            if organism.entity_type is EntityType.SPECIES and line.species_entity_id is None:
                line.species_entity_id = organism.id
    rng = ctx.rng(f"living.side.{line.id}")
    wanted: dict[LineTrait, int] = {}
    for trait, strength in draft.traits:
        wanted[trait] = clamp_int(wanted.get(trait, 0) + strength, -PERCENT, PERCENT)
    inherited = await germline_traits(ctx, draft.source_ids)
    carried = set(wanted)
    for trait, strength in wanted.items():
        blended = clamp_int(strength + inherited.pop(trait, 0), -PERCENT, PERCENT)
        ctx.session.add(LivingLineTraitRow(line_id=line.id, trait=trait, strength=blended, side_effect=False, locked=[]))
        free = [item for item in LineTrait if item not in carried]
        if free and (LINE_OUTCOMES[outcome].side_effects or rng.chance(design.side_effect_chance)):
            side = rng.pick(free)
            carried.add(side)
            ctx.session.add(LivingLineTraitRow(line_id=line.id, trait=side, strength=-abs(strength) // 2, side_effect=True, locked=[]))
    for trait, strength in inherited.items():
        if trait not in carried:
            carried.add(trait)
            ctx.session.add(LivingLineTraitRow(line_id=line.id, trait=trait, strength=strength, side_effect=False, locked=[]))
    add_gift(ctx, line, carried, rng)
    await ctx.session.flush()
    await cross_or_release(ctx, line, draft)
    await record(
        ctx,
        "living.line_made",
        roles={IncidentRole.MAKER: maker.id, IncidentRole.SUBJECT: line.species_entity_id},
        facts={"line": line.name, "method": line.method, "traits": len(carried)},
    )
    return line


def add_gift(ctx: TickContext, line: LivingLineRow, carried: set[LineTrait], rng: SeededRandom) -> None:
    free = [item for item in LineTrait if item not in carried]
    if free and LINE_OUTCOMES[line.outcome].gifted:
        gift = rng.pick(free)
        carried.add(gift)
        ctx.session.add(LivingLineTraitRow(line_id=line.id, trait=gift, strength=ctx.rules.living.exceeded_gift, side_effect=False, locked=[]))


async def cross_or_release(ctx: TickContext, line: LivingLineRow, draft: LineDraft) -> None:
    table = ctx.rules.living
    if line.method is CultivationMethod.HYBRIDISING and len(set(draft.source_ids)) >= 2:
        if ctx.rng(f"living.hybrid.{line.id}").chance(table.hybrid_sterile_pct):
            if "fertility" not in line.locked:
                line.fertility = Fertility.STERILE
        else:
            for row in await ctx.session.scalars(select(LivingLineTraitRow).where(LivingLineTraitRow.line_id == line.id, LivingLineTraitRow.strength > 0)):
                row.strength = clamp_int(row.strength + table.hybrid_vigour, -PERCENT, PERCENT)
    elif line.method is CultivationMethod.WILD_RELEASE:
        await run_wild(ctx, line)


async def escape(ctx: TickContext, line: LivingLineRow) -> bool:
    if line.escaped or line.species_entity_id is None or held(line.species_entity_id):
        return False
    traits = await traits_of(ctx.session, line.id)
    spreads = any(traits.get(trait, 0) > 0 for trait in SPREADING)
    chance = ctx.rules.living_methods.escape_chance * (PERCENT + (ctx.rules.living.escape_spread_pct if spreads else 0)) // PERCENT
    if line.outcome is LineOutcome.EXCEEDED:
        chance = chance * (PERCENT + ctx.rules.living.exceeded_escape_pct) // PERCENT
    owner = await ctx.session.get(EntityRow, line.owner_node_id) if line.owner_node_id is not None else None
    if await regulated(ctx.session, owner):
        chance = chance * (PERCENT - ctx.rules.living.regulated_escape_cut_pct) // PERCENT
    if not ctx.rng(f"living.escape.{line.id}.{ctx.epoch}").chance(chance):
        return False
    return await run_wild(ctx, line)


async def run_wild(ctx: TickContext, line: LivingLineRow) -> bool:
    if line.species_entity_id is None:
        return False
    owner = await ctx.session.get(EntityRow, line.owner_node_id) if line.owner_node_id is not None else None
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(owner.id) if owner is not None else None
    if region is None:
        return False
    if await ctx.session.get(SpeciesRangeRow, (line.species_entity_id, region)) is None:
        ctx.session.add(
            SpeciesRangeRow(
                species_entity_id=line.species_entity_id,
                region_entity_id=region,
                abundance=PERCENT // 4,
                trend=RangeTrend.RISING,
                fit=line.stability,
                hunted=0,
                since_epoch=ctx.epoch,
                updated_epoch=ctx.epoch,
                locked=[],
            )
        )
    line.escaped = True
    if "outcome" not in line.locked:
        line.outcome = LineOutcome.ESCAPED
    await record(ctx, "living.escaped", roles={IncidentRole.PLACE: region}, facts={"line": line.name}, place=region)
    return True


async def drift(ctx: TickContext, line: LivingLineRow) -> LivingLineRow | None:
    table = ctx.rules.living_methods
    if "drift_pct" not in line.locked and line.generation:
        drift_rule = LINE_OUTCOMES[line.outcome].drift_rule
        extra = int(getattr(table, drift_rule)) if drift_rule is not None else 0
        extra += ctx.rules.living.wild_release_drift_pct if line.method is CultivationMethod.WILD_RELEASE else 0
        line.drift_pct = clamp_percent(line.drift_pct + table.drift_per_generation + extra)
    if line.drift_pct < table.new_line_drift or "drift_pct" in line.locked:
        return None
    child = LivingLineRow(
        name=f"{line.name}, drifted",
        method=line.method,
        outcome=line.outcome,
        stability=line.stability,
        generation=0,
        drift_pct=0,
        fertility=Fertility.BREEDS_WILD,
        metabolism=line.metabolism,
        owner_node_id=None,
        maker_node_id=line.maker_node_id,
        species_entity_id=line.species_entity_id,
        drifted_from_id=line.id,
        escaped=line.escaped,
        founded_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(child)
    line.drift_pct = 0
    await ctx.session.flush()
    for trait in list(await ctx.session.scalars(select(LivingLineTraitRow).where(LivingLineTraitRow.line_id == line.id))):
        ctx.session.add(LivingLineTraitRow(line_id=child.id, trait=trait.trait, strength=trait.strength // 2, side_effect=trait.side_effect, locked=[]))
    await record(ctx, "living.drifted", roles={IncidentRole.SUBJECT: line.species_entity_id}, facts={"line": line.name, "new_line": child.name})
    return child


async def cross_wild(ctx: TickContext, line: LivingLineRow) -> bool:
    table = ctx.rules.living
    if line.fertility is not Fertility.CROSSES_WILD or line.species_entity_id is None or held(line.species_entity_id):
        return False
    if not ctx.rng(f"living.cross_wild.{line.id}.{ctx.epoch}").chance(table.wild_cross_pct):
        return False
    lean = sum(1 if strength > 0 else -1 for strength in (await traits_of(ctx.session, line.id)).values())
    shift = table.wild_cross_fit if lean >= 0 else -table.wild_cross_fit
    ranges = list(
        await ctx.session.scalars(
            select(SpeciesRangeRow).where(SpeciesRangeRow.species_entity_id == line.species_entity_id).order_by(SpeciesRangeRow.region_entity_id)
        )
    )
    for row in ranges:
        if "fit" not in row.locked and not held(row.region_entity_id):
            with explaining():
                term("living.wild_cross_fit", shift, source_node_id=line.species_entity_id)
                row.fit = clamp_percent(row.fit + shift)
    await record(ctx, "line.crossed_wild", roles={IncidentRole.SUBJECT: line.species_entity_id}, facts={"line": line.name, "fit": shift, "ranges": len(ranges)})
    return True


async def keep_lines(ctx: TickContext) -> int:
    kept = 0
    for line in list(await ctx.session.scalars(select(LivingLineRow).order_by(LivingLineRow.id))):
        if line.owner_node_id is not None and held(line.owner_node_id):
            continue
        await drift(ctx, line)
        await escape(ctx, line)
        await cross_wild(ctx, line)
        kept += 1
    return kept
