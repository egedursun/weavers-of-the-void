from sqlalchemy import select

from aerona.catalog.powers import unlocked_power_slots
from aerona.core.random import SeededRandom
from aerona.db.tables.divine import AvatarRow, DivineStandingRow, DivineWoundRow, DomainActivityRow, GodGoalRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.sons import SonPowerRow, SonRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.divine import DivineWoundKind, DomainActivity, GoalSource, GoalState, GodGoalKind, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.son import PowerEffect, Stat
from aerona.domain.models.entity_stats import EventStats
from aerona.domain.models.stats import StatBlock
from aerona.engine.divine import control
from aerona.engine.divine.activity import income, tend_domain_economy
from aerona.engine.divine.avatars import avatar_cycles, manifest
from aerona.engine.divine.goals import pursue_goals
from aerona.engine.divine.lineage import inherited_domains, inherited_stats
from aerona.engine.divine.standing import mean_neglect, tally_epoch, tend_standing
from aerona.engine.divine.wounds import avatar_slain, heal_wounds, inflict, name_exposure, sanity_ceiling, strike, worst
from aerona.engine.primitives.faith import has_unlocked_power
from aerona.rules.registry import Rules
from tests.engine.divine.pantheon import god, worship
from tests.engine.society.factories import Realm, context, make, settlement, tuned


async def test_a_war_god_earns_essence_from_battles_in_its_worlds(realm: Realm) -> None:
    war = await god(realm, "Kerr", Domain.WAR, Domain.BLOOD)
    town = await settlement(realm, "Embercourt")
    await worship(realm, town, war.id)
    for index in range(4):
        battle = await make(realm.session, f"Battle {index}", EntityType.EVENT, EventStats(), world_id=realm.world.id, birth_epoch=3)
        battle.engine_kind = EngineKind.BATTLE
    await realm.session.flush()
    before = war.essence
    ctx = context(realm.session, epoch=3)
    assert await tend_domain_economy(ctx) >= 2
    rows = list(await realm.session.scalars(select(DomainActivityRow).where(DomainActivityRow.god_node_id == war.id)))
    battles = next(row for row in rows if row.activity is DomainActivity.BATTLES)
    assert battles.count == 4 and battles.essence == income(ctx.rules, 4)
    assert war.essence > before


async def test_a_god_without_an_aim_takes_one_and_reaching_it_rewards_it(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    ctx = context(realm.session, tuned(son_goals={"choose_chance": 100}))
    await pursue_goals(ctx)
    goals = list(await realm.session.scalars(select(GodGoalRow).where(GodGoalRow.god_node_id == sea.id)))
    assert len(goals) == 1 and goals[0].state is GoalState.ACTIVE and goals[0].source is GoalSource.ENGINE
    for row in goals:
        await realm.session.delete(row)
    await realm.session.flush()
    aim = await control.set_goal(context(realm.session), sea.id, GodGoalKind.BE_WORSHIPPED, amount=1)
    xp = sea.xp
    await worship(realm, await settlement(realm, "Saltmouth"), sea.id)
    await pursue_goals(context(realm.session, tuned(son_goals={"choose_chance": 0})))
    assert aim.state is GoalState.DONE and aim.progress == 100 and sea.xp > xp


async def test_a_rebellious_aim_makes_a_rebel_and_a_held_god_is_left_alone(realm: Realm) -> None:
    rebel = await god(realm, "Varr", Domain.LIES, Domain.SHADOW)
    rebel.loyalty = 10
    aim = await control.set_goal(context(realm.session), rebel.id, GodGoalKind.REBEL)
    token = HELD_SCOPE.set(HeldScope(None, frozenset({rebel.id})))
    try:
        await pursue_goals(context(realm.session))
    finally:
        HELD_SCOPE.reset(token)
    assert aim.state is GoalState.ACTIVE and not rebel.rebel
    rebel.rebel = True
    await pursue_goals(context(realm.session))
    assert aim.state is GoalState.DONE


async def test_answered_prayers_kindle_love_and_silence_breeds_neglect(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    sea.current_world_id = realm.far_region.world_id
    town = await settlement(realm, "Saltmouth")
    await worship(realm, town, sea.id)
    realm.session.add(
        MessageRow(epoch=2, sender_node_id=town.id, recipient_node_id=sea.id, intent=MessageIntent.PRAYER, text="hear us", answered=True, answered_epoch=3)
    )
    realm.session.add(MessageRow(epoch=2, sender_node_id=town.id, recipient_node_id=sea.id, intent=MessageIntent.PRAYER, text="hear us", answered=False))
    await realm.session.flush()
    await tend_standing(context(realm.session, epoch=3))
    row = await realm.session.get(DivineStandingRow, (town.id, sea.id))
    assert row is not None and row.love > 0 and row.neglect > 0
    assert await mean_neglect(context(realm.session), sea.id) == row.neglect


async def test_a_prayer_answered_after_its_epoch_counts_as_answered_and_a_fresh_one_waits(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    town = await settlement(realm, "Saltmouth")
    await worship(realm, town, sea.id)
    realm.session.add(
        MessageRow(epoch=2, sender_node_id=town.id, recipient_node_id=sea.id, intent=MessageIntent.PRAYER, text="hear us", answered=True, answered_epoch=3)
    )
    realm.session.add(MessageRow(epoch=3, sender_node_id=town.id, recipient_node_id=sea.id, intent=MessageIntent.PRAYER, text="hear us", answered=False))
    await realm.session.flush()
    tally = (await tally_epoch(context(realm.session, epoch=3), {sea.id})).tallies[(town.id, sea.id)]
    assert (tally.answered, tally.unanswered) == (1, 0)


async def test_a_beaten_god_may_be_wounded_and_its_wounds_bite(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    rival = await god(realm, "Kerr", Domain.WAR, Domain.BLOOD)
    ctx = context(realm.session, tuned(divine_wounds={"wound_chance": 100}))
    assert await strike(ctx, sea, rival.id, WoundCause.DUEL, 10) is not None
    name = await inflict(ctx, sea, DivineWoundKind.STOLEN_NAME, WoundCause.CREATOR, severity=50)
    void = await inflict(ctx, sea, DivineWoundKind.VOID_WOUND, WoundCause.CREATOR, severity=50)
    assert name is not None and void is not None
    deepest = await worst(realm.session, sea.id, DivineWoundKind.STOLEN_NAME)
    assert deepest >= name.severity == 50
    assert await name_exposure(realm.session, sea.id, 40) == 1 - deepest * 40 / 100 / 100
    assert await sanity_ceiling(realm.session, sea.id, 60) == 70
    before = name.healed
    await heal_wounds(context(realm.session))
    assert name.healed > before


async def test_severed_domains_take_power_slots(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    sea.level = 30
    ctx = context(realm.session)
    slots = unlocked_power_slots(ctx.rules, sea.level)
    realm.session.add(SonPowerRow(son_id=sea.id, slot=min(slots), name="Spring", description="", effect=PowerEffect.ESSENCE_SPRING))
    await realm.session.flush()
    assert await has_unlocked_power(realm.session, ctx.rules, sea, PowerEffect.ESSENCE_SPRING)
    for _ in slots:
        realm.session.add(DivineWoundRow(god_node_id=sea.id, kind=DivineWoundKind.SEVERED_DOMAIN, domain=Domain.SEA, cause=WoundCause.CREATOR, locked=[]))
    await realm.session.flush()
    assert not await has_unlocked_power(realm.session, ctx.rules, sea, PowerEffect.ESSENCE_SPRING)


async def test_a_mortal_form_walks_wins_peoples_and_its_death_shatters_the_god(realm: Realm) -> None:
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    town = await settlement(realm, "Saltmouth")
    ctx = context(realm.session, tuned(avatars={"preach_chance": 100}))
    avatar = await manifest(ctx, sea, town)
    assert await realm.session.get(AvatarRow, avatar.id) is not None
    assert await avatar_cycles(ctx) == 1
    standing = await realm.session.get(DivineStandingRow, (town.id, sea.id))
    assert standing is not None and standing.awe > 0
    wound = await avatar_slain(ctx, avatar.id)
    assert wound is not None and wound.kind is DivineWoundKind.SHATTERED_MANIFESTATION
    assert await realm.session.get(AvatarRow, avatar.id) is None
    try:
        await manifest(ctx, sea, town)
    except Exception as error:
        assert "shattered" in str(error)
    else:
        raise AssertionError("a shattered god took a mortal form")
    dead = await realm.session.get(EntityRow, avatar.id)
    assert dead is not None and dead.status is EntityStatus.CANON


def test_a_child_of_two_sons_takes_the_mean_of_their_stats_and_a_domain_from_each() -> None:
    first = SonRow(domain_primary=Domain.SEA, domain_secondary=Domain.STORM)
    second = SonRow(domain_primary=Domain.FIRE, domain_secondary=Domain.CRAFT)
    for parent, value in ((first, 40), (second, 80)):
        for stat in Stat:
            setattr(parent, stat.value, value)
    rules = Rules()
    stats = inherited_stats(rules, SeededRandom.for_epoch(1, 1, "child"), StatBlock.uniform(10), [first, second])
    spread = rules.avatars.inheritance_deviation
    assert all(60 - spread <= stats.get(stat) <= 60 + spread for stat in Stat)
    one, two = inherited_domains(SeededRandom.for_epoch(1, 1, "child"), (Domain.LOVE, Domain.LIFE), [first, second])
    assert one in first.domains and two in second.domains
