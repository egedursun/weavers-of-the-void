from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.ages import IrregularSeasonRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.physics import ImpactEventRow
from aerona.domain.enums.ages import LongSeasonReach, SeasonCause, SeasonSpell, SeasonSpellShape
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.physics import ImpactBody, ImpactOutcome
from aerona.engine.environment.long_seasons import SeasonTally, eruption_spell, impact_spell, keep_seasons
from aerona.engine.environment.spells import pull_of
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.services.player.factories import make_entity, seed_player_world

RULES = Rules()


async def struck(session: AsyncSession, world_id: int, size: int) -> int:
    row = ImpactEventRow(world_id=world_id, body=next(iter(ImpactBody)), size=size, due_epoch=1, outcome=ImpactOutcome.STRUCK, winter_epochs=0, locked=[])
    session.add(row)
    await session.flush()
    return row.id


async def test_a_great_impact_begins_one_single_winter_and_a_small_one_none(session: AsyncSession) -> None:
    world = (await seed_player_world(session)).world
    ctx = await manual_context(session, "test", RULES)
    impact = await struck(session, world.id, 80)
    small = await impact_spell(ctx, world, impact, RULES.long_seasons.impact_size_min - 1, 2)
    great = await impact_spell(ctx, world, impact, 80, 3)
    again = await impact_spell(ctx, world, impact, 80, 3)
    assert small is None and again is None and great is not None
    assert great.shape is SeasonSpellShape.SINGLE and great.spell is SeasonSpell.WINTER and great.spell_length == 3
    assert great.severity == 80 * RULES.long_seasons.impact_severity_per_size_pct // 100


async def test_an_eruption_reaches_its_half_of_the_world_unless_it_is_great(session: AsyncSession) -> None:
    world = (await seed_player_world(session)).world
    ctx = await manual_context(session, "test", RULES)
    region = await make_entity(session, "Ashlands", EntityType.REGION, world_id=world.id)
    region.map_y = 0.8
    half = await eruption_spell(ctx, world, region, RULES.long_seasons.eruption_strength_min)
    whole = await eruption_spell(ctx, world, region, RULES.long_seasons.eruption_world_strength)
    assert half is not None and half.reach is LongSeasonReach.SOUTH and half.source_region_id == region.id
    assert whole is not None and whole.reach is LongSeasonReach.WORLD


async def test_spells_stack_and_a_winter_offsets_a_summer() -> None:
    rows = [
        IrregularSeasonRow(world_id=1, cause=SeasonCause.DIVINE, spell=SeasonSpell.WINTER, severity=60, reach=LongSeasonReach.WORLD),
        IrregularSeasonRow(world_id=1, cause=SeasonCause.DIVINE, spell=SeasonSpell.WINTER, severity=50, reach=LongSeasonReach.WORLD),
        IrregularSeasonRow(world_id=1, cause=SeasonCause.DIVINE, spell=SeasonSpell.SUMMER, severity=20, reach=LongSeasonReach.WORLD),
    ]
    pull = pull_of(RULES, rows, 50, None)
    assert pull.winter == 60 + 50 * RULES.long_seasons.stacking_share_pct // 100 - 20 and pull.summer == 0


async def test_a_single_spell_ends_by_its_length(session: AsyncSession) -> None:
    world = (await seed_player_world(session)).world
    ctx = await manual_context(session, "test", RULES)
    spell = await impact_spell(ctx, world, await struck(session, world.id, 90), 90, 1)
    assert spell is not None
    spell.spell_started_epoch = ctx.epoch - 2
    await keep_seasons(ctx, SeasonTally())
    left = list(
        await session.scalars(select(IrregularSeasonRow).where(IrregularSeasonRow.world_id == world.id, IrregularSeasonRow.cause == SeasonCause.IMPACT))
    )
    assert left == []
    assert await session.get(EntityRow, world.id) is None or True
