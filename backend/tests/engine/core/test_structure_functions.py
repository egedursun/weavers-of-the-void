import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.demography import LabourRow, PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import InheritanceCustom, Job, MartialStyle
from aerona.domain.enums.entity import EntityStatus, MortalRole
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.mind.book import skills_of
from aerona.engine.primitives.knowledge import KnowledgeMap, knowledge_level
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.settlement.book import town_of
from aerona.engine.structures.construction import Commission, begin, finish
from aerona.engine.structures.functions import run_functions
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, knowledge, mortal, settlement, tuned_rules

K = StructureKind
CERTAIN = tuned_rules(
    structure_functions={
        "library_deepen_pct": 100,
        "monastery_deepen_pct": 100,
        "academy_deepen_pct": 100,
        "archive_deepen_pct": 100,
        "observatory_deepen_pct": 100,
        "arena_duel_chance": 100,
    }
)


async def context(session: AsyncSession, rules: Rules = CERTAIN) -> TickContext:
    return await manual_context(session, "test", rules=rules)


async def standing(ctx: TickContext, world: CoreWorld, kind: StructureKind, **stats: int) -> tuple[EntityRow, StructureProfileRow]:
    town = await settlement(ctx.session, "Brookhold", world, world.regions[0], population=6000, prosperity=80, piety=70)
    ctx.session.add(LabourRow(community_entity_id=town.id, job=Job.BUILDING, workers=100, output_pct=100, epoch=1))
    await ctx.session.flush()
    found = await town_of(ctx, town, await KnowledgeMap.load(ctx.session))
    found.profile.treasury = 100000
    work, row = await begin(ctx, Commission(site=town, kind=K.SHRINE))
    await finish(ctx, row)
    profile = await ctx.session.get(StructureProfileRow, work.id)
    assert profile is not None
    profile.kind = kind
    profile.effect_pct = 100
    profile.host_entity_id = town.id
    set_stats(town, **stats)
    await ctx.session.flush()
    return town, profile


@pytest.mark.parametrize(
    ("kind", "key"),
    [
        (K.TEMPLE, "piety"),
        (K.SHRINE, "piety"),
        (K.MONASTERY, "piety"),
        (K.WONDER, "piety"),
        (K.FORT, "defense"),
        (K.CITADEL, "defense"),
        (K.MARKET, "prosperity"),
        (K.WORKSHOP, "prosperity"),
    ],
)
async def test_a_working_house_lifts_its_hosts_stat_toward_its_floor(session: AsyncSession, world: CoreWorld, kind: StructureKind, key: str) -> None:
    ctx = await context(session)
    town, _ = await standing(ctx, world, kind, **{key: 0})
    tally = await run_functions(ctx)
    assert tally.held == 1
    assert 0 < (stat(town, key) or 0) <= ctx.rules.structure_functions.citadel_defense


async def test_a_house_leaves_a_stat_already_above_its_floor(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town, _ = await standing(ctx, world, K.MARKET, prosperity=100)
    tally = await run_functions(ctx)
    assert tally.held == 0 and stat(town, "prosperity") == 100


@pytest.mark.parametrize("kind", [K.LIBRARY, K.MONASTERY, K.ACADEMY, K.COSMIC_ARCHIVE])
async def test_houses_of_learning_deepen_what_their_host_knows(session: AsyncSession, world: CoreWorld, kind: StructureKind) -> None:
    ctx = await context(session)
    town, _ = await standing(ctx, world, kind)
    record = await knowledge(session, world, "Tide reckoning", KnowledgeBranch.ARCHITECTURE)
    await bond(session, town.id, record.id, BondKind.KNOWS)
    before = knowledge_level(ctx.rules, record)
    tally = await run_functions(ctx)
    assert tally.deepened == 1 and knowledge_level(ctx.rules, record) == before + 1


async def test_an_observatory_deepens_only_the_sky(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town, _ = await standing(ctx, world, K.OBSERVATORY)
    ground = await knowledge(session, world, "Field reckoning", KnowledgeBranch.ARCHITECTURE)
    sky = await knowledge(session, world, "Star reckoning", KnowledgeBranch.ASTRONOMY)
    await bond(session, town.id, ground.id, BondKind.KNOWS)
    await bond(session, town.id, sky.id, BondKind.KNOWS)
    ground_level, sky_level = knowledge_level(ctx.rules, ground), knowledge_level(ctx.rules, sky)
    await run_functions(ctx)
    assert knowledge_level(ctx.rules, ground) == ground_level
    assert knowledge_level(ctx.rules, sky) == sky_level + 1


async def test_learning_without_known_records_deepens_nothing(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    await standing(ctx, world, K.LIBRARY)
    assert (await run_functions(ctx)).deepened == 0


async def test_a_school_raises_literacy_and_trains_resident_scribes(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town, _ = await standing(ctx, world, K.SCHOOL)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    culture = PeopleCultureRow(
        people_entity_id=world.people.id,
        cohesion=50,
        literacy=0,
        urbanisation=0,
        martial_style=next(iter(MartialStyle)),
        inheritance=next(iter(InheritanceCustom)),
    )
    session.add(culture)
    scribe = await mortal(session, "Ilsa", world, town.id)
    scribe.mortal_role = MortalRole.SCRIBE
    await session.flush()
    tally = await run_functions(ctx)
    assert tally.held == 1 and culture.literacy == ctx.rules.structure_functions.school_literacy_step
    assert SkillKind.WRITING in await skills_of(session, scribe.id)


async def test_a_hospital_trains_its_healers(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town, _ = await standing(ctx, world, K.HOSPITAL)
    healer = await mortal(session, "Oren", world, town.id)
    healer.mortal_role = MortalRole.HEALER
    bystander = await mortal(session, "Pell", world, town.id)
    await session.flush()
    await run_functions(ctx)
    assert SkillKind.MEDICINE in await skills_of(session, healer.id)
    assert SkillKind.MEDICINE not in await skills_of(session, bystander.id)


async def test_an_arena_sets_two_fighters_against_each_other(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town, _ = await standing(ctx, world, K.ARENA)
    fighters = [await mortal(session, name, world, town.id) for name in ("Asa", "Bram")]
    for fighter in fighters:
        fighter.mortal_role = MortalRole.WARRIOR
        fighter.importance = 0
    await session.flush()
    tally = await run_functions(ctx)
    assert tally.duels == 1
    assert sorted(fighter.importance or 0 for fighter in fighters) == [0, ctx.rules.structure_functions.arena_duel_renown]


async def test_an_arena_with_one_fighter_holds_no_duel(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town, _ = await standing(ctx, world, K.ARENA)
    lone = await mortal(session, "Asa", world, town.id)
    lone.mortal_role = MortalRole.WARRIOR
    await session.flush()
    assert (await run_functions(ctx)).duels == 0


async def test_an_anchoring_house_feeds_its_god_and_a_fallen_host_does_nothing(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town, profile = await standing(ctx, world, K.MARKET, prosperity=0)
    profile.dedicated_son_id = world.son.id
    profile.anchor = True
    world.son.existence = 10
    town.status = EntityStatus.DESTROYED
    town.end_epoch = ctx.epoch
    await session.flush()
    tally = await run_functions(ctx)
    assert world.son.existence == 10 + ctx.rules.structure_functions.anchor_existence
    assert tally.held == 0 and stat(town, "prosperity") == 0


async def test_the_deepening_cap_limits_each_epoch(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, tuned_rules(structure_functions={"library_deepen_pct": 100}, record_schema={"function_knowledge_cap": 0}))
    town, _ = await standing(ctx, world, K.LIBRARY)
    record = await knowledge(session, world, "Tide reckoning", KnowledgeBranch.ARCHITECTURE)
    await bond(session, town.id, record.id, BondKind.KNOWS)
    assert (await run_functions(ctx)).deepened == 0
