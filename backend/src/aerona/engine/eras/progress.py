from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.eras import ERA_FLOORS, ERA_MARKERS, POWDER
from aerona.catalog.techniques import BRANCH_GRAPH, PROGRAMMES, TECHNIQUES, TechniqueSpec
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import HolderLevelRow, HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.eras import TechProgrammeRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.eras import EraChannel, ProgrammeStage
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import TechnologyEra
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import RouteSpec, open_route
from aerona.engine.economy.purse import coin_of, take_coin
from aerona.engine.eras.effects import channel_value, era_techniques, held_by, world_start
from aerona.engine.lore.research import gate_open
from aerona.engine.primitives.folk import folk_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int

COMMUNITIES = (EntityType.SETTLEMENT, EntityType.PEOPLE)
LIVE = (ProgrammeStage.PLANNING, ProgrammeStage.BUILDING, ProgrammeStage.TESTING)
SPECIALISMS = (SkillKind.SCIENCE, SkillKind.ENGINEERING, SkillKind.COMPUTING)
STAGE_WORDS = {ProgrammeStage.BUILDING: "began to build", ProgrammeStage.TESTING: "began to test", ProgrammeStage.COMPLETE: "mastered"}


@dataclass
class EraTally:
    floored: int = 0
    started: int = 0
    advanced: int = 0
    completed: int = 0
    sabotaged: int = 0
    abandoned: int = 0


def requirements_met(spec: TechniqueSpec, known: set[Technique] | frozenset[Technique]) -> bool:
    return all(item in known for item in spec.requires)


def researchable(spec: TechniqueSpec, known: set[Technique] | frozenset[Technique]) -> bool:
    return not spec.programme and requirements_met(spec, known)


async def powder_barred(ctx: TickContext, holder_id: int, technique: Technique) -> bool:
    if technique not in POWDER:
        return False
    holder = await ctx.session.get(EntityRow, holder_id)
    return holder is not None and (await ctx.laws()).has(NaturalLaw.NO_GUNPOWDER, holder.world_id)


async def keep_floors(ctx: TickContext, tally: EraTally) -> None:
    start = await world_start(ctx.session)
    floors = ERA_FLOORS[start]
    order = list(TechnologyEra)
    markers = [marker for era, marker in ERA_MARKERS if order.index(era) <= order.index(start)]
    if not floors and not markers:
        return
    seasoned = set(await ctx.session.scalars(select(HolderLevelRow.holder_entity_id)))
    fresh = await ctx.session.scalars(
        select(EntityRow.id).where(EntityRow.entity_type.in_(list(COMMUNITIES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for holder in list(fresh):
        if holder in seasoned or held(holder):
            continue
        for branch, level in floors.items():
            ctx.session.add(HolderLevelRow(holder_entity_id=holder, branch=branch, level=level, practitioners=0, progress=0))
        known = await held_by(ctx.session, holder)
        for marker in markers:
            if marker not in known:
                ctx.session.add(HolderTechniqueRow(holder_entity_id=holder, technique=marker, since_epoch=ctx.epoch, secret=False))
        tally.floored += 1
    await ctx.session.flush()


async def era_doom(ctx: TickContext) -> float:
    total = 0
    for polity in await ctx.session.scalars(select(PolityProfileRow.polity_entity_id).order_by(PolityProfileRow.polity_entity_id)):
        total += channel_value(ctx.rules, await era_techniques(ctx.session, polity), EraChannel.DOOM)
    return float(total)


def levels_of(rows: list[HolderLevelRow]) -> dict[KnowledgeBranch, int]:
    return {row.branch: row.level for row in rows}


async def within_reach(ctx: TickContext, capital: int, technique: Technique) -> bool:
    spec = TECHNIQUES[technique]
    levels = levels_of(list(await ctx.session.scalars(select(HolderLevelRow).where(HolderLevelRow.holder_entity_id == capital))))
    known = await held_by(ctx.session, capital)
    if technique in known or levels.get(spec.branch, 0) < spec.level or not gate_open(spec.gate, levels):
        return False
    return gate_open(BRANCH_GRAPH[spec.branch], levels) and requirements_met(spec, known)


async def begin(ctx: TickContext, tally: EraTally) -> None:
    running = {(row.polity_entity_id, row.technique) for row in await ctx.session.scalars(select(TechProgrammeRow).where(TechProgrammeRow.stage.in_(LIVE)))}
    for realm in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        if held(realm.polity_entity_id) or realm.capital_entity_id is None:
            continue
        for technique in sorted(PROGRAMMES):
            if (realm.polity_entity_id, technique) in running or not await within_reach(ctx, realm.capital_entity_id, technique):
                continue
            if not ctx.rng(seed_of("programme.begin", realm.polity_entity_id, technique.value, ctx.epoch)).chance(ctx.rules.programmes.start_chance):
                continue
            ctx.session.add(TechProgrammeRow(polity_entity_id=realm.polity_entity_id, technique=technique, started_epoch=ctx.epoch, locked=[]))
            tally.started += 1
    await ctx.session.flush()


async def specialists(ctx: TickContext, polity: int) -> int:
    folk = await folk_among(ctx.session, [polity])
    found = await ctx.session.scalars(
        select(SkillRow.holder_node_id)
        .join(EntityRow, EntityRow.id == SkillRow.holder_node_id)
        .where(
            folk,
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            SkillRow.skill.in_(list(SPECIALISMS)),
            SkillRow.level >= ctx.rules.programmes.specialist_skill,
        )
    )
    return len(set(found))


async def tell(ctx: TickContext, row: TechProgrammeRow, realm: EntityRow, stage: ProgrammeStage) -> None:
    label = TECHNIQUES[row.technique].label.lower()
    await ctx.chronicle(
        ChronicleKind.CIVILIZATION,
        f"{realm.name} {STAGE_WORDS[stage]} {label}.",
        template_key=f"programmes.{stage.value}",
        entity_ids=[realm.id],
        magnitude=ctx.rules.programmes.rumour_magnitude,
    )


async def finish(ctx: TickContext, row: TechProgrammeRow, realm: EntityRow, profile: PolityProfileRow) -> None:
    row.stage, row.finished_epoch = ProgrammeStage.COMPLETE, ctx.epoch
    capital = profile.capital_entity_id
    if capital is not None and row.technique not in await held_by(ctx.session, capital):
        ctx.session.add(HolderTechniqueRow(holder_entity_id=capital, technique=row.technique, since_epoch=ctx.epoch, secret=False))
    if row.technique is Technique.ROCKETRY:
        await launch_route(ctx, realm)
    await tell(ctx, row, realm, ProgrammeStage.COMPLETE)


async def launch_route(ctx: TickContext, realm: EntityRow) -> None:
    from_world = realm.world_id
    if from_world is None:
        return
    joined = set(
        await ctx.session.scalars(select(RouteRow.world_b_id).where(RouteRow.world_a_id == from_world, RouteRow.method == TravelMethod.ROCKETRY))
    ) | set(await ctx.session.scalars(select(RouteRow.world_a_id).where(RouteRow.world_b_id == from_world, RouteRow.method == TravelMethod.ROCKETRY)))
    target = await ctx.session.scalar(select(WorldRow.id).where(WorldRow.id != from_world, WorldRow.id.not_in(joined or {0})).order_by(WorldRow.id).limit(1))
    if target is None:
        return
    spec = RouteSpec(first_world_id=from_world, second_world_id=target, method=TravelMethod.ROCKETRY, controller_id=realm.id)
    await open_route(ctx.session, ctx.rules, ctx.rng(seed_of("rocketry", realm.id, ctx.epoch)), ctx.epoch, spec)


async def sabotage(ctx: TickContext, row: TechProgrammeRow, tally: EraTally) -> None:
    table = ctx.rules.programmes
    spies = list(await ctx.session.scalars(select(SpyNetworkRow.owner_entity_id).where(SpyNetworkRow.target_entity_id == row.polity_entity_id)))
    for owner in sorted(set(spies)):
        if owner == row.polity_entity_id or held(owner):
            continue
        if ctx.rng(seed_of("programme.sabotage", row.id, owner, ctx.epoch)).chance(table.sabotage_chance):
            row.progress = clamp_int(row.progress - table.sabotage_loss, 0, PERCENT)
            row.sabotaged += 1
            tally.sabotaged += 1
            return


async def advance(ctx: TickContext, row: TechProgrammeRow, tally: EraTally) -> None:
    table = ctx.rules.programmes
    realm = await ctx.session.get(EntityRow, row.polity_entity_id)
    profile = await ctx.session.get(PolityProfileRow, row.polity_entity_id)
    if realm is None or profile is None or realm.status is not EntityStatus.CANON:
        row.stage = ProgrammeStage.ABANDONED
        return
    if "progress" not in row.locked:
        short = await coin_of(ctx.session, ctx.rules, realm) - table.treasury_cost < table.abandon_below
        if short or not await take_coin(ctx.session, ctx.rules, realm, table.treasury_cost):
            if "stage" not in row.locked:
                row.stage = ProgrammeStage.ABANDONED
                tally.abandoned += 1
            return
        row.progress = clamp_int(row.progress + table.base_progress + await specialists(ctx, realm.id) * table.specialist_progress, 0, PERCENT)
        await sabotage(ctx, row, tally)
        tally.advanced += 1
    stage = (
        ProgrammeStage.COMPLETE
        if row.progress >= PERCENT
        else ProgrammeStage.TESTING
        if row.progress >= table.testing_at
        else ProgrammeStage.BUILDING
        if row.progress >= table.building_at
        else ProgrammeStage.PLANNING
    )
    if stage is row.stage or "stage" in row.locked:
        return
    row.visibility = clamp_int(row.visibility + PERCENT // 4, 0, PERCENT)
    if stage is ProgrammeStage.COMPLETE:
        await finish(ctx, row, realm, profile)
        tally.completed += 1
        return
    if LIVE.index(stage) > LIVE.index(row.stage):
        await tell(ctx, row, realm, stage)
    row.stage = stage


async def keep_programmes(ctx: TickContext, tally: EraTally) -> None:
    await begin(ctx, tally)
    for row in list(await ctx.session.scalars(select(TechProgrammeRow).where(TechProgrammeRow.stage.in_(LIVE)).order_by(TechProgrammeRow.id))):
        if held(row.polity_entity_id):
            continue
        await advance(ctx, row, tally)
    await ctx.session.flush()


async def keep_eras(ctx: TickContext, tally: EraTally) -> None:
    await keep_floors(ctx, tally)
    await keep_programmes(ctx, tally)
