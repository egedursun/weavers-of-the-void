from aerona.catalog.domain_effects import DOMAIN_EFFECTS, HOOKS, SYNERGIES
from aerona.db.tables.divine import DivineWoundRow, WorldDomainHookRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.divine import DivineWoundKind, DomainHook, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.war import WarCause, WarSide, WarStatus
from aerona.domain.models.entity_stats import EventStats
from aerona.engine.divine.book import DivineBook
from aerona.engine.divine.hooks import foe_pct
from tests.engine.divine.pantheon import foreign, god, worship
from tests.engine.society.factories import Realm, context, make, mortal, settlement


def test_every_domain_has_hooks_an_activity_and_every_hook_is_used() -> None:
    assert set(DOMAIN_EFFECTS) == set(Domain)
    assert all(effect.hooks for effect in DOMAIN_EFFECTS.values())
    used = {hook for effect in DOMAIN_EFFECTS.values() for hook in effect.hooks} | {synergy.hook for synergy in SYNERGIES}
    assert used == set(DomainHook) == set(HOOKS)


async def test_the_faithful_of_a_sea_god_gain_its_hooks_and_others_do_not(realm: Realm) -> None:
    ctx = context(realm.session)
    port = await settlement(realm, "Saltmouth")
    inland = await settlement(realm, "Dryhollow")
    sea = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    await worship(realm, port, sea.id)
    table = ctx.rules.domains
    assert await ctx.hook_pct(port.id, DomainHook.SEA_CALM) == table.major_hook_pct
    assert await ctx.hook_pct(port.id, DomainHook.NAVAL_MIGHT) == table.major_hook_pct * 2 + table.synergy_pct
    assert await ctx.hook_pct(inland.id, DomainHook.SEA_CALM) == 0
    sailor = await mortal(realm, "Ketta", location_id=port.id)
    assert await ctx.hook_factor(sailor.id, DomainHook.SEA_CALM) > 1


async def test_a_fading_god_gives_less_and_a_severed_domain_falls_silent(realm: Realm) -> None:
    port = await settlement(realm, "Saltmouth")
    sea = await god(realm, "Ondra", Domain.SEA, Domain.DEATH, existence=50)
    await worship(realm, port, sea.id)
    ctx = context(realm.session)
    assert await ctx.hook_pct(port.id, DomainHook.SEA_CALM) == ctx.rules.domains.major_hook_pct / 2
    realm.session.add(DivineWoundRow(god_node_id=sea.id, kind=DivineWoundKind.SEVERED_DOMAIN, domain=Domain.SEA, cause=WoundCause.CREATOR, locked=[]))
    await realm.session.flush()
    fresh = context(realm.session)
    assert await fresh.hook_pct(port.id, DomainHook.SEA_CALM) == 0
    assert await fresh.hook_pct(port.id, DomainHook.SOUL_HOLD) > 0


async def test_a_world_can_strengthen_or_silence_a_hook(realm: Realm) -> None:
    port = await settlement(realm, "Saltmouth")
    sea = await god(realm, "Ondra", Domain.SEA, Domain.SALT)
    await worship(realm, port, sea.id)
    realm.session.add(WorldDomainHookRow(world_id=realm.world.id, domain=Domain.SEA, hook=DomainHook.SEA_CALM, pct=0))
    await realm.session.flush()
    ctx = context(realm.session)
    assert await ctx.hook_pct(port.id, DomainHook.SEA_CALM) == 0


async def test_foreign_gods_give_their_faithful_hooks_too_and_the_cap_holds(realm: Realm) -> None:
    town = await settlement(realm, "Graintown")
    old = await foreign(realm.session, realm, "Ussamar", Domain.HARVEST, power=100)
    await worship(realm, town, old.id)
    ctx = context(realm.session)
    assert await ctx.hook_pct(town.id, DomainHook.HARVEST_FLOOR) == ctx.rules.domains.major_hook_pct
    book = await DivineBook.load(realm.session, ctx.rules)
    assert book.share(old.id, DomainHook.HARVEST_FLOOR) == 1.0


async def test_fire_on_the_foe_reaches_towns_at_war_with_the_faithful(realm: Realm) -> None:
    ash = await god(realm, "Kerr", Domain.FIRE, Domain.ASH)
    attacker = await settlement(realm, "Embercourt")
    victim = await settlement(realm, "Timberfold")
    await worship(realm, attacker, ash.id)
    event = await make(realm.session, "The Burning War", EntityType.EVENT, EventStats(), world_id=realm.world.id)
    war = WarRow(event_entity_id=event.id, world_id=realm.world.id, status=WarStatus.ONGOING, cause=WarCause.DECLARED, started_epoch=1)
    realm.session.add(war)
    await realm.session.flush()
    realm.session.add_all(
        [
            WarSideRow(war_id=war.id, entity_id=attacker.id, side=WarSide.ATTACKER, joined_epoch=1, locked=[]),
            WarSideRow(war_id=war.id, entity_id=victim.id, side=WarSide.DEFENDER, joined_epoch=1, locked=[]),
        ]
    )
    await realm.session.flush()
    ctx = context(realm.session)
    assert await foe_pct(ctx, victim.id, DomainHook.FIRE_CURSE) > 0
    assert await foe_pct(ctx, attacker.id, DomainHook.FIRE_CURSE) == 0
