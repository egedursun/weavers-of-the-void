import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.son import Stat
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import Atmosphere, Discovery, Gravity, WorldType
from aerona.rules.registry import Rules
from aerona.services.player import cosmic, creation, foreign_gods, world_edits
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, add_world, make_son


async def test_edit_world_physics_and_validation(scope: PlayerScope, session: AsyncSession, world: PlayerWorld, rules: Rules) -> None:
    son = await make_son(session, "Velkar", world.world.id)
    await world_edits.edit_world(
        scope,
        world_edits.EditWorld(
            world_id=world.world.id,
            name="Orvael Prime",
            world_type=WorldType.OCEAN,
            atmosphere=Atmosphere.DENSE,
            leakage=40,
            mortal_agents=3,
            guardian_son_id=son.id,
        ),
    )
    assert world.world.name == "Orvael Prime"
    assert world.world.world_type is WorldType.OCEAN
    assert world.world.terrain_sea == rules.world_terrain.ocean_sea_pct / 100
    assert world.world.leakage == 40 and world.world.mortal_agents == 3
    assert world.world.patron_son_id == son.id and not world.world.patron_automatic
    with pytest.raises(ValidationFailedError):
        await world_edits.edit_world(scope, world_edits.EditWorld(world_id=world.world.id, time_factor=0))
    with pytest.raises(ValidationFailedError):
        await world_edits.edit_world(scope, world_edits.EditWorld(world_id=world.world.id, mortal_agents=rules.god_hand.mortal_agents_per_world_cap + 1))


async def test_a_new_world_type_brings_its_forced_physics(scope: PlayerScope, world: PlayerWorld) -> None:
    await world_edits.edit_world(scope, world_edits.EditWorld(world_id=world.world.id, world_type=WorldType.GREENHOUSE))
    assert world.world.atmosphere is Atmosphere.TOXIC
    await world_edits.edit_world(scope, world_edits.EditWorld(world_id=world.world.id, world_type=WorldType.SUPER_EARTH, atmosphere=Atmosphere.DENSE))
    assert world.world.gravity is Gravity.HIGH and world.world.atmosphere is Atmosphere.DENSE


async def test_forget_and_remember_world(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    other = await add_world(session, "Kesh")
    await cosmic.open_route(scope, cosmic.OpenRoute(first_world_id=world.world.id, second_world_id=other.id, method=TravelMethod.ANCIENT_GATE))
    await world_edits.edit_world(scope, world_edits.EditWorld(world_id=other.id, discovery=Discovery.FORGOTTEN))
    assert other.discovery is Discovery.FORGOTTEN
    outcome = await world_edits.edit_world(scope, world_edits.EditWorld(world_id=other.id, discovery=Discovery.KNOWN))
    assert other.discovery is Discovery.KNOWN
    assert "came out of the mist" in outcome.message
    with pytest.raises(ValidationFailedError):
        await world_edits.edit_world(scope, world_edits.EditWorld(world_id=world.world.id, discovery=Discovery.FORGOTTEN))


async def test_place_and_edit_foreign_god(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await creation.place_foreign_god(scope, creation.PlaceForeignGod(world_id=world.world.id, name="Old Moru", power=40))
    god_id = outcome.values["god_id"]
    assert isinstance(god_id, int)
    await foreign_gods.edit_foreign_god(
        scope,
        foreign_gods.EditForeignGod(
            god_id=god_id,
            stance=-300,
            status=ForeignGodStatus.DEAD,
            stats={Stat.WILL: 500},
            personality={"fear": "the light"},
            powers=(foreign_gods.ForeignPower(name="Shield", effect=ForeignGodPowerEffect.SHIELD),),
        ),
    )
    god = await foreign_gods.guards.foreign_god(session, god_id)
    assert god.stance == -100 and god.status is ForeignGodStatus.DEAD and god.death_epoch == world.cosmos.epoch
    assert god.will == 100 and god.personality is not None and god.personality.fear == "the light"
    with pytest.raises(ValidationFailedError):
        await foreign_gods.edit_foreign_god(scope, foreign_gods.EditForeignGod(god_id=god_id, personality={"mood": "x"}))


async def test_edit_foreign_god_depth_and_wake(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    outcome = await creation.place_foreign_god(scope, creation.PlaceForeignGod(world_id=world.world.id, name="Old Moru", power=40))
    god_id = outcome.values["god_id"]
    assert isinstance(god_id, int)
    depth = foreign_gods.ForeignDepth(history=" Born of ash. ", secrets=("the first fire", " "), desire="silence")
    await foreign_gods.edit_foreign_god(scope, foreign_gods.EditForeignGod(god_id=god_id, depth=depth, status=ForeignGodStatus.DEAD))
    god = await foreign_gods.guards.foreign_god(session, god_id)
    assert god.depth is not None and god.depth.history == "Born of ash." and god.depth.secrets == ("the first fire",) and god.depth.desire == "silence"
    await foreign_gods.edit_foreign_god(scope, foreign_gods.EditForeignGod(god_id=god_id, status=ForeignGodStatus.AWAKE))
    assert god.status is ForeignGodStatus.AWAKE and god.death_epoch is None and god.awakening_pressure == 0
