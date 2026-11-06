import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.cosmic_state import AddictionImmunityRow
from aerona.db.tables.society import AddictionRow
from aerona.db.tables.sons import SonPowerRow
from aerona.domain.enums.affliction import CureKind, PackageKind, Transmission
from aerona.domain.enums.body import Consciousness, InjuryKind, NerveDamage, TreatmentStep
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.son import PowerEffect
from aerona.engine.body.afflictions import STAGE_HOLD
from aerona.engine.gods.economy import ADDICTION_HOLD
from aerona.services.player import afflictions, body, cosmic_orders, god_power
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity, make_son


async def test_afflictions_are_given_reshaped_held_cured_and_unmade(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    bearer = await make_entity(session, "Orrin", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    given = await afflictions.give(scope, afflictions.GiveAffliction(bearer_id=bearer.id, package=PackageKind.VOID_TAINT, transmission=Transmission.CONTACT))
    row = await session.get(AfflictionRow, given.values["affliction_id"])
    assert row is not None and row.stage == 1
    with pytest.raises(ValidationFailedError):
        await afflictions.give(scope, afflictions.GiveAffliction(bearer_id=bearer.id, package=PackageKind.VOID_TAINT, transmission=Transmission.CONTACT))
    await afflictions.edit(scope, afflictions.EditAffliction(affliction_id=row.id, stage=2, transmission=Transmission.GAZE))
    assert row.stage == 2 and row.transmission is Transmission.GAZE
    with pytest.raises(ValidationFailedError):
        await afflictions.edit(scope, afflictions.EditAffliction(affliction_id=row.id, stage=9))
    await afflictions.hold(scope, afflictions.HoldAffliction(affliction_id=row.id))
    assert STAGE_HOLD in row.locked
    await afflictions.cure_action(scope, afflictions.CureAffliction(affliction_id=row.id, how=CureKind.RITE))
    assert row.cured_epoch is not None
    await afflictions.delete(scope, afflictions.AfflictionTarget(affliction_id=row.id))
    assert await session.get(AfflictionRow, row.id) is None


async def test_blood_consciousness_and_wounds_are_set_held_and_treated(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    bearer = await make_entity(session, "Lysa", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    struck = await body.maim(scope, body.Maim(bearer_id=bearer.id, part="left_leg", kind=InjuryKind.DEEP_CUT, severity=4))
    await body.set_body_value(scope, body.SetBodyValue(bearer_id=bearer.id, field="blood", value=40))
    await body.set_body_value(scope, body.SetBodyValue(bearer_id=bearer.id, field="teeth", value=99))
    shape = await session.get(BodyRow, bearer.id)
    assert shape is not None and shape.blood == 40 and "blood" in shape.locked and shape.teeth == 32
    await body.set_consciousness(scope, body.SetConsciousness(bearer_id=bearer.id, consciousness=Consciousness.DIZZY))
    assert shape.consciousness is Consciousness.DIZZY and "consciousness" in shape.locked
    injury = await session.get(InjuryRow, struck.values["injury_id"])
    assert injury is not None
    await body.edit_injury(scope, body.EditInjury(injury_id=injury.id, bleeding=20, nerve=NerveDamage.MOTOR, treatments=[TreatmentStep.CLEAN]))
    assert injury.bleeding == 20 and injury.nerve is NerveDamage.MOTOR and injury.treatments == ["clean"]
    await body.treat_injury(scope, body.TreatInjury(injury_id=injury.id, step=TreatmentStep.SUTURE))
    assert injury.bleeding == 0 and "suture" in injury.treatments
    with pytest.raises(ValidationFailedError):
        await body.treat_injury(scope, body.TreatInjury(injury_id=injury.id, step=TreatmentStep.SUTURE))


async def test_cravings_immunities_and_son_powers_are_controlled(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Harrowgate", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    leaf = await make_entity(session, "Dreamleaf", EntityType.RESOURCE, world_id=world.world.id, location_id=world.region.id)
    pair = {"entity_id": town.id, "resource_id": leaf.id}
    await cosmic_orders.set_addiction(scope, cosmic_orders.AddictionSet(**pair, hold=True))
    craving = await session.get(AddictionRow, (town.id, leaf.id))
    assert craving is not None and craving.addicted_since_epoch is not None and ADDICTION_HOLD in craving.locked
    await cosmic_orders.set_addiction(scope, cosmic_orders.AddictionSet(**pair, remove=True))
    assert await session.get(AddictionRow, (town.id, leaf.id)) is None
    await cosmic_orders.set_immunity(scope, cosmic_orders.ImmunitySet(**pair, recovered_epoch=3))
    immunity = await session.get(AddictionImmunityRow, (town.id, leaf.id))
    assert immunity is not None and immunity.recovered_epoch == 3
    await cosmic_orders.set_immunity(scope, cosmic_orders.ImmunitySet(**pair, immune=False))
    assert await session.get(AddictionImmunityRow, (town.id, leaf.id)) is None
    son = await make_son(session, "Avel", world.world.id)
    slot = 2
    existing = await session.get(SonPowerRow, (son.id, slot))
    if existing is not None:
        await session.delete(existing)
        await session.flush()
    with pytest.raises(ValidationFailedError):
        await god_power.set_son_power(scope, god_power.SonPower(son_id=son.id, slot=slot, name="Tidecall"))
    await god_power.set_son_power(scope, god_power.SonPower(son_id=son.id, slot=slot, name="Tidecall", effect=PowerEffect.CURSER))
    power = await session.get(SonPowerRow, (son.id, slot))
    assert power is not None and power.name == "Tidecall"
    await god_power.set_son_power(scope, god_power.SonPower(son_id=son.id, slot=slot, remove=True))
    assert await session.get(SonPowerRow, (son.id, slot)) is None
