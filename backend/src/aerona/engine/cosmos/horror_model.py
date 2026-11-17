from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.core.grammar import several
from aerona.core.total import total
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.horror import HorrorEventRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.horror import HorrorEffect, HorrorScope, HorrorSense, HorrorSource, HorrorTarget
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import DARK_STAR_TYPES
from aerona.domain.models.entity_stats import KnowledgeStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import open_alignment
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.cosmos.worldlife import hot_regions
from aerona.engine.mortal.standing import add_stress
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.primitives.queries import canon, subtree
from aerona.engine.primitives.records import RecordSpec, open_record, retire
from aerona.engine.primitives.stats import POPULATION_KEY, scale_stat, shift_stat, stat_or
from aerona.engine.recording.record import record

PERCEIVERS = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.MORTAL, EntityType.CULT, EntityType.FACTION})
ERASURE_GUARDS = frozenset({*COMMUNITY_TYPES, EntityType.MORTAL})
REVEALED_SUBTYPE = "knowledge from outside the world"
LEGACY_REVEALED_SUBTYPES = frozenset({REVEALED_SUBTYPE, "whispers from beyond"})
EFFECT_DIRECTION: Mapping[HorrorEffect, int] = total(
    HorrorEffect,
    {
        HorrorEffect.SUPPRESS: -1,
        HorrorEffect.INVERT: -1,
        HorrorEffect.DISTORT: -1,
        HorrorEffect.MULTIPLY: 1,
        HorrorEffect.TAKE: -1,
        HorrorEffect.REVEAL: 1,
        HorrorEffect.MARK: 0,
    },
)
EFFECT_PAST: Mapping[HorrorEffect, str] = total(
    HorrorEffect,
    {
        HorrorEffect.SUPPRESS: "suppressed",
        HorrorEffect.INVERT: "inverted",
        HorrorEffect.DISTORT: "distorted",
        HorrorEffect.MULTIPLY: "multiplied",
        HorrorEffect.TAKE: "took",
        HorrorEffect.REVEAL: "revealed",
        HorrorEffect.MARK: "marked",
    },
)
PERCEIVED: Mapping[HorrorSense, bool] = total(
    HorrorSense,
    {
        HorrorSense.SEEN: True,
        HorrorSense.HEARD: True,
        HorrorSense.FELT: True,
        HorrorSense.DREAMED: True,
        HorrorSense.ABSENT: True,
        HorrorSense.NOT_PERCEIVED: False,
    },
)
SCOPE_TYPES: Mapping[HorrorScope, frozenset[EntityType] | None] = total(
    HorrorScope,
    {
        HorrorScope.PERSON: frozenset({EntityType.MORTAL}),
        HorrorScope.COMMUNITY: frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE}),
        HorrorScope.REGION: frozenset({EntityType.REGION}),
        HorrorScope.WORLD: None,
    },
)


@dataclass(frozen=True)
class HorrorSpec:
    target: HorrorTarget
    effect: HorrorEffect
    scope: HorrorScope = HorrorScope.WORLD
    sense: HorrorSense = HorrorSense.SEEN
    source: HorrorSource = HorrorSource.UNKNOWN


HORROR_PRESETS: Mapping[str, HorrorSpec] = {
    "time_multiplied": HorrorSpec(HorrorTarget.TIME, HorrorEffect.MULTIPLY, HorrorScope.WORLD, HorrorSense.SEEN, HorrorSource.PHENOMENON),
    "minds_marked": HorrorSpec(HorrorTarget.MINDS, HorrorEffect.MARK, HorrorScope.WORLD, HorrorSense.SEEN, HorrorSource.OUTER_BEING),
    "language_taken": HorrorSpec(HorrorTarget.LANGUAGE, HorrorEffect.TAKE, HorrorScope.WORLD, HorrorSense.ABSENT, HorrorSource.UNKNOWN),
    "dead_taken": HorrorSpec(HorrorTarget.THE_DEAD, HorrorEffect.TAKE, HorrorScope.WORLD, HorrorSense.SEEN, HorrorSource.UNKNOWN),
    "place_taken": HorrorSpec(HorrorTarget.PLACE, HorrorEffect.TAKE, HorrorScope.REGION, HorrorSense.ABSENT, HorrorSource.RIFT),
    "light_suppressed": HorrorSpec(HorrorTarget.LIGHT, HorrorEffect.SUPPRESS, HorrorScope.WORLD, HorrorSense.SEEN, HorrorSource.UNKNOWN),
    "minds_revealed": HorrorSpec(HorrorTarget.MINDS, HorrorEffect.REVEAL, HorrorScope.PERSON, HorrorSense.HEARD, HorrorSource.OUTER_BEING),
}


async def subject_of(ctx: TickContext, world: WorldRow, scope: HorrorScope) -> EntityRow | None:
    kinds = SCOPE_TYPES[scope]
    if kinds is None:
        return None
    found = await canon(ctx.session, kinds, world.id)
    if scope is HorrorScope.REGION:
        hot = set(await hot_regions(ctx, world.id))
        found = sorted(found, key=lambda item: (item.id not in hot, item.id))
    else:
        found = sorted(found, key=lambda item: (-(item.importance or 0), -stat_or(item, "intellect", 0), item.id))
    return found[0] if found else None


async def within(ctx: TickContext, world: WorldRow, row: HorrorEventRow, types: frozenset[EntityType] | None) -> list[EntityRow]:
    found = await canon(ctx.session, types, world.id)
    if row.subject_node_id is None:
        return [item for item in found if not held(item.id)]
    reach = {row.subject_node_id} | {item.id for item in await subtree(ctx.session, row.subject_node_id)}
    return [item for item in found if item.id in reach and not held(item.id)]


async def reachable(ctx: TickContext, world: WorldRow, row: HorrorEventRow, types: frozenset[EntityType], *, anywhere: bool) -> list[EntityRow]:
    if anywhere:
        return [item for item in await canon(ctx.session, types, world.id) if not held(item.id)]
    return await within(ctx, world, row, types)


async def on_light(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    star = await ctx.session.get(StarRow, world.star_id) if world.star_id is not None else None
    if star is None or star.star_type in DARK_STAR_TYPES or direction == 0 or held(star.id):
        return None
    before = star.brightness
    star.brightness = max(0, min(PERCENT_MAX, star.brightness + direction * ctx.rules.cosmic_horror.light_loss))
    return f"the light of {star.name} went from {before} to {star.brightness}"


async def on_stress(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    mortals = await within(ctx, world, row, frozenset({EntityType.MORTAL}))
    for mortal in mortals:
        await add_stress(ctx.session, mortal.id, ctx.rules.cosmic_horror.horror_stress * max(1, abs(direction)), ctx.epoch)
    return f"{several(len(mortals), 'mortal was', 'mortals were')} troubled" if mortals else None


async def on_weather(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    if direction == 0:
        return None
    communities = await within(ctx, world, row, frozenset(COMMUNITY_TYPES))
    for community in communities:
        shift_stat(community, "prosperity", direction * ctx.rules.cosmic_horror.weather_shift, 0)
    return f"the prosperity of {several(len(communities), 'community', 'communities')} moved by the weather" if communities else None


async def on_time(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    horror = ctx.rules.cosmic_horror
    if direction > 0:
        await open_alignment(ctx, [TravelMethod.ANCIENT_GATE, TravelMethod.SLINGSHOT_ORBIT], danger_add=horror.alignment_route_danger)
        for item in await WorldRepository(ctx.session).all_worlds():
            if not held(item.id):
                item.leakage = min(PERCENT_MAX, item.leakage + horror.alignment_leak)
        return "every ancient gate and slingshot route opened at once and leakage rose in every world"
    if direction < 0 and not held(world.id):
        world.leakage = min(PERCENT_MAX, world.leakage + horror.alignment_leak)
        return f"the leakage of {world.name} rose to {world.leakage}"
    return None


async def on_memory(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    if direction >= 0:
        return None
    holders = [item.id for item in await within(ctx, world, row, frozenset({EntityType.MORTAL, EntityType.PEOPLE, EntityType.SETTLEMENT}))]
    if not holders:
        return None
    rows = list(await ctx.session.scalars(select(MemoryRow.id).where(MemoryRow.holder_node_id.in_(holders)).order_by(MemoryRow.id)))
    lost = rows[: len(rows) * ctx.rules.cosmic_horror.memory_loss_pct // PERCENT]
    if lost:
        await ctx.session.execute(delete(MemoryRow).where(MemoryRow.id.in_(lost)))
    return f"{several(len(lost), 'memory was', 'memories were')} lost" if lost else None


async def revealed_knowledge(ctx: TickContext, world: WorldRow) -> EntityRow:
    horror = ctx.rules.cosmic_horror
    known = [item for item in await canon(ctx.session, [EntityType.KNOWLEDGE], world.id) if item.subtype in LEGACY_REVEALED_SUBTYPES]
    if known:
        return known[0]
    return await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            name=f"Knowledge from Outside ({world.name})",
            entity_type=EntityType.KNOWLEDGE,
            body="Knowledge that came from outside the world.",
            stats=KnowledgeStats(level=horror.revealed_knowledge_level, spread=0),
            power=horror.revealed_knowledge_power,
            world_id=world.id,
            subtype=REVEALED_SUBTYPE,
            knowledge_branch=KnowledgeBranch.FORBIDDEN,
        ),
    )


async def reveal(ctx: TickContext, world: WorldRow, row: HorrorEventRow) -> str | None:
    knowledge = await revealed_knowledge(ctx, world)
    heard = set(
        await ctx.session.scalars(
            select(BondRow.source_node_id).where(BondRow.target_node_id == knowledge.id, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE)
        )
    )
    anywhere = row.scope is HorrorScope.PERSON
    mortals = [item for item in await reachable(ctx, world, row, frozenset({EntityType.MORTAL}), anywhere=anywhere) if item.id not in heard]
    communities = [item for item in await reachable(ctx, world, row, frozenset(COMMUNITY_TYPES), anywhere=anywhere) if item.id not in heard]
    if mortals:
        listener = max(mortals, key=lambda item: (stat_or(item, "intellect", 0), -item.id))
    elif communities:
        listener = max(communities, key=lambda item: (item.importance or 0, -item.id))
    else:
        return None
    if not await teach(ctx, listener.id, knowledge, "learned it from outside the world"):
        return None
    if anywhere and "subject_node_id" not in row.locked:
        row.subject_node_id = listener.id
    shift_sanity(ctx.rules, listener, -ctx.rules.cosmic_horror.revealed_sanity_loss)
    return f"{listener.name} gained knowledge from outside the world"


async def on_language(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    if direction > 0:
        return await reveal(ctx, world, row)
    if direction == 0:
        return None
    rng = ctx.rng(f"horror.language.{row.id}")
    forgotten = 0
    for language in await canon(ctx.session, [EntityType.LANGUAGE], world.id):
        if held(language.id):
            continue
        found = list(await ctx.session.scalars(select(LexemeRow.id).where(LexemeRow.language_entity_id == language.id).order_by(LexemeRow.id)))
        lost = rng.sample(found, len(found) * ctx.rules.cosmic_horror.language_loss_pct // PERCENT)
        if lost:
            await ctx.session.execute(delete(LexemeRow).where(LexemeRow.id.in_(lost)))
            forgotten += len(lost)
    return f"{several(forgotten, 'word was', 'words were')} forgotten" if forgotten else None


async def on_bodies(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    horror = ctx.rules.cosmic_horror
    if row.effect is HorrorEffect.TAKE:
        communities = await within(ctx, world, row, frozenset(COMMUNITY_TYPES))
        for community in communities:
            scale_stat(ctx.rules, community, POPULATION_KEY, 1 - horror.population_loss_pct / PERCENT)
        return f"{several(len(communities), 'community', 'communities')} lost people" if communities else None
    species = (await within(ctx, world, row, frozenset({EntityType.SPECIES})))[: horror.horror_mutations]
    repository = EntityRepository(ctx.session)
    for item in species:
        await repository.add_flag(item.id, EntityFlag.MUTATION, ctx.epoch)
    return f"{several(len(species), 'kind of being', 'kinds of being')} changed in body" if species else None


async def on_minds(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    if direction > 0:
        return await reveal(ctx, world, row)
    touched = await within(ctx, world, row, PERCEIVERS)
    for entity in touched:
        shift_sanity(ctx.rules, entity, -ctx.rules.cosmic_horror.mind_mark_sanity_loss)
    return f"{several(len(touched), 'mind', 'minds')} lost sanity" if touched else None


async def on_dead(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    if direction >= 0:
        return None
    souls = (await within(ctx, world, row, frozenset({EntityType.SPIRIT})))[: ctx.rules.cosmic_horror.dead_taken]
    for soul in souls:
        await retire(ctx.session, soul, ctx.epoch, f"Epoch {ctx.epoch}: taken from the world by a horror.")
    return f"{', '.join(soul.name for soul in souls)} left the world of the dead" if souls else None


async def erasable(ctx: TickContext, world: WorldRow, row: HorrorEventRow) -> EntityRow | None:
    places = await within(ctx, world, row, frozenset({EntityType.PLACE}))
    regions = await within(ctx, world, row, frozenset({EntityType.REGION}))
    hot = set(await hot_regions(ctx, world.id))
    pool = sorted(places, key=lambda item: item.location_id not in hot) + (
        sorted(regions, key=lambda item: item.id not in hot) if len(regions) >= ctx.rules.cosmic_horror.void_min_regions else []
    )
    for candidate in pool:
        if not any(item.entity_type in ERASURE_GUARDS for item in await subtree(ctx.session, candidate.id)):
            return candidate
    return None


async def on_place(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    if row.effect is not HorrorEffect.TAKE:
        if held(world.id):
            return None
        world.leakage = min(PERCENT_MAX, world.leakage + ctx.rules.cosmic_horror.alignment_leak)
        return f"a place in {world.name} was touched and the leakage rose to {world.leakage}"
    target = await erasable(ctx, world, row)
    if target is None:
        return None
    for item in [target, *await subtree(ctx.session, target.id)]:
        await retire(ctx.session, item, ctx.epoch, f"Epoch {ctx.epoch}: erased by a horror.", status=EntityStatus.DESTROYED)
    await EntityRepository(ctx.session).add_flag(target.id, EntityFlag.VOID, ctx.epoch)
    return f"{target.name} was erased from the map"


async def on_law(ctx: TickContext, world: WorldRow, row: HorrorEventRow, direction: int) -> str | None:
    if held(world.id):
        return None
    step = ctx.rules.cosmic_horror.alignment_leak * (-1 if direction > 0 else 1)
    world.leakage = max(0, min(PERCENT_MAX, world.leakage + step))
    return f"the leakage of {world.name} is now {world.leakage}"


Applier = Callable[[TickContext, WorldRow, HorrorEventRow, int], Awaitable[str | None]]
APPLIERS: Mapping[HorrorTarget, Applier] = total(
    HorrorTarget,
    {
        HorrorTarget.LIGHT: on_light,
        HorrorTarget.SOUND: on_stress,
        HorrorTarget.WEATHER: on_weather,
        HorrorTarget.TIME: on_time,
        HorrorTarget.MEMORY: on_memory,
        HorrorTarget.LANGUAGE: on_language,
        HorrorTarget.SLEEP: on_stress,
        HorrorTarget.BODIES: on_bodies,
        HorrorTarget.MINDS: on_minds,
        HorrorTarget.THE_DEAD: on_dead,
        HorrorTarget.PLACE: on_place,
        HorrorTarget.LAW: on_law,
    },
)


async def perceived(ctx: TickContext, world: WorldRow, row: HorrorEventRow) -> int:
    if not PERCEIVED[row.sense] or row.sanity_cost <= 0:
        return 0
    touched = await within(ctx, world, row, PERCEIVERS)
    for entity in touched:
        shift_sanity(ctx.rules, entity, -row.sanity_cost)
    return len(touched)


def told_result(outcome: str | None, felt: int) -> str:
    parts = [part for part in (outcome, f"{several(felt, 'one', 'ones')} who perceived it lost sanity" if felt else None) if part]
    return f": {'; '.join(parts)}" if parts else ""


async def raise_horror(ctx: TickContext, world: WorldRow, spec: HorrorSpec, *, source_node_id: int | None = None) -> HorrorEventRow:
    horror = ctx.rules.cosmic_horror
    subject = await subject_of(ctx, world, spec.scope)
    row = HorrorEventRow(
        world_id=world.id,
        target=spec.target,
        effect=spec.effect,
        scope=spec.scope,
        sense=spec.sense,
        source=spec.source,
        source_node_id=source_node_id,
        subject_node_id=subject.id if subject is not None else None,
        duration=horror.horror_duration,
        sanity_cost=horror.horror_sanity_cost,
        leak=horror.horror_leak,
        epoch=ctx.epoch,
        until_epoch=ctx.epoch + horror.horror_duration,
    )
    row.locked = []
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def unleash(ctx: TickContext, world: WorldRow, row: HorrorEventRow) -> str:
    outcome = await APPLIERS[row.target](ctx, world, row, EFFECT_DIRECTION[row.effect])
    felt = await perceived(ctx, world, row)
    if row.leak and not held(world.id):
        world.leakage = max(0, min(PERCENT_MAX, world.leakage + row.leak))
    written = await record(
        ctx,
        f"horror.{row.target.value}.{row.effect.value}",
        roles={IncidentRole.SUBJECT: world.id, IncidentRole.TARGET: row.subject_node_id, IncidentRole.ACTOR: row.source_node_id},
        facts={
            "title": f" ({row.name})" if row.name else "",
            "effect": row.effect,
            "deed": EFFECT_PAST[row.effect],
            "target_kind": row.target,
            "sense": row.sense,
            "source": row.source,
            "scope": row.scope,
            "outcome": outcome,
            "felt": felt,
            "result": told_result(outcome, felt),
        },
        world_id=world.id,
    )
    return written.text


async def horror_event(ctx: TickContext, spec: HorrorSpec, world: WorldRow, *, source_node_id: int | None = None) -> str:
    row = await raise_horror(ctx, world, spec, source_node_id=source_node_id)
    return await unleash(ctx, world, row)


def drawn_spec(ctx: TickContext, world: WorldRow) -> HorrorSpec:
    rng = ctx.rng(f"horror.spec.{world.id}.{ctx.epoch}")
    return HorrorSpec(
        rng.pick(list(HorrorTarget)), rng.pick(list(HorrorEffect)), rng.pick(list(HorrorScope)), rng.pick(list(HorrorSense)), rng.pick(list(HorrorSource))
    )


async def keep_horrors(ctx: TickContext) -> int:
    lingering = 0
    active = select(HorrorEventRow).where(HorrorEventRow.until_epoch.is_not(None), HorrorEventRow.until_epoch > ctx.epoch, HorrorEventRow.epoch < ctx.epoch)
    for row in list(await ctx.session.scalars(active.order_by(HorrorEventRow.id))):
        world = await ctx.session.get(WorldRow, row.world_id)
        if world is None or held(world.id):
            continue
        lingering += await perceived(ctx, world, row)
    return lingering
