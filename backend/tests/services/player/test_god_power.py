import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.entity_stats import MortalStats
from aerona.events.kinds import EventKind
from aerona.rules.registry import Rules
from aerona.services.player import god_power
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, Recorder, action_kinds, bond, changed_tables, make_entity, make_son


async def test_drain_son_gains_essence_and_is_ledgered(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Velkar", world.world.id, essence=100)
    before = world.creator.essence
    outcome = await god_power.drain_son(scope, god_power.SonTarget(son_id=son.id))
    assert son.essence < 100
    assert world.creator.essence > before
    assert outcome.essence_gained == world.creator.essence - before
    assert await action_kinds(session) == [ActionKind.DRAIN_ESSENCE]
    assert {"sons", "creator"} <= await changed_tables(session, outcome.ledger_entry_id)


async def test_demote_charges_and_rejects_lowest(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    son = await make_son(session, "Iolen", world.world.id, rarity=Rarity.UNCOMMON)
    outcome = await god_power.demote_son(scope, god_power.SonTarget(son_id=son.id))
    assert son.rarity is Rarity.COMMON
    assert outcome.essence_spent == rules.god_power.demote_cost
    essence = world.creator.essence
    with pytest.raises(ValidationFailedError):
        await god_power.demote_son(scope, god_power.SonTarget(son_id=son.id))
    await session.refresh(world.creator)
    assert world.creator.essence == essence


async def test_deify_creates_son_kills_mortal_and_moves_worship(
    scope: PlayerScope, session: AsyncSession, world: PlayerWorld, recorder: Recorder, rules: Rules
) -> None:
    mortal = await make_entity(
        session,
        "Asha",
        EntityType.MORTAL,
        world_id=world.world.id,
        power_level=11,
        stats=MortalStats(hp=40, strength=90, agility=20, intellect=80, charisma=10, age=30, lifespan=70),
    )
    village = await make_entity(session, "Ashford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    await bond(session, village.id, mortal.id, BondKind.WORSHIPS)
    before = world.creator.essence
    outcome = await god_power.deify_mortal(scope, god_power.EntityTarget(entity_id=mortal.id))
    son = await session.get(SonRow, outcome.values["son_id"])
    assert son is not None and son.name == "Asha"
    assert son.rarity is Rarity.LEGENDARY
    assert son.loyalty == rules.god_power.deify_loyalty
    assert son.existence == rules.god_power.deify_existence
    assert son.current_world_id == world.world.id
    assert mortal.status is EntityStatus.DEAD
    assert await EntityRepository(session).has_flag(mortal.id, EntityFlag.DEIFIED)
    assert world.creator.essence == before - rules.god_power.deify_cost
    worship = await session.scalar(
        select(BondRow).where(
            BondRow.source_node_id == village.id, BondRow.target_node_id == son.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE
        )
    )
    assert worship is not None
    assert EventKind.NEW_SON in recorder.kinds()
    assert ActionKind.DEIFY in await action_kinds(session)


async def test_deify_refuses_non_mortal_without_cost(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    before = world.creator.essence
    with pytest.raises(ValidationFailedError):
        await god_power.deify_mortal(scope, god_power.EntityTarget(entity_id=world.region.id))
    await session.refresh(world.creator)
    assert world.creator.essence == before


async def test_world_wrath_strikes_regions(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    outcome = await god_power.world_wrath(scope, god_power.WorldWrath(world_id=world.world.id, disaster=Disaster.STORM))
    assert outcome.created_ids
    assert outcome.essence_spent == rules.god_power.world_wrath_cost


async def test_bloodline_curse_and_lift(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    root = await make_entity(session, "Brann", EntityType.MORTAL, world_id=world.world.id)
    await god_power.bloodline_curse(scope, god_power.BloodlineCurse(entity_id=root.id))
    assert await EntityRepository(session).has_flag(root.id, EntityFlag.BLOODLINE_CURSE)
    lifted = await god_power.bloodline_curse(scope, god_power.BloodlineCurse(entity_id=root.id, lift=True))
    assert lifted.ledger_entry_id is not None
    assert await action_kinds(session) == [ActionKind.LINEAGE_CURSE, ActionKind.LIFT_LINEAGE_CURSE]


async def test_devour_son(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    await god_power.devour_son(scope, god_power.DevourSon(son_id=son.id, reason="hunger"))
    assert son.status is SonStatus.DEAD
