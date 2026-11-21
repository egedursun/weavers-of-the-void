from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.catalog.divine_grammar import FOREIGN_PRESETS, SCOPE_RANK, SON_PRESETS, VERB_SIGN, Grammar
from aerona.catalog.domains import DOMAIN_LABELS
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.concealment import HiddenTruthRow
from aerona.db.tables.divine import WorldAttentionRow
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.foreign_gods import ForeignGodPowerRow, ForeignGodRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.powers import PowerSourceRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.divine import DivineCost, DivineMode, DivineObject, DivineScope, DivineVerb
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import MemoryKind, PressureKind, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import domains_of, faithful_communities, living_gods
from aerona.engine.economy.stocks import goods_of
from aerona.engine.mind.book import pressures_of, stored_values, write_pressures, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.mortal.standing import shift_standing
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import record

Apply = Callable[[TickContext, EntityRow, str | None, int, int], Awaitable[None]]
DOMAIN_LIFT = 25


async def on_stat(ctx: TickContext, target: EntityRow, key: str | None, amount: int, _holder: int) -> None:
    shift_stat(target, key or "prosperity", amount, 0)


async def on_need(ctx: TickContext, target: EntityRow, key: str | None, amount: int, _holder: int) -> None:
    kind = PressureKind(key) if key is not None and key in PressureKind._value2member_map_ else PressureKind.HUNGER
    pressures = await pressures_of(ctx.session, target.id)
    pressures[kind] = clamp_percent(pressures.get(kind, 0) - amount)
    await write_pressures(ctx.session, target.id, pressures)


async def on_skill(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    here = select(EntityRow.id).where(EntityRow.location_id == target.id)
    holders = [target.id, *list(await ctx.session.scalars(here.limit(ctx.rules.divine_grammar.reach)))]
    for row in list(
        await ctx.session.scalars(
            select(SkillRow).where(SkillRow.holder_node_id.in_(holders)).order_by(SkillRow.level.desc()).limit(ctx.rules.divine_grammar.reach)
        )
    ):
        row.level = clamp_int(row.level + amount, 0, PERCENT)


async def on_value(ctx: TickContext, target: EntityRow, key: str | None, amount: int, _holder: int) -> None:
    axis = ValueAxis(key) if key is not None and key in ValueAxis._value2member_map_ else ValueAxis.PIETY
    holder = ValueHolder.PERSONAL if target.entity_type is EntityType.MORTAL else ValueHolder.CULTURE
    values = dict(await stored_values(ctx.session, holder, target.id))
    values[axis] = clamp_int(values.get(axis, 0) + amount, -PERCENT, PERCENT)
    await write_values(ctx.session, holder, target.id, values)


async def on_trait(ctx: TickContext, target: EntityRow, key: str | None, amount: int, holder: int) -> None:
    await on_value(ctx, target, key, amount, holder)


async def on_commodity(ctx: TickContext, target: EntityRow, key: str | None, amount: int, _holder: int) -> None:
    kind = CommodityKind(key) if key is not None and key in CommodityKind._value2member_map_ else CommodityKind.GRAIN
    stocks = goods_of(ctx.session, ctx.epoch)
    if amount > 0:
        await stocks.add(target.id, kind, amount * ctx.rules.divine_grammar.goods_per_point, GoodsFlow.AID)
    else:
        await stocks.take(target.id, kind, -amount * ctx.rules.divine_grammar.goods_per_point, GoodsFlow.LOSS)


async def on_species(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    shift_stat(target, "fertility", amount, 0)


async def on_line(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    for line in list(await ctx.session.scalars(select(LivingLineRow).where(LivingLineRow.owner_node_id == target.id))):
        if "stability" not in line.locked:
            line.stability = clamp_percent(line.stability + amount)


async def on_structure(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    for row in list(await ctx.session.scalars(select(StructureProfileRow).where(StructureProfileRow.host_entity_id == target.id))):
        if not held(row.structure_entity_id) and "condition" not in row.locked:
            row.condition = clamp_percent(row.condition + amount)


async def on_weather(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    region = (await RegionAtlas.load(ctx.session)).top_region(target.id)
    land = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    if land is not None and not held(land.entity_id) and "rainfall_shift" not in land.locked:
        land.rainfall_shift = clamp_int(land.rainfall_shift + amount, -PERCENT, PERCENT)


async def on_source(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    for source in list(await ctx.session.scalars(select(PowerSourceRow).where(PowerSourceRow.scope_node_id.in_([target.id, target.world_id or 0])))):
        if "stability" not in source.locked:
            source.stability = clamp_percent(source.stability + amount)


async def on_power(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    region = (await RegionAtlas.load(ctx.session)).top_region(target.id)
    land = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    if land is not None and not held(land.entity_id) and "magic_density" not in land.locked:
        land.magic_density = clamp_percent(land.magic_density + amount)


async def on_mind(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    here = select(EntityRow.id).where(EntityRow.location_id == target.id)
    for mind in list(await ctx.session.scalars(select(MindProfileRow).where(MindProfileRow.node_id.in_([target.id, *list(await ctx.session.scalars(here))])))):
        if not held(mind.node_id) and "stability" not in mind.locked:
            mind.stability = clamp_percent(mind.stability + amount)


async def on_truth(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    for truth in list(await ctx.session.scalars(select(HiddenTruthRow).where(HiddenTruthRow.subject_node_id == target.id))):
        if "strength" not in truth.locked:
            truth.strength = clamp_percent(truth.strength + amount)


async def on_law(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, _holder: int) -> None:
    shift_stat(target, "justice", amount, 0)


async def on_memory(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, holder: int) -> None:
    kind = MemoryKind.GOODWILL if amount > 0 else MemoryKind.ILL_WILL
    await remember(ctx.session, ctx.rules, holder_id=target.id, subject_id=holder, kind=kind, magnitude=amount, epoch=ctx.epoch, note="a god's hand")


async def on_incident(ctx: TickContext, target: EntityRow, _key: str | None, amount: int, holder: int) -> None:
    await shift_standing(ctx.session, target, "piety", abs(amount) // 2, ctx.epoch, default=0)
    await record(ctx, "divine.power_incident", roles={IncidentRole.SUBJECT: [target.id, holder]})


APPLIERS: Mapping[DivineObject, Apply] = total(
    DivineObject,
    {
        DivineObject.STAT: on_stat,
        DivineObject.NEED: on_need,
        DivineObject.SKILL: on_skill,
        DivineObject.VALUE: on_value,
        DivineObject.TRAIT: on_trait,
        DivineObject.COMMODITY: on_commodity,
        DivineObject.SPECIES: on_species,
        DivineObject.LINE: on_line,
        DivineObject.STRUCTURE: on_structure,
        DivineObject.WEATHER: on_weather,
        DivineObject.SOURCE: on_source,
        DivineObject.POWER: on_power,
        DivineObject.MIND: on_mind,
        DivineObject.TRUTH: on_truth,
        DivineObject.LAW: on_law,
        DivineObject.MEMORY: on_memory,
        DivineObject.INCIDENT: on_incident,
    },
)


async def god_of(ctx: TickContext, node_id: int) -> SonRow | ForeignGodRow | None:
    return await ctx.session.get(SonRow, node_id) or await ctx.session.get(ForeignGodRow, node_id)


async def targets_of(ctx: TickContext, row: DivinePowerRow, target_id: int | None) -> list[EntityRow]:
    if target_id is not None:
        target = await ctx.session.get(EntityRow, target_id)
        return [target] if target is not None else []
    holder = await ctx.session.get(EntityRow, row.holder_node_id)
    if holder is not None:
        home = await ctx.session.get(EntityRow, holder.location_id) if holder.location_id is not None else None
        return [holder] if row.scope is DivineScope.PERSON or home is None else [home]
    faithful = await faithful_communities(ctx.session, row.holder_node_id)
    return faithful[: ctx.rules.divine_grammar.reach * (SCOPE_RANK[row.scope] + 1)]


async def strength_of(ctx: TickContext, row: DivinePowerRow) -> int:
    god = await god_of(ctx, row.holder_node_id)
    own = {domain.value for domain in domains_of(god)} if god is not None else set()
    lift = len(own & set(row.domains or [])) * DOMAIN_LIFT
    return row.strength * (PERCENT + lift) // PERCENT * ctx.rules.divine_grammar.effect_pct // PERCENT


async def pay(ctx: TickContext, row: DivinePowerRow) -> bool:
    god = await god_of(ctx, row.holder_node_id)
    amount = row.cost_amount
    if row.cost is DivineCost.ESSENCE:
        if isinstance(god, SonRow):
            if god.essence < amount:
                return False
            god.essence -= amount
        elif isinstance(god, ForeignGodRow):
            if god.faith < amount:
                return False
            god.faith -= amount
    elif row.cost is DivineCost.ATTENTION:
        holder = await ctx.session.get(EntityRow, row.holder_node_id)
        world = holder.world_id if holder is not None else None
        attention = await ctx.session.get(WorldAttentionRow, world) if world is not None else None
        if attention is not None and "attention" not in attention.locked:
            attention.attention = clamp_percent(attention.attention - amount)
    elif row.cost is DivineCost.SACRIFICE:
        for community in await faithful_communities(ctx.session, row.holder_node_id):
            if not held(community.id):
                shift_stat(community, "prosperity", -amount, 0)
    elif row.cost is DivineCost.STANDING and isinstance(god, SonRow):
        god.essence = max(0, god.essence - amount // 2)
    elif row.cost is DivineCost.DOMAIN and "strength" not in row.locked:
        row.strength = max(0, row.strength - amount // 2)
    return True


async def wield(ctx: TickContext, row: DivinePowerRow, target_id: int | None = None) -> int:
    amount = VERB_SIGN[row.verb] * await strength_of(ctx, row)
    touched = 0
    for target in await targets_of(ctx, row, target_id):
        if held(target.id):
            continue
        await APPLIERS[row.object](ctx, target, row.object_key, amount, row.holder_node_id)
        touched += 1
    row.last_used_epoch = ctx.epoch
    return touched


async def threatened(ctx: TickContext, row: DivinePowerRow) -> bool:
    targets = await targets_of(ctx, row, None)
    for target in targets:
        pressures = await pressures_of(ctx.session, target.id)
        if max(pressures.get(PressureKind.INSECURITY, 0), pressures.get(PressureKind.HUNGER, 0)) >= ctx.rules.divine_grammar.trigger_at:
            return True
    return False


async def carry_presets(ctx: TickContext) -> int:
    known = {(row.holder_node_id, row.son_preset, row.foreign_preset) for row in await ctx.session.scalars(select(DivinePowerRow))}
    made = 0
    for power in list(await ctx.session.scalars(select(SonPowerRow).order_by(SonPowerRow.son_id, SonPowerRow.slot))):
        if (power.son_id, power.effect, None) not in known and not held(power.son_id):
            spec = SON_PRESETS[power.effect]
            ctx.session.add(preset_row(power.son_id, power.name, spec, ctx.epoch, son=power))
            made += 1
    for gift in list(await ctx.session.scalars(select(ForeignGodPowerRow).order_by(ForeignGodPowerRow.god_id, ForeignGodPowerRow.slot))):
        if (gift.god_id, None, gift.effect) not in known and not held(gift.god_id):
            ctx.session.add(preset_row(gift.god_id, gift.name, FOREIGN_PRESETS[gift.effect], ctx.epoch, foreign=gift))
            made += 1
    return made


def preset_row(
    holder: int, name: str, spec: Grammar, epoch: int, *, son: SonPowerRow | None = None, foreign: ForeignGodPowerRow | None = None
) -> DivinePowerRow:
    row = DivinePowerRow(holder_node_id=holder, name=name, verb=spec.verb, object=spec.object, object_key=spec.key, scope=spec.scope)
    row.mode, row.cost, row.cost_amount, row.cooldown, row.strength, row.domains = spec.mode, DivineCost.ESSENCE, 5, 1, 20, []
    row.son_preset = son.effect if son is not None else None
    row.foreign_preset = foreign.effect if foreign is not None else None
    row.granted_epoch, row.locked = epoch, []
    return row


async def grant_by_worship(ctx: TickContext) -> int:
    table = ctx.rules.divine_grammar
    holding = set(await ctx.session.scalars(select(DivinePowerRow.holder_node_id)))
    granted = 0
    for god in await living_gods(ctx.session):
        if god.id in holding or held(god.id):
            continue
        faithful = await faithful_communities(ctx.session, god.id)
        if len(faithful) < table.grant_faithful:
            continue
        first = domains_of(god)[0]
        row = DivinePowerRow(holder_node_id=god.id, name=f"{DOMAIN_LABELS[first]} of {god.name}", verb=DivineVerb.INSPIRE, object=DivineObject.VALUE)
        row.object_key, row.scope, row.mode = ValueAxis.PIETY.value, DivineScope.COMMUNITY, DivineMode.PASSIVE
        row.cost, row.cost_amount, row.cooldown, row.strength = DivineCost.ESSENCE, 0, 1, table.grant_strength
        row.domains, row.granted_epoch, row.locked = [first.value], ctx.epoch, []
        ctx.session.add(row)
        granted += 1
    return granted


async def keep_powers(ctx: TickContext) -> None:
    ctx.count("divine_presets_carried", await carry_presets(ctx))
    ctx.count("divine_powers_granted", await grant_by_worship(ctx))
    wielded = 0
    for row in list(await ctx.session.scalars(select(DivinePowerRow).order_by(DivinePowerRow.id))):
        if held(row.holder_node_id) or row.son_preset is not None or row.foreign_preset is not None or row.mode is DivineMode.ACTIVE:
            continue
        if row.mode is DivineMode.TRIGGERED and not await threatened(ctx, row):
            continue
        if row.last_used_epoch is not None and ctx.epoch - row.last_used_epoch < row.cooldown:
            continue
        wielded += await wield(ctx, row)
    ctx.count("divine_powers_wielded", wielded)
