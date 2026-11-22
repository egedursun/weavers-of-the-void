from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.battle_depth import BASE_DISCIPLINE, WeaponProfile, formation_for
from aerona.catalog.eras import POWDER
from aerona.catalog.techniques import UNIT_TECHNIQUES
from aerona.catalog.units import FAMILY_WEAPONS, KIND_WEAPONS, STYLE_UNITS, SUCCESSORS, UNITS, UnitSpec
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.equipment import ArmyUnitEquipmentRow, UnitDesignTechniqueRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow, UnitDesignRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.ecology import HerdTraining
from aerona.domain.enums.economy import CommodityKind, GoodsFlow, MaterialSlot
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, ScarKind
from aerona.domain.enums.military import ArmourType, MoraleState, ShieldType, Stance, UnitKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw, SocialClass
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.body.customs import people_of
from aerona.engine.collective.makers import makers_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import at_war, solidarity
from aerona.engine.demography.biology import kin_army, profiles_of
from aerona.engine.ecology.domestication import herd_uses, trained_effect, trained_heads
from aerona.engine.economy.materials import node_material
from aerona.engine.economy.stocks import goods_of, holding
from aerona.engine.equipment.field import equip_stack
from aerona.engine.eras.effects import era_of, era_order, technique_era, world_start
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lore.research import techniques_of
from aerona.engine.military.templates import blend, realm_template, weights_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import apportion, clamp_int, round_half_up
from aerona.engine.primitives.stats import set_base_stats, set_stats, stat, stat_or
from aerona.engine.recording.record import record as record_incident
from aerona.engine.regime.book import morale_factor
from aerona.engine.vehicles.fleet import outfit_army
from aerona.rules.registry import Rules

ARMOUR_BY_METAL = (ArmourType.HIDE, ArmourType.PADDED, ArmourType.MAIL, ArmourType.SCALE, ArmourType.PLATE)
METAL_WEAPONS = frozenset({"crossbow", "blade", "pike", "firearm", "launcher", "beam"})
FALLBACK = UnitKind.LEVY
KNOWING = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
MOUNT_NEEDS = {
    UnitKind.LIGHT_CAVALRY: "mount",
    UnitKind.HEAVY_CAVALRY: "mount",
    UnitKind.MOUNTED_ARCHERS: "mount",
    UnitKind.CHARIOTS: "mount",
    UnitKind.BEAST_RIDERS: "mount",
    UnitKind.WAR_BEASTS: "war",
    UnitKind.SKY_RIDERS: "sky_mount",
    UnitKind.BOUND_BEASTS: "bound_beast",
}


async def fieldable(ctx: TickContext, community: EntityRow) -> set[Technique]:
    known = set(await techniques_of(ctx.session, community.id))
    if known & POWDER and (await ctx.laws()).has(NaturalLaw.NO_GUNPOWDER, community.world_id):
        known -= POWDER
    return known


def allowed(spec: UnitSpec, community_id: int, knowledge: KnowledgeMap, techniques: set[Technique] | None = None) -> bool:
    if spec.branch is not None and knowledge.level(community_id, spec.branch) < spec.level:
        return False
    needed = UNIT_TECHNIQUES.get(spec.kind)
    return not techniques or needed is None or needed in techniques


@dataclass(frozen=True)
class EraReach:
    now: TechnologyEra
    began: TechnologyEra


def settled(rules: Rules, era: EraReach, kind: UnitKind) -> bool:
    needed = UNIT_TECHNIQUES.get(kind)
    if needed is None:
        return True
    first = technique_era(needed)
    since = era_order(first) if first is not None else 0
    return since < era_order(era.began) or era_order(era.now) - since >= rules.military_units.successor_settled_eras


def settled_successor(rules: Rules, kind: UnitKind, *, community_id: int, knowledge: KnowledgeMap, techniques: set[Technique], era: EraReach) -> UnitKind:
    current = kind
    seen = {kind}
    while (newer := SUCCESSORS.get(current)) is not None and newer not in seen:
        if not allowed(UNITS[newer], community_id, knowledge, techniques) or not settled(rules, era, newer):
            break
        current = newer
        seen.add(newer)
    return current


async def knower(session: AsyncSession, owner: EntityRow) -> EntityRow:
    if owner.entity_type in KNOWING:
        return owner
    return await people_of(session, owner) or owner


async def era_here(ctx: TickContext, techniques: set[Technique]) -> EraReach:
    began = await world_start(ctx.session)
    return EraReach(era_of(techniques, began), began)


async def modernise(ctx: TickContext, army: EntityRow, owner: EntityRow, rows: Sequence[ArmyUnitRow], knowledge: KnowledgeMap) -> int:
    if held(army.id) or held(owner.id):
        return 0
    profile = await ctx.session.get(ArmyProfileRow, army.id)
    if profile is not None and "doctrine" not in profile.locked:
        profile.doctrine = await doctrine_of(ctx.session, owner)
    knowing = await knower(ctx.session, owner)
    techniques = await fieldable(ctx, knowing)
    era = await era_here(ctx, techniques)
    metallurgy = knowledge.level(knowing.id, KnowledgeBranch.METALLURGY)
    equipment = stat(army, "equipment") or 0
    moved = 0
    for row in rows:
        newer = settled_successor(ctx.rules, row.kind, community_id=knowing.id, knowledge=knowledge, techniques=techniques, era=era)
        if newer is row.kind or "kind" in (row.locked or []):
            continue
        older = row.kind
        spec = UNITS[newer]
        row.kind, row.design_id = newer, None
        row.armour, row.shield, row.helmet = outfit(spec, metallurgy, equipment)
        row.weapons = weapon_mix(spec, metallurgy)
        row.social_class = spec.social_class
        await equip_stack(ctx, row, spec, owner, None)
        await record_incident(
            ctx,
            "military.stack_modernised",
            roles={IncidentRole.SUBJECT: army.id, IncidentRole.OWNER: owner.id},
            facts={"from_kind": older, "to_kind": newer, "soldiers": row.count},
        )
        moved += 1
    return moved


async def doctrine_of(session: AsyncSession, community: EntityRow) -> MartialStyle:
    people = await people_of(session, community)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.martial_style if culture is not None else MartialStyle.SHIELDWALL


def best(kinds: tuple[UnitKind, ...], community_id: int, knowledge: KnowledgeMap, techniques: set[Technique] | None = None) -> UnitKind | None:
    return next((kind for kind in kinds if allowed(UNITS[kind], community_id, knowledge, techniques)), None)


def add(plan: dict[UnitKind, float], kind: UnitKind | None, share: float) -> None:
    if kind is not None and share > 0:
        plan[kind] = plan.get(kind, 0.0) + share


async def land_of(ctx: TickContext, community: EntityRow) -> RegionEnvironmentRow | None:
    region_id = (await RegionAtlas.load(ctx.session)).top_region(community.id)
    return await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None


async def extras(ctx: TickContext, community: EntityRow, knowledge: KnowledgeMap, society: CommunitySocietyRow | None) -> dict[UnitKind, float]:
    table = ctx.rules.military_units
    plan: dict[UnitKind, float] = {}
    cid = community.id
    techniques = await fieldable(ctx, community)
    land = await land_of(ctx, community)
    if society is not None and society.share(SocialClass.NOBLE) > 0:
        add(plan, best((UnitKind.HEAVY_CAVALRY,), cid, knowledge, techniques), society.share(SocialClass.NOBLE) / PERCENT * table.noble_share_pct / PERCENT)
    if land is not None and land.coast_kind is not CoastKind.NONE:
        fleet = table.naval_share_pct / PERCENT
        add(plan, best((UnitKind.NAVAL_CREW,), cid, knowledge, techniques), fleet * 3 / 4)
        add(plan, best((UnitKind.MARINES,), cid, knowledge, techniques), fleet / 4)
    add(plan, best((UnitKind.SKY_CREW,), cid, knowledge, techniques), table.naval_share_pct / PERCENT / 2)
    add(plan, best((UnitKind.VOID_CREW,), cid, knowledge, techniques), table.naval_share_pct / PERCENT / 2)
    if await holding(ctx.session, cid, CommodityKind.MOUNTS) > 0:
        beasts = table.beast_share_pct / PERCENT
        add(plan, UnitKind.BEAST_RIDERS, beasts / 2)
        add(plan, UnitKind.WAR_BEASTS, beasts / 2)
        if knowledge.level(cid, KnowledgeBranch.SKY_NAVIGATION) >= 1:
            add(plan, UnitKind.SKY_RIDERS, beasts / 2)
        if knowledge.level(cid, KnowledgeBranch.MAGIC) >= UNITS[UnitKind.BATTLE_CASTERS].level:
            add(plan, UnitKind.BOUND_BEASTS, beasts / 4)
    magic = table.magic_share_pct / PERCENT
    add(plan, best((UnitKind.BATTLE_CASTERS,), cid, knowledge, techniques), magic)
    add(plan, best((UnitKind.CONSTRUCTS,), cid, knowledge, techniques), magic / 2)
    if allowed(UNITS[UnitKind.SUMMONERS], cid, knowledge, techniques):
        add(plan, UnitKind.SUMMONERS, magic / 2)
        add(plan, UnitKind.SUMMONED_HOST, magic)
    if land is not None and land.scars.get(ScarKind.LEAK_WOUND.value, 0) > 0:
        add(plan, UnitKind.SUMMONED_HOST, magic * land.scars[ScarKind.LEAK_WOUND.value] / PERCENT)
    engineers = table.engineer_share_pct / PERCENT
    add(plan, best((UnitKind.SAPPERS,), cid, knowledge, techniques), engineers / 2)
    add(plan, best((UnitKind.ENGINEERS,), cid, knowledge, techniques), engineers / 4)
    add(plan, best((UnitKind.ARTILLERY_CREW, UnitKind.SIEGE_CREW), cid, knowledge, techniques), engineers / 2)
    add(plan, best((UnitKind.VEHICLE_CREW,), cid, knowledge, techniques), engineers / 2)
    if society is not None and society.share(SocialClass.PRIEST) >= PERCENT / 10:
        add(plan, UnitKind.SUPPORT_CASTERS, table.priest_share_pct / PERCENT)
        add(plan, UnitKind.GUARD_INFANTRY, table.priest_share_pct / PERCENT)
    add(plan, best((UnitKind.MEDICS,), cid, knowledge, techniques), table.medic_share_pct / PERCENT)
    electronic = table.electronic_share_pct / PERCENT
    add(plan, best((UnitKind.SIGNALS_TROOPS,), cid, knowledge, techniques), electronic / 2)
    add(plan, best((UnitKind.DRONE_OPERATORS,), cid, knowledge, techniques), electronic / 2)
    add(plan, best((UnitKind.PILOTS,), cid, knowledge, techniques), table.air_share_pct / PERCENT)
    add(plan, best((UnitKind.DROP_TROOPS,), cid, knowledge, techniques), table.naval_share_pct / PERCENT / 4)
    add(plan, best((UnitKind.SPECIAL_FORCES,), cid, knowledge, techniques), table.special_share_pct / PERCENT)
    add(plan, best((UnitKind.PEACEKEEPERS,), cid, knowledge, techniques), table.peace_share_pct / PERCENT)
    if await at_war(ctx, {cid}):
        add(plan, UnitKind.PARTISANS, table.partisan_share_pct / PERCENT)
    return plan


async def composition(ctx: TickContext, community: EntityRow, size: int, knowledge: KnowledgeMap) -> dict[UnitKind, int]:
    table = ctx.rules.military_units
    style = await doctrine_of(ctx.session, community)
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    plan: dict[UnitKind, float] = {}
    techniques = await fieldable(ctx, community)
    styled = [kind for kind in STYLE_UNITS.get(style, STYLE_UNITS["shieldwall"]) if allowed(UNITS[kind], community.id, knowledge, techniques)]
    for index, kind in enumerate(styled):
        plan[kind] = plan.get(kind, 0.0) + table.style_share_pct / PERCENT / (index + 1) / sum(1 / (i + 1) for i in range(len(styled)))
    for kind, share in (await extras(ctx, community, knowledge, society)).items():
        add(plan, kind, share)
    template = await realm_template(ctx, community.id)
    if template is not None:
        drawn = {kind: weight for kind, weight in weights_of(template).items() if allowed(UNITS[kind], community.id, knowledge, techniques)}
        plan = blend(ctx.rules, plan, drawn)
    biology, culture = await profiles_of(ctx.session, community)
    plan = kin_army(ctx.rules, biology, culture, plan, beasts=await herd_uses(ctx, community.id), mount_needs=MOUNT_NEEDS)
    drilled = trained_effect(ctx.rules, await trained_heads(ctx.session, community.id, HerdTraining.WAR))
    if drilled > 0:
        add(plan, UnitKind.WAR_BEASTS, ctx.rules.husbandry.war_share_pct / PERCENT * drilled)
    for kind, successor in SUCCESSORS.items():
        if kind in plan and allowed(UNITS[successor], community.id, knowledge, techniques):
            moved = plan[kind] * table.successor_share_pct / PERCENT
            plan[kind] -= moved
            add(plan, successor, moved)
    knowing = await knower(ctx.session, community)
    known = techniques if knowing is community else await fieldable(ctx, knowing)
    era = await era_here(ctx, known)
    for kind in sorted(plan):
        newer = settled_successor(ctx.rules, kind, community_id=knowing.id, knowledge=knowledge, techniques=known, era=era)
        if newer is not kind:
            add(plan, newer, plan.pop(kind))
    fallback = settled_successor(ctx.rules, FALLBACK, community_id=knowing.id, knowledge=knowledge, techniques=known, era=era)
    rest = max(0.0, 1 - sum(plan.values()))
    plan[fallback] = plan.get(fallback, 0.0) + rest
    total = sum(plan.values()) or 1.0
    counts = {kind: round_half_up(size * share / total) for kind, share in plan.items()}
    counts = {kind: count for kind, count in counts.items() if count >= table.min_stack or kind is fallback}
    gap = size - sum(counts.values())
    counts[fallback] = max(0, counts.get(fallback, 0) + gap)
    return {kind: count for kind, count in counts.items() if count > 0}


def weapon_mix(spec: UnitSpec, metallurgy: int) -> list[str]:
    mix = KIND_WEAPONS.get(spec.kind) or FAMILY_WEAPONS[spec.family]
    allowed = [weapon for weapon in mix if metallurgy >= 1 or weapon not in METAL_WEAPONS]
    return list(allowed or ("blunt",))


async def rearm(ctx: TickContext, army: EntityRow, owner: EntityRow | None, rows: Sequence[ArmyUnitRow]) -> int:
    table = ctx.rules.battle_magic
    for row in rows:
        if "condition" not in (row.locked or []):
            row.condition = clamp_int(row.condition - table.wear_per_season, 0, PERCENT)
    if owner is None:
        return 0
    for row in rows:
        design = await ctx.session.get(UnitDesignRow, row.design_id) if row.design_id is not None else None
        await equip_stack(ctx, row, design_spec(design) if design is not None else UNITS[row.kind], owner, design)
    worn = [row for row in rows if row.count > 0 and row.condition < PERCENT and "condition" not in (row.locked or [])]
    wanted = sum(row.count for row in worn) // max(1, ctx.rules.materials.soldiers_per_kit)
    if not worn or wanted <= 0 or await holding(ctx.session, owner.id, CommodityKind.WEAPONS) <= 0:
        return 0
    taken = await goods_of(ctx.session, ctx.epoch).take_units(owner.id, CommodityKind.WEAPONS, wanted, GoodsFlow.WAR)
    share = min(1.0, taken / wanted)
    for row in worn:
        row.condition = clamp_int(row.condition + round_half_up(table.rearm_per_season * share), 0, PERCENT)
    return taken


def outfit(spec: UnitSpec, metallurgy: int, equipment: int) -> tuple[ArmourType, ShieldType, bool]:
    armour = spec.armour
    if armour in ARMOUR_BY_METAL:
        best = ARMOUR_BY_METAL[min(len(ARMOUR_BY_METAL) - 1, metallurgy)]
        armour = armour if ARMOUR_BY_METAL.index(armour) <= ARMOUR_BY_METAL.index(best) else best
    shield = spec.shield
    if shield is ShieldType.SMALL and equipment < PERCENT // 4:
        shield = ShieldType.NONE
    return armour, shield, metallurgy >= 1 or armour is ArmourType.ENCHANTED


@memoized(ArmyUnitRow)
async def stack_rows(session: AsyncSession, army_id: int) -> tuple[ArmyUnitRow, ...]:
    return tuple(await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id).order_by(ArmyUnitRow.id)))


async def stacks_of(session: AsyncSession, army_id: int) -> list[ArmyUnitRow]:
    return list(await stack_rows(session, army_id))


async def profile_of(ctx: TickContext, army: EntityRow, owner: EntityRow | None) -> ArmyProfileRow:
    profile = await ctx.session.get(ArmyProfileRow, army.id)
    if profile is not None:
        return profile
    atlas = await RegionAtlas.load(ctx.session)
    doctrine = await doctrine_of(ctx.session, owner) if owner is not None else MartialStyle.SHIELDWALL
    profile = ArmyProfileRow(
        army_entity_id=army.id,
        region_entity_id=atlas.top_region(army.id) or (atlas.top_region(owner.id) if owner is not None else None),
        stance=Stance.MARCH,
        doctrine=doctrine,
        supply_days=ctx.rules.logistics.supply_days,
        supply_line=[],
        cohesion=70,
        war_chest=0,
        disease=0,
        loot=0,
        entrenchment=0,
        forced_march=False,
        baggage=0,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(profile)
    return profile


def drill_fields(rules: Rules, spec: UnitSpec) -> dict[str, object]:
    return {
        "organisation": PERCENT,
        "discipline": BASE_DISCIPLINE[spec.kind],
        "ammunition": rules.battle_depth.volleys_carried if spec.missile > 0 else 0,
        "formation": formation_for(spec.kind, spec.family),
        "morale_state": MoraleState.STEADY,
        "missing": 0,
    }


def design_spec(row: UnitDesignRow) -> UnitSpec:
    base = UNITS[row.base_kind]
    return UnitSpec(
        kind=row.base_kind,
        family=row.family,
        label=row.name,
        melee=row.melee,
        missile=row.missile,
        defence=row.defence,
        speed=row.speed,
        mass=row.mass,
        cost=row.cost,
        upkeep=row.upkeep,
        armour=row.armour,
        shield=row.shield,
        branch=base.branch,
        level=base.level,
        social_class=row.social_class,
        counters_charge=row.counters_charge,
        terror=row.terror,
        flying=row.flying,
        profile=WeaponProfile(row.reach, row.volleys, row.accuracy, row.piercing),
    )


async def designs_of(session: AsyncSession, owner: EntityRow) -> list[UnitDesignRow]:
    makers = await makers_of(session, owner)
    rows = sorted(
        await session.scalars(select(UnitDesignRow).where(UnitDesignRow.owner_entity_id.in_(makers), UnitDesignRow.retired.is_(False))),
        key=lambda row: (makers.index(row.owner_entity_id or owner.id), row.id),
    )
    needs: dict[int, set[Technique]] = {}
    for design_id, technique in await session.execute(
        select(UnitDesignTechniqueRow.design_id, UnitDesignTechniqueRow.technique).where(UnitDesignTechniqueRow.design_id.in_([row.id for row in rows]))
    ):
        needs.setdefault(design_id, set()).add(technique)
    known = {technique for maker in makers for technique in await techniques_of(session, maker)} if needs else set()
    return [row for row in rows if needs.get(row.id, set()) <= known]


def design_worth(design: UnitDesignRow, style: str) -> int:
    favoured = design.base_kind in STYLE_UNITS.get(style, ())
    return design.melee + design.missile + design.defence + design.terror + (PERCENT if favoured else 0) + (PERCENT // 4 if design.counters_charge else 0)


def armour_allowed(armour: ArmourType, metallurgy: int) -> bool:
    if armour not in ARMOUR_BY_METAL:
        return armour is not ArmourType.ENCHANTED or metallurgy >= len(ARMOUR_BY_METAL) - 1
    return ARMOUR_BY_METAL.index(armour) <= min(len(ARMOUR_BY_METAL) - 1, metallurgy)


async def choose_design(
    ctx: TickContext, owner: EntityRow, kind: UnitKind, count: int, *, metallurgy: int, designs: Sequence[UnitDesignRow]
) -> UnitDesignRow | None:
    same = [design for design in designs if design.base_kind is kind]
    fitting = [design for design in same if armour_allowed(design.armour, metallurgy)]
    if not fitting:
        return same[0] if same else None
    kits = count // max(1, ctx.rules.materials.soldiers_per_kit)
    stocked = await holding(ctx.session, owner.id, CommodityKind.WEAPONS) >= kits
    base = UNITS[kind].cost
    affordable = [design for design in fitting if design.cost <= base or stocked]
    if not affordable:
        return fitting[0]
    style = await doctrine_of(ctx.session, owner)
    return max(affordable, key=lambda design: (design_worth(design, style), -design.id))


async def muster(ctx: TickContext, army: EntityRow, owner: EntityRow | None, knowledge: KnowledgeMap) -> list[ArmyUnitRow]:
    rows = await stacks_of(ctx.session, army.id)
    size = stat(army, "size") or 0
    await profile_of(ctx, army, owner)
    if rows:
        if owner is not None:
            await modernise(ctx, army, owner, rows, knowledge)
        align(army, rows)
        return rows
    if size <= 0 or owner is None:
        return rows
    metallurgy = knowledge.level(owner.id, KnowledgeBranch.METALLURGY)
    equipment = stat(army, "equipment") or 0
    experience = stat(army, "experience") or 0
    morale = clamp_int(
        stat_or(army, "morale", ctx.rules.morale.base)
        * await solidarity(ctx.session, owner, ctx.rules.asabiyya.morale_weight)
        * await morale_factor(ctx.session, ctx.rules, owner.id),
        0,
        PERCENT,
    )
    issued = await node_material(ctx.session, army.id, MaterialSlot.WEAPONS)
    material = issued.material.value if issued is not None and issued.material is not None else None
    condition = clamp_int(PERCENT // 2 + equipment // 2, 0, PERCENT)
    designs = await designs_of(ctx.session, owner)
    for kind, count in (await composition(ctx, owner, size, knowledge)).items():
        design = await choose_design(ctx, owner, kind, count, metallurgy=metallurgy, designs=designs)
        spec = design_spec(design) if design is not None else UNITS[kind]
        armour, shield, helmet = outfit(spec, metallurgy, equipment)
        row = ArmyUnitRow(
            army_entity_id=army.id,
            kind=kind,
            count=count,
            quality=clamp_int(PERCENT // 2 + (equipment - PERCENT // 2) * ctx.rules.military_units.equipment_quality_pct / PERCENT, 0, PERCENT),
            armour=armour,
            shield=shield,
            helmet=helmet,
            weapons=weapon_mix(spec, metallurgy),
            material=material,
            experience=clamp_int(experience, 0, PERCENT),
            morale=clamp_int(morale, 0, PERCENT),
            fatigue=0,
            wounded=0,
            condition=condition,
            social_class=spec.social_class,
            origin_entity_id=owner.id,
            design_id=design.id if design is not None else None,
            locked=[],
            **drill_fields(ctx.rules, spec),
        )
        ctx.session.add(row)
        rows.append(row)
    await ctx.session.flush()
    for row in rows:
        design = next((item for item in designs if item.id == row.design_id), None)
        await equip_stack(ctx, row, design_spec(design) if design is not None else UNITS[row.kind], owner, design)
    await outfit_army(ctx, army, owner, rows, knowledge)
    return rows


def sync(army: EntityRow, rows: Sequence[ArmyUnitRow], rules: Rules) -> None:
    total = sum(row.count for row in rows)
    if not rows:
        return
    morale = round_half_up(sum(row.morale * row.count for row in rows) / max(1, total))
    experience = round_half_up(sum(row.experience * row.count for row in rows) / max(1, total))
    set_base_stats(
        army, size=clamp_int(total, 0, rules.limits.army_soldier_cap), morale=clamp_int(morale, 0, PERCENT), experience=clamp_int(experience, 0, PERCENT)
    )


def take(rows: Sequence[ArmyUnitRow], losses: int) -> int:
    alive = [row for row in rows if row.count > 0]
    total = sum(row.count for row in alive)
    if total <= 0 or losses <= 0:
        return 0
    done = 0
    ordered = sorted(alive, key=lambda item: (-item.count, item.id))
    parts = apportion(losses, {index: float(row.count) for index, row in enumerate(ordered)})
    for index, row in enumerate(ordered):
        part = max(0, min(row.count, parts.get(index, 0)))
        row.count -= part
        done += part
    return done


def regrow(rows: Sequence[ArmyUnitRow], added: int) -> None:
    if added <= 0 or not rows:
        return
    biggest = max(rows, key=lambda item: (item.count, -item.id))
    biggest.count += added


def align(army: EntityRow, rows: Sequence[ArmyUnitRow]) -> None:
    size = stat(army, "size") or 0
    total = sum(row.count for row in rows)
    if size < total:
        take(rows, total - size)
    elif size > total:
        regrow(rows, size - total)
    for key in ("morale", "experience"):
        wanted = stat(army, key)
        if wanted is None or not rows:
            continue
        current = round_half_up(sum(getattr(row, key) * row.count for row in rows) / max(1, sum(row.count for row in rows)))
        if wanted != current:
            for row in rows:
                setattr(row, key, clamp_int(getattr(row, key) + wanted - current, 0, PERCENT))


async def resize(session: AsyncSession, rules: Rules, army: EntityRow, size: int) -> int:
    soldiers = clamp_int(size, 0, rules.limits.army_soldier_cap)
    set_stats(army, size=soldiers)
    rows = await stacks_of(session, army.id)
    if rows:
        align(army, rows)
    return soldiers


async def retire_stacks(session: AsyncSession, army_id: int) -> int:
    cleared = 0
    for row in await stacks_of(session, army_id):
        cleared += row.count
        row.count = 0
        row.wounded = 0
    return cleared


async def reconcile_sizes(ctx: TickContext) -> dict[str, int]:
    found = {"aligned": 0, "mustered": 0, "retired": 0, "modernised": 0}
    knowledge: KnowledgeMap | None = None
    for row in list(await ctx.session.scalars(select(ArmyRow).order_by(ArmyRow.entity_id))):
        army = await ctx.session.get(EntityRow, row.entity_id)
        if army is None:
            continue
        stacks = await stacks_of(ctx.session, army.id)
        if army.status is not EntityStatus.CANON or row.disbanded_epoch is not None:
            if any(stack.count for stack in stacks) or (stat(army, "size") or 0):
                with flowing(FlowCategory.DEATH):
                    set_stats(army, size=0)
                await retire_stacks(ctx.session, army.id)
                found["retired"] += 1
            continue
        size = stat(army, "size") or 0
        if not stacks:
            if size > 0:
                knowledge = knowledge or await KnowledgeMap.load(ctx.session)
                await muster(ctx, army, await ctx.session.get(EntityRow, row.owner_entity_id), knowledge)
                found["mustered"] += 1
            continue
        owner = await ctx.session.get(EntityRow, row.owner_entity_id) if row.owner_entity_id is not None else None
        if owner is not None:
            knowledge = knowledge or await KnowledgeMap.load(ctx.session)
            found["modernised"] += await modernise(ctx, army, owner, stacks, knowledge)
        if sum(stack.count for stack in stacks) != size:
            align(army, stacks)
            found["aligned"] += 1
    await ctx.session.flush()
    return found


async def equip_bare_stacks(ctx: TickContext) -> int:
    carried = select(ArmyUnitEquipmentRow.unit_id).distinct()
    statement = (
        select(ArmyUnitRow, ArmyRow.owner_entity_id)
        .join(ArmyRow, ArmyRow.entity_id == ArmyUnitRow.army_entity_id)
        .where(ArmyRow.disbanded_epoch.is_(None), ArmyUnitRow.count > 0, ArmyUnitRow.id.not_in(carried))
        .order_by(ArmyUnitRow.id)
    )
    issued = 0
    for unit, owner_id in (await ctx.session.execute(statement)).all():
        owner = await ctx.session.get(EntityRow, owner_id) if owner_id is not None else None
        if owner is None:
            continue
        design = await ctx.session.get(UnitDesignRow, unit.design_id) if unit.design_id is not None else None
        issued += await equip_stack(ctx, unit, design_spec(design) if design is not None else UNITS[unit.kind], owner, design)
    return issued
