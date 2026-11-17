import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.foreign_gods import ForeignGodPowerDraft, ForeignGodRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.foreign_gods import GodConflictRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.son import SonStatus, Stat
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.war import GodConflictOutcome
from aerona.domain.enums.world import StarType
from aerona.domain.models.entity_stats import CelestialStats, CultStats, PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.foreign_gods import (
    NewForeignGod,
    add_foreign_god,
    awaken_text,
    birth_local_gods,
    clean_powers,
    clean_stats,
    parse_domains,
    resolve_god_war,
    seeded_stats,
    stat_effect,
    unwrap_text,
    war_power,
)
from aerona.engine.cosmos.stars import black_sun, choose_epoch_stars, extinguish_star, hang_star, rekindle_star, supernova
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_son, make_world, tick, tuned


async def test_epoch_star_is_a_sky_body_of_the_world(ctx: TickContext, cosmos: Cosmos) -> None:
    body = await make_entity(ctx.session, "Lantern", EntityType.CELESTIAL, CelestialStats(brightness=90), world_id=cosmos.home.id)
    chosen = await choose_epoch_stars(ctx)
    assert chosen[cosmos.home.id] == body.id and cosmos.home.epoch_star_entity_id == body.id


async def test_supernova_burns_worlds_and_advances_doom(ctx: TickContext, cosmos: Cosmos) -> None:
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=10000), world_id=cosmos.home.id)
    other = await make_world(ctx.session, "Velmor")
    sail = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.LIGHT_SAIL)
    text = await supernova(ctx, cosmos.star)
    assert cosmos.star.star_type is StarType.STAR_REMNANT and "exploded" in text
    assert people.stats.population == round(10000 * (1 - ctx.rules.sky.supernova_population_loss_pct / 100))
    assert cosmos.home.leakage == ctx.rules.sky.supernova_leak
    assert (await CosmosRepository(ctx.session).require_cosmos()).doom_clock == ctx.rules.sky.supernova_apocalypse
    assert not sail.active


async def test_black_sun_feeds_outer_cults(ctx: TickContext, cosmos: Cosmos) -> None:
    cult = await make_entity(ctx.session, "Whisper", EntityType.CULT, CultStats(followers=100), world_id=cosmos.home.id, flags=[EntityFlag.OUTER_CULT])
    await black_sun(ctx, cosmos.star)
    assert cosmos.star.star_type is StarType.BLACK_SUN and cosmos.star.brightness == 0
    assert cult.stats.followers == round(100 * ctx.rules.sky.black_sun_outer_cult_mult_pct / 100)


async def test_extinguish_and_rekindle(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Coast", cosmos.home.id, fertility=60)
    await extinguish_star(ctx, cosmos.star.id, "Velan", cosmos.creator.id)
    assert cosmos.star.star_type is StarType.DEAD_STAR
    assert region.stats.fertility == 60 - ctx.rules.pantheon.extinguish_fertility_loss
    await rekindle_star(ctx, cosmos.star.id, "Aeron", cosmos.creator.id)
    assert cosmos.star.star_type is StarType.REBORN_STAR
    with pytest.raises(ValidationFailedError):
        await rekindle_star(ctx, cosmos.star.id, "Aeron", cosmos.creator.id)
    star = await hang_star(ctx, "Newlight", StarType.BLUE_GIANT, cosmos.creator.id)
    assert star.brightness > 0


def test_seeded_stats_are_stable(rules: Rules) -> None:
    assert seeded_stats(rules, "Vesmorn:1:1") == seeded_stats(rules, "Vesmorn:1:1")
    assert seeded_stats(rules, "Vesmorn:1:1") != seeded_stats(rules, "Vesmorn:2:1")


def test_sanitizers() -> None:
    powers = clean_powers({"0": {"effect": "shield", "name": ""}, "1": {"effect": "unknown"}})
    assert [power.effect for power in powers] == [ForeignGodPowerEffect.SHIELD]
    assert unwrap_text('["one", "two"]') == "one\n\ntwo"
    assert parse_domains("Glass / Sound", (Domain.SEA, Domain.SALT)) == (Domain.GLASS, Domain.SOUND)
    assert parse_domains("Nothing", (Domain.SEA, Domain.SALT)) == (Domain.SEA, Domain.SALT)


async def test_war_power_and_stat_effect(ctx: TickContext, cosmos: Cosmos) -> None:
    god = await add_foreign_god(ctx.session, ctx.rules, ctx.rng(), ctx.epoch, NewForeignGod("Vesmorn", cosmos.home.id, (Domain.GLASS, None), power=60))
    god.apply_stats(clean_stats({stat.value: 80 for stat in Stat}, None, ctx.rules))
    share = ctx.rules.foreign_gods.war_stat_share_pct
    assert war_power(ctx.rules, god, set()) == pytest.approx(60 * (100 - share) / 100 + 80 * share / 100)
    assert war_power(ctx.rules, god, {ForeignGodPowerEffect.SHIELD}) - war_power(ctx.rules, god, set()) == ctx.rules.foreign_gods.power_shield
    assert stat_effect(ctx.rules, god, Stat.CHARISMA, 20) == pytest.approx((80 - ctx.rules.foreign_gods.stat_neutral) * 0.2)


async def test_god_war_kills_without_deathless(ctx: TickContext, cosmos: Cosmos) -> None:
    son = await make_son(ctx.session, "Velan", cosmos.home.id, stats=100)
    god = await add_foreign_god(ctx.session, ctx.rules, ctx.rng(), ctx.epoch, NewForeignGod("Vesmorn", cosmos.home.id, (Domain.GLASS, None), power=0))
    god.apply_stats(clean_stats({stat.value: 1 for stat in Stat}, None, ctx.rules))
    result = await resolve_god_war(ctx, son, god)
    assert result.outcome is GodConflictOutcome.ATTACKER_WON and god.status is ForeignGodStatus.DEAD and god.death_epoch == ctx.epoch
    killed = await ctx.session.scalar(select(BondRow).where(BondRow.kind == BondKind.KILLED, BondRow.target_node_id == god.id))
    assert killed is not None and killed.source_node_id == son.id
    assert await ctx.session.scalar(select(GodConflictRow)) is not None


async def test_god_war_spares_the_deathless_and_wounds_losers(ctx: TickContext, cosmos: Cosmos) -> None:
    son = await make_son(ctx.session, "Velan", cosmos.home.id, stats=100)
    god = await add_foreign_god(ctx.session, ctx.rules, ctx.rng(), ctx.epoch, NewForeignGod("Vesmorn", cosmos.home.id, (Domain.GLASS, None), power=0))
    god.apply_stats(clean_stats({stat.value: 1 for stat in Stat}, None, ctx.rules))
    await ForeignGodRepository(ctx.session).set_powers(god.id, [ForeignGodPowerDraft("Undying", ForeignGodPowerEffect.DEATHLESS, "It cannot die.")])
    await resolve_god_war(ctx, son, god)
    assert god.status is ForeignGodStatus.DEFEATED
    weak = await make_son(ctx.session, "Morak", cosmos.home.id, stats=1)
    weak.hp = 1
    giant = await add_foreign_god(
        ctx.session, ctx.rules, ctx.rng("giant"), ctx.epoch, NewForeignGod("Ulgrath", cosmos.home.id, (Domain.STONE, None), power=100)
    )
    giant.apply_stats(clean_stats({stat.value: 100 for stat in Stat}, None, ctx.rules))
    lost = await resolve_god_war(ctx, weak, giant)
    assert lost.outcome is GodConflictOutcome.DEFENDER_WON and weak.status is SonStatus.ASLEEP and lost.son_slept


async def test_local_god_birth_and_waking_text(ctx: TickContext, cosmos: Cosmos) -> None:
    await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    born = await birth_local_gods(ctx)
    assert len(born) == 1 and born[0].status is ForeignGodStatus.ASLEEP and born[0].title and born[0].title.startswith("the sleeping")
    assert await birth_local_gods(ctx) == []
    awaken_text(born[0])
    assert born[0].title is not None and not born[0].title.startswith("the sleeping")


async def test_mourning_blocks_a_new_local_god(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "agents", local_god_rebirth_epochs=10))
    await make_entity(session, "Tarn", EntityType.PEOPLE, PeopleStats(population=5000), world_id=cosmos.home.id)
    god = await add_foreign_god(session, ctx.rules, ctx.rng(), 1, NewForeignGod("Old One", cosmos.home.id, (Domain.DEATH, None)))
    god.status = ForeignGodStatus.DEAD
    god.death_epoch = ctx.epoch - 1
    assert await birth_local_gods(ctx) == []
