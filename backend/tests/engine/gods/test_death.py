from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog import god_lines
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ThreadRow
from aerona.db.tables.society import ResurrectionOrderRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.son import SonDeathCause, SonStatus
from aerona.domain.models.stats import StatBlock
from aerona.engine.gods.devotion import RiteKind, SchemeKind, resurrection_rite, resurrection_state, scatter_bones, sibling_scheme
from aerona.engine.gods.god_death import epochs_until_resurrection, god_death, gods_fate
from aerona.engine.gods.mortality import Killer, ProtectorKind, attempt_kill, failed_kill_refund, kill_chance, kill_cost
from aerona.engine.gods.stats import Trait, trait_or
from aerona.engine.phases.god_death import death_engine
from aerona.engine.primitives.faith import worship_creator
from aerona.rules.registry import Rules
from aerona.services.gods import death as service
from tests.engine.gods.factories import GodsWorld, bond, chronicle_keys, make_context, make_entity, make_son


def _tuned(rules: Rules, **changes: int) -> Rules:
    return replace(rules, death=replace(rules.death, **changes))


async def test_kill_cost_and_chance(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    patron = await make_son(session, "Iolen", world.world.id)
    mortal = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id, power_level=3)
    mortal.importance = 8
    death = rules.death
    assert await kill_cost(session, rules, mortal) == round(
        death.take_life_base_cost + 3 * death.take_life_cost_per_power + 8 / death.take_life_cost_importance_divisor
    )
    await bond(session, mortal.id, patron.id, BondKind.WORSHIPS)
    chance = await kill_chance(session, rules, mortal, son)
    expected = death.take_life_base_success + 50 / death.take_life_might_divisor - 8 / death.take_life_importance_resist - death.take_life_patron_resist
    assert chance.percent == round(expected)
    assert [protector.kind for protector in chance.protectors] == [ProtectorKind.PATRON]
    await worship_creator(session, mortal, 2, "vow")
    shielded = await kill_chance(session, rules, mortal, son)
    assert [protector.kind for protector in shielded.protectors] == [ProtectorKind.CREATOR]
    assert failed_kill_refund(_tuned(rules, take_life_refund_pct=50), 40) == 20


async def test_failed_kill_creates_legend(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _tuned(rules, take_life_base_success=0, take_life_min_chance=0, take_life_max_chance=0)
    son = await make_son(session, "Velkar", world.world.id)
    mortal = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id)
    outcome = await attempt_kill(make_context(session, tuned, 2), mortal, Killer(ActorKind.SON, son.name, son.id, son.might), "Aeron")
    assert not outcome.success and outcome.legend_id is not None
    assert trait_or(mortal, Trait.CHARISMA, 0) == 50 + rules.death.survivor_charisma_gain
    assert await EntityRepository(session).has_flag(mortal.id, EntityFlag.RETURNED_FROM_DEATH)
    immortal = await make_entity(session, "Eternal", EntityType.MORTAL, world_id=world.world.id)
    await EntityRepository(session).add_flag(immortal.id, EntityFlag.IMMORTAL, 1)
    blocked = await attempt_kill(make_context(session, rules, 2), immortal, Killer(ActorKind.SON, son.name, son.id), "Aeron")
    assert blocked.immortal and immortal.status is EntityStatus.CANON


async def test_god_death_builds_corpse_shade_order(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _tuned(rules, apostasy_chance=0)
    son = await make_son(session, "Velkar", world.world.id, essence=80)
    enemy = await make_son(session, "Iolen", world.world.id)
    await SonRepository(session).change_relation(son.id, enemy.id, -50)
    people = await make_entity(session, "Faithful", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, people.id, son.id, BondKind.WORSHIPS)
    before = world.creator.essence
    death = await god_death(make_context(session, tuned, 3), son, "fell", SonDeathCause.OTHER)
    assert son.status is SonStatus.DEAD and son.corpse_entity_id == death.corpse.id if death.corpse else False
    assert death.corpse is not None and death.corpse.engine_kind is EngineKind.GOD_CORPSE and death.corpse.location_id == world.region.id
    assert death.shade is not None and death.shade.location_id == death.corpse.id
    assert death.order is not None and await session.get(ResurrectionOrderRow, death.order.id) is not None
    assert death.loyal == 1 and death.apostates == 0
    assert world.creator.essence == before + round(80 / rules.death.dead_essence_divisor)
    assert enemy.fame == rules.death.god_death_enemy_renown
    assert await session.scalar(select(ThreadRow.id)) is not None
    assert god_lines.GOD_DEATH.key in await chronicle_keys(session)


async def test_rites_schemes_and_scatter(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _tuned(rules, apostasy_chance=0, sibling_descent_success=100)
    son = await make_son(session, "Velkar", world.world.id)
    friend = await make_son(session, "Iolen", world.world.id, essence=200)
    people = await make_entity(session, "Faithful", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, people.id, son.id, BondKind.WORSHIPS)
    ctx = make_context(session, tuned, 3)
    await god_death(ctx, son, "fell", SonDeathCause.OTHER)
    rite = await resurrection_rite(ctx, people, son, RiteKind.OFFERING)
    assert rite.contribution == round(rules.death.offering_devotion * rules.death.pilgrimage_multiplier_pct / 100)
    blood = await resurrection_rite(ctx, people, son, RiteKind.BLOOD)
    assert blood.devotion == rite.devotion + blood.contribution
    spontaneous = await resurrection_rite(ctx, people, son, RiteKind.RITE)
    assert spontaneous.contribution == round(rules.death.rite_devotion * rules.death.pilgrimage_multiplier_pct / 100)
    scheme = await sibling_scheme(ctx, friend, son, SchemeKind.DESCENT)
    assert scheme.contribution == rules.death.sibling_descent_devotion
    assert await SonRepository(session).relation(friend.id, son.id) == rules.death.sibling_scheme_relation_gain
    with pytest.raises(ValidationFailedError):
        await sibling_scheme(ctx, friend, son, SchemeKind.BARGAIN)
    scattered = await scatter_bones(ctx, friend, son)
    state = await resurrection_state(session, tuned, son, 3)
    assert state is not None and state.devotion == scheme.devotion - rules.death.scatter_bones_devotion_loss
    assert scattered.contribution == -rules.death.scatter_bones_devotion_loss


async def test_life_sacrifice_requires_people(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    ctx = make_context(session, rules, 3)
    await god_death(ctx, son, "fell", SonDeathCause.OTHER)
    mortal = await make_entity(session, "Devotee", EntityType.MORTAL, world_id=world.world.id)
    result = await resurrection_rite(ctx, mortal, son, RiteKind.LIFE)
    assert result.contribution == rules.death.self_sacrifice_devotion
    assert mortal.status is EntityStatus.DEAD


async def test_auto_resurrection_and_fading(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _tuned(rules, cult_resurrection_chance=100, resurrection_devotion_required=1, resurrection_min_epochs=0)
    son = await make_son(session, "Velkar", world.world.id)
    await god_death(make_context(session, tuned, 3), son, "fell", SonDeathCause.OTHER)
    assert epochs_until_resurrection(rules, son, 3) == rules.death.resurrection_min_epochs
    await gods_fate(make_context(session, tuned, 4, "gods_fate"))
    assert son.status is SonStatus.ACTIVE
    assert god_lines.SON_RESURRECTED.key in await chronicle_keys(session)
    corpse = await session.get(EntityRow, son.corpse_entity_id)
    assert corpse is not None and await EntityRepository(session).has_flag(corpse.id, EntityFlag.EMPTY_TOMB)
    fading = await make_son(session, "Faded", world.world.id)
    fading.existence = 1
    for epoch in range(5, 5 + rules.death.fading_death_epochs):
        await gods_fate(make_context(session, rules, epoch, "gods_fate"))
    assert fading.status is SonStatus.DEAD and fading.death_cause is SonDeathCause.FADING
    assert god_lines.FADING_ONE.key in await chronicle_keys(session)


async def test_death_engine_foreign_strike_and_rites(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _tuned(
        rules, foreign_god_smite_chance=100, take_life_min_chance=100, take_life_max_chance=100, rite_chance=100, sacrifice_chance=0, apostasy_chance=0
    )
    await ForeignGodRepository(session).create(
        ForeignGodDraft(name="Ur", world_id=world.world.id, domain_primary=Domain.SEA, power=50, stats=StatBlock.uniform(50), created_epoch=1)
    )
    victim = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id)
    son = await make_son(session, "Velkar", world.world.id)
    people = await make_entity(session, "Faithful", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, people.id, son.id, BondKind.WORSHIPS)
    await god_death(make_context(session, tuned, 3), son, "fell", SonDeathCause.OTHER)
    await death_engine(make_context(session, tuned, 4, "death_engine"))
    assert victim.status is EntityStatus.DEAD
    assert god_lines.RITE.key in await chronicle_keys(session)


async def test_death_services(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    friend = await make_son(session, "Iolen", world.world.id)
    await SonRepository(session).change_relation(son.id, friend.id, 40)
    before = world.creator.essence
    await service.kill_son(session, rules, son.id, "betrayal")
    assert son.status is SonStatus.DEAD
    assert friend.loyalty == 60 + rules.death.kill_son_loyalty_gain
    assert world.creator.essence <= before - rules.death.creator_kill_son_cost + son.essence
    with pytest.raises(ValidationFailedError):
        await service.kill_son(session, rules, son.id)
    world.creator.essence = 1000
    await service.resurrect(session, rules, son.id)
    assert son.status is SonStatus.ACTIVE
    mortal = await make_entity(session, "Ysra", EntityType.MORTAL, world_id=world.world.id)
    assert await service.grant_protection(session, rules, mortal.id)
    price = await service.kill_price(session, rules, mortal.id, son.id)
    assert price.creator_cost == rules.death.creator_take_life_cost
    outcome = await service.take_life(session, rules, mortal.id)
    assert outcome.success and mortal.status is EntityStatus.DEAD
    statuses = await service.fading_statuses(session, rules)
    assert {status.son_id for status in statuses} == {son.id, friend.id}
    restored = await service.restore_existence(session, rules, friend.id, 150)
    assert restored.existence == 100
