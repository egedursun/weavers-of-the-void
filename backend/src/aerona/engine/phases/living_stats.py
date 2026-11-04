import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow
from aerona.db.tables.place import PlaceSecretRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityType
from aerona.domain.enums.place import DiscoveryMode
from aerona.engine.context import TickContext
from aerona.engine.environment.secrets import reveal
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.knowledge_levels import known_records, shift_level
from aerona.engine.phases.society_support.knowledge import teach
from aerona.engine.phases.works import owner_of
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, flags_by_entity, has_flag, remove_flag
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.rules.registry import Rules

PIETY_KEY = "piety"
PROSPERITY_KEY = "prosperity"
WEALTH_KEY = "wealth"
DEFENSE_KEY = "defense"
KNOWLEDGE_ROLE = "knowledge"
FUNCTION_BY_KIND = {
    EngineKind.TEMPLE: PIETY_KEY,
    EngineKind.WALL: DEFENSE_KEY,
    EngineKind.LIBRARY: KNOWLEDGE_ROLE,
    EngineKind.SCHOOL: KNOWLEDGE_ROLE,
    EngineKind.OBSERVATORY: KNOWLEDGE_ROLE,
    EngineKind.COSMIC_ARCHIVE: KNOWLEDGE_ROLE,
}
FUNCTION_BY_WORD: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:temple|shrine|altar|tomb|monastery|monument|statue|sanctuary)\b"), PIETY_KEY),
    (re.compile(r"\b(?:wall|walls|fortress|fort|tower|keep|citadel|gate|bastion)\b"), DEFENSE_KEY),
    (re.compile(r"\b(?:library|archive|observatory|school|academy|scriptorium)\b"), KNOWLEDGE_ROLE),
    (re.compile(r"\b(?:harbour|harbor|port|bridge|road|market|bazaar|caravanserai|inn|pier)\b"), PROSPERITY_KEY),
    (re.compile(r"\b(?:mine|quarry|workshop|forge|smithy|foundry|loom|mill)\b"), WEALTH_KEY),
    (re.compile(r"\b(?:well|cistern|canal|dam|aqueduct|granary)\b"), PROSPERITY_KEY),
)


def function_role(work: EntityRow) -> str:
    if work.engine_kind in FUNCTION_BY_KIND:
        return FUNCTION_BY_KIND[work.engine_kind]
    text = f"{work.subtype or ''} {work.name}".casefold()
    return next((role for pattern, role in FUNCTION_BY_WORD if pattern.search(text)), PROSPERITY_KEY)


async def reveal_by_mystery(ctx: TickContext, place: EntityRow, seeker: EntityRow) -> bool:
    secret = await ctx.session.scalar(
        select(PlaceSecretRow)
        .where(PlaceSecretRow.place_entity_id == place.id, PlaceSecretRow.revealed_epoch.is_(None), PlaceSecretRow.held.is_(False))
        .order_by(PlaceSecretRow.strength, PlaceSecretRow.id)
        .limit(1)
    )
    if secret is None:
        return False
    ground = await ctx.session.get(PlaceEnvironmentRow, place.id)
    region = await ctx.session.get(RegionEnvironmentRow, ground.region_entity_id) if ground is not None and ground.region_entity_id is not None else None
    await reveal(ctx, secret, DiscoveryMode.MYSTERY, seeker, region)
    return True


async def solve_mysteries(ctx: TickContext) -> int:
    table = ctx.rules.record_schema
    lost = await flags_by_entity(ctx.session, EntityFlag.LOST)
    lost_knowledge = [item for item in await canon(ctx.session, [EntityType.KNOWLEDGE]) if item.id in lost]
    communities = await canon(ctx.session, COMMUNITY_TYPES)
    solved = 0
    for place in await canon(ctx.session, [EntityType.PLACE]):
        if solved >= table.mystery_cap:
            break
        mystery = stat_or(place, "mystery", 0)
        if mystery < table.mystery_threshold or not ctx.rng(f"mystery.{place.id}").chance(mystery / table.mystery_divisor):
            continue
        near = [item for item in communities if item.location_id == place.id or (place.location_id is not None and item.location_id == place.location_id)]
        if not near:
            continue
        seeker = ctx.rng(f"seeker.{place.id}").pick(near)
        set_stats(place, mystery=clamp_int(mystery - table.mystery_solved_loss, 0, PERCENT))
        solved += 1
        if await reveal_by_mystery(ctx, place, seeker):
            continue
        found = next((item for item in lost_knowledge if item.world_id == place.world_id), None)
        if found is not None:
            await teach(ctx, seeker.id, found, f"found in the mystery of {place.name}")
            await remove_flag(ctx.session, found.id, EntityFlag.LOST)
            lost_knowledge.remove(found)
            text = f"{seeker.name} solved the mystery of {place.name} and found the forgotten knowledge of {found.name} there."
            await note(ctx, text, key="living_stats.mystery_knowledge", ids=[seeker.id, place.id, found.id], kind=ChronicleKind.KNOWLEDGE)
        elif stat(seeker, PIETY_KEY) is not None:
            set_stats(seeker, piety=clamp_int(stat_or(seeker, PIETY_KEY, 0) + table.mystery_pilgrim_piety, 0, PERCENT))
            await note(
                ctx,
                f"The mystery of {place.name} draws pilgrims; {seeker.name} carried offerings there.",
                key="living_stats.pilgrims",
                ids=[seeker.id, place.id],
            )
    return solved


async def deepen_by_work(ctx: TickContext, work: EntityRow, owner: EntityRow, deepened: int) -> bool:
    table = ctx.rules.record_schema
    function = stat_or(work, "function", 0)
    if deepened >= table.function_knowledge_cap or not ctx.rng(f"work_knowledge.{work.id}").chance(function / table.function_knowledge_divisor):
        return False
    options = [item for item in await known_records(ctx.session, owner.id) if knowledge_level(ctx.rules, item) < ctx.rules.knowledge.level_cap]
    if not options:
        return False
    chosen = ctx.rng(f"work_pick.{work.id}").pick(options)
    level = shift_level(ctx.rules, chosen, 1)
    if level is None:
        return False
    text = f"The scribes working at {work.name} deepened the knowledge of {chosen.name} (level {level})."
    await note(ctx, text, key="living_stats.work_knowledge", ids=[work.id, owner.id, chosen.id], kind=ChronicleKind.KNOWLEDGE)
    return True


async def work_functions(ctx: TickContext) -> int:
    table = ctx.rules.record_schema
    deepened = 0
    held = 0
    for work in await canon(ctx.session, [EntityType.STRUCTURE]):
        function = stat_or(work, "function", 0)
        if function <= 0:
            continue
        if stat_or(work, "durability", PERCENT) < table.function_sturdy_threshold:
            set_stats(work, function=clamp_int(function - table.function_wear, 0, PERCENT))
            continue
        owner = await owner_of(ctx, work)
        if owner is None:
            continue
        role = function_role(work)
        if role == KNOWLEDGE_ROLE:
            deepened += 1 if await deepen_by_work(ctx, work, owner, deepened) else 0
            continue
        key = role if stat(owner, role) is not None else PROSPERITY_KEY if role == WEALTH_KEY and stat(owner, PROSPERITY_KEY) is not None else None
        if key is None:
            continue
        current = stat_or(owner, key, 0)
        floor = round(function * table.function_floor_pct / PERCENT)
        if current >= floor:
            continue
        set_stats(owner, **{key: clamp_int(current + min(table.function_step, floor - current), 0, PERCENT)})
        held += 1
    ctx.count("knowledge_deepened", deepened)
    return held


async def mock_prophecy(ctx: TickContext, prophecy: EntityRow) -> None:
    table = ctx.rules.record_schema
    if await has_flag(ctx.session, prophecy.id, EntityFlag.MOCKED):
        return
    await add_flag(ctx.session, prophecy.id, EntityFlag.MOCKED, ctx.epoch)
    son = await ctx.session.get(SonRow, prophecy.creator_son_id) if prophecy.creator_son_id is not None else None
    if son is not None and son.alive:
        son.fame = max(0, son.fame - table.prophecy_fame_loss)
    tail = f"; the word of {son.name} lost its weight" if son is not None else ""
    await note(
        ctx,
        f"{prophecy.name} has gone unfulfilled for ages; now it is spoken of with mockery in the streets{tail}.",
        key="living_stats.mocked",
        ids=[prophecy.id],
        son_id=son.id if son else None,
    )


async def prophecy_certainty(ctx: TickContext) -> int:
    table = ctx.rules.record_schema
    worn = 0
    for prophecy in await canon(ctx.session, [EntityType.PROPHECY]):
        certainty = stat(prophecy, "certainty")
        if certainty is None:
            continue
        if ctx.epoch - prophecy.birth_epoch >= table.prophecy_grace and certainty > 0:
            before = certainty
            certainty = clamp_int(certainty - table.certainty_wear, 0, PERCENT)
            set_stats(prophecy, certainty=certainty)
            worn += 1
            if before >= table.certainty_collapse > certainty:
                await mock_prophecy(ctx, prophecy)
        if certainty < table.certainty_threshold:
            continue
        floor = round(certainty * table.certainty_piety_pct / PERCENT)
        for bond in await active_bonds(ctx.session, list(BondKind), sources=[prophecy.id]):
            await _hold_piety(ctx.session, ctx.rules, bond.target_node_id, floor)
    return worn


async def _hold_piety(session: AsyncSession, rules: Rules, entity_id: int, floor: int) -> None:
    entity = await session.get(EntityRow, entity_id)
    if entity is None or not entity.living or entity.entity_type not in COMMUNITY_TYPES:
        return
    piety = stat(entity, PIETY_KEY)
    if piety is None or piety >= floor:
        return
    set_stats(entity, piety=clamp_int(piety + rules.record_schema.function_step, 0, floor))


@reads(
    "knowledge.spread",
    "people.piety",
    "people.prosperity",
    "place.mystery",
    "prophecy.certainty",
    "settlement.defense",
    "settlement.piety",
    "settlement.prosperity",
    "structure.durability",
    "structure.function",
    "table.bonds",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.nodes",
    "table.place_environment",
    "table.place_secrets",
    "table.region_environment",
)
@writes(
    "knowledge.spread",
    "people.piety",
    "place.mystery",
    "prophecy.certainty",
    "settlement.defense",
    "structure.function",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.place_environment",
    "table.place_profiles",
    "table.place_secrets",
    "table.region_environment",
    "table.resource_profiles",
    "table.rite_effects",
    "table.rite_profiles",
    "table.sons",
)
async def living_stats(ctx: TickContext) -> None:
    ctx.count("mysteries", await solve_mysteries(ctx))
    ctx.count("functions", await work_functions(ctx))
    ctx.count("prophecies_worn", await prophecy_certainty(ctx))


async def run_living_stats(session: AsyncSession, rules: Rules) -> None:
    await living_stats(await manual_context(session, "living_stats", rules))


PHASES = (Phase("living_stats", living_stats),)
