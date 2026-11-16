from collections import defaultdict
from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import func, select

from aerona.catalog.structure_effects import EFFECTS, STRUCTURE_OWN_EFFECTS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.structure import ConstructionState, EffectTarget, StructureEffect, StructureKind
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.lore.research_depth import add_progress, research_choices
from aerona.engine.mind.skills import practise
from aerona.engine.mortal.standing import add_stress
from aerona.engine.nature.seasons import region_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat

T = EffectTarget
Apply = Callable[[TickContext, EntityRow, SettlementProfileRow, int], Awaitable[None]]
BOUNDED = frozenset({T.PUBLIC_ORDER, T.CRIME, T.UNREST, T.SANITATION, T.FIRE_RISK, T.PRESTIGE, T.SIEGE_SUPPLIES, T.SIEGE_WATER})
TRAINED_FEW = 3


def field_shift(name: str) -> Apply:
    async def shift(_ctx: TickContext, _town: EntityRow, profile: SettlementProfileRow, amount: int) -> None:
        if name in profile.locked:
            return
        value = getattr(profile, name) + amount
        setattr(profile, name, clamp_int(value, 0, PERCENT) if T(name) in BOUNDED else max(0, value))

    return shift


def stat_shift(name: str) -> Apply:
    async def shift(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, amount: int) -> None:
        shift_stat(town, name, amount, ctx.rules.society.default_stat, high=PERCENT)

    return shift


async def lettered(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, amount: int) -> None:
    people = await people_of(ctx.session, town)
    culture = await ctx.session.get(PeopleCultureRow, people.id) if people is not None else None
    if culture is not None and people is not None and not held(people.id) and "literacy" not in culture.locked:
        culture.literacy = clamp_int(culture.literacy + amount, 0, PERCENT)


async def studied(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, amount: int) -> None:
    people = await people_of(ctx.session, town)
    holder = people.id if people is not None else town.id
    choices = await research_choices(ctx.session, holder)
    if choices and not held(holder):
        await add_progress(ctx, holder, choices[0], amount)


async def folk_of(ctx: TickContext, town: EntityRow) -> list[int]:
    here = await present_among(ctx.session, [town.id])
    rows = await ctx.session.scalars(
        select(EntityRow.id).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return [node for node in rows if not held(node)]


async def trained(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, amount: int) -> None:
    for node in (await folk_of(ctx, town))[:TRAINED_FEW]:
        best = await ctx.session.scalar(select(SkillRow.skill).where(SkillRow.holder_node_id == node).order_by(SkillRow.level.desc()).limit(1))
        if best is not None:
            await practise(ctx.session, ctx.rules, node, best, amount, epoch=ctx.epoch)


async def calmed(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, amount: int) -> None:
    for node in await folk_of(ctx, town):
        await add_stress(ctx.session, node, -amount, ctx.epoch)


async def speculated(ctx: TickContext, town: EntityRow, _profile: SettlementProfileRow, amount: int) -> None:
    swing = amount if ctx.rng(f"speculation.{town.id}.{ctx.epoch}").chance(ctx.rules.structure_effects.boom_pct) else -amount
    shift_stat(town, "prosperity", swing, ctx.rules.society.default_stat, high=PERCENT)


APPLIERS: Mapping[EffectTarget, Apply] = total(
    EffectTarget,
    {
        T.CALM: calmed,
        T.CONSTRUCTION_CAPACITY: field_shift("construction_capacity"),
        T.CRIME: field_shift("crime"),
        T.FIRE_RISK: field_shift("fire_risk"),
        T.HAULING_CAPACITY: field_shift("hauling_capacity"),
        T.INVESTMENT_POOL: field_shift("investment_pool"),
        T.KNOWLEDGE: studied,
        T.LITERACY: lettered,
        T.MILITIA: field_shift("militia"),
        T.PIETY: stat_shift("piety"),
        T.PRESTIGE: field_shift("prestige"),
        T.PROSPERITY: stat_shift("prosperity"),
        T.PUBLIC_ORDER: field_shift("public_order"),
        T.SANITATION: field_shift("sanitation"),
        T.SIEGE_SUPPLIES: field_shift("siege_supplies"),
        T.SIEGE_WATER: field_shift("siege_water"),
        T.SPECULATION: speculated,
        T.TRAIN: trained,
        T.TREASURY: field_shift("treasury"),
        T.UNREST: field_shift("unrest"),
    },
)


async def own_effects(ctx: TickContext, town_id: int) -> dict[StructureEffect, float]:
    rows = await ctx.session.execute(
        select(StructureProfileRow.kind, StructureProfileRow.level).where(
            StructureProfileRow.host_entity_id == town_id,
            StructureProfileRow.construction_state == ConstructionState.COMPLETE,
            StructureProfileRow.condition > 0,
        )
    )
    found: dict[StructureEffect, float] = defaultdict(float)
    for kind, level in rows.all():
        for effect in STRUCTURE_OWN_EFFECTS[kind]:
            found[effect] += max(1, level)
    return found


async def last_epidemic(ctx: TickContext, region_id: int | None) -> int | None:
    if region_id is None:
        return None
    ongoing = await ctx.session.scalar(select(OutbreakRow.id).where(OutbreakRow.region_entity_id == region_id, OutbreakRow.ended_epoch.is_(None)).limit(1))
    if ongoing is not None:
        return ctx.epoch
    return await ctx.session.scalar(select(func.max(OutbreakRow.ended_epoch)).where(OutbreakRow.region_entity_id == region_id))


async def tend_quarantine(ctx: TickContext, town: EntityRow) -> None:
    table = ctx.rules.structure_effects
    houses = select(StructureProfileRow).where(StructureProfileRow.host_entity_id == town.id, StructureProfileRow.kind == StructureKind.QUARANTINE_HOUSE)
    rows = list(await ctx.session.scalars(houses))
    if not rows:
        return
    last = await last_epidemic(ctx, await region_of(ctx.session, town.id))
    afraid = last is not None and ctx.epoch - last < table.quarantine_memory
    for row in rows:
        if held(row.structure_entity_id) or "condition" in row.locked:
            continue
        row.condition = PERCENT if afraid and last == ctx.epoch else max(0, row.condition - (0 if afraid else table.quarantine_decay))


async def act_own_effects(ctx: TickContext, town: EntityRow, profile: SettlementProfileRow) -> int:
    table = ctx.rules.structure_effects
    await tend_quarantine(ctx, town)
    pushed: dict[EffectTarget, float] = defaultdict(float)
    for effect, levels in (await own_effects(ctx, town.id)).items():
        spec = EFFECTS[effect]
        pushed[spec.target] += spec.sign * levels * spec.weight * table.step_pct / PERCENT / PERCENT
    acted = 0
    for target, amount in sorted(pushed.items()):
        capped = round_half_up(max(-table.cap, min(table.cap, amount)))
        if capped:
            await APPLIERS[target](ctx, town, profile, capped)
            acted += 1
    return acted
