from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.sons import PowerDraft, SonRepository
from aerona.db.tables.epochs import EpochStatsRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.son import PowerEffect, SonStatus
from aerona.domain.models.entity_stats import ArtworkStats, CultStats
from aerona.engine.context import TickContext
from aerona.engine.phases.doom import doom_clock, set_doom_clock, trigger_apocalypse
from aerona.engine.phases.population import population_baseline, population_growth
from aerona.engine.phases.sons import (
    domain_rivalry,
    existence_target,
    rebel_theft,
    renew_existence,
    set_son_relation,
    sons_renewal,
    step_toward,
    works_remember_gods,
)
from aerona.engine.primitives.ledger import DoomItem, EssenceItem, LedgerKey, doom_items, essence_items, read, record
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat
from aerona.engine.snapshot import epoch_statistics, world_snapshot
from aerona.engine.transition import advance_epoch, creator_essence, pour_essence
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, add_flag, bond, entity, son_draft, tuned_rules


async def test_population_grows_logistically_and_cults_convert(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    cult = await entity(
        session, "Lantern Way", EntityType.CULT, CultStats(followers=200, influence=40), world_id=world.world.id, location_id=world.regions[0].id
    )
    await bond(session, cult.id, world.son.id, BondKind.WORSHIPS)
    await population_baseline(ctx)
    await population_growth(ctx)
    assert read(ctx, LedgerKey.POPULATION_START) == 6000
    assert (stat(cult, "followers") or 0) > 200
    assert read(ctx, LedgerKey.POPULATION_TO_CULTS) > 0
    assert read(ctx, LedgerKey.POPULATION_GROWTH) > 0


def test_existence_moves_toward_its_target(rules: Rules) -> None:
    target = existence_target(rules, faith=100, fame=100, anchor_alive=True, worshippers=3)
    assert target <= 100
    assert step_toward(20, 90, 10) == 30
    assert step_toward(90, 20, 10) == 80


async def test_sons_renewal_wakes_heals_and_regenerates(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    sleeper = await SonRepository(session).create(son_draft("Nym", world.world.id, (Domain.SLEEP, Domain.DREAM)))
    sleeper.status = SonStatus.ASLEEP
    sleeper.sleep_epochs_left = 1
    world.son.hp = 10
    essence_before = world.son.essence
    await SonRepository(session).set_powers(world.son.id, [PowerDraft("Spring", "Wells.", PowerEffect.ESSENCE_SPRING)])
    await sons_renewal(ctx)
    assert sleeper.status is SonStatus.ACTIVE and sleeper.hp > 0
    assert world.son.hp > 10
    assert world.son.faith > 0
    assert world.son.essence > essence_before
    assert read(ctx, LedgerKey.TOTAL_FAITH) == world.son.faith + sleeper.faith


async def test_remembrance_rivalry_and_rebels(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    art = await entity(session, "Hymn of Ithren", EntityType.ARTWORK, ArtworkStats(renown=50), world_id=world.world.id, location_id=world.regions[0].id)
    await bond(session, art.id, world.son.id, BondKind.TELLS_OF)
    fame = world.son.fame
    await works_remember_gods(ctx)
    assert world.son.fame == fame + ctx.rules.world_epoch_transition.artwork_renown
    twin = await SonRepository(session).create(son_draft("Ivara", world.world.id, (Domain.HARVEST, Domain.LIGHT)))
    await domain_rivalry(ctx)
    assert await SonRepository(session).relation(world.son.id, twin.id) == -2 * ctx.rules.world_epoch_transition.domain_rivalry
    assert await set_son_relation(ctx, world.son.id, twin.id, 25) == 25
    twin.rebel = True
    await rebel_theft(ctx)
    assert (
        read(ctx, LedgerKey.STOLEN_ESSENCE)
        == ctx.rules.world_epoch_transition.rebel_steal_base + twin.level * ctx.rules.world_epoch_transition.rebel_steal_per_level
    )


async def test_doom_clock_counts_and_destroys(session: AsyncSession, world: CoreWorld) -> None:
    await add_flag(session, world.people.id, EntityFlag.GODLESS)
    ctx = await manual_context(session, "doom")
    await doom_clock(ctx)
    items = doom_items(ctx)
    assert items[DoomItem.GODLESS] == ctx.rules.apocalypse.godless
    assert items[DoomItem.PEACE] == -ctx.rules.apocalypse.peace
    world.cosmos.doom_clock = ctx.rules.balance.apocalypse_threshold - 1
    crowded = await manual_context(session, "doom_end", tuned_rules(apocalypse={"godless": 50}, balance={"apocalypse_speed": 100}))
    await doom_clock(crowded)
    assert world.cosmos.doom_clock == ctx.rules.balance.apocalypse_threshold * ctx.rules.apocalypse.after_ruin_pct // 100
    keys = list(await session.scalars(select(ChronicleRow.template_key)))
    assert "doom.apocalypse" in keys


async def test_doom_turns_into_a_calling_when_worlds_leak(session: AsyncSession, world: CoreWorld) -> None:
    world.world.leakage = 90
    ctx = await manual_context(session, "calling")
    assert await trigger_apocalypse(ctx, calling=True) == ctx.rules.balance.apocalypse_threshold * ctx.rules.apocalypse.after_calling_pct // 100
    assert world.world.leakage == 100
    assert await set_doom_clock(ctx, 5) == 5


async def test_creator_essence_soft_cap_and_overflow(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "essence")
    world.creator.essence = ctx.rules.balance.creator_essence_soft_cap + 500
    record(ctx, LedgerKey.TOTAL_FAITH, 100)
    before = world.creator.essence
    await creator_essence(ctx)
    items = essence_items(ctx)
    assert items[EssenceItem.HALVED] < 0
    assert items[EssenceItem.OVERFLOW] < 0
    assert world.creator.essence < before
    result = await pour_essence(ctx, 10)
    assert result.given > 0


async def test_statistics_and_advance(ctx: TickContext, world: CoreWorld, session: AsyncSession) -> None:
    snapshot = await world_snapshot(session)
    assert snapshot.population == 6000
    assert snapshot.sons[world.son.id].existence == world.son.existence
    data = await epoch_statistics(ctx)
    assert data.languages == 1
    assert await session.get(EpochStatsRow, ctx.epoch) is not None
    await advance_epoch(ctx)
    assert world.cosmos.epoch == ctx.epoch + 1
    assert world.cosmos.epoch_start_year == ctx.rules.time.years_per_epoch
    assert any(status is EntityStatus.CANON for status in [world.people.status])


async def test_a_son_whose_anchor_perished_is_told_fading_only_when_its_existence_falls(world: CoreWorld, session: AsyncSession) -> None:
    anchor = await entity(session, "Lost Shrine", EntityType.ARTWORK, ArtworkStats(), world_id=world.world.id)
    anchor.status, anchor.end_epoch = EntityStatus.DESTROYED, 1
    world.son.anchor_entity_id = anchor.id
    ctx = await manual_context(session, "anchor", tuned_rules(world_epoch_transition={"existence_step": 100}))
    world.son.existence = 0
    await renew_existence(ctx, world.son, 100000)
    world.son.existence = 100
    await renew_existence(ctx, world.son, 0)
    told = list(await session.scalars(select(ChronicleRow.text).where(ChronicleRow.template_key == "sons.existence").order_by(ChronicleRow.id)))
    assert len(told) == 2
    assert "anchor perished" not in told[0] and "anchor perished" in told[1]
