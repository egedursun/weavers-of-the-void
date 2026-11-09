import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.repositories.sons import PowerDraft, SonRepository
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.society import AddictionRow
from aerona.db.tables.warfare import CaptiveRow, TributeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.son import PowerEffect, SonDeathCause
from aerona.domain.enums.war import CaptiveStatus, TributeStatus
from aerona.domain.models.stats import StatBlock
from aerona.engine.gods.devotion import RiteKind, SchemeKind
from aerona.engine.gods.god_death import god_death
from aerona.engine.services.war import take_captive
from aerona.rules.registry import Rules
from aerona.services.gods import cosmic_economy as economy_service
from aerona.services.player import assignments, catalog, cosmic_orders, death, diplomacy, god_power, interventions, warfare
from aerona.services.player.interventions import GodPunishmentKind
from aerona.services.player.scope import PlayerScope
from tests.engine.gods.factories import make_context
from tests.services.player.factories import PlayerWorld, action_kinds, add_world, bond, make_entity, make_son


async def _foreign(session: AsyncSession, world: PlayerWorld, power: int = 50) -> int:
    god = await ForeignGodRepository(session).create(
        ForeignGodDraft(name="Ur", world_id=world.world.id, domain_primary=Domain.SEA, power=power, stats=StatBlock.uniform(50), created_epoch=1)
    )
    return god.id


async def test_failed_suppression_does_not_count_as_a_suppression(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    son.rebel = True
    son.will, son.strength, son.level = 100, 100, 50
    await interventions.punish(scope, interventions.Punish(son_id=son.id, kind=GodPunishmentKind.SUPPRESS))
    kinds = list(await session.scalars(select(ActionRecordRow.kind)))
    assert ActionKind.SUPPRESS_REBELLION not in kinds and ActionKind.SUPPRESS_FAILED in kinds


async def test_captive_actions_resolve_by_the_captive_entity_id(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    captor = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    prisoner = await make_entity(session, "Kharun", EntityType.MORTAL, world_id=world.world.id)
    home = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await take_captive(make_context(session, scope.rules, 2), captor, prisoner, None, description="raid", home_id=home.id)
    await warfare.free(scope, warfare.CaptiveTarget(captive_id=prisoner.id))
    row = await session.scalar(select(CaptiveRow))
    assert row is not None and row.status is CaptiveStatus.RESCUED
    with pytest.raises(NotFoundError):
        await warfare.free(scope, warfare.CaptiveTarget(captive_id=prisoner.id))


async def test_ransom_resolves_by_the_captive_entity_id(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    captor = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    prisoner = await make_entity(session, "Kharun", EntityType.MORTAL, world_id=world.world.id)
    home = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await take_captive(make_context(session, scope.rules, 2), captor, prisoner, None, description="raid", home_id=home.id)
    await warfare.ransom(scope, warfare.CaptiveTarget(captive_id=prisoner.id))
    row = await session.scalar(select(CaptiveRow))
    assert row is not None and row.status is not CaptiveStatus.HELD


async def test_tribute_is_forgiven_by_the_pays_tribute_bond_id(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    payer = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    receiver = await make_entity(session, "Bralk", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await warfare.tribute(scope, warfare.Tribute(payer_id=payer.id, receiver_id=receiver.id))
    row = await session.scalar(select(TributeRow))
    assert row is not None and row.bond_id is not None
    await warfare.forgive(scope, warfare.TributeTarget(bond_id=row.bond_id))
    await session.refresh(row)
    assert row.status is TributeStatus.ENDED
    with pytest.raises(NotFoundError):
        await warfare.forgive(scope, warfare.TributeTarget(bond_id=row.bond_id))


async def test_sibling_scheme_and_scatter_actions(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    dead = await make_son(session, "Velkar", world.world.id)
    friend = await make_son(session, "Iolen", world.world.id, essence=500)
    await god_death(make_context(session, rules, 2), dead, "fell", SonDeathCause.OTHER)
    outcome = await death.sibling_scheme(scope, death.SiblingScheme(sibling_id=friend.id, son_id=dead.id, kind=SchemeKind.RITE))
    assert outcome.values["contribution"] == rules.death.sibling_rite_devotion
    assert friend.essence == 500 - rules.death.sibling_rite_cost
    scattered = await death.scatter_bones(scope, death.ScatterBones(sibling_id=friend.id, son_id=dead.id))
    assert scattered.values["contribution"] == -rules.death.scatter_bones_devotion_loss
    assert await action_kinds(session) == [ActionKind.SIBLING_SCHEME, ActionKind.SCATTER_BONES]
    with pytest.raises(ValidationFailedError):
        await death.sibling_scheme(scope, death.SiblingScheme(sibling_id=friend.id, son_id=friend.id, kind=SchemeKind.RITE))


async def test_force_rebellion_action(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    await god_power.force_rebellion(scope, god_power.ForceRebellion(son_id=son.id, manifesto="No more chains"))
    assert son.rebel
    with pytest.raises(ValidationFailedError):
        await god_power.force_rebellion(scope, god_power.ForceRebellion(son_id=son.id, manifesto="Again"))
    with pytest.raises(ValidationFailedError):
        other = await make_son(session, "Iolen", world.world.id)
        await god_power.force_rebellion(scope, god_power.ForceRebellion(son_id=other.id, manifesto="  "))


async def test_economy_actions_run_and_cure_addiction(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    await cosmic_orders.run_resource_mechanics(scope, cosmic_orders.Empty())
    await cosmic_orders.run_cosmic_economy(scope, cosmic_orders.Empty())
    people = await make_entity(session, "Eaters", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    resource = await make_entity(session, "Vein", EntityType.RESOURCE, world_id=world.world.id, location_id=world.region.id)
    session.add(AddictionRow(community_entity_id=people.id, resource_entity_id=resource.id, owned_epochs=9, addicted_since_epoch=1, withdrawal_since_epoch=2))
    await session.flush()
    cured = await cosmic_orders.cure_addiction(scope, cosmic_orders.AddictionCure(entity_id=people.id, resource_id=resource.id))
    assert cured.values["cured"] is True
    row = await session.get(AddictionRow, (people.id, resource.id))
    assert row is not None and row.addicted_since_epoch is None
    again = await cosmic_orders.cure_addiction(scope, cosmic_orders.AddictionCure(entity_id=people.id, resource_id=resource.id))
    assert again.values["cured"] is False
    assert not await economy_service.cure_addiction(session, scope.rules, people.id, resource.id)


async def test_new_actions_are_in_the_catalogue() -> None:
    for action_id in ("sibling:scheme", "sibling:scatter", "rebellion:force", "economy:resources", "economy:cosmic", "addiction:cure"):
        assert catalog.action(action_id).sync is not None


async def test_distribution_preview_lists_scores_and_next_mover(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    other = await add_world(session, "Kesh")
    await make_entity(session, "Keshfolk", EntityType.PEOPLE, world_id=other.id)
    first = await make_son(session, "Velkar", world.world.id)
    second = await make_son(session, "Iolen", world.world.id)
    people = await make_entity(session, "Hearthfolk", EntityType.PEOPLE, world_id=world.world.id)
    await bond(session, people.id, first.id, BondKind.WORSHIPS)
    preview = await assignments.distribution_preview(scope)
    assert [item.son_id for item in preview.candidates] == [second.id, first.id]
    assert preview.next_son_id == second.id
    assert preview.godless_world_ids == [other.id]
    second.manually_assigned_epoch = world.cosmos.epoch
    guarded = await assignments.distribution_preview(scope)
    assert guarded.next_son_id == first.id


async def test_foreign_god_drain_and_kill_actions(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    god_id = await _foreign(session, world)
    drained = await god_power.drain_foreign_god(scope, god_power.ForeignGodTarget(god_id=god_id))
    god = await session.get(ForeignGodRow, god_id)
    assert god is not None and god.power < 50
    assert drained.essence_gained > 0
    follower = await make_entity(session, "Faithful", EntityType.PEOPLE, world_id=world.world.id)
    await bond(session, follower.id, god_id, BondKind.WORSHIPS)
    world.creator.essence = 5000
    killed = await god_power.kill_foreign_god(scope, god_power.KillForeignGod(god_id=god_id, reason="hubris"))
    assert god.status is ForeignGodStatus.DEAD
    assert killed.essence_spent > 0
    with pytest.raises(ValidationFailedError):
        await god_power.drain_foreign_god(scope, god_power.ForeignGodTarget(god_id=god_id))


async def test_strip_power_and_manifest_actions(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    await SonRepository(session).set_powers(son.id, [PowerDraft("Tide", "Moves water", PowerEffect.TIRELESS)])
    gained = await god_power.strip_power(scope, god_power.StripPower(son_id=son.id, slot=0))
    assert gained.essence_spent == rules.god_power.strip_power_cost
    assert await SonRepository(session).powers(son.id) == []
    with pytest.raises(ValidationFailedError):
        await god_power.strip_power(scope, god_power.StripPower(son_id=son.id, slot=0))
    mortal = await make_entity(session, "Asha", EntityType.MORTAL, world_id=world.world.id)
    shown = await god_power.manifest(scope, god_power.Manifest(entity_id=mortal.id, words="Rise."))
    assert shown.essence_spent == rules.god_power.manifest_cost
    with pytest.raises(ValidationFailedError):
        await god_power.manifest(scope, god_power.Manifest(entity_id=mortal.id, words=" "))


async def test_manual_rite_action(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    people = await make_entity(session, "Faithful", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, people.id, son.id, BondKind.WORSHIPS)
    await god_death(make_context(session, rules, 2), son, "fell", SonDeathCause.OTHER)
    outcome = await diplomacy.order_rite(scope, diplomacy.Rite(entity_id=people.id, son_id=son.id, kind=RiteKind.PRAYER))
    assert "Velkar" in outcome.message
    assert ActionKind.RESURRECTION_RITE in await action_kinds(session)
    with pytest.raises(NotFoundError):
        await diplomacy.order_rite(scope, diplomacy.Rite(entity_id=people.id, son_id=999999, kind=RiteKind.PRAYER))
