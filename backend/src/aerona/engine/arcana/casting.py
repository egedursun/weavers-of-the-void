from dataclasses import dataclass, field

from aerona.catalog.arcana import DRY_SPREAD, LEAK_EMPOWERED, RAIN_HELPED, RAIN_HINDERED, WET_CONDUCTED
from aerona.constants.units import PERCENT
from aerona.db.tables.arcana import RiteGrammarRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import LegendProfileRow, RiteProfileRow
from aerona.db.tables.discovery import TheoryProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.culture import RiteEffectKind
from aerona.domain.enums.entity import COMMUNITY_TYPES
from aerona.domain.enums.environment import WeatherEffect
from aerona.domain.enums.region import TerrainHazard
from aerona.engine.arcana.grammar import backlash_factor, ensure_grammar
from aerona.engine.arcana.resistance import carries_iron, disrupted, penetration_of, resistance_of
from aerona.engine.arcana.vis import burn_for
from aerona.engine.context import TickContext
from aerona.engine.environment.hazards import HazardTally, strike
from aerona.engine.environment.local import weather_here
from aerona.engine.happenings.profile import year_at
from aerona.engine.primitives.distance import RegionAtlas

E = RiteEffectKind
CORRUPTED = {E.HEAL: E.DAMAGE, E.BLESS: E.CURSE, E.FERTILITY: E.CURSE, E.HARVEST_BLESSING: E.CURSE, E.WARD: E.SCRY, E.EXORCISE: E.SUMMON}
HOSTILE_EFFECTS = frozenset({E.DAMAGE, E.CURSE, E.SCRY, E.BIND})


@dataclass
class Shaping:
    grammar: RiteGrammarRow
    strength: float = 1.0
    backlash: float = 1.0
    corrupted: bool = False
    resisted: bool = False
    notes: list[str] = field(default_factory=list)


async def paradigm_factor(ctx: TickContext, grammar: RiteGrammarRow) -> float:
    theory = await ctx.session.get(TheoryProfileRow, grammar.paradigm_entity_id) if grammar.paradigm_entity_id is not None else None
    if theory is None:
        return 1.0
    table = ctx.rules.paradigms
    floor = table.floor_pct / PERCENT
    factor = floor + (1 - floor) * theory.correctness / PERCENT
    rival = await ctx.session.get(TheoryProfileRow, theory.rival_entity_id) if theory.rival_entity_id is not None else None
    if rival is not None and rival.explanatory_power > theory.explanatory_power:
        factor *= 1 - table.shift_drop_pct / PERCENT
    return factor


async def myth_factor(ctx: TickContext, caster: EntityRow, grammar: RiteGrammarRow) -> tuple[float, bool]:
    legend = await ctx.session.get(LegendProfileRow, grammar.myth_entity_id) if grammar.myth_entity_id is not None else None
    if legend is None:
        return 1.0, False
    table = ctx.rules.myth_coupling
    factor = 1 + legend.credence * table.power_pct / PERCENT / PERCENT
    if caster.entity_type in COMMUNITY_TYPES and legend.fixed_in_entity_id in {caster.id, caster.location_id}:
        factor += table.site_pct / PERCENT
    corrupted = legend.distortion > table.corruption_at and ctx.rng(f"myth.corrupt.{caster.id}.{grammar.rite_entity_id}.{ctx.epoch}").chance(legend.distortion)
    return factor, corrupted


async def wildfire(ctx: TickContext, atlas: RegionAtlas, region_id: int | None, wet: int, shaping: Shaping) -> None:
    ground = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
    hazards = ctx.rules.hazards
    if ground is None or ground.forest_cover < hazards.wildfire_forest_min or wet > hazards.wildfire_wet_max:
        return
    if ctx.rng(f"rite.wildfire.{region_id}.{ctx.epoch}").chance(ctx.rules.spell_environment.wildfire_pct):
        await strike(ctx, atlas, ground, TerrainHazard.WILDFIRE, season=None, year=year_at(ctx, ctx.epoch, f"rite.wildfire.{region_id}"), tally=HazardTally())
        shaping.notes.append("the dry forest caught and burned")


async def environment(ctx: TickContext, caster: EntityRow, target: EntityRow | None, shaping: Shaping) -> None:
    table = ctx.rules.spell_environment
    form = shaping.grammar.form
    aim = target if target is not None else caster
    weather = await weather_here(ctx, aim.id, f"rite.env.{aim.id}")
    wet = weather.effect(WeatherEffect.WET) if weather is not None else 0
    if form in RAIN_HINDERED and form is not SpellForm.FIRE and wet:
        shaping.strength *= max(0.0, 1 - wet * table.rain_pct / PERCENT / PERCENT)
        shaping.notes.append("the rain dimmed it")
    if form in RAIN_HELPED and wet:
        shaping.strength *= 1 + wet * table.rain_pct / PERCENT / PERCENT
    if form in WET_CONDUCTED and target is not None and wet:
        shaping.strength *= 1 + wet * table.wet_pct / PERCENT / PERCENT
        shaping.notes.append("the wet carried it to its mark")
    atlas = await RegionAtlas.load(ctx.session)
    if form in DRY_SPREAD:
        await wildfire(ctx, atlas, atlas.top_region(aim.id), wet, shaping)
    if disrupted(shaping.grammar) and target is not None and await carries_iron(ctx, target):
        shaping.strength *= max(0.0, 1 - table.iron_pct / PERCENT)
        shaping.notes.append("iron broke its hold")
    world = await ctx.session.get(WorldRow, caster.world_id) if caster.world_id is not None else None
    if form in LEAK_EMPOWERED and world is not None and world.leakage:
        shaping.strength *= 1 + world.leakage * table.leak_power_pct / PERCENT / PERCENT
        shaping.backlash *= 1 + world.leakage * table.leak_backlash_pct / PERCENT / PERCENT


async def shape_casting(
    ctx: TickContext,
    caster: EntityRow,
    target: EntityRow | None,
    row: RiteProfileRow,
    *,
    effects: list[RiteEffectKind],
    mastery: int,
    caster_god: int | None,
    warded: float,
) -> Shaping:
    grammar = await ensure_grammar(ctx.session, ctx.rules, row)
    shaping = Shaping(grammar=grammar, backlash=backlash_factor(ctx.rules, grammar))
    reliability = await paradigm_factor(ctx, grammar)
    shaping.strength *= reliability
    shaping.backlash /= max(0.1, reliability)
    myth, shaping.corrupted = await myth_factor(ctx, caster, grammar)
    shaping.strength *= myth
    if shaping.corrupted:
        shaping.notes.append("the twisted myth turned the rite")
    await environment(ctx, caster, target, shaping)
    if await burn_for(ctx, caster, grammar.form, row.power * ctx.rules.vis.per_power):
        shaping.strength *= 1 + ctx.rules.vis.power_pct / PERCENT
        shaping.notes.append(f"it burned {grammar.form.value} vis")
    if target is not None and target.id != caster.id and set(effects) & HOSTILE_EFFECTS:
        resist = await resistance_of(ctx, target, caster_god=caster_god, form_disrupted=disrupted(grammar), warded=warded)
        if penetration_of(ctx, row, mastery) < resist:
            shaping.resisted = True
            shaping.notes.append(f"{target.name} resisted it")
    return shaping


def corrupted_effect(effect: RiteEffectKind) -> RiteEffectKind:
    return CORRUPTED.get(effect, effect)
