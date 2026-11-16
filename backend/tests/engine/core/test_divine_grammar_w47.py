from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.divine_grammar import FOREIGN_PRESETS, SON_PRESETS, VERB_SIGN
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.sons import SonPowerRow
from aerona.domain.enums.divine import DivineCost, DivineMode, DivineObject, DivineScope, DivineVerb
from aerona.domain.enums.son import PowerEffect
from aerona.engine.divine.grammar import APPLIERS, carry_presets, pay, wield
from aerona.engine.primitives.stats import stat
from tests.engine.core.factories import CoreWorld
from tests.engine.core.test_minds_w44 import at


def test_every_verb_object_and_old_gift_is_in_the_grammar() -> None:
    assert set(APPLIERS) == set(DivineObject)
    assert all(VERB_SIGN[verb] != 0 for verb in DivineVerb)
    assert SON_PRESETS and FOREIGN_PRESETS


async def test_a_wielded_blessing_raises_its_target_and_costs_essence(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    row = DivinePowerRow(holder_node_id=world.son.id, name="A Kind Hand", verb=DivineVerb.BLESS, object=DivineObject.STAT, scope=DivineScope.PERSON)
    row.object_key, row.mode, row.cost, row.cost_amount, row.cooldown, row.strength, row.domains, row.locked = (
        "prosperity",
        DivineMode.ACTIVE,
        DivineCost.ESSENCE,
        1,
        0,
        50,
        [],
        [],
    )
    session.add(row)
    world.son.essence = 10
    before = stat(world.people, "prosperity") or 0
    assert await pay(ctx, row)
    assert await wield(ctx, row, world.people.id) == 1
    assert world.son.essence == 9
    assert (stat(world.people, "prosperity") or 0) > before


async def test_old_gifts_carry_over_once(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await at(session, 3)
    session.add(SonPowerRow(son_id=world.son.id, slot=0, name="Leader of hosts", description="leads", effect=PowerEffect.WAR_LEADER))
    await session.flush()
    assert await carry_presets(ctx) == 1
    assert await carry_presets(ctx) == 0
    carried = await session.scalar(select(DivinePowerRow).where(DivinePowerRow.son_preset == PowerEffect.WAR_LEADER))
    assert carried is not None and carried.verb is DivineVerb.INSPIRE
