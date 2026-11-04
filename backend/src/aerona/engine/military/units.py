from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.techniques import UNIT_TECHNIQUES
from aerona.catalog.units import STYLE_UNITS, UNITS, UnitSpec
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import CoastKind, ScarKind
from aerona.domain.enums.military import ArmourType, ShieldType, Stance, UnitFamily, UnitKind
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import holding
from aerona.engine.lore.research import techniques_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

ARMOUR_BY_METAL = (ArmourType.HIDE, ArmourType.PADDED, ArmourType.MAIL, ArmourType.SCALE, ArmourType.PLATE)
WEAPONS: dict[UnitFamily, tuple[str, ...]] = {
    UnitFamily.INFANTRY: ("spear", "blade"),
    UnitFamily.MISSILE: ("bow", "blade"),
    UnitFamily.MOUNTED: ("spear", "blade"),
    UnitFamily.BEAST: ("claw",),
    UnitFamily.ENGINEER: ("blunt",),
    UnitFamily.MAGIC: ("staff",),
    UnitFamily.NAVAL: ("spear", "bow"),
    UnitFamily.EXOTIC: ("claw",),
}
FALLBACK = UnitKind.LEVY
NAVAL_LADDER = (UnitKind.WARSHIPS, UnitKind.GALLEYS, UnitKind.LONGSHIPS)


def allowed(spec: UnitSpec, community_id: int, knowledge: KnowledgeMap, techniques: set[Technique] | None = None) -> bool:
    if spec.branch is not None and knowledge.level(community_id, spec.branch) < spec.level:
        return False
    needed = UNIT_TECHNIQUES.get(spec.kind)
    return not techniques or needed is None or needed in techniques


async def doctrine_of(session: AsyncSession, community: EntityRow) -> str:
    people = await people_of(session, community)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.martial_style.value if culture is not None else "shieldwall"


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
    techniques = await techniques_of(ctx.session, cid)
    land = await land_of(ctx, community)
    if society is not None and society.share(SocialClass.NOBLE) > 0:
        add(plan, best((UnitKind.HEAVY_CAVALRY,), cid, knowledge, techniques), society.share(SocialClass.NOBLE) / PERCENT * table.noble_share_pct / PERCENT)
    if land is not None and land.coast_kind is not CoastKind.NONE:
        fleet = table.naval_share_pct / PERCENT
        add(plan, best(NAVAL_LADDER, cid, knowledge, techniques), fleet * 3 / 4)
        add(plan, best((UnitKind.FIRE_SHIPS,), cid, knowledge, techniques), fleet / 4)
    add(plan, best((UnitKind.SKYSHIPS,), cid, knowledge, techniques), table.naval_share_pct / PERCENT / 2)
    if await holding(ctx.session, cid, CommodityKind.MOUNTS) > 0:
        beasts = table.beast_share_pct / PERCENT
        add(plan, UnitKind.BEAST_RIDERS, beasts / 2)
        add(plan, UnitKind.WAR_BEASTS, beasts / 2)
        if knowledge.level(cid, KnowledgeBranch.SKY_NAVIGATION) >= 1:
            add(plan, UnitKind.SKY_MOUNTS, beasts / 2)
        if knowledge.level(cid, KnowledgeBranch.MAGIC) >= UNITS[UnitKind.WAR_MAGES].level:
            add(plan, UnitKind.BOUND_BEASTS, beasts / 4)
    magic = table.magic_share_pct / PERCENT
    add(plan, best((UnitKind.WAR_MAGES,), cid, knowledge, techniques), magic)
    add(plan, best((UnitKind.GOLEMS,), cid, knowledge, techniques), magic / 2)
    if allowed(UNITS[UnitKind.NECROMANCERS], cid, knowledge, techniques):
        add(plan, UnitKind.NECROMANCERS, magic / 2)
        add(plan, UnitKind.GHOST_HOST, magic)
    if land is not None and land.scars.get(ScarKind.LEAK_WOUND.value, 0) > 0:
        add(plan, UnitKind.VOID_SPAWN, magic * land.scars[ScarKind.LEAK_WOUND.value] / PERCENT)
    engineers = table.engineer_share_pct / PERCENT
    add(plan, best((UnitKind.SAPPERS,), cid, knowledge, techniques), engineers / 2)
    add(plan, best((UnitKind.SIEGE_ENGINES,), cid, knowledge, techniques), engineers / 2)
    if society is not None and society.share(SocialClass.PRIEST) >= PERCENT / 10:
        add(plan, UnitKind.PRIESTS, table.priest_share_pct / PERCENT)
        add(plan, UnitKind.TEMPLE_GUARD, table.priest_share_pct / PERCENT)
    return plan


async def composition(ctx: TickContext, community: EntityRow, size: int, knowledge: KnowledgeMap) -> dict[UnitKind, int]:
    table = ctx.rules.military_units
    style = await doctrine_of(ctx.session, community)
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    plan: dict[UnitKind, float] = {}
    techniques = await techniques_of(ctx.session, community.id)
    styled = [kind for kind in STYLE_UNITS.get(style, STYLE_UNITS["shieldwall"]) if allowed(UNITS[kind], community.id, knowledge, techniques)]
    for index, kind in enumerate(styled):
        plan[kind] = plan.get(kind, 0.0) + table.style_share_pct / PERCENT / (index + 1) / sum(1 / (i + 1) for i in range(len(styled)))
    for kind, share in (await extras(ctx, community, knowledge, society)).items():
        add(plan, kind, share)
    rest = max(0.0, 1 - sum(plan.values()))
    plan[FALLBACK] = plan.get(FALLBACK, 0.0) + rest
    total = sum(plan.values()) or 1.0
    counts = {kind: round_half_up(size * share / total) for kind, share in plan.items()}
    counts = {kind: count for kind, count in counts.items() if count >= table.min_stack or kind is FALLBACK}
    gap = size - sum(counts.values())
    counts[FALLBACK] = max(0, counts.get(FALLBACK, 0) + gap)
    return {kind: count for kind, count in counts.items() if count > 0}


def outfit(spec: UnitSpec, metallurgy: int, equipment: int) -> tuple[ArmourType, ShieldType, bool]:
    armour = spec.armour
    if armour in ARMOUR_BY_METAL:
        best = ARMOUR_BY_METAL[min(len(ARMOUR_BY_METAL) - 1, metallurgy)]
        armour = armour if ARMOUR_BY_METAL.index(armour) <= ARMOUR_BY_METAL.index(best) else best
    shield = spec.shield
    if shield is ShieldType.SMALL and equipment < PERCENT // 4:
        shield = ShieldType.NONE
    return armour, shield, metallurgy >= 1 or armour is ArmourType.ENCHANTED


async def stacks_of(session: AsyncSession, army_id: int) -> list[ArmyUnitRow]:
    return list(await session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == army_id).order_by(ArmyUnitRow.id)))


async def profile_of(ctx: TickContext, army: EntityRow, owner: EntityRow | None) -> ArmyProfileRow:
    profile = await ctx.session.get(ArmyProfileRow, army.id)
    if profile is not None:
        return profile
    atlas = await RegionAtlas.load(ctx.session)
    doctrine = await doctrine_of(ctx.session, owner) if owner is not None else "shieldwall"
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


async def muster(ctx: TickContext, army: EntityRow, owner: EntityRow | None, knowledge: KnowledgeMap) -> list[ArmyUnitRow]:
    rows = await stacks_of(ctx.session, army.id)
    size = stat(army, "size") or 0
    await profile_of(ctx, army, owner)
    if rows:
        align(army, rows)
        return rows
    if size <= 0 or owner is None:
        return rows
    metallurgy = knowledge.level(owner.id, KnowledgeBranch.METALLURGY)
    equipment = stat(army, "equipment") or 0
    experience = stat(army, "experience") or 0
    morale = stat(army, "morale") or ctx.rules.morale.base
    for kind, count in (await composition(ctx, owner, size, knowledge)).items():
        spec = UNITS[kind]
        armour, shield, helmet = outfit(spec, metallurgy, equipment)
        row = ArmyUnitRow(
            army_entity_id=army.id,
            kind=kind,
            count=count,
            quality=clamp_int(PERCENT // 2 + (equipment - PERCENT // 2) * ctx.rules.military_units.equipment_quality_pct / PERCENT, 0, PERCENT),
            armour=armour,
            shield=shield,
            helmet=helmet,
            weapons=list(WEAPONS[spec.family]),
            experience=clamp_int(experience, 0, PERCENT),
            morale=clamp_int(morale, 0, PERCENT),
            fatigue=0,
            wounded=0,
            condition=PERCENT,
            social_class=spec.social_class,
            origin_entity_id=owner.id,
        )
        ctx.session.add(row)
        rows.append(row)
    await ctx.session.flush()
    return rows


def sync(army: EntityRow, rows: Sequence[ArmyUnitRow], rules: Rules) -> None:
    total = sum(row.count for row in rows)
    if not rows:
        return
    morale = round_half_up(sum(row.morale * row.count for row in rows) / max(1, total))
    experience = round_half_up(sum(row.experience * row.count for row in rows) / max(1, total))
    set_stats(army, size=clamp_int(total, 0, rules.limits.army_soldier_cap), morale=clamp_int(morale, 0, PERCENT), experience=clamp_int(experience, 0, PERCENT))


def take(rows: Sequence[ArmyUnitRow], losses: int) -> int:
    alive = [row for row in rows if row.count > 0]
    total = sum(row.count for row in alive)
    if total <= 0 or losses <= 0:
        return 0
    done = 0
    for index, row in enumerate(sorted(alive, key=lambda item: (-item.count, item.id))):
        part = losses - done if index == len(alive) - 1 else round_half_up(losses * row.count / total)
        part = max(0, min(row.count, part))
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
